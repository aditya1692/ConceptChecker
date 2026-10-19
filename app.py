import os

import gradio as gr
import requests
import json
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


    return r.json()["choices"][0]["message"]["content"]


def get_examples():
    ideas = []
    # Open the file and parse the JSON data
    with open('golden_pairs.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    for ideaEntry in data:
        ideas.append(ideaEntry["idea"])

    return ideas

gr.ChatInterface(
    fn=check_response,
    examples=get_examples()
).launch()