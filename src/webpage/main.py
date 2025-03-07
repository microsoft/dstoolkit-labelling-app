"""
Main entry point for the labelling application.
This script initializes the Streamlit interface and sets up navigation based on user role.
"""
import streamlit as st
from webpage.initial_st_setup import initial_setup
from webpage.labelling_consts import _USER_ROLE_KEY


def main():
    """Initialize the application and set up navigation based on user role."""
    # Set up initial Streamlit configuration
    initial_setup()

    # Always include the labelling view as the default page
    pages = [st.Page("labelling_page.py", title="Labelling View", default=True)]

    # Add data analysis view for users with appropriate role
    if st.session_state.get(_USER_ROLE_KEY) is True:
        data_analysis_view = st.Page(
            "data_analysis/ds_view.py", title="Data Analysis View"
        )
        pages.append(data_analysis_view)

    # Run the navigation with configured pages
    page_navigation = st.navigation(pages)
    page_navigation.run()


if __name__ == "__main__":
    main()
