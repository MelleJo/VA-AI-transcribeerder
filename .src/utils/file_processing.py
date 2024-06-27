import tempfile
from PyPDF2 import PdfReader
from docx import Document

def read_docx(file_path):
    doc = Document(file_path)
    fullText = []
    for para in doc.paragraphs:
        fullText.append(para.text)
    return '\n'.join(fullText)

def process_uploaded_file(uploaded_file):
    if uploaded_file.name.endswith('.docx'):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
            tmp_docx.write(uploaded_file.getvalue())
            tmp_docx_path = tmp_docx.name
        transcript = read_docx(tmp_docx_path)
        tempfile.NamedTemporaryFile(delete=True)
    elif uploaded_file.name.endswith('.pdf'):
        pdf_reader = PdfReader(uploaded_file)
        transcript = ""
        for page in pdf_reader.pages:
            transcript += page.extract_text()
    else:
        transcript = uploaded_file.getvalue().decode("utf-8")
    
    return transcript