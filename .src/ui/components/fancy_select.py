# Create a new file: ui/components/fancy_select.py

import streamlit as st
from streamlit_antd.button import st_antd_button

def fancy_select(options, key_prefix):
    selected = None
    for option in options:
        if st_antd_button(
            option,
            type="default",
            style={
                "width": "100%",
                "margin-bottom": "10px",
                "height": "50px",
                "font-size": "16px",
                "display": "flex",
                "align-items": "center",
                "justify-content": "left",
                "padding-left": "20px",
                "border-radius": "8px",
                "transition": "all 0.3s",
            },
            key=f"{key_prefix}_{option}"
        ):
            selected = option
    return selected

