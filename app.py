import os

import gradio as gr
import requests
import json
from dotenv import load_dotenv
from enum import Enum

load_dotenv()

golden_dataSet = []
selected_dataSet_Index = -1

class Status(Enum):
    IDLE = 1
    CASE_ONE = 2
    CASE_ONE_FOLLOW_UP = 3
    CASE_TWO = 4
    RESULT = 5

current_status = Status.IDLE

def check_response(message, history):
    global current_status

    if current_status == Status.IDLE:
        set_selected_dataSet_Index(message)

        if selected_dataSet_Index == -1:
            return "Idea not found in the dataset. Please select an idea from the examples."

        current_status = Status.CASE_ONE
        return golden_dataSet[selected_dataSet_Index]["opening_case"]["question"]

    elif current_status == Status.CASE_ONE:
        # Handle CASE_ONE logic here
        pass
    elif current_status == Status.CASE_ONE_FOLLOW_UP:
        # Handle CASE_ONE_FOLLOW_UP logic here
        pass

    elif current_status == Status.CASE_TWO:
        # Handle CASE_TWO logic here
        pass

    elif current_status == Status.RESULT:
        # Handle RESULT logic here
        pass


def set_selected_dataSet_Index(message):
    global selected_dataSet_Index
    for i, entry in enumerate(golden_dataSet):
        if entry["idea"] == message:
            selected_dataSet_Index = i
            break

def process_by_llm(prompt, message, history):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers = {
                "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}"
            },
    
        json={
            "messages": [
            {
               "role": "user", 
               "content": prompt + "  "+ message
            }
        ],

        "model": "openai/gpt-oss-120b"
    })
    
    
    return r.json()["choices"][0]["message"]["content"]

def init_goldenDataSet():
    global golden_dataSet
    with open('golden_pairs.json', 'r', encoding='utf-8') as file:
        golden_dataSet = json.load(file)

    print("Golden data set initialized with", len(golden_dataSet), "entries.")

def get_examples():
    ideas = []

    for ideaEntry in golden_dataSet:
        ideas.append(ideaEntry["idea"])

    return ideas

def init():
    init_goldenDataSet()


init_goldenDataSet()

gr.ChatInterface(
    title="Concept Checker",
    description="Check your ideas against the golden dataset.",
    fn=check_response,
    examples=get_examples()
).launch()