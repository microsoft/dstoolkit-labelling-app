from datetime import datetime
from utils.azure_blob_utils import download_file_from_blob, list_files_in_blob
from utils.logger import logger
from config import LABELLING_DATETIME_FORMAT, LABELLING_RESULTS_FOLDER
from webpage.labelling_consts import FILE_NAME
from webpage.load_data import read_data_from_file
from webpage.manage_user_session import get_loading_key, get_results_key


import streamlit as st


def reload_results_from_file(file_name: str) -> None:
    file = download_file_from_blob(file_name)
    if file is None:
        return
    loading_exeption_msg = "Error loading data from file."
    try:
        df = read_data_from_file(file)
        if df is None:
            st.error(loading_exeption_msg)
            return None

        st.session_state[get_results_key()] = df.copy()
        st.session_state[get_loading_key()] = False  # No need to load the results again
        st.toast("✔️ Results loaded successfully!")
    except Exception as e:
        logger.error(f"Error loading data from file: {e}")
        st.error(f"Error loading data from file. {e}")


def decode_file_name(file_name: str) -> tuple[str, str]:
    """
    Decodes the file name to get the date and user name.

    Args:
        file_name (str): The name of the file.

    Returns:
        tuple[str, str]: The original file name and the user name.
    """
    # TODO: replace with more reliable separation
    parts = file_name.replace(LABELLING_RESULTS_FOLDER, "").split("_")
    return parts[-2], parts[-1].replace(".json", "")


def load_saved_results(user_name: str | None) -> bool:
    """
    Loads the saved results (if availalbe) for a given user.

    Args:
        user_name (str | None): The name of the user. If None, returns False.

    Returns:
        bool: True if the resutls can be loaded and user needs to be informed, False otherwise.
    """

    if not user_name:
        return False

    loading_key = get_loading_key()
    if not st.session_state.get(loading_key, True):
        return False
    files = list_files_in_blob(folder=LABELLING_RESULTS_FOLDER, extension=".json")
    if files is None:
        return False

    saved_files = []
    for file in files:
        # Filter files by user name
        if file.endswith(f"{st.session_state[FILE_NAME]}_{user_name}.json"):
            saved_files.append(file)

    if not saved_files:
        st.sidebar.warning("No saved files found")
        st.session_state[loading_key] = False
        return False

    if st.session_state.get(loading_key, True):
        try:
            # Get the latest file
            file_name = sorted(
                saved_files,
                key=lambda x: datetime.strptime(
                    x.replace(LABELLING_RESULTS_FOLDER, "").split("_")[0],
                    LABELLING_DATETIME_FORMAT,
                ),
                reverse=True,
            )[0]
        except Exception as e:
            logger.warning(f"Error sorting files: {e}")
            return False

        if st.button(
            "✔️ Load latest saved results",
            on_click=lambda: reload_results_from_file(file_name),
        ):
            return False
        else:
            return True
    return False
