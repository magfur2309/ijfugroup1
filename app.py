import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import hashlib

def extract_full_text(pdf_file):
    """Menggabungkan teks dari semua halaman untuk mencegah kehilangan data antar halaman."""
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    return full_text

def extract_table_data(pdf_file):
    """Menggunakan pdfplumber untuk mengekstrak tabel dengan lebih akurat."""
    data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and any(row):  # Pastikan ada data
                        data.append(row)
    return data

def extract_invoice_details(pdf_file):
    """Ekstrak informasi faktur seperti nomor faktur, nama penjual, dan pembeli."""
    text = extract_full_text(pdf_file)
    
    no_fp = re.search(r'Kode dan Nomor Seri Faktur Pajak:\s*(\d+)', text)
    nama_penjual = re.search(r'Pengusaha Kena Pajak:\s*Nama\s*:\s*([\w\s\-.,&()]+)', text)
    nama_pembeli = re.search(r'Pembeli.*?:\s*Nama\s*:\s*([\w\s\-.,&()]+)', text)
    
    return {
        "no_fp": no_fp.group(1) if no_fp else "Tidak ditemukan",
        "nama_penjual": nama_penjual.group(1).strip() if nama_penjual else "Tidak ditemukan",
        "nama_pembeli": nama_pembeli.group(1).strip() if nama_pembeli else "Tidak ditemukan",
    }

def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            invoice_details = extract_invoice_details(uploaded_file)
            table_data = extract_table_data(uploaded_file)
            
            for row in table_data:
                if len(row) >= 4:  # Pastikan baris memiliki cukup data
                    all_data.append([
                        invoice_details["no_fp"], invoice_details["nama_penjual"], invoice_details["nama_pembeli"],
                        row[0], row[1], row[2], row[3]
                    ])
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Kode", "Nama Barang", "Qty", "Harga"])
            df.index += 1  
            
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
            output.seek(0)
            st.download_button(label="\U0001F4E5 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def login_page():
    users = {
        "user1": hashlib.sha256("ijfugroup1".encode()).hexdigest(),
        "user2": hashlib.sha256("ijfugroup2".encode()).hexdigest()
    }
    
    st.title("Login Convert PDF FP To Excel")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
        submit_button = st.form_submit_button("Login")
    
    if submit_button:
        if username in users and hashlib.sha256(password.encode()).hexdigest() == users[username]:
            st.session_state["logged_in"] = True
            st.success("Login berhasil! Selamat Datang")
        else:
            st.error("Username atau password salah")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    main_app()
