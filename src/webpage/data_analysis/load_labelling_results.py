import pandas as pd
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

import streamlit as st

from config import LABELLING_RESULTS_FOLDER
from utils.azure_blob_utils import download_file_from_blob, list_files_in_blob
from utils.logger import logger
from webpage.data_analysis.analysis_consts import LOW_VARIANCE_THRESHOLD
from webpage.labelling_consts import (
    _PROCESS_RESULTS_DATA,
    _PROCESS_RESULTS_RAW_DATA,
    _PROCESS_RESULTS_RUN_ID,
    _PROCESS_RESULTS_SCORE,
    LABEL_QUALITY,
    QUALITY_LABELS,
    USER_NAME,
)
from webpage.load_data import read_data_from_file
from webpage.reload_saved_results import decode_file_name


def calculate_score(df: pd.DataFrame, quality_to_score: Dict[Any, Any]) -> pd.DataFrame:
    """
    Calculate and normalize scores for each row in the dataframe.

    Args:
        df (pd.DataFrame): Dataframe containing the labelling quality column.
        quality_to_score (Dict[Any, Any]): Dictionary mapping quality labels to scores.

    Returns:
        pd.DataFrame: Dataframe with calculated scores.
    """
    if LABEL_QUALITY not in df.columns:
        logger.warning(f"Column {LABEL_QUALITY} not found in dataframe")
        return df

    df[_PROCESS_RESULTS_SCORE] = df[LABEL_QUALITY].apply(
        lambda x: quality_to_score.get(x, 0) / len(QUALITY_LABELS)
        if not pd.isna(x)
        else None
    )
    return df


def merge_dataframes_with_user_scores(raw_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Merge dataframes from multiple users for the same run with proper column handling.

    Args:
        raw_dfs (List[pd.DataFrame]): List of dataframes to merge.

    Returns:
        pd.DataFrame: Merged dataframe with unified columns.
    """
    if not raw_dfs:
        return pd.DataFrame()

    merged_df = None
    col_suffix = "$$dup"  # Suffix for duplicate columns in merge

    for df in raw_dfs:
        if df.empty:
            continue

        user = df[USER_NAME].iloc[0]
        df_copy = df.copy()

        # Rename the score column to include the user name
        score_col = f"{_PROCESS_RESULTS_SCORE}_{user}"
        df_copy.rename(columns={_PROCESS_RESULTS_SCORE: score_col}, inplace=True)

        if merged_df is None:
            merged_df = df_copy
            continue

        # Outer merge on index and handle duplicate columns
        merged_df = pd.merge(
            merged_df,
            df_copy,
            how="outer",
            left_index=True,
            right_index=True,
            suffixes=("", col_suffix),
        )

        # Process duplicate columns
        for col in list(merged_df.columns):
            if col.endswith(col_suffix):
                original_col = col[: -len(col_suffix)]
                merged_df[original_col] = merged_df[original_col].fillna(merged_df[col])
                merged_df.drop(columns=col, inplace=True)

    return merged_df


def process_file_data(file_name: str) -> Optional[pd.DataFrame]:
    """
    Process a single results file from blob storage.

    Args:
        file_name (str): Name of the file to process.

    Returns:
        Optional[pd.DataFrame]: Processed dataframe or None if error.
    """
    file_content = download_file_from_blob(file_name)
    if file_content is None:
        logger.warning(f"Could not download file: {file_name}")
        return None

    try:
        df = read_data_from_file(file_content)
        if df is None:
            logger.error(f"Failed to read data from {file_name}")
            return None

        # Extract metadata from filename
        run_id, user_name = decode_file_name(file_name)

        # Add metadata columns
        df[_PROCESS_RESULTS_RUN_ID] = run_id
        df[USER_NAME] = user_name

        # Ensure quality label column exists
        if LABEL_QUALITY not in df.columns:
            df[LABEL_QUALITY] = None

        return df

    except Exception as e:
        logger.error(f"Error processing file {file_name}: {e}")
        return None


@st.cache_data(ttl="5min")
def read_all_results(
    check_for_low_variance: bool = True
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Read and process all labelling results from blob storage.

    Args:
        check_for_low_variance (bool): Whether to filter out runs with low score variance.

    Returns:
        Optional[Dict[str, Dict[str, Any]]]: Processed results organized by run_id.
    """
    with st.spinner(text="Loading labelled results..."):
        # Map quality labels to scores
        quality_to_score = {v: k for k, v in QUALITY_LABELS.items()}

        # Data structures to hold results
        all_data: Dict[str, Dict[str, Any]] = {}
        file_names: Dict[str, Dict[str, str]] = defaultdict(dict)

        # Get all available result files
        files = list_files_in_blob(folder=LABELLING_RESULTS_FOLDER, extension=".json")
        if not files:
            st.warning("No result files found in storage.")
            return None

        # Process each file
        for file_name in files:
            df = process_file_data(file_name)
            if df is None:
                continue

            run_id = df[_PROCESS_RESULTS_RUN_ID].iloc[0]
            user_name = df[USER_NAME].iloc[0]
            file_names.setdefault(run_id, {})[user_name] = file_name

            # Calculate scores
            df = calculate_score(df, quality_to_score)

            # Check for low variance
            if (
                check_for_low_variance
                and _PROCESS_RESULTS_SCORE in df.columns
                and df[_PROCESS_RESULTS_SCORE].std() < LOW_VARIANCE_THRESHOLD
            ):
                st.warning(
                    f"Low variance in Run: {run_id}; Score Mean: {df[_PROCESS_RESULTS_SCORE].mean():.2f}; "
                    f"User: {user_name}. Removing this run from analysis."
                )
                continue

            # Initialize data structure for this run
            if run_id not in all_data:
                all_data[run_id] = {_PROCESS_RESULTS_RAW_DATA: []}

            # Store data by user and in raw data list
            if user_name in all_data[run_id]:
                all_data[run_id][user_name] = pd.concat(
                    [all_data[run_id][user_name], df]
                )
            else:
                all_data[run_id][user_name] = df

            all_data[run_id][_PROCESS_RESULTS_RAW_DATA].append(df)

        # Merge data for each run
        for run_id, data in all_data.items():
            data[_PROCESS_RESULTS_DATA] = merge_dataframes_with_user_scores(
                data[_PROCESS_RESULTS_RAW_DATA]
            )

        return all_data


def progress_view_per_file(all_data: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """
    Generate a summary dataframe showing labelling progress per user for each run.

    Args:
        all_data (Dict[str, Dict[str, Any]]): Dictionary containing processed run data.

    Returns:
        pd.DataFrame: Summary dataframe with progress statistics.
    """
    labelled_samples: List[Dict[str, Union[str, int, float]]] = []

    for run_id, data in all_data.items():
        df: pd.DataFrame = data[_PROCESS_RESULTS_DATA]
        total_samples: int = df.shape[0]

        # Count non-NaN score values for each user
        score_columns = [
            col for col in df.columns if col.startswith(f"{_PROCESS_RESULTS_SCORE}_")
        ]
        for col in score_columns:
            user_name = col.split(f"{_PROCESS_RESULTS_SCORE}_")[1]
            count = df[col].notna().sum()
            percentage = (count / total_samples) * 100 if total_samples > 0 else 0

            labelled_samples.append(
                {
                    _PROCESS_RESULTS_RUN_ID: run_id,
                    "user_name": user_name,
                    "labelled_samples_count": count,
                    "labelled_percentage": percentage,
                }
            )

    return pd.DataFrame(labelled_samples)


def progress_view_labelled_by_at_least_n(
    all_data: Dict[str, Dict[str, Any]], n_values: List[int] = [1, 2]
) -> pd.DataFrame:
    """
    Generate a summary showing topics labelled by at least n users per run.

    Args:
        all_data (Dict[str, Dict[str, Any]]): Dictionary containing processed run data.
        n_values (List[int]): List of threshold values for checking labelling coverage.

    Returns:
        pd.DataFrame: Summary dataframe with coverage statistics.
    """
    results: List[Dict[str, Union[str, int, float]]] = []

    for run_id, data in all_data.items():
        df: pd.DataFrame = data[_PROCESS_RESULTS_DATA]
        total: int = df.shape[0]

        entry: Dict[str, Union[str, int, float]] = {_PROCESS_RESULTS_RUN_ID: run_id}
        score_columns = df.filter(like=_PROCESS_RESULTS_SCORE)

        for n in n_values:
            # Count rows with at least n non-null values in score columns
            count = df[score_columns.notna().sum(axis=1) >= n].shape[0]
            percentage = (count / total) * 100 if total > 0 else 0

            entry[f"labelled_by_at_least_{n}"] = count
            entry[f"labelled_percentage_at_least_{n}"] = percentage

        results.append(entry)

    return pd.DataFrame(results).sort_values(by=[_PROCESS_RESULTS_RUN_ID])
