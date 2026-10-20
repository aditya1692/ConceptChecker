import os

import gradio as gr
import requests

# The backend (index.py) owns golden_pairs.json; start it first with: uvicorn index:app
BACKEND_URL = os.environ.get("BACKEND_URL", "https://conceptchecker.vercel.app")

def check_response(message, history, request: gr.Request):
    r = requests.post(
        f"{BACKEND_URL}/api/check",
        # session_hash keeps each browser tab's conversation separate on the backend
        json={"session_id": request.session_hash, "workflow": message}
    )
    r.raise_for_status()

    return r.json()["check"]

def get_examples():
    r = requests.get(f"{BACKEND_URL}/api/ideas")
    r.raise_for_status()

    return r.json()

gr.ChatInterface(
    title="Concept Checker",
    description="Check your ideas against the golden dataset.",
    fn=check_response,
    examples=get_examples()
).launch()
