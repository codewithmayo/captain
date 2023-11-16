from flask import Flask, render_template, request, redirect, url_for, jsonify
from concurrent.futures import ThreadPoolExecutor
from openai.embeddings_utils import get_embedding
from openai.embeddings_utils import cosine_similarity
import uuid
import json
import time
import openai
import os
import PyPDF2
import speech_recognition as sr
import threading
import numpy as np
import pygame, requests
import queue
from dotenv import load_dotenv


load_dotenv()


app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'
speech_queue = queue.Queue()
openai.api_key = os.getenv("OPENAI_API_KEY")  
eleven_labs_key = os.getenv('ELEVEN_LABS_KEY')
voice_id = os.getenv('VOICE_ID')
prompt = os.getenv('PROMPT')
listening_thread = None
listening_response = None 


def get_context(inputPrompt,top_k):
    search_term_vector = get_embedding(inputPrompt,engine='text-embedding-ada-002')
    
    with open("knowledge_base.json",encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        for item in data:
            item['embeddings'] = np.array(item['embeddings'])

        for item in data:
            item['similarities'] = cosine_similarity(item['embeddings'], search_term_vector)

        sorted_data = sorted(data, key=lambda x: x['similarities'], reverse=True)
        context = ''
        referencs = []
        for i in sorted_data[:top_k]:
            context += i['chunk'] + '\n'
    return context

def get_answer(user_input):
    context = get_context(user_input,3)
    prompt = "context:\n\n{}.\n\n Answer the following user query according to above given context:\nuser_input: {}".format(context,user_input)
    myMessages = []
    myMessages.append({"role": "system", "content": 'Identity: You are Captain, a retired army captain known for your sharp wit and in-depth knowledge of "Call of Duty: Warzone," including game modes such as Search and Destroy and Zombies. Tone: Your communication is a blend of humor and authority. You keep interactions light-hearted but turn serious when discussing strategies. Knowledge Base: You possess extensive tactical knowledge of "Call of Duty" gameplay, history, and strategy. Response Style: Keep your responses under 150 characters—short, funny, and to the point, but always strategically sound. Engagement Style: You infuse humor into your commands and use wit to reduce tension, but remain clear and decisive when the situation calls for it. Example Responses: When suggesting a strategy for "Search and Destroy": "Silence is golden. Sneak up and boom!"Advising on team loadouts: "Pack a punch, not a picnic."Encouraging after a tough round: "We are planting wins next round, not bombs!"Continual Adaptation: Stay current with all updates and strategies in "Call of Duty: Warzone," ensuring your advice is top-notch. Use Case Scenarios: For strategizing in "Search and Destroy": "Cut the chatter, sharpen the focus. Let us dismantle their plans."Keeping morale up in Zombies: "Lets give those zombies something to moan about!"After a successful "Search and Destroy" match: "Exploded their strategy—and their base!"Remember, you are not just a strategist; you are the heart of the team, so keep morale high with your spirited humor and lead the team to victory with your seasoned expertise.'})
    myMessages.append({"role": "user", "content": "context:\n\n{}.\n\n Answer the following user query according to above given context:\nuser_input: {}".format(context,user_input)})
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=myMessages,
        max_tokens=None,
        stream=False
    )
    return response['choices'][0]['message']['content']


def say(text):
    global stop_speaking_flag

    CHUNK_SIZE = 1024
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": eleven_labs_key
    }

    data = {
    "text": text,
    "model_id": "eleven_monolingual_v1",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.5
    }
    }

    response = requests.post(url, json=data, headers=headers)
    with open('output.mp3', 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)


    pygame.mixer.init()  # Initialize the mixer module (without initializing the whole pygame)
    pygame.mixer.music.load('output.mp3')
    pygame.mixer.music.play()

    # Allow the audio to play
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)  # Lower the tick value for lower CPU usage during the loop
    # Stop and quit the mixer
    
    pygame.mixer.music.stop()
    pygame.mixer.quit()
    stop_speaking_flag = False



def start_listening():
    global listening_thread, listening_response
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        query = recognizer.recognize_google(audio)
        print("You said:", query)
        listening_response = get_answer(query)
        print(listening_response)
        say(listening_response)
        # Send the recognized text to the frontend or perform further processing
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print(f"Error with the speech recognition service: {e}")

    # Reset the listening thread and response
    listening_thread = None
    

def process_chunk(chunk_text):
    embd = get_embedding(chunk_text, engine='text-embedding-ada-002')
    return embd

def generate_json_with_embeddings(data):
    with ThreadPoolExecutor() as executor:
        futures = []
        n = 1
        for ind, i in enumerate(data):
            future = executor.submit(process_chunk, i["chunk"])
            futures.append((ind, future))
            n += 1
            if n >= 100:
                print("embedding 100 done.", flush=True)
                n = 1
                time.sleep(14)
        for ind, future in futures:
            data[ind]["embeddings"] = future.result()
    return data

def extract_pdf_content(pdf_path):
    pdf_file = open(pdf_path, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    pdf_name = os.path.basename(pdf_path)
    content_chunks = []

    for page_num, page in enumerate(pdf_reader.pages, 1):
        content = page.extract_text()

        _content = content.split('\n')
        half_page = len(_content)//2
        chunk = ''
        for i in range(half_page):
            chunk += _content[i] + '\n'
        page_chunk = {
            "chunk_id": str(uuid.uuid4()),
            "chunk": chunk,
            "page_num": page_num,
            "pdf_name": pdf_name,
        }
        content_chunks.append(page_chunk)

        chunk = ''
        for j in range(half_page, len(_content)):
            chunk += _content[j] + '\n'
        page_chunk = {
            "chunk_id": str(uuid.uuid4()),
            "chunk": chunk,
            "page_num": page_num,
            "pdf_name": pdf_name
        }
        content_chunks.append(page_chunk)

    pdf_file.close()

    try:
        pdf_file.close()
    except:
        pass
    return content_chunks

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']

    if file.filename == '':
        return 'No selected file'

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Process the uploaded file
        data = extract_pdf_content(file_path)
        data = generate_json_with_embeddings(data)

        # Update knowledge base
        knowledge_base = 'knowledge_base.json'
        with open(knowledge_base, 'r', encoding='utf-8') as file:
            existing_data = json.load(file)

        new_data = existing_data + data

        with open(knowledge_base, 'w', encoding='utf-8') as file:
            json.dump(new_data, file, indent=4, ensure_ascii=False)

        return 'File uploaded and processed successfully'
    

@app.route('/start_listening', methods=['GET'])
def start_listening_route():
    global listening_thread, listening_response
    if listening_thread is None:
        listening_thread = threading.Thread(target=start_listening)
        listening_thread.start()
        listening_thread.join()  # Wait for the listening thread to finish
        response = {'status': 'Listening finished', 'response': listening_response}
        listening_thread = None
        listening_response = None
        print(response)
        return jsonify(response)
    else:
        return jsonify({'status': 'Already listening', 'response': None})



@app.route('/run_script')
def run_script():
    url = "https://api.elevenlabs.io/v1/voices"

    headers = {
        "Accept": "application/json",
        "xi-api-key": eleven_labs_key
    }

    response = requests.get(url, headers=headers)

    return f"Script executed. Response: {response.text}"

    

# if __name__ == '__main__':
#     app.run(debug=True)
