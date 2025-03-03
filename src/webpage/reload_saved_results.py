from datetime import datetime
from typing import List, Optional, Tuple

import streamlit as st

from utils.azure_blob_utils import download_file_from_blob, list_files_in_blob
from utils.logger import logger
from config import LABELLING_DATETIME_FORMAT, LABELLING_RESULTS_FOLDER
from webpage.labelling_consts import FILE_NAME, FILE_NAME_SEPARATOR
from webpage.load_data import read_data_from_file
from webpage.manage_user_session import get_loading_key, get_results_key


def reload_results_from_file(file_name: str) -> None:
    """
    Reload saved results from a file in Azure Blob Storage.

    Args:
        file_name (str): The name of the file to download and load.
    """
    file = download_file_from_blob(file_name)
    if file is None:
        st.error("Could not download file from storage.")
        return

    try:
        df = read_data_from_file(file)
        if df is None:
            st.error("Error loading data from file.")
            return

        st.session_state[get_results_key()] = df.copy()
        st.session_state[get_loading_key()] = False  # No need to load the results again
        st.toast("✔️ Results loaded successfully!")
    except Exception as e:
        logger.error(f"Error loading data from file: {e}")
        st.error(f"Error loading data from file: {e}")


def decode_file_name(file_name: str) -> Tuple[str, str]:
    """
    Decodes the file name to get the run_id and user name.

    Args:
        file_name (str): The name of the file.

    Returns:
        Tuple[str, str]: The run_id and the user name.
    """
    file_path = file_name.replace(LABELLING_RESULTS_FOLDER, "")

    # Check if file uses the new separator format
    if FILE_NAME_SEPARATOR in file_path:
        # Using split with maxsplit=2 to handle potential additional separators in the filename
        parts = file_path.split(FILE_NAME_SEPARATOR)
        if len(parts) >= 3:
            # Format: [datetime]___[run_id]___[user_name].json
            run_id = parts[1]
            user_name = parts[2].replace(".json", "")
            return run_id, user_name

    # Fallback to old underscore method for backward compatibility
    parts = file_path.split("_")
    return parts[-2], parts[-1].replace(".json", "")


def get_saved_files_for_user(user_name: str, run_id: str) -> List[str]:
    """
    Get all saved files for a specific user and run ID.

    Args:
        user_name (str): The user name to filter files by.
        run_id (str): The run ID to filter files by.

    Returns:
        List[str]: List of file paths that match the user and run ID.
    """
    files = list_files_in_blob(folder=LABELLING_RESULTS_FOLDER, extension=".json")
    if not files:
        return []

    saved_files = []
    for file in files:
        # Check both new format and old format files
        if FILE_NAME_SEPARATOR in file:
            parts = file.split(FILE_NAME_SEPARATOR)
            if (
                len(parts) >= 3
                and parts[1] == run_id
                and parts[2].endswith(f"{user_name}.json")
            ):
                saved_files.append(file)
        # Fallback to old format for backward compatibility
        elif file.endswith(f"{run_id}_{user_name}.json"):
            saved_files.append(file)

    return saved_files


def get_latest_saved_file(files: List[str]) -> Optional[str]:
    """
    Get the latest saved file based on the timestamp in the filename.

    Args:
        files (List[str]): List of file paths to check.

    Returns:
        Optional[str]: The path of the latest file, or None if no files or error.
    """
    if not files:
        return None

    try:
        # Get the latest file
        return sorted(
            files,
            key=lambda x: datetime.strptime(
                x.replace(LABELLING_RESULTS_FOLDER, "").split(FILE_NAME_SEPARATOR)[0]
                if FILE_NAME_SEPARATOR in x
                else x.replace(LABELLING_RESULTS_FOLDER, "").split("_")[0],
                LABELLING_DATETIME_FORMAT,
            ),
            reverse=True,
        )[0]
    except Exception as e:
        logger.warning(f"Error sorting files: {e}")
        return None


def load_saved_results(user_name: str) -> bool:
    """
    Loads the saved results (if available) for a given user.

    Args:
        user_name (str): The name of the user. If None or empty, returns False.

    Returns:
        bool: True if the results can be loaded and user needs to be informed, False otherwise.
    """
    if not user_name:
        return False

    loading_key = get_loading_key()
    if not st.session_state.get(loading_key, True):
        return False

    # Get all saved files for this user and run ID
    saved_files = get_saved_files_for_user(user_name, st.session_state[FILE_NAME])

    if not saved_files:
        st.sidebar.warning("No saved files found")
        st.session_state[loading_key] = False
        return False

    if st.session_state.get(loading_key, True):
        file_name = get_latest_saved_file(saved_files)
        if not file_name:
            return False

        if st.button(
            "✔️ Load latest saved results",
            on_click=lambda: reload_results_from_file(file_name),
        ):
            return False
        else:
            return True
    return False
