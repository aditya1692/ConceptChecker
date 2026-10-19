import gradio as gr
from requests import Request


def random_response(message, history):
    return "you typed: "+ message


gr.ChatInterface(
    fn=random_response, 
).launch()