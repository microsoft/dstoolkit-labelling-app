from typing import Optional
from config import REQUIRED_COLS
from utils.logger import logger
from webpage.labelling_consts import FILE_HASH, FILE_NAME, FILENAME_HASH


import pandas as pd
import streamlit as st


import json
import random
from io import BytesIO

from webpage.manage_user_session import upd_state_on_file_reload
from utils.azure_blob_utils import download_file_from_blob, list_files_in_blob


def read_data_from_file(file: BytesIO) -> pd.DataFrame | None:
    """
    Reads data from a file and returns it as a pandas DataFrame.
    Parameters:
        file (BytesIO): The file object containing the data.
    Returns:
        pd.DataFrame | None: The loaded data as a pandas DataFrame, or None if there was an error.
    Raises:
        Exception: If there was an error loading the data from the file.
    """

    try:
        data = json.load(file)
        if "data" not in data:
            df = pd.DataFrame.from_dict(data, orient="columns").reset_index(drop=True)
            return df
        df = pd.DataFrame.from_dict(data["data"])
        df.columns = data["columns"]
        return df
    except Exception as e:
        logger.exception(f"Error loading data from file: {e}")
        st.error("Error loading data from file.")
        return None


def get_labelling_data() -> pd.DataFrame | None:
    """
    Retrieves labelling data from a selected file and returns it as a pandas DataFrame.

    Returns:
        pd.DataFrame: The labelling data as a pandas DataFrame, or None if there was an error.
    """
    files = list_files_in_blob(extension=".json")
    if files is None:
        return None

    file_name = st.sidebar.selectbox("Select the results file to analyse", files)
    if file_name is None:
        return None

    file: Optional[BytesIO] = download_file_from_blob(file_name)
    if file is None:
        return None

    df = read_data_from_file(file)
    if df is None:
        return None

    # Check if required columns are present
    for col in REQUIRED_COLS:
        if col not in df.columns:
            st.error(f"Column {col} is missing from the file.")
            return None

    st.session_state[FILE_NAME] = ".".join(file_name.split(".")[:-1])

    # Check if the file has changed
    filename_hash = hash(file_name)
    if st.session_state.get(FILENAME_HASH) != filename_hash:
        st.session_state[FILENAME_HASH] = filename_hash
        # Generate a new hash for the file, to be used as a unique identifier
        # If user loaded file a, then file b, then file a again, the hash will be different
        # Requied for caching
        st.session_state[FILE_HASH] = random.randint(0, int(1e9))  # nosec
    return df


@st.cache_data()
def process_data(
    df: pd.DataFrame,
    n: int | None = None,
    random_seed: Optional[int] = None,
    file_hash: Optional[int] = None,
) -> pd.DataFrame:
    """
    Randomly selects 'n' rows from the given DataFrame and stores them in the session state.

    Parameters:
        df (pd.DataFrame): The DataFrame from which rows will be selected.
        n (int): The number of rows to be selected. Default is 5.
        random_seed (Optional[int]): The random seed for caching. Default is None.
        file_hash (Optional[int]): The hash of the file. Default is None. Requried for streamlit caching.

    Returns:
        pd.DataFrame: The randomly selected rows from the DataFrame.
    """
    if n is not None:
        res = df.sample(n=n, random_state=random_seed)
    else:
        res = df
    upd_state_on_file_reload(res)
    return res
