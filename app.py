import streamlit as st
import fitz  # PyMuPDF
import io
import re
import pandas as pd

def extract_text_from_pdf(uploaded_file):
    # Read the uploaded file into bytes
    pdf_bytes = uploaded_file.read()

    # Ensure the file is a valid PDF by checking the magic bytes (%PDF)
    if pdf_bytes[:4] != b'%PDF':
        raise ValueError("Not a valid PDF file")
    
    # Open the PDF from bytes using fitz (PyMuPDF)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")  # Correct way to use the byte stream

    # Extract text from each page in the PDF
    text = ""
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text += page.get_text()

    return text

# Function to extract relevant data (No, Item Name, Quantity, and Price) from the extracted text
def extract_relevant_data(text):
    # Regex pattern to capture the required information: No, Item Name, Quantity, and Price
    pattern = r"(\d+)\s([A-Za-z0-9\s]+)\s(\d+)\s(?:[xX])\s?([\d,.]+)\s?(?:Kilogram|Katalog|Rp\s[\d,.]+)?"
    
    # Find all matches based on the regex pattern
    matches = re.findall(pattern, text)
    
    # Create a DataFrame with extracted data
    data = {
        "No": [match[0] for match in matches],
        "Item Name": [match[1].strip() for match in matches],
        "Quantity": [match[2] for match in matches],
        "Price": [match[3] for match in matches]
    }
    
    df = pd.DataFrame(data)
    return df

def main():
    st.title("PDF Text Extractor")
    
    # Upload file
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        try:
            # Extract text from the PDF
            text = extract_text_from_pdf(uploaded_file)
            
            # Extract relevant data (No, Item Name, Quantity, Price)
            extracted_data = extract_relevant_data(text)
            
            # Display the extracted data in a table
            st.write("Extracted Data:")
            st.dataframe(extracted_data)
            
            # Provide option to download the extracted data as an Excel file
            excel_file = io.BytesIO()
            with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
                extracted_data.to_excel(writer, index=False, sheet_name="Extracted Data")
            
            excel_file.seek(0)
            st.download_button(
                label="Download Excel file",
                data=excel_file,
                file_name="extracted_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
