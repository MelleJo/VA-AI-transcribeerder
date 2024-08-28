import streamlit as st
import html

def display_summary(summary):
    if summary:
        st.markdown('<div class="summary-box">', unsafe_allow_html=True)
        st.markdown('<h3>Samenvatting</h3>', unsafe_allow_html=True)
        st.markdown(summary, unsafe_allow_html=True)
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