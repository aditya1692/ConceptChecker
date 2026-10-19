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
        prompt = get_case_one_prompt()

        response = process_by_llm(prompt, message, history)

        print("LLM Response:", response)
        response_split = response.strip().split(",")
        missed_step_index = int(response_split[0])
        recited_indicator_index = int(response_split[1])

        if missed_step_index != -1 or recited_indicator_index != -1:
            current_status = Status.CASE_ONE_FOLLOW_UP
            return "It seems there are some issues with your answer. Let's discuss them."
        else:
            current_status = Status.CASE_TWO
            return "Great! Let's move on to the next case."
    
    elif current_status == Status.CASE_ONE_FOLLOW_UP:
        # Handle CASE_ONE_FOLLOW_UP logic here
        pass

    elif current_status == Status.CASE_TWO:
        # Handle CASE_TWO logic here
        pass

    elif current_status == Status.RESULT:
        # Handle RESULT logic here
        pass

def get_followUp_prompt(missed_step_index, recited_indicator_index):
    prompt = ""

    if (missed_step_index != -1):
        missed_part = golden_dataSet[selected_dataSet_Index]["opening_case"]["expected_steps"][missed_step_index]
        prompt += f"The user missed the following expected step in the answer: {missed_part}\n draft a follow up question, Ask them to work it out, not define it. Push with why, and what breaks without it."

    if (recited_indicator_index != -1):
        prompt += f"The user recited the indicator at index {recited_indicator_index}.\n"

    return prompt

def get_case_one_prompt():
        expected_steps = golden_dataSet[selected_dataSet_Index]["opening_case"]["expected_steps"]
        recited_indicators = golden_dataSet[selected_dataSet_Index]["opening_case"]["recited_indicators"]

        expected_steps_sub_prompt = f"Here is a list of required parts in an ideal answer {expected_steps}, flag index of any missing part if you don't find similar content in the user's response\n"
        recited_indicators_sub_prompt = f"reciting indicators to look for in answer: {recited_indicators}, flag index of any similar indicator found in the user's response\n"
        logic_sub_prompt = "Evaluate the user's response carefully. Use similar meaning matching instead of exact string matching. \n"
        output_format_sub_prompt = 'return your evaluation strictly in comma seperated string in this format: missed_step_index, recited_indicator_index. Nothing else. Default value -1 for both if nothing is missing or found\n'


        prompt = logic_sub_prompt  + expected_steps_sub_prompt + recited_indicators_sub_prompt+ output_format_sub_prompt + ", here is the user answer:"
        print("Generated prompt for CASE_ONE:", prompt)
        return prompt

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
    
    print(r.json()["choices"][0]["message"]["reasoning"])
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