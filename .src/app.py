import streamlit as st
from config import load_config
from ui.pages import render_page
from ui.components import setup_page_style, initialize_session_state

def main():
    try:
        # Load configuration
        config = load_config()

        # Set up Streamlit page
        st.set_page_config(
            page_title=config["APP_TITLE"],
            page_icon=config["APP_ICON"],
            layout=config["APP_LAYOUT"]
        )

        # Set up page style and initialize session state
        setup_page_style()
        initialize_session_state(config)

        # Render the appropriate page based on the current step
        render_page(st.session_state.current_step)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.stop()

if __name__ == "__main__":
    main()
