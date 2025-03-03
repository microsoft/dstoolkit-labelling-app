"""
Ground truth handler for labelling applications.
"""

import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional

from config import PREDICTIONS_COLUMN, QUESTION_COLUMN
from webpage.form_handling.custom_form_handler import CustomFormHandler
from webpage.manage_user_session import get_results_key
from webpage.labelling_consts import (
    SELECTED_ROW_ID,
    SYN_CORRECTED_QUESTION,
    SYN_DATA,
    SYN_GT_ANSWER,
    SYN_QA_RELEVANCE,
)


class GroundTruthHandler(CustomFormHandler):
    """Handler for ground truth forms."""

    def __init__(self, question_hash: str):
        """
        Initialize a ground truth form handler.

        Args:
            question_hash (str): The hash of the current question
        """
        super().__init__(
            form_id="ground_truth",
            form_title="Ground Truth",
            data_key=SYN_DATA,
            persistence_key=f"ground_truth_{question_hash}",
        )
        self.question_hash = question_hash

    def render_ground_truth_form(self) -> Dict[str, Any]:
        """Render the ground truth form fields."""
        # Get current row and dataframe
        df = st.session_state.get(get_results_key())
        if df is None:
            return {}

        ind = df.index[st.session_state[SELECTED_ROW_ID]]

        # Set default values from dataframe
        relevance = df.loc[ind].get(SYN_QA_RELEVANCE, True)
        irrelevant = st.checkbox(
            "The question is not relevant",
            key=f"syn_gt_qa_irrelevant_{self.question_hash}",
            value=False if relevance else True,
        )

        question = df.loc[ind].get(SYN_CORRECTED_QUESTION)
        if pd.isna(question):
            question = df.loc[ind].get(QUESTION_COLUMN, "")

        corrected_question = st.text_area(
            "Rewrite the question (Optional)",
            key=f"syn_corrected_question_{self.question_hash}",
            value=question,
        )

        gt_code = df.loc[ind].get(SYN_GT_ANSWER)
        if pd.isna(gt_code):
            gt_code = df.loc[ind].get(PREDICTIONS_COLUMN, "")

        gt_answer = st.text_area(
            "Provide Ground Truth (Optional)",
            key=f"syn_gt_code_{self.question_hash}",
            value=gt_code,
        )

        # Return the collected data
        return {
            SYN_QA_RELEVANCE: not irrelevant,
            SYN_CORRECTED_QUESTION: corrected_question,
            SYN_GT_ANSWER: gt_answer,
        }

    def save_to_dataframe(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Save the ground truth data to the dataframe.

        Args:
            df (Optional[pd.DataFrame]): The dataframe to modify. If None, retrieves from session state.

        Returns:
            pd.DataFrame: The updated dataframe
        """
        if df is None:
            df = st.session_state.get(get_results_key())

        if df is None:
            st.error("Results dataframe not found in session state")
            return pd.DataFrame()

        # Get current row index
        ind = df.index[st.session_state[SELECTED_ROW_ID]]

        # Get form data
        result = {
            SYN_QA_RELEVANCE: True
            if not st.session_state[f"syn_gt_qa_irrelevant_{self.question_hash}"]
            else False,
            SYN_CORRECTED_QUESTION: st.session_state[
                f"syn_corrected_question_{self.question_hash}"
            ],
            SYN_GT_ANSWER: st.session_state[f"syn_gt_code_{self.question_hash}"],
        }

        # Store in session state
        if SYN_DATA not in st.session_state:
            st.session_state[SYN_DATA] = {}
        st.session_state[SYN_DATA][self.question_hash] = result

        # Update dataframe
        for k, v in result.items():
            df.loc[ind, k] = v

        st.toast("✔️ Ground truth saved!")
        return df
