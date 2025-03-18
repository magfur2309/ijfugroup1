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
    incomplete_row = None  # Untuk menyimpan baris yang belum lengkap
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # Ekstraksi data header (No FP, Nama Penjual, Nama Pembeli)
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
                for row in table:
                  if len(row) >= 4 and row[0] and row[0].isdigit():  # Baris baru dengan nomor urut
    nama_barang = row[2] if len(row) > 2 and row[2] else "Tidak ditemukan"

    # Hapus teks "Nama Barang Kena Pajak / Jasa Kena Pajak"
    nama_barang = re.sub(r'Nama Barang Kena Pajak / Jasa Kena Pajak\s*', '', nama_barang, flags=re.IGNORECASE)

    harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', nama_barang)
    if harga_qty_info:
        harga = float(harga_qty_info.group(1).replace('.', '').replace(',', '.'))
        qty = float(harga_qty_info.group(2).replace('.', '').replace(',', '.'))
        unit = harga_qty_info.group(3)
    else:
        harga, qty, unit = 0.0, 0.0, "Unknown"

    total = harga * qty
    ppn = round(total * 0.11, 2)
    dpp = total - ppn

    data.append([
        no_fp or "Tidak ditemukan", 
        nama_penjual or "Tidak ditemukan", 
        nama_pembeli or "Tidak ditemukan", 
        tanggal_faktur, 
        nama_barang, 
        qty, 
        unit, 
        harga, 
        total, 
        dpp, 
        ppn
    ])


    data.append([no_fp or "Tidak ditemukan", nama_penjual or "Tidak ditemukan", 
                 nama_pembeli or "Tidak ditemukan", tanggal_faktur, 
                 nama_barang, qty, unit, harga, total, dpp, ppn])

                        
                        # Jika baris sebelumnya belum lengkap, gabungkan
                        if incomplete_row:
                            incomplete_row[4] += f" {nama_barang}"  # Gabungkan Nama Barang
                            incomplete_row[5] += qty
                            incomplete_row[7] += harga
                            incomplete_row[8] += total
                            incomplete_row[9] += dpp
                            incomplete_row[10] += ppn
                            data.append(incomplete_row)
                            incomplete_row = None
                        else:
                            # Simpan sebagai baris baru
                            data.append([no_fp or "Tidak ditemukan", nama_penjual or "Tidak ditemukan", 
                                         nama_pembeli or "Tidak ditemukan", tanggal_faktur, 
                                         nama_barang, qty, unit, harga, total, dpp, ppn])
                    else:
                        # Jika baris tidak lengkap, simpan sementara
                        incomplete_row = [no_fp or "Tidak ditemukan", nama_penjual or "Tidak ditemukan", 
                                          nama_pembeli or "Tidak ditemukan", tanggal_faktur, 
                                          row[2] if len(row) > 2 and row[2] else "Tidak ditemukan", 
                                          0, "Unknown", 0, 0, 0, 0]  # Data sementara
                
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
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga", "Total", "DPP", "PPN"])
            df.index += 1  
            
            # Format angka menjadi 2 desimal
            df[["Qty", "Harga", "Total", "DPP", "PPN"]] = df[["Qty", "Harga", "Total", "DPP", "PPN"]].applymap(lambda x: f"{x:.2f}")
            
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
