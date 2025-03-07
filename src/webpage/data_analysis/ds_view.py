"""
Data Analysis view for the Data Scientist.

This module displays progress, summary statistics, and visualizations for labelling experiments.
"""

from typing import Any, Dict, List
import streamlit as st
import pandas as pd
import tabulate

from webpage.initial_st_setup import initial_setup
from webpage.data_analysis.load_labelling_results import (
    progress_view_labelled_by_at_least_n,
    progress_view_per_file,
    read_all_results,
)
from webpage.data_analysis.results_summary import (
    calculate_stats_for_all_runs,
    plot_correlation_heatmap,
    plot_score_distribution,
)
from webpage.labelling_consts import (
    _PROCESS_RESULTS_DATA as RESULTS_DATA_KEY,
    _PROCESS_RESULTS_SCORE,
)


def transform_pandas_df_to_markdown(df: pd.DataFrame) -> str:
    """
    Convert a pandas DataFrame to a Markdown-formatted table.

    Parameters:
        df (pd.DataFrame): The DataFrame to convert.

    Returns:
        str: A string representing the Markdown formatted table.
    """
    return tabulate.tabulate(df, headers="keys", tablefmt="pipe")


def progress_view(results: Dict[str, Any]) -> None:
    """
    Display labelling progress visualizations for experiments.

    Shows two sections: overall per-file progress and progress where
    files have been labelled by at least a specified number of users.

    Parameters:
        results (Dict[str, Any]): Dictionary containing labelling results.
    """
    st.markdown("# Labelling Progress")
    with st.expander("Progress per file"):
        per_file_progress = progress_view_per_file(results)
        st.markdown(transform_pandas_df_to_markdown(per_file_progress))
    with st.expander("Progress per file labelled by at least n users"):
        st.dataframe(progress_view_labelled_by_at_least_n(results))


def summary_view(results: Dict[str, Any]) -> None:
    """
    Display summary statistics for experiments.

    Dynamically determines numeric columns from the first experiment and
    allows selecting additional columns for processing.

    Parameters:
        results (Dict[str, Any]): Dictionary containing labelling results.
    """
    st.markdown("# Results Summary")
    # Use the first experiment to retrieve numeric columns.
    sample_df: pd.DataFrame = next(iter(results.values()))[RESULTS_DATA_KEY]
    numeric_columns = [
        col
        for col in sample_df.columns
        if pd.api.types.is_numeric_dtype(sample_df[col])
    ]
    selected_columns = st.multiselect(
        "Select additional columns to include in the summary", numeric_columns, []
    )
    summary_stats = calculate_stats_for_all_runs(
        results, columns_to_process=selected_columns
    )
    st.dataframe(summary_stats)


def correlation_analysis(results: Dict[str, Any]) -> None:
    """
    Perform and display correlation analysis on numeric metrics.

    Aggregates data across experiments and allows selection of metrics
    (excluding any score columns) for correlation heatmap visualization.

    Parameters:
        results (Dict[str, Any]): Dictionary containing labelling results.
    """
    run_data: pd.DataFrame = pd.concat(
        [data[RESULTS_DATA_KEY] for data in results.values()], ignore_index=True
    )
    available_metrics = [
        col
        for col in run_data.columns
        if pd.api.types.is_numeric_dtype(run_data[col]) and "score" not in col
    ]
    if not available_metrics:
        st.info("No additional metrics available for correlation analysis.")
        return

    selected_metrics = st.multiselect(
        "Select metrics for correlation", available_metrics, available_metrics
    )
    if selected_metrics:
        try:
            plot_correlation_heatmap(run_data, selected_metrics)
        except NameError:
            st.error(
                "Function plot_correlation_heatmap is not available in results_summary."
            )


def worst_scored_examples(results: Dict[str, Any]) -> None:
    """
    Display the top-10 worst scored examples across experiments.

    Aggregates labelling data, computes a mean score (across available score columns)
    for each row, and then presents the 10 rows with the lowest scores.

    Parameters:
        results (Dict[str, Any]): Dictionary containing labelling results.
    """
    st.markdown("## Top-10 Worst Scored Examples")

    # Combine labelling data from selected experiments.
    dataframes: List[pd.DataFrame] = [
        data[RESULTS_DATA_KEY] for data in results.values() if RESULTS_DATA_KEY in data
    ]
    if not dataframes:
        st.info("No labelling data available.")
        return

    combined_df: pd.DataFrame = pd.concat(dataframes, ignore_index=True)
    # Compute the mean score over all available score columns.
    score_columns = combined_df.filter(like=_PROCESS_RESULTS_SCORE)
    combined_df[_PROCESS_RESULTS_SCORE] = score_columns.mean(axis=1)

    if _PROCESS_RESULTS_SCORE not in combined_df.columns:
        st.error(f"Column '{_PROCESS_RESULTS_SCORE}' not found in the data.")
        return

    combined_df[_PROCESS_RESULTS_SCORE] = pd.to_numeric(
        combined_df[_PROCESS_RESULTS_SCORE], errors="coerce"
    )
    filtered_df = combined_df.dropna(subset=[_PROCESS_RESULTS_SCORE])
    worst_examples: pd.DataFrame = filtered_df.nsmallest(
        10, columns=[_PROCESS_RESULTS_SCORE]
    )
    st.write(worst_examples)


def ds_view() -> None:
    """
    Render the Data Scientist view of labelling experiments analysis.

    This consolidated view includes sections for progress monitoring, result summaries,
    score distributions, correlation analyses, and worst scored examples.
    """
    results: Dict[str, Any] = read_all_results()

    all_experiments: List[str] = list(results.keys())
    selected_experiments: List[str] = st.sidebar.multiselect(
        "Select the experiments to analyse", all_experiments, all_experiments
    )
    if not selected_experiments:
        st.warning("Please select at least one experiment.")
        return

    # Filter out unselected experiments.
    filtered_results: Dict[str, Any] = {
        k: v for k, v in results.items() if k in selected_experiments
    }

    progress_view(filtered_results)
    summary_view(filtered_results)

    st.markdown("# Score Distribution")
    for run_id in selected_experiments:
        plot_score_distribution(filtered_results, run_id=run_id, user_name=None)

    correlation_analysis(filtered_results)
    worst_scored_examples(filtered_results)


def main() -> None:
    """
    Set up the necessary initial configurations and launch the Data Scientist view.

    This function is the entry point when the module is executed as a script.
    """
    initial_setup()
    ds_view()


if __name__ == "__main__":
    main()
else:
    ds_view()
