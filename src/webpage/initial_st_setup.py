from utils.logger import logger

from utils.st_utils import LOGO_ICON
from webpage.labelling_consts import APP_TITLE
import streamlit as st
from streamlit.errors import StreamlitAPIException
from webpage.user_management import auth_users


def initial_setup():
    if "page_configured" not in st.session_state:
        try:
            st.set_page_config(page_title=APP_TITLE, page_icon=LOGO_ICON, layout="wide")

            st.session_state["page_configured"] = True
        except StreamlitAPIException as e:
            # Error will be thrown if initial_setup is called more than once
            logger.error(f"Error initialising the page config: {e}")

    auth_users()
    # You can use st.session_state["authentication_status"] to check if the user is authenticated
    # This application allows to continue without authentication
