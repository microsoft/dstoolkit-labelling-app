from typing import Any, Dict, Optional, Callable, Union
import pandas as pd
import streamlit as st

from webpage.labelling_consts import SELECTED_ROW_ID
from webpage.manage_user_session import get_results_key


class CustomFormHandler:
    """
    A handler for creating, rendering, and managing feedback forms

    This class provides a standardized way to:
    - Create custom forms with various input types
    - Save form data to the session state and dataframe
    - Load previously saved form data

    Compatible with the labelling_page.py form structure.
    """

    def __init__(
        self,
        form_id: str,
        form_title: str,
        data_key: str,
        persistence_key: str,
        hash_field: str = SELECTED_ROW_ID,
    ):
        """
        Initialize a custom form handler.

        Args:
            form_id (str): Base identifier for the form
            form_title (str): The title to display for the form
            data_key (str): The key to store form data in the dataframe
            persistence_key (str): The key to store form state in session state
            hash_field (str): Session state field containing the hash/ID to use in form keys
        """
        self.form_id = form_id
        self.form_title = form_title
        self.data_key = data_key
        self.persistence_key = persistence_key
        self.hash_field = hash_field

        # Initialize the form data in session state if it doesn't exist
        if self.persistence_key not in st.session_state:
            st.session_state[self.persistence_key] = {}

    def get_form_key(self) -> str:
        """
        Generate a form key using the form_id and the current hash value.

        Returns:
            str: A unique form key compatible with the labelling page format
        """
        hash_value = st.session_state.get(self.hash_field, "default")
        return f"{self.form_id}_{hash_value}"

    def render_form(
        self, render_function: Callable, button_name: str = "Submit"
    ) -> Dict[str, Any]:
        """
        Render a custom form using the provided render function.

        Args:
            render_function: A function that renders form elements and returns form data

        Returns:
            Dict[str, Any]: The collected form data or an empty dict if no submission
        """
        form_data = {}
        form_key = self.get_form_key()

        with st.form(key=form_key):
            st.write(f"### {self.form_title}")
            # Call the custom render function to build the form
            form_data = render_function()

            # Create the submit button
            submitted = st.form_submit_button(button_name)

        if submitted and form_data:
            # Save the form data to session state
            st.session_state[self.persistence_key] = form_data
            self.save_to_dataframe()
            st.toast(f"✅ {self.form_title} submitted successfully!")
            return form_data

        return {}

    def save_to_dataframe(
        self,
        df: pd.DataFrame = None,
        row_idx: Optional[Union[int, str]] = None,
        transform_function: Optional[Callable] = None,
    ) -> pd.DataFrame:
        """
        Save the form data to the specified dataframe.

        Args:
            df (pd.DataFrame): The dataframe to save data to
            row_idx (Optional[Union[int, str]]): The row index where data should be saved
                                                (defaults to current selected row)
            transform_function (Optional[Callable]): Optional function to transform
                                                     data before saving

        Returns:
            pd.DataFrame: The updated dataframe
        """
        if df is None:
            df = st.session_state.get(get_results_key())

        form_data = st.session_state.get(self.persistence_key, {})
        if not form_data:
            return df

        if transform_function:
            form_data = transform_function(form_data)

        # Use the current selected row if none is provided
        if row_idx is None:
            row_idx = st.session_state.get(self.hash_field)

        if row_idx is None or row_idx not in df.index:
            st.warning("No valid row selected for saving form data")
            return df

        # Make sure the data column exists in the dataframe
        if self.data_key not in df.columns:
            df[self.data_key] = None

        # Save the data to the dataframe
        df.at[row_idx, self.data_key] = form_data

        return df

    def load_from_dataframe(
        self,
        df: pd.DataFrame,
        row_idx: Optional[Union[int, str]] = None,
        transform_function: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Load form data from the dataframe.

        Args:
            df (pd.DataFrame): The dataframe to load data from
            row_idx (Optional[Union[int, str]]): The row index to load data from
                                                (defaults to current selected row)
            transform_function (Optional[Callable]): Optional function to transform data
                                                     after loading

        Returns:
            Dict[str, Any]: The loaded form data or empty dict if no data exists
        """
        # Use the current selected row if none is provided
        if row_idx is None:
            row_idx = st.session_state.get(self.hash_field)

        if (
            row_idx is None
            or row_idx not in df.index
            or self.data_key not in df.columns
        ):
            return {}

        form_data = df.at[row_idx, self.data_key]

        if form_data is None or not isinstance(form_data, dict):
            return {}

        if transform_function:
            form_data = transform_function(form_data)

        # Store the loaded data in session state
        st.session_state[self.persistence_key] = form_data
        return form_data

    def has_saved_data(
        self, df: pd.DataFrame, row_idx: Optional[Union[int, str]] = None
    ) -> bool:
        """
        Check if there is saved form data for the specified row.

        Args:
            df (pd.DataFrame): The dataframe to check
            row_idx (Optional[Union[int, str]]): The row index to check
                                                (defaults to current selected row)

        Returns:
            bool: True if saved data exists, False otherwise
        """
        # Use the current selected row if none is provided
        if row_idx is None:
            row_idx = st.session_state.get(self.hash_field)

        if (
            row_idx is None
            or row_idx not in df.index
            or self.data_key not in df.columns
        ):
            return False

        form_data = df.at[row_idx, self.data_key]
        return form_data is not None and isinstance(form_data, dict)

    def clear_form_data(self) -> None:
        """
        Clear the form data from session state.
        """
        if self.persistence_key in st.session_state:
            st.session_state[self.persistence_key] = {}
