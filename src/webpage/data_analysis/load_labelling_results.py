import pandas as pd
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

import streamlit as st

from config import LABELLING_RESULTS_FOLDER
from utils.azure_blob_utils import download_file_from_blob, list_files_in_blob
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
from utils.logger import logger

LOW_VARIANCE_THRESHOLD = 0.1


def calculate_score(df: pd.DataFrame, quality_to_score: Dict[Any, Any]) -> pd.DataFrame:
    """
    Calculate and normalize scores for each row in the dataframe based on the provided quality_to_score dictionary.

    Parameters:
        df (pd.DataFrame): Dataframe containing the labelling quality column.
        quality_to_score (Dict[Any, Any]): Dictionary mapping quality labels to their corresponding scores.

    Returns:
        pd.DataFrame: Dataframe with an added/updated score column.
    """
    df[_PROCESS_RESULTS_SCORE] = df[LABEL_QUALITY].apply(quality_to_score.get) / len(
        QUALITY_LABELS
    )
    return df


def merge_runs_data(raw_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Merge a list of dataframes that belong to a single run. Renames the score column to include the user name
    from each dataframe and performs an outer merge on the index.

    Parameters:
        raw_dfs (List[pd.DataFrame]): List of dataframes corresponding to multiple users in the same run.

    Returns:
        pd.DataFrame: Merged dataframe containing data from all users with unified score columns.
    """
    merged_df: Optional[pd.DataFrame] = None
    for df in raw_dfs:
        user: str = df[USER_NAME].iloc[0]
        df = df.copy()
        # Rename the score column to include the user name
        df.rename(
            columns={_PROCESS_RESULTS_SCORE: f"{_PROCESS_RESULTS_SCORE}_{user}"},
            inplace=True,
        )
        if merged_df is None:
            merged_df = df
        else:
            # Outer merge on index and reconcile duplicate columns
            col_sep = "$$dup"
            merged_df = pd.merge(
                merged_df,
                df,
                how="outer",
                left_index=True,
                right_index=True,
                suffixes=("", col_sep),
            )
            for col in list(merged_df.columns):
                if col.endswith(col_sep):
                    original_col = col[: -len(col_sep)]
                    merged_df[original_col] = merged_df[original_col].fillna(
                        merged_df[col]
                    )
                    merged_df.drop(columns=col, inplace=True)
    return merged_df  # type: ignore


@st.cache_data()
@st.spinner(text="Loading labelled results...")
def read_all_results(check_for_low_variance: bool = True) -> Optional[Dict[Any, Any]]:
    """
    Read and process labelling results from blob storage. Loads JSON files, computes scores and merges data by run.

    Parameters:
        check_for_low_variance (bool): Flag to check for low variance in scores. If the standard deviation
                                       of scores in a run is below a threshold, that run is skipped.

    Returns:
        Optional[Dict[Any, Any]]:
            A dictionary keyed by run_id. Each value is a dictionary containing:
            - _PROCESS_RESULTS_RAW_DATA: a list of raw dataframes for the run.
            - _PROCESS_RESULTS_DATA: the merged dataframe after processing.
            Also includes metadata information for each file.
            Returns None if no files were found.
    """
    quality_to_score = {v: k for k, v in QUALITY_LABELS.items()}

    all_data: Dict[str, Dict[str, Any]] = {}
    meta_data: Dict[str, Dict[str, Any]] = {}
    file_names: Dict[str, Dict[str, str]] = defaultdict(dict)

    files = list_files_in_blob(folder=LABELLING_RESULTS_FOLDER, extension=".json")
    if not files:
        return None

    for file_name in files:
        file = download_file_from_blob(file_name)
        if file is None:
            continue

        try:
            df = read_data_from_file(file)
            if df is None:
                st.error("Error loading data from file.")
                continue
        except Exception as e:
            logger.error(f"Error loading data from file {file_name}: {e}")
            st.warning(f"Error loading data from file. {e}")
            continue

        run_id, user_name = decode_file_name(file_name)
        meta_data[file_name] = {
            _PROCESS_RESULTS_RUN_ID: run_id,
            USER_NAME: user_name,
        }

        # Add run_id and user_name columns
        df[_PROCESS_RESULTS_RUN_ID] = run_id
        df[USER_NAME] = user_name
        file_names.setdefault(run_id, {})[user_name] = file_name

        # Initialize missing quality label column if not present
        if LABEL_QUALITY not in df.columns:
            df[LABEL_QUALITY] = None

        # Calculate score and filter out low variance runs
        df = calculate_score(df, quality_to_score)
        if (
            check_for_low_variance
            and df[_PROCESS_RESULTS_SCORE].std() < LOW_VARIANCE_THRESHOLD
        ):
            st.warning(
                f"Low variance in Run: {run_id}; Score Mean: {df[_PROCESS_RESULTS_SCORE].mean()}; User: {user_name}. "
                "Removing this run from analysis."
            )
            continue

        if run_id not in all_data:
            all_data[run_id] = {_PROCESS_RESULTS_RAW_DATA: []}

        # Combine data for the same user in the same run
        if user_name in all_data[run_id]:
            all_data[run_id][user_name] = pd.concat([all_data[run_id][user_name], df])
        else:
            all_data[run_id][user_name] = df

        all_data[run_id][_PROCESS_RESULTS_RAW_DATA].append(df)

    # Combine all raw dataframes for each run
    for run_id, data in all_data.items():
        data[_PROCESS_RESULTS_DATA] = merge_runs_data(data[_PROCESS_RESULTS_RAW_DATA])
    return all_data


def progress_view_per_file(all_data: Dict[Any, Any]) -> pd.DataFrame:
    """
    Generate a summary dataframe that shows the count and percentage of labelled samples per user for each run.

    Parameters:
        all_data (Dict[Any, Any]): Dictionary containing run data. Each key represents a run and its value contains
                                   the merged dataframe among other information.

    Returns:
        pd.DataFrame: Summary dataframe with each row representing a user per run along with counts and percentages.
    """
    labelled_samples: List[Dict[str, Union[str, int, float]]] = []
    for run_id, data in all_data.items():
        df: pd.DataFrame = data[_PROCESS_RESULTS_DATA]
        total_samples: int = df.shape[0]
        # Count non-NaN score values for each user's score column
        labelled_count = df.filter(like=_PROCESS_RESULTS_SCORE).notna().sum(axis=0)
        for col, count in labelled_count.items():
            if col.startswith(f"{_PROCESS_RESULTS_SCORE}_"):
                user_name = col.split(f"{_PROCESS_RESULTS_SCORE}_")[1]
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
    all_data: Dict[Any, Any], n_values: List[int] = [1, 2]
) -> pd.DataFrame:
    """
    Generate a summary dataframe showing how many topics have been labelled by at least n users per run.

    Parameters:
        all_data (Dict[Any, Any]): Dictionary containing run data with merged dataframes.
        n_values (List[int], optional): List of threshold values for minimum number of users who should have labelled a topic.
                                        Defaults to [1, 2].

    Returns:
        pd.DataFrame: Summary dataframe that includes counts and percentages of topics labelled by at least n users, sorted by run_id.
    """
    labelled_by_at_least_n: Dict[Any, Dict[int, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    total_topics: Dict[Any, int] = {}
    for run_id, data in all_data.items():
        df: pd.DataFrame = data[_PROCESS_RESULTS_DATA]
        total: int = df.shape[0]
        total_topics[run_id] = total
        score_columns = df.filter(like=_PROCESS_RESULTS_SCORE)
        for n in n_values:
            count = df[score_columns.columns][
                score_columns.notna().sum(axis=1) >= n
            ].shape[0]
            labelled_by_at_least_n[run_id][n] = count

    # Compile results including percentage values
    results: List[Dict[str, Union[str, int, float]]] = []
    for run_id in all_data.keys():
        total: int = total_topics.get(run_id, 0)
        entry: Dict[str, Union[str, int, float]] = {_PROCESS_RESULTS_RUN_ID: run_id}
        for n in n_values:
            count = labelled_by_at_least_n[run_id].get(n, 0)
            percentage = (count / total) * 100 if total > 0 else 0
            entry[f"labelled_by_at_least_{n}"] = count
            entry[f"labelled_percentage_at_least_{n}"] = percentage
        results.append(entry)

    return pd.DataFrame(results).sort_values(by=[_PROCESS_RESULTS_RUN_ID])
