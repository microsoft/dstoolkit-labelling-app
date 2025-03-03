"""
Specialized form handlers for the labelling app.
"""

import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from config import LABELLING_DATETIME_FORMAT, PREDICTIONS_COLUMN, QUESTION_COLUMN
from webpage.labelling_consts import (
    ANSWER_IS_BETTER,
    END_TIME_MS,
    ERROR,
    ERROR_ANALYSIS,
    ERROR_CATEGORIES_LIST,
    ERROR_CATEGORIES_MARKDOWN,
    ERROR_DATA,
    ERROR_DESCRIPTION,
    ERROR_SNIPPET,
    FEEDBACK,
    FEEDBACK_DATA,
    LABEL_QUALITY,
    QUALITY_LABELS,
    QUESTION_HASH,
    SELECTED_ROW_ID,
    SYN_CORRECTED_QUESTION,
    SYN_DATA,
    SYN_GT_ANSWER,
    SYN_QA_RELEVANCE,
)
from webpage.form_handling.custom_form_handler import CustomFormHandler
from webpage.manage_user_session import get_results_key


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

        st.toast("✔️ Error information saved!")
        return df


class ErrorFeedbackHandler(CustomFormHandler):
    """Handler for error feedback forms."""

    def __init__(self, question_hash: str):
        """
        Initialize an error feedback form handler.

        Args:
            question_hash (str): The hash of the current question
        """
        super().__init__(
            form_id="error_feedback",
            form_title="Error Feedback",
            data_key=ERROR_DATA,
            persistence_key=f"error_feedback_{question_hash}",
        )
        self.question_hash = question_hash

    def render_error_feedback_form(self) -> Dict[str, Any]:
        """Render the error feedback form fields."""
        st.text_area(
            "Part of the answer",
            key=f"error_snippet_{self.question_hash}",
            help="Enter the part of the answer that you want to provide feedback on.",
        )

        st.multiselect(
            "Error Category",
            ERROR_CATEGORIES_LIST,
            key=f"error_{self.question_hash}",
            help=ERROR_CATEGORIES_MARKDOWN,
        )

        st.text_area(
            "(Optional) Error Description",
            key=f"error_description_{self.question_hash}",
        )

        # Return the collected data
        return {
            ERROR_SNIPPET: st.session_state[f"error_snippet_{self.question_hash}"],
            ERROR: st.session_state[f"error_{self.question_hash}"],
            ERROR_DESCRIPTION: st.session_state[
                f"error_description_{self.question_hash}"
            ],
            QUESTION_HASH: self.question_hash,
        }

    def save_to_dataframe(
        self, result_callback: Optional[Callable] = None
    ) -> pd.DataFrame:
        """
        Save the error data to the dataframe.

        Args:
            result_callback (Optional[Callable]): Optional callback to modify result data

        Returns:
            pd.DataFrame: The updated dataframe
        """
        df = st.session_state.get(get_results_key())
        if df is None:
            st.error("Results dataframe not found in session state")
            return pd.DataFrame()

        # Get current row index
        ind = df.index[st.session_state[SELECTED_ROW_ID]]

        # Get form data
        results = {}
        if result_callback is None:
            # Get data directly from session state keys
            results = {
                ERROR_SNIPPET: st.session_state[f"error_snippet_{self.question_hash}"],
                ERROR: st.session_state[f"error_{self.question_hash}"],
                ERROR_DESCRIPTION: st.session_state[
                    f"error_description_{self.question_hash}"
                ],
                QUESTION_HASH: self.question_hash,
            }
        else:
            # Use the callback to get the data
            results = result_callback()

        # Store in global error data
        if ERROR_DATA not in st.session_state:
            st.session_state[ERROR_DATA] = {}
        st.session_state[ERROR_DATA][self.question_hash] = results

        # Update error analysis column
        if ERROR_ANALYSIS not in df.columns:
            df[ERROR_ANALYSIS] = None

        # Add the error analysis entry
        if df.loc[ind, ERROR_ANALYSIS] is None:
            df.loc[ind, ERROR_ANALYSIS] = [results]
        else:
            df.loc[ind, ERROR_ANALYSIS].append(results)

        # Update end time
        df.loc[ind, END_TIME_MS] = datetime.now().strftime(LABELLING_DATETIME_FORMAT)
        st.toast("✔️ Quality information saved!")

        return df


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

        st.toast("✔️ Data is saved!")
        return df
