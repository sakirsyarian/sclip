# SmartClip AI - Tutorial untuk Pemula

> Panduan lengkap untuk setup dan menjalankan SmartClip AI dari nol. Cocok untuk yang baru belajar Python!

---

## Daftar Isi

1. [Persiapan Awal](#1-persiapan-awal)
2. [Install Python](#2-install-python)
3. [Setup Project](#3-setup-project)
4. [Install Dependencies](#4-install-dependencies)
5. [Dapatkan API Key Gemini](#5-dapatkan-api-key-gemini)
6. [Install FFmpeg](#6-install-ffmpeg)
7. [Menjalankan SmartClip](#7-menjalankan-smartclip)
8. [Contoh Penggunaan](#8-contoh-penggunaan)
   - [8.1 Multi-Language Support](#81-multi-language-support-dukungan-multi-bahasa)
9. [Troubleshooting](#9-troubleshooting)
10. [Glossary](#10-glossary)
11. [FAQ (Frequently Asked Questions)](#11-faq-frequently-asked-questions)

---

## 1. Persiapan Awal

### Apa yang Kamu Butuhkan

| Item | Keterangan |
|------|------------|
| Komputer | Windows 10/11, macOS, atau Linux |
| Internet | Untuk download dan API calls |
| Storage | Minimal 2GB free space |
| RAM | Minimal 4GB (8GB recommended) |

### Tools yang Akan Di-install

1. **Python** - Bahasa pemrograman untuk menjalankan SmartClip
2. **FFmpeg** - Tool untuk memproses video
3. **yt-dlp** - Tool untuk download video YouTube (optional)
4. **Google Gemini API Key** - Untuk AI analysis

---

## 2. Install Python

### Windows

1. Buka https://www.python.org/downloads/
2. Klik tombol **"Download Python 3.12.x"** (atau versi terbaru)
3. Jalankan installer yang sudah di-download
4. ⚠️ **PENTING**: Centang **"Add Python to PATH"** di awal instalasi!
5. Klik **"Install Now"**
6. Tunggu sampai selesai

**Verifikasi instalasi:**
```cmd
python --version
```
Harus muncul seperti: `Python 3.12.0`

### macOS

1. Buka Terminal (Cmd + Space, ketik "Terminal")
2. Install Homebrew (jika belum ada):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
3. Install Python:
```bash
brew install python
```

**Verifikasi:**
```bash
python3 --version
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Verifikasi:**
```bash
python3 --version
```

---

## 3. Setup Project

### Step 1: Buka Terminal/Command Prompt

**Windows:**
- Tekan `Win + R`
- Ketik `cmd` lalu Enter
- Atau cari "Command Prompt" di Start Menu

**macOS/Linux:**
- Buka aplikasi Terminal

### Step 2: Navigasi ke Folder Project

```cmd
cd D:\Development\python\sclip
```

Atau jika folder belum ada, buat dulu:
```cmd
mkdir D:\Development\python\sclip
cd D:\Development\python\sclip
```

### Step 3: Buat Virtual Environment

Virtual environment adalah "ruang terisolasi" untuk project Python. Ini mencegah konflik antar project.

**Windows:**
```cmd
python -m venv venv
```

**macOS/Linux:**
```bash
python3 -m venv venv
```

### Step 4: Aktifkan Virtual Environment

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

> Jika error di PowerShell, jalankan dulu:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**macOS/Linux:**
```bash
source venv/bin/activate
```

Setelah aktif, prompt akan berubah menjadi:
```
(venv) D:\Development\python\sclip>
```

### Step 5: Upgrade pip

```cmd
pip install --upgrade pip
```

---

## 4. Install Dependencies

### Install dari requirements.txt

Project sudah menyediakan file `requirements.txt`. Install semua dependencies dengan:

```cmd
pip install -r requirements.txt
```

Dependencies yang akan ter-install:
- **click** - Framework untuk CLI
- **rich** - Output console yang cantik
- **google-genai** - SDK untuk Google Gemini AI
- **yt-dlp** - Download video YouTube

Tunggu sampai semua package ter-install. Ini mungkin memakan waktu beberapa menit.

### Verifikasi instalasi

```cmd
pip list
```

Pastikan semua package muncul di list.

### Install sebagai Package (Optional)

Untuk menggunakan command `sclip` langsung (tanpa `python -m src.main`):

```cmd
pip install -e .
```

Setelah ini, kamu bisa langsung menjalankan:
```cmd
sclip --help
```

---

## 5. Dapatkan API Key Gemini

### Step 1: Buka Google AI Studio

1. Buka browser
2. Pergi ke: https://aistudio.google.com/
3. Login dengan akun Google kamu

### Step 2: Buat API Key

1. Klik **"Get API Key"** di sidebar kiri
2. Klik **"Create API Key"**
3. Pilih project (atau buat baru)
4. Copy API key yang muncul

> ⚠️ **PENTING**: Simpan API key ini dengan aman! Jangan share ke siapapun.

### Step 3: Setup API Key

Ada 3 cara untuk menyimpan API key:

**Cara 1: Environment Variable (Recommended)**

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your-api-key-here
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
```

**macOS/Linux:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

**Cara 2: Via CLI Flag**

Kamu bisa langsung pass API key saat menjalankan command:
```cmd
sclip -i video.mp4 --api-key "your-api-key-here"
```

**Cara 3: Config File**

Buat folder dan file config:

**Windows:**
```cmd
mkdir %USERPROFILE%\.sclip
echo {"gemini_api_key": "your-api-key-here"} > %USERPROFILE%\.sclip\config.json
```

**macOS/Linux:**
```bash
mkdir -p ~/.sclip
echo '{"gemini_api_key": "your-api-key-here"}' > ~/.sclip/config.json
```

**Cara 4: Setup Wizard**

Jalankan setup wizard untuk konfigurasi interaktif:
```cmd
sclip --setup
```

---

## 6. Install FFmpeg

FFmpeg adalah tool untuk memproses video. SmartClip membutuhkan ini untuk trim, crop, dan burn captions.

### Windows

**Cara 1: Menggunakan winget (Windows 11)**
```cmd
winget install FFmpeg
```

**Cara 2: Manual Download**
1. Buka https://www.gyan.dev/ffmpeg/builds/
2. Download **"ffmpeg-release-essentials.zip"**
3. Extract ke `C:\ffmpeg`
4. Tambahkan ke PATH:
   - Buka Start Menu, cari "Environment Variables"
   - Klik "Edit the system environment variables"
   - Klik "Environment Variables"
   - Di "System variables", cari "Path", klik "Edit"
   - Klik "New", tambahkan `C:\ffmpeg\bin`
   - OK semua dialog

**Verifikasi:**
```cmd
ffmpeg -version
```

### macOS

```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install ffmpeg
```

---

## 7. Menjalankan SmartClip

### Struktur Folder Project

Setelah setup, folder project akan terlihat seperti ini:

```
sclip/
├── venv/                 # Virtual environment (auto-generated)
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── commands/
│   │   ├── clip.py       # Main clipping workflow
│   │   └── setup.py      # Setup wizard
│   ├── services/
│   │   ├── downloader.py # YouTube download
│   │   ├── gemini.py     # AI analysis
│   │   └── renderer.py   # Video rendering
│   ├── utils/
│   │   ├── captions.py   # Caption generation
│   │   ├── cleanup.py    # Temp file management
│   │   ├── config.py     # Config management
│   │   ├── ffmpeg.py     # FFmpeg wrapper
│   │   ├── logger.py     # Console output
│   │   ├── validation.py # Input validation
│   │   └── video.py      # Video analysis
│   └── types/
│       └── __init__.py   # Type definitions
├── tests/
├── pyproject.toml
├── requirements.txt
└── README.md
```

### Cara Menjalankan

**Pastikan virtual environment aktif!**

```cmd
# Aktifkan venv (jika belum)
venv\Scripts\activate

# Jalankan SmartClip
python -m src.main --help
```

Atau jika sudah di-install sebagai package:
```cmd
sclip --help
```

---

## 8. Contoh Penggunaan

### Contoh 1: Proses Video Lokal

```cmd
sclip -i "D:\Videos\podcast.mp4"
```

Ini akan:
1. Menganalisis video dengan Gemini AI
2. Menemukan 5 momen viral
3. Membuat 5 short clips di folder `./output`

### Contoh 2: Proses Video YouTube

```cmd
sclip -u "https://www.youtube.com/watch?v=xxxxx"
```

### Contoh 3: Custom Output Folder

```cmd
sclip -i video.mp4 -o "D:\MyClips"
```

### Contoh 4: Batasi Jumlah Clips

```cmd
sclip -i video.mp4 -n 3
```

### Contoh 5: Preview Tanpa Render (Dry Run)

```cmd
sclip -i video.mp4 --dry-run
```

### Contoh 6: Verbose Mode (Lihat Detail)

```cmd
sclip -i video.mp4 -v
```

### Contoh 7: Format Square untuk Instagram

```cmd
sclip -i video.mp4 -a 1:1
```

### Contoh 8: Format Portrait untuk TikTok/Reels

```cmd
sclip -i video.mp4 -a 9:16
```

### Contoh 9: Tanpa Captions

```cmd
sclip -i video.mp4 --no-captions
```

### Contoh 10: Custom Caption Style

```cmd
sclip -i video.mp4 -s bold
sclip -i video.mp4 -s karaoke
sclip -i video.mp4 -s minimal
```

### Contoh 11: Check Dependencies

```cmd
sclip --check-deps
```

### Contoh 12: Setup Wizard

```cmd
sclip --setup
```

### Contoh 13: Lihat Info Video

```cmd
sclip -i video.mp4 --info
```

### Contoh 14: Custom Duration Range

```cmd
sclip -i video.mp4 --min-duration 20 --max-duration 45
```

### Contoh 15: Force Overwrite Existing Files

```cmd
sclip -i video.mp4 -f
```

### Contoh 16: Menggunakan Bahasa Lain untuk Captions

```cmd
# Default: Bahasa Indonesia (tanpa flag)
sclip -i video.mp4

# Explicit Bahasa Indonesia
sclip -i video.mp4 -l id

# English
sclip -i video.mp4 -l en

# Bahasa lain
sclip -i video.mp4 -l ja   # Japanese
sclip -i video.mp4 -l ko   # Korean
```

---

## 8.1. Multi-Language Support (Dukungan Multi-Bahasa)

SmartClip mendukung berbagai bahasa untuk caption generation. Bahasa default adalah **Indonesia (`id`)**, tapi kamu bisa menggunakan bahasa lain sesuai kebutuhan.

### Cara Menggunakan

Gunakan flag `-l` atau `--language` diikuti kode bahasa:

```cmd
sclip -i video.mp4 -l <kode_bahasa>
```

### Daftar Bahasa yang Didukung

| Kode | Bahasa | Contoh |
|------|--------|--------|
| `id` | Indonesia (Default) | `sclip -i video.mp4` atau `sclip -i video.mp4 -l id` |
| `en` | English | `sclip -i video.mp4 -l en` |
| `ja` | Japanese (日本語) | `sclip -i video.mp4 -l ja` |
| `ko` | Korean (한국어) | `sclip -i video.mp4 -l ko` |
| `zh` | Chinese (中文) | `sclip -i video.mp4 -l zh` |
| `es` | Spanish (Español) | `sclip -i video.mp4 -l es` |
| `fr` | French (Français) | `sclip -i video.mp4 -l fr` |
| `de` | German (Deutsch) | `sclip -i video.mp4 -l de` |
| `pt` | Portuguese (Português) | `sclip -i video.mp4 -l pt` |
| `ru` | Russian (Русский) | `sclip -i video.mp4 -l ru` |
| `ar` | Arabic (العربية) | `sclip -i video.mp4 -l ar` |
| `hi` | Hindi (हिन्दी) | `sclip -i video.mp4 -l hi` |
| `th` | Thai (ไทย) | `sclip -i video.mp4 -l th` |
| `vi` | Vietnamese (Tiếng Việt) | `sclip -i video.mp4 -l vi` |
| `ms` | Malay (Bahasa Melayu) | `sclip -i video.mp4 -l ms` |

> **Note:** Bahasa yang didukung tergantung pada kemampuan Google Gemini AI. Daftar di atas adalah bahasa-bahasa umum yang biasanya didukung dengan baik.

### Bagaimana Cara Kerjanya?

1. SmartClip mengirim parameter `language` ke Gemini AI
2. Gemini menganalisis audio dalam video
3. Gemini men-transcribe dan generate captions dalam bahasa yang diminta
4. Captions di-render ke video output

### Tips Penggunaan Multi-Bahasa

1. **Sesuaikan dengan audio video**: Jika video berbahasa Indonesia, gunakan `-l id`. Jika berbahasa Inggris, gunakan `-l en`.

2. **Translasi otomatis**: Gemini bisa men-transcribe audio dalam satu bahasa dan menghasilkan caption dalam bahasa lain (misalnya audio English → caption Indonesia).

3. **Akurasi terbaik**: Untuk hasil terbaik, gunakan bahasa yang sama dengan audio video.

4. **Font support**: Pastikan sistem kamu memiliki font yang mendukung bahasa target (terutama untuk CJK: Chinese, Japanese, Korean).

### Contoh Use Cases

```cmd
# Podcast Indonesia → Caption Indonesia (default)
sclip -i podcast_indo.mp4

# Interview English → Caption English
sclip -i interview_eng.mp4 -l en

# Video Jepang → Caption Jepang
sclip -i anime_clip.mp4 -l ja

# Video Korea → Caption Korea
sclip -i kdrama_clip.mp4 -l ko

# Video English → Caption Indonesia (translasi)
sclip -i ted_talk.mp4 -l id

# Video Indonesia → Caption English (translasi)
sclip -i vlog_indo.mp4 -l en
```

### Troubleshooting Multi-Bahasa

**Q: Caption tidak muncul atau karakter aneh?**
- Pastikan font yang mendukung bahasa tersebut ter-install di sistem
- Untuk CJK (Chinese, Japanese, Korean), install font seperti Noto Sans CJK

**Q: Hasil transcription tidak akurat?**
- Pastikan audio video jelas dan minim noise
- Coba gunakan bahasa yang sama dengan audio video
- Gemini AI tidak 100% akurat, terutama untuk bahasa dengan dialek regional

**Q: Bahasa tidak didukung?**
- Coba gunakan kode bahasa ISO 639-1 yang benar
- Beberapa bahasa mungkin memiliki dukungan terbatas di Gemini

---

## 9. Troubleshooting

### Error: "Python is not recognized"

**Penyebab:** Python tidak ada di PATH

**Solusi:**
1. Reinstall Python
2. Pastikan centang "Add Python to PATH"

### Error: "No module named 'xxx'"

**Penyebab:** Package belum ter-install

**Solusi:**
```cmd
pip install nama-package
```

Atau install ulang semua:
```cmd
pip install -r requirements.txt
```

### Error: "FFmpeg not found"

**Penyebab:** FFmpeg tidak ter-install atau tidak ada di PATH

**Solusi:**
1. Install FFmpeg (lihat Section 6)
2. Restart terminal setelah install
3. Atau gunakan flag `--ffmpeg-path`:
```cmd
sclip -i video.mp4 --ffmpeg-path "C:\ffmpeg\bin\ffmpeg.exe"
```

### Error: "Invalid API key"

**Penyebab:** API key salah atau expired

**Solusi:**
1. Buat API key baru di https://aistudio.google.com/
2. Update environment variable atau config file

### Error: "Rate limit exceeded"

**Penyebab:** Terlalu banyak request ke Gemini API

**Solusi:**
1. Tunggu beberapa menit
2. Gemini free tier punya limit per menit/hari

### Error: "Video too short"

**Penyebab:** Video kurang dari 60 detik

**Solusi:**
- SmartClip membutuhkan video minimal 60 detik
- Gunakan video yang lebih panjang

### Error: "Video too long"

**Penyebab:** Video melebihi context window Gemini

**Solusi:**
- SmartClip akan otomatis chunking video panjang (> 30 menit)
- Jika masih error, coba video yang lebih pendek dulu

### Virtual Environment Tidak Aktif

**Gejala:** Package tidak ditemukan meskipun sudah install

**Solusi:**
```cmd
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

Pastikan ada `(venv)` di awal prompt.

### Error: "Must provide either --input or --url"

**Penyebab:** Tidak ada input video yang diberikan

**Solusi:**
Berikan salah satu:
```cmd
sclip -i video.mp4        # File lokal
sclip -u "youtube-url"    # YouTube URL
```

### Error: "Cannot use both --input and --url"

**Penyebab:** Memberikan kedua input sekaligus

**Solusi:**
Pilih salah satu saja, jangan keduanya.

---

## 10. Glossary

| Term | Penjelasan |
|------|------------|
| **CLI** | Command Line Interface - program yang dijalankan via terminal |
| **Virtual Environment (venv)** | Ruang terisolasi untuk install package Python |
| **pip** | Package manager untuk Python |
| **API Key** | Kunci untuk mengakses layanan (seperti Gemini) |
| **FFmpeg** | Tool open-source untuk memproses video/audio |
| **FFprobe** | Tool dari FFmpeg untuk menganalisis metadata video |
| **yt-dlp** | Tool untuk download video dari YouTube |
| **Burn-in Captions** | Subtitle yang "ditanam" permanen ke video |
| **Aspect Ratio** | Perbandingan lebar:tinggi video (9:16, 1:1, 16:9) |
| **Dry Run** | Menjalankan preview tanpa benar-benar memproses |
| **Chunking** | Memecah video panjang jadi bagian-bagian kecil |
| **H.264** | Codec video standar untuk kompatibilitas tinggi |
| **AAC** | Codec audio standar untuk kompatibilitas tinggi |
| **ASS** | Format subtitle dengan styling (Advanced SubStation Alpha) |

---

## Quick Reference Card

```
# Setup (sekali saja)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .              # Optional: install as package

# Setiap kali mau pakai
venv\Scripts\activate
sclip [options]

# Options yang sering dipakai
-i, --input       : File video input
-u, --url         : YouTube URL
-o, --output      : Folder output (default: ./output)
-n, --max-clips   : Jumlah clips (default: 5)
-a, --aspect-ratio: Aspect ratio (9:16, 1:1, 16:9)
-s, --caption-style: Style caption (default, bold, minimal, karaoke)
-l, --language    : Bahasa untuk captions (default: id - Indonesia)
-f, --force       : Overwrite existing files
-v, --verbose     : Mode detail
-q, --quiet       : Mode silent (errors only)
--dry-run         : Preview tanpa render
--no-captions     : Skip caption burn-in
--no-metadata     : Skip metadata files
--info            : Lihat info video saja
--check-deps      : Cek dependencies
--setup           : Setup wizard
--help            : Bantuan
--version         : Lihat versi
```

---

## CLI Options Reference

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--input` | `-i` | - | Path ke file video lokal |
| `--url` | `-u` | - | YouTube URL |
| `--output` | `-o` | `./output` | Folder output |
| `--max-clips` | `-n` | `5` | Maksimum clips |
| `--min-duration` | - | `45` | Durasi minimum (detik) |
| `--max-duration` | - | `180` | Durasi maksimum (detik) |
| `--aspect-ratio` | `-a` | `9:16` | Aspect ratio output |
| `--caption-style` | `-s` | `default` | Style caption |
| `--language` | `-l` | `id` | Bahasa (Indonesia) |
| `--force` | `-f` | `false` | Overwrite files |
| `--verbose` | `-v` | `false` | Debug output |
| `--quiet` | `-q` | `false` | Silent mode |
| `--dry-run` | - | `false` | Preview only |
| `--no-captions` | - | `false` | Skip captions |
| `--no-metadata` | - | `false` | Skip metadata |
| `--keep-temp` | - | `false` | Keep temp files |
| `--api-key` | - | env var | Gemini API key |
| `--model` | - | `gemini-2.0-flash` | Gemini model to use |
| `--ffmpeg-path` | - | auto | Custom FFmpeg path |
| `--info` | - | `false` | Show video info |
| `--check-deps` | - | `false` | Check dependencies |
| `--setup` | - | `false` | Run setup wizard |

---

## 11. FAQ (Frequently Asked Questions)

### Umum

**Q: Berapa lama waktu yang dibutuhkan untuk memproses video?**

A: Waktu pemrosesan tergantung pada beberapa faktor:
- Durasi video asli
- Kecepatan internet (untuk upload ke Gemini API)
- Spesifikasi hardware komputer
- Jumlah clips yang di-generate

Sebagai patokan, video 30 menit biasanya membutuhkan 5-15 menit untuk diproses sepenuhnya.

**Q: Apakah SmartClip gratis?**

A: SmartClip sendiri gratis dan open-source. Namun, kamu membutuhkan:
- Google Gemini API key (ada free tier dengan batasan)
- FFmpeg (gratis dan open-source)
- yt-dlp (gratis dan open-source, optional untuk YouTube)

**Q: Format video apa saja yang didukung?**

A: SmartClip mendukung format input berikut:
- `.mp4` (recommended)
- `.mkv`
- `.avi`
- `.mov`
- `.webm`
- `.m4v`
- `.mpeg`, `.mpg`
- `.flv`

Output selalu dalam format `.mp4` (H.264 + AAC) untuk kompatibilitas maksimal.

**Q: Berapa durasi minimum dan maksimum video yang bisa diproses?**

A: 
- Minimum: 60 detik (video lebih pendek akan ditolak)
- Maksimum: Tidak ada batasan keras, tapi video > 30 menit akan di-chunk otomatis

---

### API & Gemini

**Q: Apa itu rate limit dan bagaimana mengatasinya?**

A: Rate limit adalah batasan jumlah request ke Gemini API dalam periode waktu tertentu. Jika kamu mendapat error "Rate limit exceeded":
1. Tunggu beberapa menit sebelum mencoba lagi
2. Gemini free tier memiliki batasan per menit dan per hari
3. Untuk penggunaan intensif, pertimbangkan upgrade ke paid tier

**Q: API key saya tidak berfungsi, apa yang harus dilakukan?**

A: Cek hal-hal berikut:
1. Pastikan API key di-copy dengan benar (tanpa spasi di awal/akhir)
2. Cek apakah API key masih aktif di [Google AI Studio](https://aistudio.google.com/)
3. Pastikan billing sudah di-setup jika menggunakan paid tier
4. Coba generate API key baru jika masih bermasalah

**Q: Kenapa hasil analisis AI kadang tidak akurat?**

A: AI tidak sempurna. Beberapa tips untuk hasil lebih baik:
- Gunakan video dengan audio yang jelas
- Video dengan satu speaker biasanya lebih akurat
- Hindari video dengan banyak background noise
- Coba jalankan ulang - hasil bisa berbeda setiap kali

**Q: Apakah video saya aman? Apakah Google menyimpan video saya?**

A: Video di-upload ke Gemini API untuk analisis. Menurut kebijakan Google:
- Video diproses untuk menghasilkan analisis
- Sebaiknya baca [Google AI Terms of Service](https://ai.google.dev/terms) untuk detail lengkap
- Jangan upload video yang mengandung informasi sensitif atau rahasia

---

### FFmpeg & Video Processing

**Q: Kenapa FFmpeg tidak terdeteksi meskipun sudah di-install?**

A: Beberapa kemungkinan:
1. FFmpeg belum ditambahkan ke PATH
2. Terminal/Command Prompt perlu di-restart setelah install
3. Coba gunakan `--ffmpeg-path` untuk specify lokasi manual:
   ```cmd
   sclip -i video.mp4 --ffmpeg-path "C:\ffmpeg\bin\ffmpeg.exe"
   ```

**Q: Rendering sangat lambat, bagaimana mempercepat?**

A: Beberapa tips:
1. Pastikan menggunakan SSD, bukan HDD
2. Tutup aplikasi lain yang berat
3. Video dengan resolusi tinggi (4K) akan lebih lambat
4. Pertimbangkan untuk mengurangi jumlah clips (`-n 3`)

**Q: Output video corrupt atau tidak bisa diputar?**

A: Coba langkah berikut:
1. Pastikan ada cukup disk space
2. Cek apakah input video tidak corrupt
3. Coba dengan video lain untuk memastikan bukan masalah SmartClip
4. Jalankan dengan `--verbose` untuk melihat error detail

**Q: Captions tidak muncul di output video?**

A: Kemungkinan penyebab:
1. AI tidak mendeteksi speech yang jelas di video
2. Font yang dibutuhkan tidak tersedia (SmartClip akan menggunakan fallback font)
3. Coba caption style berbeda: `--caption-style bold`
4. Pastikan tidak menggunakan `--no-captions`

**Q: Bagaimana cara mengubah kualitas output video?**

A: Saat ini SmartClip menggunakan setting default yang optimal (CRF 23, medium preset). Untuk kebutuhan khusus, kamu perlu memodifikasi source code di `src/services/renderer.py`.

---

### YouTube Download

**Q: Kenapa download YouTube gagal?**

A: Beberapa kemungkinan:
1. **yt-dlp tidak ter-install**: Install dengan `pip install yt-dlp`
2. **Video private/unavailable**: Pastikan video bisa diakses secara publik
3. **Video age-restricted**: SmartClip tidak bisa download video yang memerlukan login
4. **Geo-restricted**: Video tidak tersedia di region kamu
5. **yt-dlp outdated**: Update dengan `pip install --upgrade yt-dlp`

**Q: Apakah bisa download video dari platform lain selain YouTube?**

A: Saat ini SmartClip hanya mendukung YouTube URL. Untuk platform lain, download video secara manual terlebih dahulu, lalu gunakan `--input` flag.

**Q: Download YouTube sangat lambat?**

A: Kecepatan download tergantung pada:
1. Kecepatan internet kamu
2. Server YouTube
3. Kualitas video yang dipilih (SmartClip memilih kualitas terbaik)

---

### Captions & Styling

**Q: Apa perbedaan caption styles yang tersedia?**

A: SmartClip menyediakan 4 style:
- **default**: Font Arial Bold, putih dengan outline hitam, posisi bawah
- **bold**: Font Impact, kuning dengan outline tebal, posisi tengah
- **minimal**: Font Helvetica, putih dengan outline tipis, posisi bawah
- **karaoke**: Font Arial Bold dengan highlight kata per kata (word-by-word)

**Q: Bagaimana cara mengubah font caption?**

A: Saat ini font ditentukan oleh style preset. Untuk custom font, kamu perlu memodifikasi `CAPTION_STYLES` di `src/utils/captions.py`.

**Q: Caption timing tidak sinkron dengan audio?**

A: Ini bisa terjadi karena:
1. AI transcription tidak 100% akurat
2. Video dengan audio yang tidak jelas
3. Coba video dengan audio yang lebih bersih

---

### Troubleshooting Lanjutan

**Q: SmartClip crash tanpa error message?**

A: Coba langkah berikut:
1. Jalankan dengan `--verbose` untuk melihat detail
2. Cek apakah ada cukup RAM (minimal 4GB, recommended 8GB)
3. Cek disk space
4. Coba dengan video yang lebih kecil/pendek

**Q: Error "Permission denied" saat menyimpan output?**

A: Kemungkinan penyebab:
1. Folder output tidak writable
2. File dengan nama sama sedang dibuka di aplikasi lain
3. Coba gunakan folder output berbeda: `-o "D:\MyClips"`
4. Gunakan `--force` untuk overwrite file existing

**Q: Bagaimana cara melihat log detail untuk debugging?**

A: Gunakan flag `--verbose`:
```cmd
sclip -i video.mp4 --verbose
```

Ini akan menampilkan:
- Progress detail setiap tahap
- FFmpeg output
- API response info
- File paths yang digunakan

**Q: SmartClip menggunakan terlalu banyak CPU/RAM?**

A: Video processing memang resource-intensive. Tips:
1. Proses satu video pada satu waktu
2. Tutup aplikasi lain
3. Untuk video panjang, biarkan proses berjalan tanpa interupsi
4. Pertimbangkan untuk mengurangi jumlah clips

**Q: Temp files tidak terhapus setelah proses selesai?**

A: Normalnya SmartClip membersihkan temp files otomatis. Jika tidak:
1. Cek folder temp sistem (`%TEMP%` di Windows, `/tmp` di Linux/macOS)
2. Cari file dengan prefix `sclip_`
3. Hapus manual jika diperlukan
4. Gunakan `--keep-temp` jika ingin menyimpan temp files untuk debugging

---

### Tips & Best Practices

**Q: Tips untuk mendapatkan clips terbaik?**

A: 
1. Gunakan video dengan audio yang jelas dan minim noise
2. Video dengan satu speaker biasanya menghasilkan clips lebih baik
3. Podcast dan interview adalah format ideal
4. Coba berbagai `--min-duration` dan `--max-duration` untuk hasil berbeda
5. Gunakan `--dry-run` dulu untuk preview sebelum rendering

**Q: Bagaimana workflow yang recommended?**

A: 
1. Jalankan `sclip --check-deps` untuk memastikan semua siap
2. Gunakan `--dry-run` untuk preview clips yang akan dibuat
3. Jika preview bagus, jalankan tanpa `--dry-run`
4. Review output dan pilih clips terbaik

**Q: Apakah bisa batch process multiple videos?**

A: Saat ini SmartClip memproses satu video per command. Untuk batch processing, kamu bisa membuat script:

**Windows (batch file):**
```batch
@echo off
for %%f in (*.mp4) do (
    sclip -i "%%f" -o "output\%%~nf"
)
```

**Linux/macOS (bash):**
```bash
for f in *.mp4; do
    sclip -i "$f" -o "output/${f%.*}"
done
```

---

## Butuh Bantuan?

Jika masih ada masalah:
1. Baca error message dengan teliti
2. Jalankan `sclip --check-deps` untuk cek dependencies
3. Jalankan `sclip --setup` untuk setup wizard
4. Cek FAQ di atas
5. Google error message tersebut
6. Cek GitHub Issues (jika ada)
7. Tanya di komunitas Python/AI

Happy clipping! 🎬
