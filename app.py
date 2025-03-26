import streamlit as st
import fitz  # PyMuPDF
import io

def extract_text_from_pdf(uploaded_file):
    # Read the uploaded file into bytes
    pdf_bytes = uploaded_file.read()
    
    # Ensure the file is a valid PDF by checking the magic bytes (%PDF)
    if pdf_bytes[:4] != b'%PDF':
        raise ValueError("Not a valid PDF file")
    
    # Open the PDF from bytes using fitz (PyMuPDF)
    doc = fitz.open(io.BytesIO(pdf_bytes))  # Use BytesIO to handle the byte data

    # Extract text from each page in the PDF
    text = ""
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text += page.get_text()

    return text

def main():
    st.title("PDF Text Extractor")
    
    # Upload file
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        try:
            # Extract text from the PDF
            text = extract_text_from_pdf(uploaded_file)
            
            # Display the extracted text
            st.text_area("Extracted Text", text, height=300)
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
