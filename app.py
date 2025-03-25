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
    previous_item = None  
    partial_row = None  

    with pdfplumber.open(pdf_file) as pdf:
        all_text = [page.extract_text() for page in pdf.pages]  # Gabungkan semua halaman
        
        for i, page in enumerate(pdf.pages):
            text = all_text[i]  # Ambil teks dari halaman yang sudah digabung
            next_text = all_text[i + 1] if i + 1 < len(pdf.pages) else ""  # Ambil halaman berikutnya jika ada

            # Gabungkan teks dari halaman ini dengan halaman berikutnya
            full_text = text + "\n" + next_text 

            table = page.extract_table({"vertical_strategy": "lines", "horizontal_strategy": "lines"})
            if table:
                for row in table:
                    if row and (not row[0] or not re.match(r'^\d+$', row[0])):
                        if partial_row:
                            partial_row[4] += " " + row[2].strip()  
                            continue  

                    if row and row[0] and re.match(r'^\d+$', row[0]):
                        nama_barang = re.sub(r'Rp [\d.,]+ x [\d.,]+ \w+.*', '', row[2]).strip()
                        potongan_match = re.search(r'Potongan Harga = Rp ([\d.,]+)', full_text)  # Cari di halaman berikutnya
                        harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', row[2])

                        harga, qty, unit = 0.0, 0.0, "Unknown"
                        if harga_qty_info:
                            harga = float(harga_qty_info.group(1).replace('.', '').replace(',', '.'))
                            qty = float(harga_qty_info.group(2).replace('.', '').replace(',', '.'))
                            unit = harga_qty_info.group(3)

                        potongan = float(potongan_match.group(1).replace('.', '').replace(',', '.')) if potongan_match else 0.0
                        total = (harga * qty) - potongan
                        dpp = round(total * 11 / 12, 2)
                        ppn = round(dpp * 0.12, 2)

                        new_row = [
                            no_fp or "Tidak ditemukan",
                            nama_penjual or "Tidak ditemukan",
                            nama_pembeli or "Tidak ditemukan",
                            tanggal_faktur,
                            nama_barang,
                            qty,
                            unit,
                            harga,
                            potongan,
                            total,
                            dpp,
                            ppn
                        ]
                        
                        if row[-1] is None or row[-1] == "":
                            partial_row = new_row
                        else:
                            data.append(new_row)
                            partial_row = None  
                        
                if partial_row:
                    potongan_lanjutan = re.search(r'Potongan Harga = Rp ([\d.,]+)', next_text)
                    if potongan_lanjutan:
                        partial_row[8] = float(potongan_lanjutan.group(1).replace('.', '').replace(',', '.'))
                        partial_row[9] = (partial_row[7] * partial_row[5]) - partial_row[8]
                        partial_row[10] = round(partial_row[9] * 11 / 12, 2)
                        partial_row[11] = round(partial_row[10] * 0.12, 2)
                    
                    data.append(partial_row)
                    partial_row = None  

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
            df = pd.DataFrame(all_data, columns=["No FP", "Nama Penjual", "Nama Pembeli", "Tanggal Faktur", "Nama Barang", "Qty", "Satuan", "Harga", "Potongan", "Total", "DPP", "PPN"])
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
