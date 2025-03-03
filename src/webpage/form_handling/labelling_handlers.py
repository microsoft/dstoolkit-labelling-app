"""
Combined module for all labelling form handlers.
"""

from webpage.form_handling.quality_feedback_handler import QualityFeedbackHandler
from webpage.form_handling.error_feedback_handler import ErrorFeedbackHandler
from webpage.form_handling.ground_truth_handler import GroundTruthHandler

__all__ = [
    "QualityFeedbackHandler",
    "ErrorFeedbackHandler",
    "GroundTruthHandler",
]
