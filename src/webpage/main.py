import streamlit as st
from webpage.initial_st_setup import initial_setup
from webpage.labelling_consts import _USER_ROLE_KEY


if __name__ == "__main__":
    initial_setup()
    pages = [st.Page("labelling_page.py", title="Labelling View", default=True)]
    if st.session_state.get(_USER_ROLE_KEY) is True:
        ds_view = st.Page("data_analysis/ds_view.py", title="Data Analysis View")
        pages.append(ds_view)

    pg = st.navigation(pages)
    pg.run()
