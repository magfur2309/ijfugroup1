import pdfplumber

pdf_path = "file_path.pdf"  # Ubah sesuai nama file PDF

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n===== Halaman {i+1} =====\n")
        print(page.extract_text())
