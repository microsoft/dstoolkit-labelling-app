# Define the categories for error analysis
ERROR_CATEGORIES = {
    1: {
        "label": "Syntax error",
        "description": "The code snippet contains a syntax error. This means there is a mistake in the structure or format of the code, making it impossible to execute.",
    },
    2: {
        "label": "Logic error",
        "description": "The code snippet contains a logic error. This means the code runs, but it doesn't do what it's supposed to do because of incorrect logic.",
    },
    3: {
        "label": "Performance issue",
        "description": "The code snippet has a performance issue. This means the code works, but it is not efficient and could be optimized to run faster or use fewer resources.",
    },
    4: {
        "label": "Hallucination",
        "description": "The code snippet contains a hallucination. This means the code includes elements or concepts that don't exist or are completely irrelevant to the task.",
    },
    5: {
        "label": "Other",
        "description": "The code snippet has an issue that doesn't fit into the other categories. This could be anything from missing functionality to incorrect usage of a function.",
    },
}
ERROR_CATEGORIES_LIST = [v["label"] for v in ERROR_CATEGORIES.values()]
ERROR_CATEGORIES_MARKDOWN = "\n".join(
    [f"- **{v['label']}**: {v['description']}" for v in ERROR_CATEGORIES.values()]
)

QUALITY_LABELS = {
    0: "Unusable",
    1: "Poor",
    2: "Average",
    3: "Good",
    4: "Very Good",
}

# Internal constants
USER_NAME = "user_name"
DS_ROLE_KEY = "data_scientist"  # Adding this key to the config file will give the user data scientist role, which gives access to the data analysis page.
FILE_NAME_SEPARATOR = "___"  # Triple underscores to reduce likelihood of conflicts

FILE_NAME = "file_name"
FILENAME_HASH = "filename_hash"
FILE_HASH = "file_hash"
QUESTION_HASH = "question_hash"
SEED = "seed"
FILE_SEED = "file_seed"
DATA = "data"
SELECTED_ROW_ID = "selected_row_id"

# Names of the columns in the results DataFrame
START_TIME_MS = "start_time_ms"
END_TIME_MS = "end_time_ms"

LABEL_QUALITY = "label_quality"
ANSWER_IS_BETTER = "answer_is_better"
FEEDBACK = "feedback"
FEEDBACK_DATA = "_feedback_data"

SYN_QA_RELEVANCE = "syn_qa_relevance"
SYN_CORRECTED_QUESTION = "syn_corrected_question"
SYN_GT_ANSWER = "syn_gt_answer"
SYN_DATA = "_syn_data"

ERROR_SNIPPET = "snippet"
ERROR = "error"
ERROR_DESCRIPTION = "description"
ERROR_ANALYSIS = "error_analysis"
ERROR_DATA = "_error_data"

# App title
APP_TITLE = "Labelling App"


# Internal config consts
_USER_ROLE_KEY = "user_is_ds"
_PROCESS_RESULTS_DATA = "data"
_PROCESS_RESULTS_RAW_DATA = "raw_data"
_PROCESS_RESULTS_SCORE = "score"
_PROCESS_RESULTS_RUN_ID = "run_id"
