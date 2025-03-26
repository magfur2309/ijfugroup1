import streamlit as st
import fitz  # PyMuPDF

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(pdf_file)
    text = ""
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text += page.get_text("text")
    return text

# Streamlit UI
def main():
    st.title("PDF to Text Converter")

    st.markdown("Upload a PDF file to extract its text.")

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        # Extract text from the uploaded PDF
        text = extract_text_from_pdf(uploaded_file)

        st.subheader("Extracted Text")
        st.text_area("Text from PDF", text, height=300)

if __name__ == "__main__":
    main()
