# 📚 Panduan Google Colab untuk SmartClip AI

Panduan lengkap untuk pemula cara menggunakan SmartClip AI di Google Colab.

## 📋 Daftar Isi

1. [Apa itu Google Colab?](#apa-itu-google-colab)
2. [Persiapan](#persiapan)
3. [Cara Upload Notebook ke Colab](#cara-upload-notebook-ke-colab)
4. [Cara Menggunakan SmartClip AI di Colab](#cara-menggunakan-smartclip-ai-di-colab)
5. [Provider Options](#provider-options)
6. [Mode Offline di Colab](#mode-offline-di-colab-ollama--local-whisper)
7. [Tips & Troubleshooting](#tips--troubleshooting)

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

### 2. API Key (Pilih Salah Satu)

**🌟 Groq API Key (GRATIS - Recommended):**
1. Buka [Groq Console](https://console.groq.com)
2. Login dengan Google atau GitHub
3. Klik **"API Keys"** → **"Create API Key"**
4. Copy API key yang muncul

**Deepgram API Key ($200 Free Credit):**
1. Buka [Deepgram Console](https://console.deepgram.com)
2. Sign up dan verifikasi email
3. Klik **"API Keys"** → **"Create Key"**
4. Copy API key yang muncul

**ElevenLabs API Key (99 Languages):**
1. Buka [ElevenLabs](https://elevenlabs.io)
2. Sign up dan login
3. Klik profile → **"API Keys"**
4. Copy API key yang muncul

**DeepSeek API Key (Very Affordable):**
1. Buka [DeepSeek Platform](https://platform.deepseek.com)
2. Sign up dan login
3. Buat API key di dashboard
4. Copy API key yang muncul

**Mistral API Key (Free Tier):**
1. Buka [Mistral Console](https://console.mistral.ai)
2. Sign up dan login
3. Buat API key di dashboard
4. Copy API key yang muncul

**Gemini API Key (Free Tier):**
1. Buka [Google AI Studio](https://aistudio.google.com/apikey)
2. Login dengan akun Google
3. Klik **"Create API Key"**
4. Copy API key yang muncul

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
| `transcriber` | Provider transcription (groq, deepgram, elevenlabs, openai, local) |
| `analyzer` | Provider analysis (groq, deepseek, gemini, mistral, openai, ollama) |
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

## Provider Options

SmartClip AI mendukung berbagai provider untuk transcription dan analysis:

### Transcription Providers

| Provider | CLI Option | API Key Env | Keterangan |
|----------|------------|-------------|------------|
| **Groq** (Default) | `--transcriber groq` | `GROQ_API_KEY` | ⚡ Gratis, sangat cepat |
| **Deepgram** | `--transcriber deepgram` | `DEEPGRAM_API_KEY` | $200 free credit, sangat cepat |
| **ElevenLabs** | `--transcriber elevenlabs` | `ELEVENLABS_API_KEY` | 99 bahasa, akurasi tinggi |
| **OpenAI** | `--transcriber openai` | `OPENAI_API_KEY` | Berbayar, akurat |
| **Local** | `--transcriber local` | - | Offline, butuh GPU |

### Analysis Providers

| Provider | CLI Option | API Key Env | Keterangan |
|----------|------------|-------------|------------|
| **Groq** (Default) | `--analyzer groq` | `GROQ_API_KEY` | ⚡ Gratis, sangat cepat |
| **DeepSeek** | `--analyzer deepseek` | `DEEPSEEK_API_KEY` | Sangat murah |
| **Gemini** | `--analyzer gemini` | `GEMINI_API_KEY` | Free tier tersedia |
| **Mistral** | `--analyzer mistral` | `MISTRAL_API_KEY` | Free tier tersedia |
| **OpenAI** | `--analyzer openai` | `OPENAI_API_KEY` | Berbayar, kualitas tinggi |
| **Ollama** | `--analyzer ollama` | - | Offline, butuh setup |

### Contoh Penggunaan

```bash
# Default (Groq untuk keduanya - GRATIS)
sclip -i video.mp4

# Deepgram + DeepSeek (murah)
sclip -i video.mp4 --transcriber deepgram --analyzer deepseek

# ElevenLabs + Mistral
sclip -i video.mp4 --transcriber elevenlabs --analyzer mistral

# Fully offline (lihat section berikutnya)
sclip -i video.mp4 --transcriber local --analyzer ollama
```

---

## Mode Offline di Colab (Ollama + Local Whisper)

Kamu bisa menjalankan SmartClip AI sepenuhnya offline di Colab menggunakan Local Whisper untuk transcription dan Ollama untuk analysis.

### Setup Local Whisper (faster-whisper)

Local Whisper menggunakan `faster-whisper` yang berjalan di GPU Colab.

```python
# Cell: Install faster-whisper
!pip install faster-whisper

# Test faster-whisper
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cuda", compute_type="float16")
print("✅ faster-whisper ready!")
```

**Model Options:**
| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny` | ~1GB | Sangat cepat | Rendah |
| `base` | ~1GB | Cepat | Cukup |
| `small` | ~2GB | Sedang | Baik |
| `medium` | ~5GB | Lambat | Sangat baik |
| `large-v3` | ~10GB | Sangat lambat | Terbaik |

> 💡 Untuk Colab gratis (T4 GPU, 15GB VRAM), gunakan `base` atau `small`

### Setup Ollama di Colab

Ollama memungkinkan menjalankan LLM secara lokal. Berikut cara setup di Colab:

```python
# Cell: Install dan jalankan Ollama
import subprocess
import time

# Install Ollama
!curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server di background
subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)  # Tunggu server start

# Download model (pilih salah satu)
!ollama pull llama3.2        # 2GB, cepat
# !ollama pull llama3.2:1b   # 1.3GB, sangat cepat
# !ollama pull mistral       # 4GB, lebih pintar
# !ollama pull qwen2.5:7b    # 4.4GB, bagus untuk bahasa Asia

# Verify
!ollama list
print("✅ Ollama ready!")
```

**Model Recommendations untuk Colab:**
| Model | Size | RAM | Keterangan |
|-------|------|-----|------------|
| `llama3.2:1b` | 1.3GB | ~3GB | Sangat cepat, basic |
| `llama3.2` | 2GB | ~5GB | Balanced (recommended) |
| `qwen2.5:7b` | 4.4GB | ~8GB | Bagus untuk Indonesia |
| `mistral` | 4GB | ~8GB | Pintar, Eropa-focused |

### Menjalankan Mode Offline

Setelah setup selesai, jalankan SmartClip AI dengan mode offline:

```python
# Cell: Generate clips (offline mode)
!sclip -i video.mp4 \
    --transcriber local \
    --analyzer ollama \
    --language id \
    -n 5
```

### Full Offline Setup Script

Copy-paste cell ini untuk setup lengkap:

```python
#@title 🔧 Setup Offline Mode (Ollama + Local Whisper)
#@markdown Jalankan cell ini untuk setup mode offline

import subprocess
import time
import os

print("📦 Installing dependencies...")
!pip install -q faster-whisper

print("\n📦 Installing Ollama...")
!curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null

print("\n🚀 Starting Ollama server...")
subprocess.Popen(
    ["ollama", "serve"], 
    stdout=subprocess.DEVNULL, 
    stderr=subprocess.DEVNULL
)
time.sleep(5)

print("\n📥 Downloading Llama 3.2 model...")
!ollama pull llama3.2

print("\n✅ Verifying setup...")
# Test Ollama
import httpx
try:
    r = httpx.get("http://localhost:11434/api/tags", timeout=5)
    models = r.json().get("models", [])
    print(f"   Ollama: {len(models)} model(s) available")
except:
    print("   ⚠️ Ollama not responding")

# Test faster-whisper
try:
    from faster_whisper import WhisperModel
    print("   faster-whisper: installed")
except ImportError:
    print("   ⚠️ faster-whisper not installed")

print("\n" + "="*50)
print("✅ OFFLINE MODE READY!")
print("="*50)
print("\nGunakan command:")
print("  sclip -i video.mp4 --transcriber local --analyzer ollama")
```

### Tips Mode Offline

1. **GPU Wajib** - Local Whisper butuh GPU untuk performa optimal
2. **RAM Usage** - Ollama + Whisper bisa pakai 8-10GB RAM
3. **First Run Lambat** - Model perlu di-load ke memory pertama kali
4. **Session Reset** - Ollama perlu di-setup ulang setiap session baru

---

## Tips & Troubleshooting

### ❌ Error: "RESOURCE_EXHAUSTED" atau "429"

**Penyebab:** Rate limit API (terlalu banyak request)

**Solusi:**
- Tunggu 1-2 menit, lalu coba lagi
- Gunakan `dry_run = True` untuk test dulu
- Kurangi jumlah `max_clips`
- Coba provider lain (DeepSeek, Mistral)

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

### ❌ Ollama tidak merespon

**Penyebab:** Server Ollama belum start atau crash

**Solusi:**
```python
# Restart Ollama
import subprocess
!pkill ollama
subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
import time; time.sleep(5)
!ollama list
```

### ❌ Local Whisper out of memory

**Penyebab:** Model terlalu besar untuk GPU

**Solusi:**
- Gunakan model lebih kecil: `tiny` atau `base`
- Atau gunakan cloud provider (Groq gratis!)

### ⚠️ File hilang setelah session berakhir

**Penyebab:** Colab tidak menyimpan file secara permanen

**Solusi:**
- Selalu download hasil sebelum menutup tab
- Atau simpan ke Google Drive

### 💡 Tips Performa

1. **Aktifkan GPU** untuk face tracking dan local whisper lebih cepat
2. **Gunakan video pendek** (< 30 menit) untuk hasil lebih cepat
3. **Mulai dengan dry_run** untuk preview sebelum render
4. **Simpan API key di Secrets** agar tidak perlu input ulang
5. **Groq adalah pilihan terbaik** - gratis dan sangat cepat!

---

## 📞 Butuh Bantuan?

- Buka [GitHub Issues](https://github.com/sakirsyarian/sclip/issues) untuk melaporkan bug
- Baca [README.md](README.md) untuk dokumentasi lengkap
- Baca [TUTORIAL.md](TUTORIAL.md) untuk tutorial bahasa Indonesia

---

Selamat mencoba! 🎬✨
