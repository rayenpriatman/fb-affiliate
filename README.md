# fb-affiliate

Alat posting konten afiliasi Shopee ke Facebook Page.

- **`dashboard.html`**: antrian posting manual (upload foto/video sendiri).
- **`autopost/`**: **video otomatis**. Naskah ditulis dari template (gratis) atau Claude (opsional), suara AI membacakan narasi,
  ffmpeg merender video vertikal 9:16, lalu video diposting ke Facebook Page. Bisa dijalankan
  terjadwal tiap hari lewat GitHub Actions.

## Cara kerja video AI

```
products.json ──► naskah: template gratis / Claude ──► Edge TTS (suara Indonesia)
                                                    │
foto produk ──► Pillow (latar + teks) ──► ffmpeg (zoom/Ken Burns, 1080x1920) ──► Facebook Page
```

Tiap jalan, satu produk dipakai secara bergiliran. Giliran berikutnya disimpan di
`autopost_state.json`.

## 1. Isi produk

Edit `products.json`:

```json
{
  "products": [
    {
      "name": "Botol Minum Tumbler 1 Liter",
      "price": "Rp49.000",
      "affiliate_link": "https://s.shopee.co.id/xxxx",
      "selling_points": ["tahan dingin 12 jam", "anti bocor"],
      "audience": "pekerja kantoran yang sering lupa minum",
      "tone": "santai, relate",
      "images": ["assets/products/tumbler-1.jpg", "https://.../foto2.jpg"]
    }
  ]
}
```

`images` bisa berupa path di repo (taruh di `assets/products/`) atau URL. Kalau kosong, video
memakai latar gradasi.

## 2. Siapkan kredensial

| Secret (GitHub → Settings → Secrets and variables → Actions) | Isi |
|---|---|
| `ANTHROPIC_API_KEY` | **Opsional, berbayar.** Kalau diisi, naskah ditulis Claude. Kalau kosong, pakai template gratis. |
| `FB_PAGE_ID` | ID Facebook Page |
| `FB_PAGE_TOKEN` | Page Access Token long-lived dengan izin `pages_manage_posts`, `pages_read_engagement` |

Cara mendapatkan Page Access Token long-lived:
1. Buat app di developers.facebook.com, lalu buka **Graph API Explorer**.
2. Pilih app-mu, centang izin `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, lalu klik *Generate Access Token*.
3. Tukar ke token long-lived:
   `GET /oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=TOKEN_TADI`
4. Ambil token Page: `GET /me/accounts?access_token=TOKEN_LONG_LIVED`. Kolom `access_token` milik Page-mu
   adalah `FB_PAGE_TOKEN`, dan `id` adalah `FB_PAGE_ID`. Token Page dari user token long-lived tidak kedaluwarsa.

Opsional: variable `TTS_VOICE` (`id-ID-GadisNeural` wanita, default, atau `id-ID-ArdiNeural` pria).

## 3. Jalankan

**Otomatis:** workflow `.github/workflows/autopost.yml` jalan tiap hari pukul 12:00 WIB
(ubah `cron` sesuai kebutuhan). Jadwal hanya aktif setelah workflow ada di branch default (`main`).
Untuk mencoba tanpa posting: tab **Actions** → *Video AI auto-post ke Facebook* → **Run workflow**,
centang *dry run*, lalu unduh videonya dari artifact.

**Lokal:**

```bash
sudo apt install ffmpeg            # macOS: brew install ffmpeg
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...  FB_PAGE_ID=...  FB_PAGE_TOKEN=...

python -m autopost --dry-run       # buat video ke folder output/, tidak diposting
python -m autopost                 # buat video + posting
python -m autopost --product 2     # pilih produk tertentu
python -m autopost --no-voice      # tanpa narasi suara
python -m autopost --writer template   # paksa naskah template gratis
python -m autopost --script-file naskah.json   # pakai naskah sendiri, tanpa Claude
```

## Catatan

- Facebook mewajibkan konten afiliasi tetap mematuhi Kebijakan Konten Bermerek. Cek naskah
  hasil AI sesekali, terutama klaim produk.
- **Biaya:** mode gratis (tanpa `ANTHROPIC_API_KEY`) Rp0. Suara Edge TTS, ffmpeg, Graph API Facebook,
  dan GitHub Actions semuanya gratis (repo privat dapat 2.000 menit Actions per bulan, satu video butuh sekitar 2–3 menit).
  Kalau `ANTHROPIC_API_KEY` diisi, ada biaya satu panggilan Claude per video (beberapa sen dolar).
- Naskah template lebih bervariasi kalau `selling_points` di `products.json` diisi dengan bahasa yang enak dibaca,
  karena kalimat itu dibacakan apa adanya.
