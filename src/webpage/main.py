from datetime import datetime

from config import (
    CONTEXT_COLUMN,
    EVALUATION_GT_COLUMN,
    LABELLING_DATETIME_FORMAT,
    PREDICTIONS_COLUMN,
    QUESTION_COLUMN,
)
from webpage.download_and_save_results import download_results, save_results_to_blob
from webpage.labelling_consts import (
    ANSWER_IS_BETTER,
    APP_TITLE,
    END_TIME_MS,
    ERROR,
    ERROR_ANALYSIS,
    ERROR_CATEGORIES_LIST,
    ERROR_CATEGORIES_MARKDOWN,
    ERROR_DESCRIPTION,
    ERROR_SNIPPET,
    FEEDBACK,
    FILE_HASH,
    LABEL_QUALITY,
    QUALITY_LABELS,
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
from webpage.save_user_labels import save_error, save_new_gt, save_user_feedback
import streamlit as st
from utils.st_utils import LABELLING_INSTRUCTIONS, LOGO_ICON
import pandas as pd

from webpage.user_management import auth_users


def display_llm_metrics(row: pd.Series) -> None:
    """
    Display the metrics for the given row.
    Parameters:
    - row: pd.Series
        The row containing the metrics data.
    Returns:
    None
    """

    # Placeholder: add the code to display the metrics here
    st.write("Metrics will be displayed here")


def main():
    init_session_state_variables()
    auth_users()
    # You can use st.session_state["authentication_status"] to check if the user is authenticated
    # This application allows to continue without authentication

    user_name = st.session_state.get(USER_NAME)
    if LABELLING_INSTRUCTIONS is not None:
        with st.expander("Instructions"):
            st.write(LABELLING_INSTRUCTIONS)

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

    # Optional settings to display additional information
    show_llm_metrics = st.sidebar.checkbox("Show LLM Metrics", False)
    show_context_data = st.sidebar.checkbox("Show context data", False)

    # Make sure the selected row is within the bounds
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

    # Set the start time if not already set for the current sample
    results_df = st.session_state.get(get_results_key())
    if results_df is None:
        st.error("Error loading results.")
        return

    ind = data.index[ind]
    if ind not in results_df.index:
        ind = str(ind)  # could happen due to serialization

    if results_df.loc[ind, START_TIME_MS] is None:
        results_df.loc[ind, START_TIME_MS] = datetime.now().strftime(
            LABELLING_DATETIME_FORMAT
        )

    # Show the progress and navigation buttons
    with st.sidebar:
        st.markdown("### Progress")
        n = len(data)
        st.number_input(
            "Sample number:",
            0,
            n - 1,
            value=st.session_state.get(SELECTED_ROW_ID)
            if 0 <= st.session_state.get(SELECTED_ROW_ID, 0) < n
            else 0,
            on_change=lambda: st.session_state.update(
                {SELECTED_ROW_ID: st.session_state["sample_number"]}
            ),
            key="sample_number",
        )

        completed_num = 0
        if LABEL_QUALITY in results_df.columns:
            completed_num = results_df[LABEL_QUALITY].count()
        st.write(f"Completed: {(100 * completed_num / n):.0f}% ({completed_num}/{n})")

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
    # Add a button to download the results
    download_results()

    row = data.iloc[st.session_state[SELECTED_ROW_ID]]

    # Display the question and the model answer
    question = row[QUESTION_COLUMN]
    if EVALUATION_GT_COLUMN in row and not pd.isna(row[EVALUATION_GT_COLUMN]):
        gt_answer = row[EVALUATION_GT_COLUMN]
    else:
        gt_answer = None
    model_answer = row[PREDICTIONS_COLUMN]

    st.markdown(f"### Question \n{question}")
    if pd.isna(gt_answer):
        st.warning("No ground truth provided.")
    if pd.isna(model_answer):
        st.warning("No model answer provided.")

    question_hash = hash(
        question + str(st.session_state[SELECTED_ROW_ID]) + get_results_key()
    )
    if not pd.isna(model_answer):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Model Answer")

            if show_context_data:
                if CONTEXT_COLUMN not in df.columns:
                    st.warning("No context data available.")
                else:
                    with st.expander("Context data"):
                        st.write(row[CONTEXT_COLUMN])
            st.markdown(model_answer)

            st.write("### Labelling")

            with st.expander("Add feedback on a part of the answer"):
                with st.form(key=f"error_form_{question_hash}", clear_on_submit=True):
                    st.text_area(
                        "Part of the answer",
                        key=f"error_snippet_{question_hash}",
                        help="Enter the part of the answer that you want to provide feedback on.",
                    )
                    st.multiselect(
                        "Error Category",
                        ERROR_CATEGORIES_LIST,
                        key=f"error_{question_hash}",
                        help=ERROR_CATEGORIES_MARKDOWN,
                    )
                    st.text_area(
                        "(Optional) Error Description",
                        key=f"error_description_{question_hash}",
                    )

                    st.form_submit_button(
                        "Submit error category",
                        on_click=save_error,
                        args=(question_hash,),
                    )
            if results_df.loc[ind].get(ERROR_ANALYSIS) is not None:
                with st.expander("Previous Feedback"):
                    for x in results_df.loc[ind].get(ERROR_ANALYSIS):
                        if not isinstance(x, dict):
                            st.markdown(f"**Error**: {x}")
                            continue
                        if x.get(QUESTION_HASH) is None:
                            st.markdown("Part of the answer: ")
                            st.code(x[ERROR_SNIPPET])
                            st.markdown(f"**Error**: {x[ERROR]}")
                            st.markdown(f"**Description**: {x[ERROR_DESCRIPTION]}")

            with st.form(key=f"label_form_{question_hash}"):
                st.write("General answer quality:")
                default_quality = results_df.loc[ind].get(LABEL_QUALITY)
                if pd.isna(default_quality):
                    default_quality = None
                st.select_slider(
                    "",
                    list(QUALITY_LABELS.values()),
                    key=f"quality_{question_hash}",
                    value=default_quality,
                )
                default_feedback = results_df.loc[ind].get(FEEDBACK)
                if pd.isna(default_feedback):
                    default_feedback = None
                st.text_area(
                    "Feedback (Optional)",
                    key=f"feedback_{question_hash}",
                    value=default_feedback,
                )
                default_answer_is_better = results_df.loc[ind].get(ANSWER_IS_BETTER)
                if pd.isna(default_answer_is_better):
                    default_answer_is_better = None
                st.checkbox(
                    "Model answer is better than provided Ground Truth",
                    key=f"answer_is_better_{question_hash}",
                    value=default_answer_is_better,  # type: ignore
                )

                st.form_submit_button(
                    "Submit feedback",
                    on_click=save_user_feedback,
                    args=(question_hash,),
                )

        with col2:
            st.markdown("### Ground Truth")
            if gt_answer is not None:
                st.write(gt_answer)
            else:
                # Adding additional labels for data without ground truth
                st.write(
                    "This is the question without a ground truth. Please, asseses the relevance of the question and provide a corrected question and ground truth answer if possible."
                )
                with st.form(key=f"gt_form_{question_hash}"):
                    relevance = results_df.loc[ind].get(SYN_QA_RELEVANCE, True)
                    st.checkbox(
                        "The question is not relevant",
                        key=f"syn_gt_qa_irrelevant_{question_hash}",
                        value=False if relevance else True,
                    )

                    question = results_df.loc[ind].get(SYN_CORRECTED_QUESTION)
                    if pd.isna(question):
                        question = row[QUESTION_COLUMN]
                    st.text_area(
                        "Rewrite the question (Optional)",
                        key=f"syn_corrected_question_{question_hash}",
                        value=question,
                    )
                    gt_code = results_df.loc[ind].get(SYN_GT_ANSWER)
                    if pd.isna(gt_code):
                        gt_code = model_answer
                    st.text_area(
                        "Provide Ground Truth (Optional)",
                        key=f"syn_gt_{question_hash}",
                        value=gt_code,
                    )

                    st.form_submit_button(
                        "Submit",
                        on_click=save_new_gt,
                        args=(question_hash,),
                    )

            if show_llm_metrics:
                st.write("### LLM Metrics")
                display_llm_metrics(row)

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
    optional_cols = [SYN_QA_RELEVANCE, SYN_CORRECTED_QUESTION]
    for col in show_cols:
        if col not in results_df.columns:
            results_df[col] = None
    for col in optional_cols:
        if col in results_df.columns:
            show_cols.append(col)
    st.dataframe(results_df[show_cols].reset_index(drop=True))
    save_results_to_blob(user_name)


if __name__ == "__main__":
    st.set_page_config(page_title=APP_TITLE, page_icon=LOGO_ICON, layout="wide")
    if LOGO_ICON is not None:
        st.image(LOGO_ICON, width=200, use_column_width=False, output_format="PNG")
    st.title(APP_TITLE)
    st.write("___")

    with st.sidebar:
        st.sidebar.title("Settings")
        st.write("___")
    main()
