import os

import gradio as gr
import requests
from dotenv import load_dotenv

load_dotenv()


def check_response(message, history):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers = {
            "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}"
        },

        json={
        "messages": [
            {
                "role": "user", 
                "content": "user typed: "+ message
            }
        ],
        "model": "openai/gpt-oss-120b"
    })

    print(r.json())
    

    return r.json()["choices"][0]["message"]["content"]


gr.ChatInterface(
    fn=check_response, 
).launch()