from datetime import datetime
from typing import Dict, Any

import pandas as pd
import streamlit as st

from config import (
    CONTEXT_COLUMN,
    EVALUATION_GT_COLUMN,
    LABELLING_DATETIME_FORMAT,
    PREDICTIONS_COLUMN,
    QUESTION_COLUMN,
)
from utils.st_utils import LABELLING_INSTRUCTIONS, LOGO_ICON
from webpage.download_and_save_results import download_results, save_results_to_blob
from webpage.initial_st_setup import initial_setup
from webpage.labelling_consts import (
    ANSWER_IS_BETTER,
    APP_TITLE,
    END_TIME_MS,
    ERROR,
    ERROR_ANALYSIS,
    ERROR_DESCRIPTION,
    ERROR_SNIPPET,
    FEEDBACK,
    FILE_HASH,
    LABEL_QUALITY,
    QUESTION_HASH,
    SEED,
    SELECTED_ROW_ID,
    START_TIME_MS,
    SYN_CORRECTED_QUESTION,
    SYN_GT_ANSWER,
    SYN_QA_RELEVANCE,
    USER_NAME,
)
from webpage.load_data import get_labelling_data, process_data
from webpage.manage_user_session import (
    get_loading_key,
    get_results_key,
    init_session_state_variables,
)
from webpage.reload_saved_results import load_saved_results
from webpage.form_handling.labelling_handlers import (
    QualityFeedbackHandler,
    ErrorFeedbackHandler,
    GroundTruthHandler,
)


def display_llm_metrics(row: pd.Series) -> None:
    """
    Display the metrics for the given row.

    Parameters:
        row: The row containing the metrics data.
    """
    # Placeholder: add the code to display the metrics here
    st.write("Metrics will be displayed here")


def headers_setup() -> None:
    """Set up the application header with logo and title."""
    if LOGO_ICON is not None:
        st.image(LOGO_ICON, width=200, use_column_width=False, output_format="PNG")
    st.title(APP_TITLE)
    st.write("___")
    with st.sidebar:
        st.sidebar.title("Settings")
        st.write("___")


def setup_sidebar_navigation(data_length: int) -> None:
    """
    Set up the sidebar navigation controls and progress display.

    Parameters:
        data_length: The total number of items in the dataset.
    """
    with st.sidebar:
        st.markdown("### Progress")
        st.number_input(
            "Sample number:",
            0,
            data_length - 1,
            value=st.session_state.get(SELECTED_ROW_ID)
            if 0 <= st.session_state.get(SELECTED_ROW_ID, 0) < data_length
            else 0,
            on_change=lambda: st.session_state.update(
                {SELECTED_ROW_ID: st.session_state["sample_number"]}
            ),
            key="sample_number",
        )

        results_df = st.session_state.get(get_results_key())
        completed_num = 0
        if results_df is not None and LABEL_QUALITY in results_df.columns:
            completed_num = results_df[LABEL_QUALITY].count()

        completion_percentage = (
            (100 * completed_num / data_length) if data_length > 0 else 0
        )
        st.write(
            f"Completed: {completion_percentage:.0f}% ({completed_num}/{data_length})"
        )

    # Add navigation buttons
    prev_button, next_button = st.sidebar.columns(2)
    prev_button.button(
        "⬅️ Prev sample",
        on_click=lambda: st.session_state.update(
            {SELECTED_ROW_ID: st.session_state[SELECTED_ROW_ID] - 1}
        ),
    )
    next_button.button(
        "Next sample ➡️",
        on_click=lambda: st.session_state.update(
            {SELECTED_ROW_ID: st.session_state[SELECTED_ROW_ID] + 1}
        ),
    )


def display_question_and_answers(
    row: pd.Series, question_hash: int, show_context_data: bool, show_llm_metrics: bool
) -> None:
    """
    Display the question, model answer, and ground truth with labelling forms.

    Parameters:
        row: The row data to display
        question_hash: Hash of the current question
        show_context_data: Whether to show context data
        show_llm_metrics: Whether to show LLM metrics
    """
    question = row[QUESTION_COLUMN]
    model_answer = row[PREDICTIONS_COLUMN]
    gt_answer = (
        row.get(EVALUATION_GT_COLUMN)
        if EVALUATION_GT_COLUMN in row and not pd.isna(row[EVALUATION_GT_COLUMN])
        else None
    )

    st.markdown(f"### Question \n{question}")

    if pd.isna(gt_answer):
        st.warning("No ground truth provided.")
    if pd.isna(model_answer):
        st.warning("No model answer provided.")
        return

    col1, col2 = st.columns(2)

    # Display model answer and labelling forms
    with col1:
        st.markdown("### Model Answer")

        if show_context_data:
            if CONTEXT_COLUMN not in row.index or pd.isna(row[CONTEXT_COLUMN]):
                st.warning("No context data available.")
            else:
                with st.expander("Context data"):
                    st.write(row[CONTEXT_COLUMN])

        st.markdown(model_answer)
        st.write("### Labelling")

        # Display error feedback form
        error_handler = ErrorFeedbackHandler(question_hash)
        with st.expander("Add feedback on a part of the answer"):
            error_handler.render_form(
                error_handler.render_error_feedback_form,
                button_name="Submit error category",
            )

        # Display previous feedback if available
        results_df = st.session_state[get_results_key()]
        ind = row.name
        if ind not in results_df.index:
            ind = str(ind)  # could happen due to serialization

        if results_df.loc[ind].get(ERROR_ANALYSIS) is not None:
            with st.expander("Previous Feedback"):
                for feedback_item in results_df.loc[ind].get(ERROR_ANALYSIS):
                    display_feedback_item(feedback_item)

        # Quality feedback form
        quality_handler = QualityFeedbackHandler(question_hash)
        quality_handler.render_form(
            quality_handler.render_quality_feedback_form, button_name="Submit feedback"
        )

    # Display ground truth or gt form
    with col2:
        st.markdown("### Ground Truth")
        if gt_answer is not None:
            st.write(gt_answer)
        else:
            gt_handler = GroundTruthHandler(question_hash)
            st.write(
                "This is the question without a ground truth. Please, assess the relevance of the question and provide a corrected question and ground truth answer if possible."
            )
            gt_handler.render_form(
                gt_handler.render_ground_truth_form, button_name="Submit ground truth"
            )

        if show_llm_metrics:
            st.write("### LLM Metrics")
            display_llm_metrics(row)


def display_feedback_item(feedback_item: Dict[str, Any]) -> None:
    """
    Display a single feedback item from previous error analysis.

    Parameters:
        feedback_item: The feedback item to display
    """
    if not isinstance(feedback_item, dict):
        st.markdown(f"**Error**: {feedback_item}")
        return

    if feedback_item.get(QUESTION_HASH) is not None:
        st.markdown("Part of the answer: ")
        st.code(feedback_item[ERROR_SNIPPET])
        st.markdown(f"**Error**: {feedback_item[ERROR]}")
        st.markdown(f"**Description**: {feedback_item[ERROR_DESCRIPTION]}")


def display_results_table() -> None:
    """Display the results table with all labelled data."""
    st.markdown("# Results")
    results_df = st.session_state[get_results_key()].copy()

    show_cols = [
        QUESTION_COLUMN,
        LABEL_QUALITY,
        FEEDBACK,
        ERROR_ANALYSIS,
        ANSWER_IS_BETTER,
        START_TIME_MS,
        END_TIME_MS,
    ]

    optional_cols = [SYN_QA_RELEVANCE, SYN_CORRECTED_QUESTION, SYN_GT_ANSWER]

    # Initialize columns if they don't exist
    for col in show_cols:
        if col not in results_df.columns:
            results_df[col] = None

    # Add optional columns if they exist
    for col in optional_cols:
        if col in results_df.columns:
            show_cols.append(col)

    st.dataframe(results_df[show_cols].reset_index(drop=True))


def handle_sample_selection(data: pd.DataFrame) -> int:
    """
    Handle selected row index validation and update start time if needed.

    Parameters:
        data: The dataset to work with

    Returns:
        The validated index of the current sample
    """
    # Make sure the selected row is within bounds
    if SELECTED_ROW_ID not in st.session_state:
        st.session_state[SELECTED_ROW_ID] = 0

    ind = st.session_state[SELECTED_ROW_ID]

    if ind >= len(data):
        st.warning("No more samples to label.")
        ind = len(data) - 1
        st.session_state[SELECTED_ROW_ID] = ind
    elif ind < 0:
        st.warning("Invalid sample index. Setting to 0.")
        st.session_state[SELECTED_ROW_ID] = 0
        ind = 0

    # Get the actual row index from the DataFrame
    row_index = data.index[ind]

    # Set the start time if not already set for the current sample
    results_df = st.session_state.get(get_results_key())
    if results_df is not None:
        if row_index not in results_df.index:
            row_index = str(row_index)  # could happen due to serialization

        if results_df.loc[row_index, START_TIME_MS] is None:
            results_df.loc[row_index, START_TIME_MS] = datetime.now().strftime(
                LABELLING_DATETIME_FORMAT
            )

    return ind


def main() -> None:
    """Main function to run the labelling application."""
    headers_setup()
    init_session_state_variables()

    user_name = st.session_state.get(USER_NAME)

    # Display instructions if available
    if LABELLING_INSTRUCTIONS is not None:
        with st.expander("Instructions"):
            st.write(LABELLING_INSTRUCTIONS)

    # Get labelling data
    df = get_labelling_data()
    if df is None:
        st.warning("Please upload a JSON file to start labelling.")
        return

    data = process_data(
        df,
        n=None,
        random_seed=st.session_state[SEED],
        file_hash=st.session_state.get(FILE_HASH),
    )

    # Check if need to load saved results
    placeholder = st.empty()
    ask_user = load_saved_results(user_name)

    loading_key = get_loading_key()
    if ask_user:
        with placeholder.container():
            st.info(
                "### Do you want to load the latest saved results? \n Values in the selectors will be set to default and unsaved changes will be overwritten with the saved data. You can still edit all the values and verify the results in the bottom table."
            )
            if st.button(
                "❌ No, I want to start again",
                on_click=lambda: st.session_state.update({loading_key: False}),
            ):
                st.session_state[loading_key] = False
            return

    # Optional settings for additional information
    show_llm_metrics = st.sidebar.checkbox("Show LLM Metrics", False)
    show_context_data = st.sidebar.checkbox("Show context data", False)

    # Handle sample selection and validation
    current_index = handle_sample_selection(data)

    # Check if results are available
    results_df = st.session_state.get(get_results_key())
    if results_df is None:
        st.error("Error loading results.")
        return

    # Set up navigation in sidebar
    setup_sidebar_navigation(len(data))

    # Add download button
    download_results()

    # Get the current row data
    current_row = data.iloc[current_index]

    # Generate a hash for the current question
    question_hash = hash(
        current_row[QUESTION_COLUMN]
        + str(st.session_state[SELECTED_ROW_ID])
        + get_results_key()
    )

    # Display question, answers and labelling forms
    display_question_and_answers(
        current_row, question_hash, show_context_data, show_llm_metrics
    )

    # Display results table
    display_results_table()

    # Save results to blob storage
    save_results_to_blob(user_name)


if __name__ == "__main__":
    initial_setup()
    main()
else:
    main()
