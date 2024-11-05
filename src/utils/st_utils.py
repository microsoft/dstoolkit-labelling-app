from asyncio import run_coroutine_threadsafe
import asyncio
from threading import Thread
import streamlit as st
import os


@st.cache_resource(show_spinner=False)
def create_loop():
    loop = asyncio.new_event_loop()
    thread = Thread(target=loop.run_forever)
    thread.start()
    return loop, thread


def run_async(coroutine):
    # Fix to run async functions in Streamlit
    if "event_loop" not in st.session_state:
        st.session_state["event_loop"], thread = create_loop()
    return run_coroutine_threadsafe(coroutine, st.session_state.event_loop)


# Load assets
curr_file_path = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(curr_file_path, "../", "assets")
logo_icon_path = os.path.join(assets_path, "logo.svg")
if os.path.exists(logo_icon_path):
    LOGO_ICON = logo_icon_path
else:
    LOGO_ICON = None

instructions_path = os.path.join(assets_path, "labelling_instructions.md")
if os.path.exists(instructions_path):
    with open(instructions_path, "r") as file:
        LABELLING_INSTRUCTIONS = file.read()
else:
    LABELLING_INSTRUCTIONS = None
