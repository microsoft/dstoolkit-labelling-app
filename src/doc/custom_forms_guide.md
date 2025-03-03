# Custom Forms Guide: Extending the Labelling App with Custom Data Collection

## Introduction

This guide demonstrates how to extend the Labelling App with custom forms for collecting specialized feedback during the labelling process. We'll walk through the general approach for creating new form handlers, integrating them into the labelling workflow, and visualizing the collected data in the data analysis view.

## Example Use Case: Context Precision Evaluation

As an example throughout this guide, we'll reference a custom form for evaluating retrieved context data precision. This could include:

1. Rating the context relevance on a scale
2. Identifying missing or irrelevant information
3. Collecting suggestions for improvement

However, the same principles apply to any custom form you might need, such as:

- User experience feedback
- Language quality assessment
- Source reliability evaluation
- Domain-specific evaluations

## Implementation Overview

### 1. Define Constants for Your Form

First, add the necessary constants in `src/webpage/labelling_consts.py` that define the form fields, values, and keys for data storage. Keep these organized and properly documented.

### 2. Create a New Form Handler

Create a file named `your_custom_handler.py` in the `src/webpage/form_handling` directory, implementing a class that extends `CustomFormHandler`:

```python
"""
Custom form handler for collecting specialized data.
"""

import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional

from webpage.form_handling.custom_form_handler import CustomFormHandler

class YourCustomHandler(CustomFormHandler):
    """Handler for your custom evaluation form."""
    
    def __init__(self, unique_identifier: str):
        """Initialize the custom form handler."""
        super().__init__(
            form_id="your_custom_form",
            form_title="Your Custom Form Title",
            data_key="_your_data_key",
            persistence_key=f"your_form_{unique_identifier}",
        )
        
    def render_custom_form(self) -> Dict[str, Any]:
        """Render your custom form fields."""
        # Implementation to render form fields using Streamlit widgets
        # and return the collected data as a dictionary
        
    def save_to_dataframe(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Save the custom form data to the dataframe."""
        # Implementation to save form data to the results dataframe
```

### 3. Update the Handlers Module

Add your new handler to `src/webpage/form_handling/labelling_handlers.py`:

```python
from webpage.form_handling.your_custom_handler import YourCustomHandler

__all__ = [
    'QualityFeedbackHandler',
    'ErrorFeedbackHandler',
    'GroundTruthHandler',
    'YourCustomHandler',  # Add your handler here
]
```

### 4. Integrate with the Labelling Page

Update `src/webpage/labelling_page.py` to include your new custom form:

```python
from webpage.form_handling.labelling_handlers import (
    QualityFeedbackHandler,
    ErrorFeedbackHandler,
    GroundTruthHandler,
    YourCustomHandler  # Import your handler
)

# In the appropriate section of the code:
with st.expander("Your Custom Form Section"):
    custom_handler = YourCustomHandler(unique_identifier)
    custom_handler.render_form(custom_handler.render_custom_form, 
                             button_name="Submit Custom Data")
```

## Visualizing Custom Form Data in the Analysis View

To visualize the collected custom form data in the data analysis view:

### 1. Add a Custom Analysis Section

Update `src/webpage/data_analysis/ds_view.py` to include a new section for your custom data:

```python
def custom_data_analysis(results: Dict[str, Any]) -> None:
    """
    Analyze and visualize custom data collected from evaluators.
    
    Parameters:
        results (Dict[str, Any]): Dictionary containing labelling results.
    """
    st.markdown("# Your Custom Analysis Section")
    
    # Combine data from all experiments
    custom_data = []
    for run_id, data in results.items():
        df = data[RESULTS_DATA_KEY]
        if "your_data_column" not in df.columns:
            continue
            
        run_custom_data = df[["your_data_column", "other_column"]].copy()
        run_custom_data['run_id'] = run_id
        custom_data.append(run_custom_data)
    
    if not custom_data:
        st.info("No custom data available.")
        return
        
    combined_df = pd.concat(custom_data, ignore_index=True)
    
    # Create visualizations based on your data
    # Examples: bar charts, histograms, scatter plots, etc.
```

### 2. Create Relevant Visualizations

Add functions to analyze and visualize patterns in your custom data:

```python
def plot_custom_data_metrics(combined_df: pd.DataFrame) -> None:
    """
    Create visualizations of custom data metrics.
    
    Parameters:
        combined_df (pd.DataFrame): DataFrame with combined custom data.
    """
    # Implementation to extract and visualize patterns from your custom data
```

## Integration Example

This is how you would integrate any custom form with the existing workflow:

1. User uploads data containing information relevant to your form
2. During labelling, the user can fill out your custom form
3. The custom form data is saved alongside other feedback
4. In the data analysis view, data scientists can see visualizations of your custom metrics

## Conclusion

By following this guide, you can add new custom forms to collect specific feedback about any aspect of your data or model outputs, and integrate them seamlessly with the existing labelling workflow. The collected data can be visualized in the data analysis view to provide insights relevant to your specific use case.

Remember to adjust the implementation details based on your requirements and integrate with your existing code patterns.
