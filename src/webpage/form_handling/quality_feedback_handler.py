"""
Quality feedback handler for labelling applications.
"""

import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional

from config import LABELLING_DATETIME_FORMAT
from webpage.form_handling.custom_form_handler import CustomFormHandler
from webpage.manage_user_session import get_results_key
from webpage.labelling_consts import (
    ANSWER_IS_BETTER,
    END_TIME_MS,
    FEEDBACK,
    FEEDBACK_DATA,
    LABEL_QUALITY,
    QUALITY_LABELS,
    SELECTED_ROW_ID,
)


class QualityFeedbackHandler(CustomFormHandler):
    """Handler for quality feedback forms."""

    def __init__(self, question_hash: str):
        """
        Initialize a quality feedback form handler.

        Args:
            question_hash (str): The hash of the current question
        """
        super().__init__(
            form_id="quality_feedback",
            form_title="Quality Feedback",
            data_key=FEEDBACK_DATA,
            persistence_key=f"quality_feedback_{question_hash}",
        )
        self.question_hash = question_hash

    def render_quality_feedback_form(self) -> Dict[str, Any]:
        """Render the quality feedback form fields."""
        # Get current row and dataframe
        df = st.session_state.get(get_results_key())
        if df is None:
            return {}

        ind = df.index[st.session_state[SELECTED_ROW_ID]]

        # Set default values from dataframe if available
        default_quality = df.loc[ind].get(LABEL_QUALITY)
        if pd.isna(default_quality):
            default_quality = None

        default_feedback = df.loc[ind].get(FEEDBACK)
        if pd.isna(default_feedback):
            default_feedback = None

        default_answer_is_better = df.loc[ind].get(ANSWER_IS_BETTER)
        if pd.isna(default_answer_is_better):
            default_answer_is_better = None

        # Render form fields
        st.write("General answer quality:")
        quality = st.select_slider(
            "",
            list(QUALITY_LABELS.values()),
            key=f"quality_{self.question_hash}",
            value=default_quality,
        )

        feedback = st.text_area(
            "Feedback (Optional)",
            key=f"feedback_{self.question_hash}",
            value=default_feedback,
        )

        answer_is_better = st.checkbox(
            "Model answer is better than provided Ground Truth",
            key=f"answer_is_better_{self.question_hash}",
            value=default_answer_is_better,
        )

        # Return the collected data
        return {
            LABEL_QUALITY: quality,
            FEEDBACK: feedback,
            ANSWER_IS_BETTER: answer_is_better,
        }

    def save_to_dataframe(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Save the feedback data to the dataframe.

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

        # Get form data from session state
        result = st.session_state.get(self.persistence_key, {})
        if not result:
            return df

        # Store in global feedback data
        if FEEDBACK_DATA not in st.session_state:
            st.session_state[FEEDBACK_DATA] = {}
        st.session_state[FEEDBACK_DATA][self.question_hash] = result

        # Update dataframe
        for k, v in result.items():
            df.loc[ind, k] = v

        # Update end time
        df.loc[ind, END_TIME_MS] = datetime.now().strftime(LABELLING_DATETIME_FORMAT)

        st.toast("✔️ Quality information saved!")
        return df
