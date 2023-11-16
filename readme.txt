    
    
                        CHANGING THE API KEYS and Voices

1. You can change the api keys of openai and Eleven Labs and voice too by going to .env file. 
2. Don't change the name of the of the variable only change the value next to "equal" sign.
3. To change the voice you will need to replace the voice id.





                CHANGING PERSONALITY OF THE AI 

1. Go to app.py file
2. Press CTRL + F  and paste "myMessages.append"

3.You will see this type of line in the results --->   myMessages.append({"role": "system", "content": 'Identity: You are Captain, a retired army....

4. The prompt is starting from the "Identity" word and all to the end until you see another "myMessages.append"
5. You can get an idea from the current prompt that is set like where its starting and where its ending.

6. The prompt is wrapped inside single quotation marks ( ‘ ’ ) so you can't use these single quotation marks 
inside your prompt. If you do you will get errors. You can use double quotation marks ( "" ) to highlight things
inside prompt.

7. Be very careful doing this even a single type could cause app failure.


                    GETTING A NEW VOICE ID 


1.You will see a button "Get Voices" in the app. 
2. Click on the button and you will see a bunch of horrible looking text.
3. Press CTRL + F and type the name of the voice.
4. On the left side of the name you will see a 'voice_id'
5. Copy the voice_id and replace it with the voice id in " .env" file to change the voice



