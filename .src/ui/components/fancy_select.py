import streamlit as st
import os

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