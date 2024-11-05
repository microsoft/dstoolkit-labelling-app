from config import LABELLING_DATETIME_FORMAT
from datetime import datetime
from webpage.labelling_consts import (
    ANSWER_IS_BETTER,
    END_TIME_MS,
    ERROR,
    ERROR_ANALYSIS,
    ERROR_DATA,
    ERROR_DESCRIPTION,
    ERROR_SNIPPET,
    FEEDBACK,
    FEEDBACK_DATA,
    LABEL_QUALITY,
    QUESTION_HASH,
    SELECTED_ROW_ID,
    SYN_CORRECTED_QUESTION,
    SYN_DATA,
    SYN_GT_ANSWER,
    SYN_QA_RELEVANCE,
)
from webpage.manage_user_session import get_results_key


import pandas as pd
import streamlit as st


from typing import Callable, Optional, cast


def save_new_gt(question_hash: str) -> None:
    """
    Saves the user feedback for a question without a ground truth.

    Parameters:
        result (Dict): A dictionary containing the user feedback for the question without a ground truth.

    Returns:
        None
    """
    df = cast(pd.DataFrame, st.session_state.get(get_results_key()))
    ind = df.index[st.session_state[SELECTED_ROW_ID]]
    result = {
        SYN_QA_RELEVANCE: True
        if not st.session_state[f"syn_gt_qa_irrelevant_{question_hash}"]
        else False,
        SYN_CORRECTED_QUESTION: st.session_state[
            f"syn_corrected_question_{question_hash}"
        ],
        SYN_GT_ANSWER: st.session_state[f"syn_gt_code_{question_hash}"],
    }
    if SYN_DATA not in st.session_state:
        st.session_state[SYN_DATA] = {}
    st.session_state[SYN_DATA][question_hash] = result
    for k, v in result.items():
        df.loc[ind, k] = v

    st.toast("✔️ Data is saved!")


def save_error(question_hash: str, result: Optional[Callable] = None) -> None:
    """
    Saves the error information in the session state DataFrame.

    Args:
        result (Callable): Callable which retrieves the error information to be saved.

    Returns:
        None
    """
    df = cast(pd.DataFrame, st.session_state.get(get_results_key()))
    ind = df.index[st.session_state[SELECTED_ROW_ID]]

    results = {}

    if result is None:
        results = {
            ERROR_SNIPPET: st.session_state[f"error_snippet_{question_hash}"],
            ERROR: st.session_state[f"error_{question_hash}"],
            ERROR_DESCRIPTION: st.session_state[f"error_description_{question_hash}"],
            QUESTION_HASH: question_hash,
        }
    else:
        results = result()

    if ERROR_DATA not in st.session_state:
        st.session_state[ERROR_DATA] = {}
    st.session_state[ERROR_DATA][question_hash] = results

    if ERROR_ANALYSIS not in df.columns:
        df[ERROR_ANALYSIS] = None
    if df.loc[ind, ERROR_ANALYSIS] is None:
        df.loc[ind, ERROR_ANALYSIS] = [results]
    else:
        df.loc[ind, ERROR_ANALYSIS].append(results)
    df.loc[ind, END_TIME_MS] = datetime.now().strftime(LABELLING_DATETIME_FORMAT)
    st.toast("✔️ Error information saved!")


def save_user_feedback(question_hash: str) -> None:
    """
    Saves the user feedback for a specific result.

    Parameters:
    result (Dict): A dictionary containing the user feedback for a specific result.

    Returns:
    None
    """
    df = cast(pd.DataFrame, st.session_state.get(get_results_key()))
    ind = df.index[st.session_state[SELECTED_ROW_ID]]
    result = {
        LABEL_QUALITY: st.session_state[f"quality_{question_hash}"],
        FEEDBACK: st.session_state[f"feedback_{question_hash}"],
        ANSWER_IS_BETTER: st.session_state[f"answer_is_better_{question_hash}"],
    }
    if FEEDBACK_DATA not in st.session_state:
        st.session_state[FEEDBACK_DATA] = {}
    st.session_state[FEEDBACK_DATA][question_hash] = result
    for k, v in result.items():
        df.loc[ind, k] = v
        df.loc[ind, END_TIME_MS] = datetime.now().strftime(LABELLING_DATETIME_FORMAT)

    st.toast("✔️ Quality information saved!")
