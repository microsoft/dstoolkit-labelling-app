from config import LABELLING_DATETIME_FORMAT, LABELLING_RESULTS_FOLDER
from datetime import datetime
from utils.logger import logger
from webpage.labelling_consts import USER_NAME
from webpage.manage_user_session import get_current_results, get_results_key


import streamlit as st

from utils.azure_blob_utils import get_container_client, upload_to_blob
from utils.st_utils import run_async


def create_file_name(user_name: str | None) -> str:
    """
    Creates a file name for the labelling results.

    Args:
        username (str | None): The username of the user. Can be None if not available.

    Returns:
        str: The generated file name in the format: {timestamp}_{file_name}_{username}.json
    """
    timestamp = datetime.now().strftime(LABELLING_DATETIME_FORMAT)
    if "file_name" not in st.session_state:
        st.session_state["file_name"] = "labelling_results"
    file_name = f"{timestamp}_{st.session_state.get('file_name')}_{user_name}.json"
    return file_name


def download_results() -> None:
    """
    Downloads the labelling results as a JSON file.

    Returns:
        None
    """
    results_key = get_results_key()
    if st.session_state.get(results_key) is None:
        return
    file = get_current_results()
    if file is None:
        st.warning("No results to download.")
        return

    file_name = create_file_name(st.session_state.get(USER_NAME))
    st.sidebar.download_button(
        label="Download results as JSON",
        data=file,
        file_name=file_name,
        mime="json/data",
    )
    st.sidebar.info(
        "Make sure to download the results locally when you are done labelling"
    )


def save_results_to_blob(user_name: str | None) -> None:
    """
    Saves the current results to a blob storage container.

    Args:
        username (str | None): The username to associate with the saved results.

    Returns:
        None
    """

    if not user_name:
        st.sidebar.warning(
            "Please login to enable automatic saving of the results in progress"
        )
        return

    results = get_current_results()
    file_name = create_file_name(user_name)
    file_name = f"{LABELLING_RESULTS_FOLDER}{file_name}"

    if results is None:
        st.warning("No results to save.")
        return
    try:
        container_clinet = get_container_client()
        run_async(
            upload_to_blob(
                file_name,
                results,
                container_clinet,  # type: ignore
                delelete_old_entries=True,
            )
        )
    except Exception as e:
        st.sidebar.error("Error saving results")
        logger.error(f"Error saving results: {e}")
