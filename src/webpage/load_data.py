import json
import random
from io import BytesIO
from typing import Optional

import pandas as pd
import streamlit as st

from config import REQUIRED_COLS
from utils.logger import logger
from utils.azure_blob_utils import download_file_from_blob, list_files_in_blob
from webpage.labelling_consts import FILE_HASH, FILE_NAME, FILENAME_HASH
from webpage.manage_user_session import upd_state_on_file_reload


def read_data_from_file(file: BytesIO) -> Optional[pd.DataFrame]:
    """
    Reads data from a file and returns it as a pandas DataFrame.

    Args:
        file (BytesIO): The file object containing the data.

    Returns:
        Optional[pd.DataFrame]: The loaded data as a DataFrame, or None if there was an error.
    """
    try:
        data = json.load(file)

        # Handle different JSON formats
        if "data" not in data:
            df = pd.DataFrame.from_dict(data, orient="columns")
        else:
            df = pd.DataFrame.from_dict(data["data"])
            df.columns = data["columns"]
            df.index = data["index"]

        return df

    except json.JSONDecodeError as e:
        logger.exception(f"Invalid JSON format: {e}")
        st.error("Invalid JSON format in the file.")
        return None
    except Exception as e:
        logger.exception(f"Error loading data from file: {e}")
        st.error("Error loading data from file.")
        return None


def get_labelling_data() -> Optional[pd.DataFrame]:
    """
    Retrieves labelling data from a user-selected file in blob storage.

    Returns:
        Optional[pd.DataFrame]: The labelling data as a DataFrame, or None if there was an error.
    """
    files = list_files_in_blob(extension=".json")
    if files is None:
        st.error("Could not retrieve files from storage.")
        return None

    file_name = st.sidebar.selectbox("Select the results file to analyse", files)
    if file_name is None:
        st.info("Please select a file to continue.")
        return None

    file = download_file_from_blob(file_name)
    if file is None:
        st.error(f"Could not download file: {file_name}")
        return None

    df = read_data_from_file(file)
    if df is None:
        return None

    # Validate required columns
    missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing_cols:
        st.error(f"Missing required columns: {', '.join(missing_cols)}")
        return None

    # Store file name and update file hash if needed
    st.session_state[FILE_NAME] = ".".join(file_name.split(".")[:-1])
    update_file_hash(file_name)

    return df


def update_file_hash(file_name: str) -> None:
    """
    Updates the file hash in session state when the file changes.

    Args:
        file_name (str): Name of the selected file.
    """
    # Check if the file has changed
    filename_hash = hash(file_name)
    if st.session_state.get(FILENAME_HASH) != filename_hash:
        st.session_state[FILENAME_HASH] = filename_hash
        # Generate a new hash for the file, to be used as a unique identifier
        # If user loaded file a, then file b, then file a again, the hash will be different
        # Required for caching
        st.session_state[FILE_HASH] = random.randint(0, int(1e9))  # nosec


@st.cache_data()
def process_data(
    df: pd.DataFrame,
    n: Optional[int] = None,
    random_seed: Optional[int] = None,
    file_hash: Optional[int] = None,
) -> pd.DataFrame:
    """
    Processes the dataset, optionally selecting a random sample.

    Args:
        df (pd.DataFrame): The DataFrame to process.
        n (Optional[int]): Number of rows to sample. If None, returns the entire DataFrame.
        random_seed (Optional[int]): Random seed for reproducibility.
        file_hash (Optional[int]): Hash of the file for caching.

    Returns:
        pd.DataFrame: The processed DataFrame.
    """
    result_df = df.sample(n=n, random_state=random_seed) if n is not None else df
    upd_state_on_file_reload(result_df)
    return result_df
