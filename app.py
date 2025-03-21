def extract_data_from_pdf(pdf_file, tanggal_faktur):
    data = []
    no_fp, nama_penjual, nama_pembeli = None, None, None
    item_buffer = []  # Menyimpan item yang terputus antar halaman
    last_row = None   # Menyimpan baris terakhir untuk pengecekan
    last_item = {}  # Menyimpan informasi barang untuk penggabungan
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # Ambil informasi tetap seperti no_fp, nama_penjual, nama_pembeli, dll.
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
            
            # Ekstraksi Tabel dan menangani baris yang terputus antar halaman
            table = page.extract_table()
            if table:
                for row in table:
                    if row and row[0] and re.match(r'^\d+$', row[0]):
                        item_key = row[2]  # Menyimpan nama barang untuk referensi penggabungan
                        
                        if last_item and last_item['key'] == item_key:
                            # Jika nama barang sama dengan yang ada pada buffer, gabungkan dengan data yang ada
                            last_item['row'][2] += ' ' + row[2]  # Gabungkan nama barang
                            continue  # Lewati baris yang sudah digabungkan
                        
                        # Jika data terputus, simpan ke buffer sementara
                        item_buffer.append(row)
                        last_item = {'key': item_key, 'row': row}  # Menyimpan data barang yang terputus
                        
                # Proses dan gabungkan item yang terpotong dengan item baru jika ada
                if item_buffer:
                    for row in item_buffer:
                        nama_barang = re.sub(r'Rp [\d.,]+ x [\d.,]+ \w+.*', '', row[2]).strip()
                        nama_barang = re.sub(r'Potongan Harga = Rp [\d.,]+', '', nama_barang).strip()
                        nama_barang = re.sub(r'PPnBM \(\d+,?\d*%\) = Rp [\d.,]+', '', nama_barang).strip()
                        nama_barang = re.sub(r'Tanggal:\s*\d{2}/\d{2}/\d{4}', '', nama_barang).strip()

                        # Menangkap Potongan Harga
                        potongan_match = re.search(r'Potongan Harga = Rp ([\d.,]+)', row[2])
                        if potongan_match:
                            potongan = float(potongan_match.group(1).replace('.', '').replace(',', '.'))
                        else:
                            potongan = 0.0

                        harga_qty_info = re.search(r'Rp ([\d.,]+) x ([\d.,]+) (\w+)', row[2])
                        if harga_qty_info:
                            harga = float(harga_qty_info.group(1).replace('.', '').replace(',', '.'))
                            qty = float(harga_qty_info.group(2).replace('.', '').replace(',', '.'))
                            unit = harga_qty_info.group(3)
                        else:
                            harga, qty, unit = 0.0, 0.0, "Unknown"

                        # Total dihitung sebagai harga * qty - potongan harga
                        total = harga * qty - potongan

                        # DPP dihitung dengan membagi total yang sudah dipotong harga dengan 1,1
                        dpp = total / (1 + 0.11)  # Menggunakan harga total yang sudah termasuk PPN dibagi 1.11 untuk PPN 11%

                        # PPN dihitung sebagai selisih antara total dan DPP
                        ppn = total - dpp

                        # Menambahkan data ke dalam list
                        data.append([no_fp or "Tidak ditemukan", nama_penjual or "Tidak ditemukan", nama_pembeli or "Tidak ditemukan", tanggal_faktur, nama_barang, qty, unit, harga, potongan, total, dpp, ppn])
                
                # Reset buffer setelah item diproses
                item_buffer = []
                last_item = None

    return data
