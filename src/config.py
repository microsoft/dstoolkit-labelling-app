# Evaluation results storage for labeling
from utils.secret_manager import secret_manager
from dotenv import load_dotenv

load_dotenv()

AZURE_STORAGE_CONTAINER_NAME = lambda: secret_manager.get_secret(
    "AZURE_STORAGE_CONTAINER_NAME"
)
AZURE_STORAGE_CONNECTION_STRING = lambda: secret_manager.get_secret(
    "AZURE_STORAGE_CONNECTION_STRING"
)

if AZURE_STORAGE_CONTAINER_NAME() is None or AZURE_STORAGE_CONNECTION_STRING() is None:
    raise ValueError("Azure Blob Storage container name or connection string is None.")


LABELLING_RESULTS_FOLDER = "labelling_results/"  # Folder in the Azure Blob Storage where the labelling results are stored
LABELLING_DATETIME_FORMAT = (
    "%Y%m%d%H%M%S"  # Datetime format used in the labelling results file names
)


# Input file columns
EVALUATION_GT_COLUMN = (
    "ground_truth"  # Column name for the ground truth answers in the input file
)
QUESTION_COLUMN = "question"  # Column name for the question in the input file
PREDICTIONS_COLUMN = (
    "predictions"  # Column name for the model's predictions in the input file
)

REQUIRED_COLS = [
    EVALUATION_GT_COLUMN,
    QUESTION_COLUMN,
    PREDICTIONS_COLUMN,
]  # Required columns in the input file
# Optional columns
CONTEXT_COLUMN = "context"  # Column name for the context in the input file


# User auth config file
USER_AUTH_CONFIG_FILE = (
    "config.yaml"  # File name for the user authentication configuration file
)
