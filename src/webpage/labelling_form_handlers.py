"""
Specialized form handlers for the labelling app.
This is a compatibility module that re-exports the handlers from their new locations.
"""

from webpage.form_handling.quality_feedback_handler import QualityFeedbackHandler
from webpage.form_handling.error_feedback_handler import ErrorFeedbackHandler
from webpage.form_handling.ground_truth_handler import GroundTruthHandler

# Re-export the handlers to maintain backward compatibility
__all__ = [
    "QualityFeedbackHandler",
    "ErrorFeedbackHandler",
    "GroundTruthHandler",
]
