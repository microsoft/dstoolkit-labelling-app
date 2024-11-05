from utils.logger import logger
from webpage.labelling_consts import (
    END_TIME_MS,
    FILE_SEED,
    SEED,
    SELECTED_ROW_ID,
    START_TIME_MS,
)

import pandas as pd
import streamlit as st


import random


def get_results_key() -> str:
    """
    Generates a results key for the given user name and file.
    Returns:
        str: The generated results key.
    """
    return f"results_{st.session_state.get('file_seed')}"


def init_session_state_variables() -> None:
    """
    Initializes the session state variables.

    Returns:
        None
    """
    if SEED not in st.session_state:
        logger.info("Initializing session state variables...")
        st.session_state[SEED] = random.randint(0, int(1e9))  # nosec
        st.session_state[SELECTED_ROW_ID] = 0
        st.session_state[get_results_key()] = None


def upd_state_on_file_reload(df: pd.DataFrame) -> None:
    """
    Update the session state variables when a file is reloaded.
    Parameters:
        df (pd.DataFrame): The DataFrame containing the file data.
    Returns:
        None
    """

    st.session_state[SELECTED_ROW_ID] = 0
    # File was reloaded, reset the seed
    st.session_state[FILE_SEED] = random.randint(0, int(1e9))  # nosec
    results_key = get_results_key()
    st.session_state[results_key] = df.copy()
    st.session_state[results_key][START_TIME_MS] = None
    st.session_state[results_key][END_TIME_MS] = None


def get_loading_key() -> str:
    """
    Generates a loading key for the given user name and file.
    Returns:
        str: The generated loading key.
    """
    return f"load_latest_results_{st.session_state.get('user_name')}_{st.session_state.get('file_seed')}"


def get_current_results() -> str | None:
    """
    Retrieves the current results from the session state and returns them as a JSON-encoded string.

    Returns:
        str | None: The JSON-encoded string of the current results, or None if the results are not available.
    """
    results = st.session_state.get(get_results_key())
    if results is None:
        return None
    return results.to_json().encode("utf-8")
