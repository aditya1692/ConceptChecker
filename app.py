import os

import gradio as gr
import requests
import json
from dotenv import load_dotenv
from enum import Enum
from datetime import datetime

load_dotenv()

golden_dataSet = []
selected_dataSet_Index = -1

class Status(Enum):
    IDLE = 1
    CASE_ONE = 2
    CASE_ONE_FOLLOW_UP = 3
    CASE_TWO = 4

current_status = Status.IDLE

RESULTS_FILE = "results.json"

follow_up_context = {}
session_result = {}

def check_response(message, history):
    global current_status, follow_up_context, session_result

    if current_status == Status.IDLE:
        set_selected_dataSet_Index(message)

        if selected_dataSet_Index == -1:
            return "Idea not found in the dataset. Please select an idea from the examples."

        data = golden_dataSet[selected_dataSet_Index]
        session_result = {
            "idea_id": data["id"],
            "idea": data["idea"],
            "opening_case": None,
            "follow_up": None,
            "fresh_case": None,
            "passed": None
        }

        current_status = Status.CASE_ONE
        return data["opening_case"]["question"]

    elif current_status == Status.CASE_ONE:
        prompt = get_case_prompt("opening_case")

        response = process_by_llm(prompt, message, history)

        print("LLM Response:", response)
        missed_step_index, recited_indicator_index = parse_case_judgement(response)
        session_result["opening_case"] = get_case_result("opening_case", message, missed_step_index, recited_indicator_index)

        if missed_step_index != -1 or recited_indicator_index != -1:
            print("Going for follow-up with missed_step_index:", missed_step_index, "and recited_indicator_index:", recited_indicator_index)

            current_status = Status.CASE_ONE_FOLLOW_UP
            followUpPrompt = get_followUp_prompt(missed_step_index, recited_indicator_index, message)
            followUp_question = process_by_llm(followUpPrompt, "", history)

            follow_up_context = {
                "missed_step_index": missed_step_index,
                "recited_indicator_index": recited_indicator_index,
                "question": followUp_question
            }
            return followUp_question
        else:
            print("No missed steps or recited indicators, moving to CASE_TWO.")

            current_status = Status.CASE_TWO
            return golden_dataSet[selected_dataSet_Index]["fresh_case"]["question"]
    
    elif current_status == Status.CASE_ONE_FOLLOW_UP:
        prompt = get_followUp_review_prompt()

        response = process_by_llm(prompt, message, history)

        print("LLM Response for follow-up review:", response)
        gap_closed = judge_followUp(response)
        print("Follow-up gap closed:", gap_closed)

        session_result["follow_up"] = {
            "question": follow_up_context["question"],
            "answer": message,
            "gap_closed": gap_closed
        }

        current_status = Status.CASE_TWO
        return golden_dataSet[selected_dataSet_Index]["fresh_case"]["question"]

    elif current_status == Status.CASE_TWO:
        prompt = get_case_prompt("fresh_case")

        response = process_by_llm(prompt, message, history)

        print("LLM Response for CASE_TWO:", response)
        missed_step_index, recited_indicator_index = parse_case_judgement(response)
        session_result["fresh_case"] = get_case_result("fresh_case", message, missed_step_index, recited_indicator_index)

        # The fresh case is the second try on a new scenario, so it decides the overall result
        session_result["passed"] = session_result["fresh_case"]["passed"]
        save_session_result()

        current_status = Status.IDLE
        return get_result_message()

def get_followUp_prompt(missed_step_index, recited_indicator_index, prev_message):
    data = golden_dataSet[selected_dataSet_Index]
    prompt = f'LEARNER\'S ANSWER:\n"{prev_message}"\n\n'

    if recited_indicator_index != -1:
        phrase = data["recited_indicators"][recited_indicator_index]

        with open("FollowUp_Guide_RecitedPhrase.txt", "r") as f:
                prompt += f.read() + "\n"

        prompt = prompt.replace("%%learner_answer%%", prev_message).replace("%%recited_phrase%%", phrase)

    if missed_step_index != -1:
        missed = data["opening_case"]["expected_steps"][missed_step_index]

        with open("FollowUp_Guide_MissingPart.txt", "r") as f:
                prompt += f.read() + "\n"

        prompt = prompt.replace("%%learner_answer%%", prev_message).replace("%%missing_part%%", missed)

    print("Follow-up prompt generated:", prompt)

    return prompt

def get_followUp_review_prompt():
    data = golden_dataSet[selected_dataSet_Index]
    missed_step_index = follow_up_context["missed_step_index"]
    recited_indicator_index = follow_up_context["recited_indicator_index"]

    missed = data["opening_case"]["expected_steps"][missed_step_index] if missed_step_index != -1 else "(not asked, return -1)"
    phrase = data["recited_indicators"][recited_indicator_index] if recited_indicator_index != -1 else "(not asked, return -1)"

    prompt = (
        f"You are grading a learner's reply to a follow-up question.\nFOLLOW-UP QUESTION: {follow_up_context['question']}\n\n"
        f"1. Does the reply convey this step in the learner's own words: {missed}\n"
        f"2. Does the reply explain the concrete mechanism (what goes wrong, who, how) behind this phrase, instead of repeating it: {phrase}\n"
        "return your evaluation strictly in comma seperated string in this format: step_present, phrase_explained. Nothing else. "
        "Use 1 for yes, 0 for no, -1 if not asked\n"
        "\nhere is the learner's reply:"
    )
    print("Generated prompt for follow-up review:", prompt)
    return prompt

def parse_case_judgement(response):
    missed_step_index, recited_indicator_index = [int(v) for v in response.strip().split(",")]
    return missed_step_index, recited_indicator_index

def get_case_result(case_key, answer, missed_step_index, recited_indicator_index):
    data = golden_dataSet[selected_dataSet_Index]

    return {
        "answer": answer,
        "missed_step": data[case_key]["expected_steps"][missed_step_index] if missed_step_index != -1 else None,
        "recited_phrase": data["recited_indicators"][recited_indicator_index] if recited_indicator_index != -1 else None,
        "passed": missed_step_index == -1 and recited_indicator_index == -1
    }

def save_session_result():
    results = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)

    results.append({"timestamp": datetime.now().isoformat(timespec="seconds"), **session_result})

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("Session result saved:", session_result)

def get_result_message():
    fresh = session_result["fresh_case"]

    if session_result["passed"]:
        return "You've got it: your reasoning held up on a new scenario. Pick another idea to continue."

    message = "Not quite yet on the new scenario."
    # Name the kind of gap only; the step and phrase stay in results.json so a retry can't be memorised
    if fresh["missed_step"]:
        message += "\nYour answer missed part of the reasoning."
    if fresh["recited_phrase"]:
        message += "\nYou used a stock phrase instead of explaining what actually goes wrong."
    return message + "\nPick an idea to try again."

def judge_followUp(response):
    step_present, phrase_explained = [int(v) for v in response.strip().split(",")]

    # Gap is closed only if every part that was flagged in the first answer now passes
    missed_ok = follow_up_context["missed_step_index"] == -1 or step_present == 1
    recited_ok = follow_up_context["recited_indicator_index"] == -1 or phrase_explained == 1
    return missed_ok and recited_ok

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

    selected_dataSet_Index = -1
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