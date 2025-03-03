import streamlit as st  # added for Streamlit
from typing import Dict, Tuple, List, Optional, Any
from scipy import stats
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.logger import logger
from webpage.labelling_consts import _PROCESS_RESULTS_SCORE


def calculate_mean_and_conf_interval(
    scores: pd.Series, confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate the mean and the half-width of the confidence interval for a set of scores.

    Parameters:
        scores (pd.Series): A Pandas Series of numerical score values.
        confidence (float): Confidence level for the interval (default is 0.95).

    Returns:
        Tuple[float, float]: A tuple containing the mean score and the plus-minus value
                             (half-width) of the confidence interval. If there are fewer than
                             2 data points, returns the mean with np.nan for the interval.
    """
    if len(scores) < 2:
        return scores.mean(), np.nan
    mean_score = scores.mean()
    sem = stats.sem(scores)
    # In case sem is 0 or nan, the interval will be degenerate.
    conf_interval = stats.t.interval(
        confidence, df=len(scores) - 1, loc=mean_score, scale=sem
    )
    conf_interval_pm = conf_interval[1] - mean_score
    return mean_score, conf_interval_pm


def process_run_data(
    run_id: str, run_data: pd.DataFrame, columns_to_process: List[str]
) -> Tuple[float, float, Dict[str, float], Dict[str, float], int]:
    """
    Process data for a single run by computing the mean quality score and additional metrics
    along with their confidence intervals.

    Parameters:
        run_id (str): The identifier for the run.
        run_data (pd.DataFrame): DataFrame containing data for this run.
        columns_to_process (List[str]): List of column names for additional metrics to process.

    Returns:
        Tuple containing:
            - mean_score (float): Mean quality score of the run.
            - conf_interval_pm (float): Plus-minus value for the confidence interval of the scores.
            - avg_metrics (Dict[str, float]): Dictionary of mean values for each metric.
            - conf_intervals (Dict[str, float]): Dictionary of confidence interval half-widths for each metric.
            - num_scores (int): The number of score samples processed.
    """
    # Compute the mean across all score columns for each sample.
    scores = run_data.filter(like=_PROCESS_RESULTS_SCORE).dropna(thresh=1).mean(axis=1)
    mean_score, conf_interval_pm = calculate_mean_and_conf_interval(scores)

    avg_metrics: Dict[str, float] = {}
    conf_intervals: Dict[str, float] = {}
    for col in columns_to_process:
        if col not in run_data.columns:
            avg_metrics[col] = np.nan
            conf_intervals[col] = np.nan
            continue
        # Align the metric with the score index to ensure same data points
        metric = run_data.loc[scores.index, col].dropna()
        avg_metrics[col] = metric.mean() if not metric.empty else np.nan
        _, conf_intervals[col] = calculate_mean_and_conf_interval(metric)

    return mean_score, conf_interval_pm, avg_metrics, conf_intervals, len(scores)


def calculate_stats_for_all_runs(
    all_data: Dict[str, Dict[str, Any]], columns_to_process: List[str]
) -> pd.DataFrame:
    """
    Aggregate statistics for all runs by computing quality scores and additional metrics.

    Parameters:
        all_data (Dict[str, Dict[str, Any]]): Dictionary mapping run IDs to a dictionary that
                                               contains the run's data under the key "data".
        columns_to_process (List[str]): List of additional metric column names to include.

    Returns:
        pd.DataFrame: A DataFrame summarizing the mean scores, confidence intervals, and metrics for each run.
    """
    avg_scores: Dict[str, float] = {}
    conf_intervals_scores: Dict[str, float] = {}
    num_values: Dict[str, int] = {}
    # For each additional metric, we create a mapping run_id -> value
    avg_metrics_all: Dict[str, Dict[str, float]] = {
        col: {} for col in columns_to_process
    }
    conf_intervals_all: Dict[str, Dict[str, float]] = {
        col: {} for col in columns_to_process
    }

    for run_id, data in all_data.items():
        run_data = data["data"]
        (
            mean_score,
            conf_interval_pm,
            run_avg_metrics,
            run_conf_intervals,
            num_scores,
        ) = process_run_data(run_id, run_data, columns_to_process)
        avg_scores[run_id] = mean_score
        conf_intervals_scores[run_id] = conf_interval_pm
        num_values[run_id] = num_scores

        for col in columns_to_process:
            avg_metrics_all[col][run_id] = run_avg_metrics.get(col, np.nan)
            conf_intervals_all[col][run_id] = run_conf_intervals.get(col, np.nan)

    # Build the results DataFrame.
    results_dict = {
        "Run ID": list(avg_scores.keys()),
        "Mean Score": [
            f"{avg_scores[run_id]:.2f} ± {conf_intervals_scores[run_id]:.2f}"
            for run_id in avg_scores.keys()
        ],
        "Num Samples": [num_values[run_id] for run_id in avg_scores.keys()],
    }
    for col in columns_to_process:
        results_dict[f"Mean {col.replace('_', ' ').title()}"] = [
            f"{avg_metrics_all[col][run_id]:.2f} ± {conf_intervals_all[col][run_id]:.2f}"
            for run_id in avg_scores.keys()
        ]

    results_df = pd.DataFrame(results_dict)
    return results_df


def plot_score_distribution(
    all_data: Dict[str, Dict[str, Any]], run_id: str, user_name: Optional[str] = None
) -> None:
    """
    Plot the distribution of quality scores for a specific run using Plotly.

    Parameters:
        all_data (Dict[str, Dict[str, Any]]): Dictionary mapping run IDs to their data (under key "data").
        run_id (str): The run identifier for which to plot the distribution.
        user_name (Optional[str]): Optionally, a user name to filter and select a specific score column.

    Returns:
        None
    """
    run_data = all_data[run_id]["data"]

    if user_name:
        score_key = f"{_PROCESS_RESULTS_SCORE}_{user_name}"
        score = run_data[run_data[score_key].notna()][score_key]
    else:
        score = run_data.filter(like=_PROCESS_RESULTS_SCORE).mean(axis=1)

    fig = px.histogram(
        score,
        nbins=20,
        title=f"Distribution of the Scores ({run_id})",
        labels={"value": "Quality Score"},
    )
    fig.update_layout(
        xaxis_title="Quality Score",
        yaxis_title="Frequency",
        bargap=0.1,
    )

    st.plotly_chart(fig)


def plot_correlation_heatmap(run_data: pd.DataFrame, metrics: List[str]) -> None:
    """
    Generate and display a correlation heatmap of quality scores and additional metrics.

    The heatmap includes formatted annotations for correlation coefficients and their
    corresponding p-values.

    Parameters:
        run_data (pd.DataFrame): DataFrame containing the scores and metric columns.
        metrics (List[str]): List of metric column names to include in the analysis.

    Returns:
        None
    """
    score_columns = [col for col in run_data.columns if "score" in col.lower()]
    # Merge and sort to keep a consistent order
    columns_to_plot = sorted(list(set(score_columns + metrics)))
    data_subset = run_data[columns_to_plot].copy()

    # Compute correlation matrix
    corr_matrix = data_subset.corr()

    # Remove completely empty rows and columns
    corr_matrix.dropna(axis=0, how="all", inplace=True)
    corr_matrix.dropna(axis=1, how="all", inplace=True)
    if corr_matrix.empty:
        st.warning("Not enough data to compute correlations.")
        return

    # Compute p-values for the correlations via pairwise computation
    p_values = pd.DataFrame(
        np.ones(corr_matrix.shape), index=corr_matrix.index, columns=corr_matrix.columns
    )
    for col1 in corr_matrix.index:
        for col2 in corr_matrix.columns:
            x = data_subset[col1]
            y = data_subset[col2]
            valid_mask = x.notna() & y.notna()
            valid_count = valid_mask.sum()

            if valid_count < 2:
                p_values.loc[col1, col2] = np.nan
            else:
                try:
                    _, p_value = stats.pearsonr(x[valid_mask], y[valid_mask])
                    p_values.loc[col1, col2] = p_value
                except Exception as e:
                    logger.warning(
                        f"Error calculating correlation for {col1} and {col2}: {e}"
                    )
                    p_values.loc[col1, col2] = np.nan

    # Create a combined dataframe with formatted correlation and p-value values
    combined_text = corr_matrix.copy()
    for row in corr_matrix.index:
        for col in corr_matrix.columns:
            r_value = corr_matrix.loc[row, col]
            p_value = p_values.loc[row, col]
            if pd.isna(r_value) or pd.isna(p_value):
                combined_text.loc[row, col] = ""
            else:
                combined_text.loc[row, col] = f"{r_value:.2f} ({p_value:.2f})"
    st.dataframe(combined_text)

    # Create annotations with both correlation and p-value
    annotations = corr_matrix.copy().astype(str)
    for row in corr_matrix.index:
        for col in corr_matrix.columns:
            r_value = corr_matrix.loc[row, col]
            p_value = p_values.loc[row, col]
            if pd.isna(r_value) or pd.isna(p_value):
                annotations.loc[row, col] = ""
            else:
                annotations.loc[row, col] = f"{r_value:.2f}\np={p_value:.2f}"

    # Plot heatmap with annotations using Plotly
    fig = go.Figure(
        data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            text=annotations.values,
            texttemplate="%{text}",
            colorscale="RdBu",
            reversescale=True,
            colorbar=dict(title="Correlation"),
        )
    )
    fig.update_layout(
        title="Correlation Heatmap of Scores and Metrics",
        xaxis_title="Metrics",
        yaxis_title="Metrics",
        width=800,
        height=600,
    )

    st.plotly_chart(fig)
