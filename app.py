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
        prompt = get_case_prompt("opening_case")

        response = process_by_llm(prompt, message, history)

        print("LLM Response:", response)
        response_split = response.strip().split(",")
        missed_step_index = int(response_split[0])
        recited_indicator_index = int(response_split[1])

        if missed_step_index != -1 or recited_indicator_index != -1:
            print("Going for follow-up with missed_step_index:", missed_step_index, "and recited_indicator_index:", recited_indicator_index)

            current_status = Status.CASE_ONE_FOLLOW_UP
            followUpPrompt = get_followUp_prompt(missed_step_index, recited_indicator_index, message)
            return process_by_llm(followUpPrompt, "", history)
        else:
            print("No missed steps or recited indicators, moving to CASE_TWO.")

            current_status = Status.CASE_TWO
            return golden_dataSet[selected_dataSet_Index]["fresh_case"]["question"]
    
    elif current_status == Status.CASE_ONE_FOLLOW_UP:
         current_status = Status.CASE_TWO
         return golden_dataSet[selected_dataSet_Index]["fresh_case"]["question"]

    elif current_status == Status.CASE_TWO:
        prompt = get_case_prompt("fresh_case")

        response = process_by_llm(prompt, message, history)

        print("LLM Response for CASE_TWO:", response)

        current_status = Status.RESULT
        return "Thank you for your response. You have completed both cases."

    elif current_status == Status.RESULT:
        # Handle RESULT logic here
        pass

def get_followUp_prompt(missed_step_index, recited_indicator_index, prev_message):
    data = golden_dataSet[selected_dataSet_Index]
    prompt = f'LEARNER\'S ANSWER:\n"{prev_message}"\n\n'

    if recited_indicator_index != -1:
        phrase = data["recited_indicators"][recited_indicator_index]

        with open("FollowUp_Guide_RecitedPhrase.txt", "r") as f:
                prompt += f.read() + "\n"

        prompt = prompt.replace("%%learner_answer%%", prev_message).replace("%%recited_indicator%%", phrase)

    if missed_step_index != -1:
        missed = data["opening_case"]["expected_steps"][missed_step_index]

        with open("FollowUp_Guide_MissingPart.txt", "r") as f:
                prompt += f.read() + "\n"

        prompt = prompt.replace("%%learner_answer%%", prev_message).replace("%%missed_part%%", missed)

    print("Follow-up prompt generated:", prompt)

    return prompt

def get_case_prompt(case_key):
        case = golden_dataSet[selected_dataSet_Index][case_key]
        expected_steps = case["expected_steps"]
        recited_indicators = golden_dataSet[selected_dataSet_Index]["recited_indicators"]

        context_sub_prompt = f"You are grading a learner's answer.\nQUESTION: {case['question']}\nREFERENCE ANSWER: {case['expected_answer']}\n\n"
        expected_steps_sub_prompt = (
            f"Here is a list of reasoning steps a complete answer should contain: {expected_steps}\n"
            "A step counts as present if the learner's answer conveys its idea in their own words, applied to this scenario. It does not need the same wording. "
            "Flag a step only if its idea is absent. If several are missing, return the lowest index.\n"
        )
        recited_indicators_sub_prompt = (
            f"Here is a list of recited buzzword phrases: {recited_indicators}\n"
            "Flag one only if the learner uses that phrase (or a near-identical buzzword) as their justification INSTEAD of explaining the mechanism. "
            "If the learner explains why (what can go wrong, on which machine, who can change what), do NOT flag it, even if the topic is related (e.g. explaining tampering is not reciting 'for security').\n"
        )
        logic_sub_prompt = "The reference answer is complete: an answer equivalent to it must get -1, -1.\n"
        output_format_sub_prompt = 'return your evaluation strictly in comma seperated string in this format: missed_step_index, recited_indicator_index. Nothing else. Default value -1 for both if nothing is missing or found\n'

        prompt = context_sub_prompt + expected_steps_sub_prompt + recited_indicators_sub_prompt + logic_sub_prompt + output_format_sub_prompt + "\nhere is the learner's answer:"
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
    
    print("\n LLM Reasoning: " + r.json()["choices"][0]["message"]["reasoning"])
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