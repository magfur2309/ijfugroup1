import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
import hashlib

def find_invoice_date(pdf_file):
    month_map = {
        "Januari": "01", "Februari": "02", "Maret": "03", "April": "04", "Mei": "05", "Juni": "06", 
        "Juli": "07", "Agustus": "08", "September": "09", "Oktober": "10", "November": "11", "Desember": "12"
    }
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                date_match = re.search(r'\b(\d{1,2})\s*(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s*(\d{4})\b', text, re.IGNORECASE)
                if date_match:
                    day, month, year = date_match.groups()
                    return f"{day.zfill(2)}/{month_map[month]}/{year}"
    return "Tidak ditemukan"

def extract_data_from_pdf(pdf_file, tanggal_faktur):
    data = []
    no_fp, nama_penjual, nama_pembeli = None, None, None
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                no_fp_match = re.search(r'Kode dan Nomor Seri Faktur Pajak:\s*(\d+)', text)
                if no_fp_match:
                    no_fp = no_fp_match.group(1)
                
                penjual_match = re.search(r'Nama\s*:\s*([\w\s\-.,&()]+)\nAlamat', text)
                if penjual_match:
                    nama_penjual = penjual_match.group(1).strip()
                
                pembeli_match = re.search(r'Pembeli.*?:\s*Nama\s*:\s*([\w\s\-.,&()]+)\nAlamat', text)
                if pembeli_match:
                    nama_pembeli = pembeli_match.group(1).strip()
                    nama_pembeli = re.sub(r'\bAlamat\b', '', nama_pembeli, flags=re.IGNORECASE).strip()
            
            table = page.extract_table()
            if table:
                last_seen_no = None  # Untuk mendeteksi baris utama
                for row in table:
                    if row and row[0] and re.match(r'^\d+$', row[0]):
                        # Cek apakah nomor urut sudah ada sebelumnya (baris utama)
                        if row[0] != last_seen_no:
                            last_seen_no = row[0]  # Simpan nomor urut untuk pengecekan
                            
                            nama_barang = re.sub(r'Tanggal:\s*\d{2}/\d{2}/\d{4}', '', row[2]).strip()
                            nama_barang = re.sub(r'PPnBM \(\d+,?\d*%\) = Rp [\d.,]+', '', nama_barang).strip()
                            nama_barang = re.sub(r'Potongan Harga = Rp [\d.,]+', '', nama_barang).strip()
                            nama_barang = re.sub(r'\bkilogram\b', '', nama_barang, flags=re.IGNORECASE).strip()
                            
                            harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', row[2])
                            if harga_qty_info:
                                harga = float(harga_qty_info.group(1).replace('.', '').replace(',', '.'))
                                qty = float(harga_qty_info.group(2).replace('.', '').replace(',', '.'))
                                unit = harga_qty_info.group(3)
                            else:
                                harga, qty, unit = 0.0, 0.0, "Unknown"
                            
                            potongan_harga_match = re.search(r'Potongan Harga = Rp ([\d.,]+)', row[2])
                            if potongan_harga_match:
                                potongan_harga = float(potongan_harga_match.group(1).replace('.', '').replace(',', '.'))
                            else:
                                potongan_harga = 0.0
                            
                            total = round((harga * qty) - potongan_harga, 2)
                            ppn = round(total * 0.11, 2)
                            dpp = round(total - ppn, 2)
                            data.append([no_fp or "Tidak ditemukan", nama_penjual or "Tidak ditemukan", nama_pembeli or "Tidak ditemukan", tanggal_faktur, nama_barang, qty, unit, harga, potongan_harga, total, dpp, ppn])
    return data


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

def main_app():
    st.title("Convert Faktur Pajak PDF To Excel")
    uploaded_files = st.file_uploader("Upload Faktur Pajak (PDF, bisa lebih dari satu)", type=["pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        all_data = []
        for uploaded_file in uploaded_files:
            tanggal_faktur = find_invoice_date(uploaded_file)
            extracted_data = extract_data_from_pdf(uploaded_file, tanggal_faktur)
            all_data.extend(extracted_data)
        
        if all_data:
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga", "Potongan Harga", "Total", "DPP", "PPN"])
            df.index += 1  
            
            st.write("### Pratinjau Data yang Diekstrak")
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=True, sheet_name='Faktur Pajak')
            output.seek(0)
            st.download_button(label="\U0001F4E5 Unduh Excel", data=output, file_name="Faktur_Pajak.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    main_app()
