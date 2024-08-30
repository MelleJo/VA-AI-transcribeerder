import streamlit as st
from docx import Document
import PyPDF2
import io

def process_uploaded_file(uploaded_file):
    file_extension = uploaded_file.name.split('.')[-1].lower()

    if file_extension == 'txt':
        return process_txt_file(uploaded_file)
    elif file_extension == 'docx':
        return process_docx_file(uploaded_file)
    elif file_extension == 'pdf':
        return process_pdf_file(uploaded_file)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

def process_txt_file(file):
    return file.getvalue().decode('utf-8')

def process_docx_file(file):
    doc = Document(file)
    return '\n'.join([paragraph.text for paragraph in doc.paragraphs])

def process_pdf_file(file):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.getvalue()))
    text = ''
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text