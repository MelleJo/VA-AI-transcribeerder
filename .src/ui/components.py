import streamlit as st
import html
from docx import Document
from io import BytesIO
import pyperclip

def display_transcript(transcript):
    if transcript:
        with st.expander("Toon Transcript", expanded=False):
            st.markdown('<div class="transcript-box">', unsafe_allow_html=True)
            st.markdown('<h4>Transcript</h4>', unsafe_allow_html=True)
            st.markdown(f'<div class="content">{html.escape(transcript)}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

def display_summary(summary):
    if summary:
        st.markdown('<div class="summary-box">', unsafe_allow_html=True)
        
        # Split the summary into sections
        sections = summary.split('\n\n')
        
        # Display header information
        header_lines = sections[0].split('\n')
        st.markdown(f"<h3>{header_lines[0]}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p><strong>Datum en tijd:</strong> {header_lines[1]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p><strong>Gebruiker:</strong> {header_lines[2]}</p>", unsafe_allow_html=True)
        st.markdown(f"<p><strong>Gesproken met:</strong> {header_lines[3].split(': ')[1]}</p>", unsafe_allow_html=True)
        
        # Display main content
        for section in sections[1:-1]:  # Exclude the last section (action points)
            st.markdown(section)
        
        # Display action points
        action_points = sections[-1].split('\n')
        st.markdown("<h4>Actiepunten/deadlines/afspraken:</h4>", unsafe_allow_html=True)
        for point in action_points[1:]:  # Skip the header
            st.markdown(f"- {point}")
        
        st.markdown('</div>', unsafe_allow_html=True)

        # Add download and copy buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Download als Word"):
                doc = create_word_document(summary)
                st.download_button(
                    label="Download Word bestand",
                    data=doc,
                    file_name="samenvatting.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        with col2:
            if st.button("Kopieer naar klembord"):
                st.write("Samenvatting gekopieerd naar klembord!")
                pyperclip.copy(summary)

def create_word_document(content):
    doc = Document()
    doc.add_paragraph(content)
    doc_io = BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io.read()

def display_department_selector(departments):
    return st.selectbox("Kies je afdeling", departments, key='department_select')

def display_input_method_selector(input_methods):
    return st.radio("Wat wil je laten samenvatten?", input_methods, key='input_method_radio')

def display_text_input():
    return st.text_area("Voeg tekst hier in:", 
                        value=st.session_state.get('input_text', ''), 
                        height=300,
                        key='input_text_area')

def display_file_uploader(file_types):
    return st.file_uploader("Choose a file", type=file_types)

def display_summarize_button():
    return st.button("Samenvatten", key='summarize_button')

def display_copy_clipboard_button():
    return st.button("Kopieer naar klembord", key='copy_clipboard_button')

def display_progress_bar():
    return st.progress(0)

def display_spinner(text):
    return st.spinner(text)

def display_success(text):
    st.success(text)

def display_error(text):
    st.error(text)

def display_warning(text):
    st.warning(text)