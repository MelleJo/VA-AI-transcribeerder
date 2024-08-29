# ui/components/fancy_select.py

import streamlit as st

def fancy_select(options, key_prefix):
    selected = None
    for option in options:
        if st.button(
            option,
            key=f"{key_prefix}_{option}",
            use_container_width=True,
        ):
            selected = option
    return selected