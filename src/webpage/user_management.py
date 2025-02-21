import streamlit as st
import streamlit_authenticator as stauth

import yaml
from yaml.loader import SafeLoader

from config import USER_AUTH_CONFIG_FILE
from utils.azure_blob_utils import download_file_from_blob, upload_to_blob
from utils.st_utils import run_async
from webpage.labelling_consts import _USER_ROLE_KEY, DS_ROLE_KEY, USER_NAME


def auth_users():
    """
    Authenticates users and manages user sessions.

    Returns:
        None
    """
    st.session_state[_USER_ROLE_KEY] = False  # Data analysis view is protected by roles
    with st.sidebar:
        config_file = download_file_from_blob(USER_AUTH_CONFIG_FILE)
        if config_file is None:
            return
        config = yaml.load(config_file, Loader=SafeLoader)

        authenticator = stauth.Authenticate(
            config["credentials"],
            config["cookie"]["name"],
            config["cookie"]["key"],
            config["cookie"]["expiry_days"],
        )

        authenticator.login()

        if st.session_state["authentication_status"]:
            if st.session_state.get("name"):
                st.write(f'Welcome *{st.session_state["name"]}*')
            authenticator.logout()
            user_name = st.session_state.get("username")
            st.session_state[USER_NAME] = user_name
            if (
                config.get("credentials", {})
                .get("usernames", {})
                .get(user_name, {})
                .get(DS_ROLE_KEY)
            ):
                st.session_state[_USER_ROLE_KEY] = True

        elif st.session_state["authentication_status"] is False:
            st.error("Username/password is incorrect")
        elif st.session_state["authentication_status"] is None:
            st.warning("Please enter your username and password")
            with st.expander("Register"):
                try:
                    (
                        email_of_registered_user,
                        username_of_registered_user,
                        name_of_registered_user,
                    ) = authenticator.register_user(
                        pre_authorization=False, captcha=False
                    )
                    if email_of_registered_user:
                        st.success("User registered successfully")
                        run_async(
                            upload_to_blob(
                                file_name=USER_AUTH_CONFIG_FILE,
                                entry=yaml.dump(config, default_flow_style=False),
                            )
                        )
                except Exception as e:
                    st.error(e)
                    if "Password does not meet criteria" in str(e):
                        st.markdown(
                            """Password needs to meet the following criteria:

- It contains at least one lowercase letter.
- It contains at least one uppercase letter.
- It contains at least one digit.
- It contains at least one special character from the set @$!%*?&.
- It has a length between 8 and 20 characters."""
                        )
