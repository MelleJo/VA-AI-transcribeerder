import streamlit as st

def update_progress(progress_placeholder, step_description, current_step, total_steps):
    """
    Update the progress bar and status message in the Streamlit app.

    :param progress_placeholder: Streamlit placeholder for the progress bar.
    :param step_description: Description of the current step.
    :param current_step: Current step number.
    :param total_steps: Total number of steps.
    """
    progress = current_step / total_steps
    progress_placeholder.progress(progress, text=f"{step_description} ({current_step}/{total_steps})")
    progress_placeholder.markdown(
        f"""
        <div style="text-align: center;">
            <strong>{step_description}</strong><br>
            Step {current_step} of {total_steps}<br>
            <progress value="{current_step}" max="{total_steps}" style="width: 100%;"></progress>
        </div>
        """,
        unsafe_allow_html=True
    )
