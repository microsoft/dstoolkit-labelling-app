# Constants


# Define threshold for identifying potentially problematic labelling patterns
# When a user assigns nearly identical scores across all samples (low variance),
# it may indicate inattentive labelling, misunderstanding of the task, or using
# a default response. We filter out these runs to improve the quality and
# reliability of our analysis results.
LOW_VARIANCE_THRESHOLD = 0.1
