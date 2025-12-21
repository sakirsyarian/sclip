# 📚 Panduan Google Colab untuk SmartClip AI

Panduan lengkap untuk pemula cara menggunakan SmartClip AI di Google Colab.

## 📋 Daftar Isi

1. [Apa itu Google Colab?](#apa-itu-google-colab)
2. [Persiapan](#persiapan)
3. [Cara Upload Notebook ke Colab](#cara-upload-notebook-ke-colab)
4. [Cara Menggunakan SmartClip AI di Colab](#cara-menggunakan-smartclip-ai-di-colab)
5. [Tips & Troubleshooting](#tips--troubleshooting)

---

## Apa itu Google Colab?

Google Colab adalah layanan gratis dari Google yang memungkinkan kamu menjalankan kode Python di cloud (server Google). 

**Keuntungan pakai Colab:**
- ✅ Gratis! Tidak perlu bayar
- ✅ Dapat GPU gratis (T4) untuk proses lebih cepat
- ✅ Tidak perlu install Python atau FFmpeg di komputer
- ✅ Bisa diakses dari mana saja (hanya butuh browser)
- ✅ RAM besar (12GB+)

**Kekurangan:**
- ⚠️ Session terbatas (~12 jam, lalu reset)
- ⚠️ Butuh koneksi internet
- ⚠️ File akan hilang setelah session berakhir (kecuali disimpan ke Google Drive)

---

## Persiapan

Sebelum mulai, pastikan kamu punya:

### 1. Akun Google
- Jika belum punya, buat di [accounts.google.com](https://accounts.google.com)

### 2. API Key (GRATIS dengan Groq!)

**Groq API Key (Recommended - GRATIS):**
1. Buka [Groq Console](https://console.groq.com)
2. Login dengan Google atau GitHub
3. Klik **"API Keys"** → **"Create API Key"**
4. Copy API key yang muncul

**Gemini API Key (Alternatif):**
1. Buka [Google AI Studio](https://aistudio.google.com/apikey)
2. Login dengan akun Google
3. Klik **"Create API Key"**
4. Copy API key yang muncul

![Get API Key](https://ai.google.dev/static/images/aistudio-api-key.png)

### 3. Video yang Ingin Diproses
- File video (MP4, MKV, AVI, MOV, WebM)
- Atau link YouTube

---

## Cara Upload Notebook ke Colab

Ada 3 cara untuk membuka notebook SmartClip AI di Colab:

### Cara 1: Upload Manual (Paling Mudah)

1. **Download file notebook**
   - Download file `smartclip_colab.ipynb` dari repository

2. **Buka Google Colab**
   - Pergi ke [colab.research.google.com](https://colab.research.google.com)
   - Login dengan akun Google

3. **Upload notebook**
   - Klik **File** → **Upload notebook**
   - Pilih file `smartclip_colab.ipynb` yang sudah didownload
   - Tunggu sampai notebook terbuka

### Cara 2: Dari Google Drive

1. **Upload ke Google Drive**
   - Buka [drive.google.com](https://drive.google.com)
   - Upload file `smartclip_colab.ipynb`

2. **Buka dengan Colab**
   - Klik kanan pada file notebook
   - Pilih **Open with** → **Google Colaboratory**

### Cara 3: Dari GitHub (Jika Sudah di-push)

1. Buka [colab.research.google.com](https://colab.research.google.com)
2. Klik tab **GitHub**
3. Masukkan URL repository: `https://github.com/sakirsyarian/sclip`
4. Pilih file `smartclip_colab.ipynb`

---

## Cara Menggunakan SmartClip AI di Colab

Setelah notebook terbuka, ikuti langkah-langkah berikut:

### Langkah 1: Aktifkan GPU (Opsional tapi Disarankan)

GPU membuat proses face tracking lebih cepat.

1. Klik **Runtime** di menu atas
2. Pilih **Change runtime type**
3. Di bagian **Hardware accelerator**, pilih **T4 GPU**
4. Klik **Save**

![Enable GPU](https://miro.medium.com/max/1400/1*m5FqJmKrKs0G8gsLqPfXYA.png)

### Langkah 2: Jalankan Cell Setup

1. Klik cell pertama (🔧 Install SmartClip AI)
2. Klik tombol **Play** (▶️) di sebelah kiri cell
3. Atau tekan **Ctrl + Enter**
4. Tunggu sampai muncul "✅ Setup complete!"

> ⏱️ Proses ini memakan waktu sekitar 1-2 menit

### Langkah 3: Masukkan API Key

1. Klik cell kedua (🔑 Enter API Key)
2. Jalankan cell (klik Play atau Ctrl+Enter)
3. Akan muncul kotak input, paste **Groq API key** kamu
4. Tekan Enter
5. Pastikan muncul "✅ API key configured"

**Tips:** Untuk menyimpan API key agar tidak perlu input ulang:
1. Klik ikon 🔑 di sidebar kiri (Secrets)
2. Klik **Add new secret**
3. Name: `GROQ_API_KEY`
4. Value: (paste API key kamu)
5. Toggle **Notebook access** ke ON

### Langkah 4: Upload Video

1. Klik cell ketiga (📤 Upload Video)
2. Pilih sumber video:

**Opsi A - Upload dari Komputer:**
- Pilih "Upload from computer" di dropdown
- Jalankan cell
- Klik **Choose Files** yang muncul
- Pilih file video dari komputer
- Tunggu upload selesai

**Opsi B - YouTube URL:**
- Pilih "YouTube URL" di dropdown
- Isi field `youtube_url` dengan link YouTube
- Jalankan cell

**Opsi C - Google Drive:**
- Pilih "Google Drive" di dropdown
- Isi field `drive_path` dengan path file di Drive
  - Contoh: `/content/drive/MyDrive/video.mp4`
- Jalankan cell
- Izinkan akses ke Google Drive jika diminta

### Langkah 5: Generate Clips

1. Klik cell keempat (🎬 Generate Clips)
2. Atur pengaturan sesuai keinginan:

| Pengaturan | Penjelasan |
|------------|------------|
| `max_clips` | Jumlah clip yang dihasilkan (1-10) |
| `aspect_ratio` | 9:16 (TikTok/Reels), 1:1 (Instagram), 16:9 (YouTube) |
| `caption_style` | Gaya caption: default, bold, minimal, karaoke |
| `language` | Bahasa caption: id (Indonesia), en (English), dll |
| `min_duration` | Durasi minimum clip (detik) |
| `max_duration` | Durasi maksimum clip (detik) |
| `no_captions` | Centang jika tidak mau caption |
| `dry_run` | Centang untuk preview tanpa render |

3. Jalankan cell
4. Tunggu proses selesai (bisa 5-15 menit tergantung durasi video)

### Langkah 6: Download Hasil

1. Klik cell kelima (📥 Download Clips)
2. Pilih metode download:

**Download to computer:**
- File akan otomatis terdownload ke komputer

**Save to Google Drive:**
- File disimpan ke folder di Google Drive
- Atur `drive_output_folder` jika perlu

**Preview in notebook:**
- Lihat preview video langsung di notebook

3. Jalankan cell

---

## Tips & Troubleshooting

### ❌ Error: "RESOURCE_EXHAUSTED" atau "429"

**Penyebab:** Rate limit API (terlalu banyak request)

**Solusi:**
- Tunggu 1-2 menit, lalu coba lagi
- Gunakan `dry_run = True` untuk test dulu
- Kurangi jumlah `max_clips`

### ❌ Error: "No module named..."

**Penyebab:** Dependencies belum terinstall

**Solusi:**
- Jalankan ulang Cell 1 (Setup)
- Pastikan tidak ada error saat install

### ❌ Video tidak terupload

**Penyebab:** File terlalu besar atau format tidak didukung

**Solusi:**
- Maksimal ukuran upload: ~100MB
- Untuk file besar, gunakan Google Drive
- Format yang didukung: MP4, MKV, AVI, MOV, WebM

### ❌ Session terputus / "Runtime disconnected"

**Penyebab:** Colab session timeout atau tidak aktif

**Solusi:**
- Klik **Reconnect** di pojok kanan atas
- Jalankan ulang dari Cell 1
- Tips: Jangan tinggalkan tab terlalu lama

### ❌ GPU tidak tersedia

**Penyebab:** Kuota GPU habis (Colab gratis ada batasnya)

**Solusi:**
- Coba lagi nanti (biasanya reset setiap hari)
- Tetap bisa jalan tanpa GPU (lebih lambat)
- Upgrade ke Colab Pro jika sering pakai

### ⚠️ File hilang setelah session berakhir

**Penyebab:** Colab tidak menyimpan file secara permanen

**Solusi:**
- Selalu download hasil sebelum menutup tab
- Atau simpan ke Google Drive

### 💡 Tips Performa

1. **Aktifkan GPU** untuk face tracking lebih cepat
2. **Gunakan video pendek** (< 30 menit) untuk hasil lebih cepat
3. **Mulai dengan dry_run** untuk preview sebelum render
4. **Simpan API key di Secrets** agar tidak perlu input ulang

---

## 📞 Butuh Bantuan?

- Buka [GitHub Issues](https://github.com/sakirsyarian/sclip/issues) untuk melaporkan bug
- Baca [README.md](README.md) untuk dokumentasi lengkap
- Baca [TUTORIAL.md](TUTORIAL.md) untuk tutorial bahasa Indonesia

---

Selamat mencoba! 🎬✨
