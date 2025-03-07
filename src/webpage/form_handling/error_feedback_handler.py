"""
Error feedback handler for labelling applications.
"""

import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from config import LABELLING_DATETIME_FORMAT
from webpage.form_handling.custom_form_handler import CustomFormHandler
from webpage.manage_user_session import get_results_key
from webpage.labelling_consts import (
    END_TIME_MS,
    ERROR,
    ERROR_ANALYSIS,
    ERROR_CATEGORIES_LIST,
    ERROR_CATEGORIES_MARKDOWN,
    ERROR_DATA,
    ERROR_DESCRIPTION,
    ERROR_SNIPPET,
    QUESTION_HASH,
    SELECTED_ROW_ID,
)


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
        st.toast("✔️ Error information saved!")

        return df
