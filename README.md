# fb-affiliate

Alat posting konten afiliasi Shopee ke Facebook Page dan YouTube Shorts.

- **`dashboard.html`**: antrian posting manual (upload foto/video sendiri).
- **`autopost/`**: **video otomatis**. Naskah ditulis dari template (gratis) atau Claude (opsional), suara AI membacakan narasi,
  ffmpeg merender video vertikal 9:16, lalu video diposting ke Facebook Page dan/atau YouTube Shorts. Bisa dijalankan
  terjadwal tiap hari lewat GitHub Actions.

## Cara kerja video AI

```
products.json ──► naskah: template gratis / Claude ──► Edge TTS (suara Indonesia)
                                                    │
foto produk ──► Pillow (latar + teks) ──► ffmpeg (zoom/Ken Burns, 1080x1920) ──► Facebook Page
                                                                                    └──► YouTube Shorts
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

### YouTube Shorts (opsional)

| Secret | Isi |
|---|---|
| `YT_CLIENT_ID` | OAuth Client ID (tipe *Desktop app*) |
| `YT_CLIENT_SECRET` | OAuth Client Secret |
| `YT_REFRESH_TOKEN` | Refresh token channel, dari `python -m autopost.youtube_auth` |

Cara mendapatkannya:
1. Buka [console.cloud.google.com](https://console.cloud.google.com), buat project, lalu aktifkan **YouTube Data API v3**.
2. **OAuth consent screen**: tipe *External*, isi nama app & email. Tambahkan akun Google pemilik channel
   sebagai *test user*, lalu klik **Publish app** (status *In production*). Kalau tetap *Testing*,
   refresh token kedaluwarsa setiap 7 hari.
3. **Credentials → Create credentials → OAuth client ID**, tipe **Desktop app**. Catat Client ID & Secret.
4. Di komputer sendiri:
   ```bash
   pip install -r requirements.txt
   python -m autopost.youtube_auth --client-id CLIENT_ID --client-secret CLIENT_SECRET
   ```
   Login dengan akun pemilik channel. Abaikan peringatan "Google hasn't verified this app"
   (klik *Advanced → Go to ...*). Refresh token yang tercetak adalah `YT_REFRESH_TOKEN`.

Penting:
- **Project API yang belum diaudit Google: video otomatis terkunci *private*.** Supaya bisa publik,
  ajukan [YouTube API audit](https://support.google.com/youtube/contact/yt_api_form) (gratis). Sebelum lolos,
  video tetap terunggah dan bisa kamu ubah ke publik manual dari YouTube Studio.
- Kuota gratis 10.000 unit/hari, satu upload memakai 1.600 unit, jadi maksimal sekitar 6 video per hari.
- Link di deskripsi YouTube Shorts tidak bisa diklik. Supaya link afiliasi bisa diklik, pasang di
  *Related video* atau profil channel, atau arahkan penonton ke Facebook.
- Judul otomatis diberi `#Shorts`. Video 9:16 dengan durasi di bawah 3 menit otomatis masuk Shorts.

### Variable tambahan (Settings → Secrets and variables → Actions → Variables)

- `PLATFORMS`: `facebook`, `youtube`, atau `facebook,youtube`. Kalau kosong, posting ke semua platform yang kredensialnya diset.
- `YT_PRIVACY`: `public` (default), `unlisted`, atau `private`.

Opsional: variable `TTS_VOICE` (`id-ID-GadisNeural` wanita, default, atau `id-ID-ArdiNeural` pria).

## 3. Jalankan

**Otomatis:** workflow `.github/workflows/autopost.yml` jalan tiap hari pukul 12:00 WIB
(ubah `cron` sesuai kebutuhan). Jadwal hanya aktif setelah workflow ada di branch default (`main`).
Untuk mencoba tanpa posting: tab **Actions** → *Video AI auto-post ke Facebook & YouTube* → **Run workflow**,
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
python -m autopost --platforms youtube         # hanya ke YouTube
python -m autopost --platforms facebook,youtube --yt-privacy unlisted
```

Kalau satu platform gagal, platform lain tetap diposting dan giliran produk tetap maju.

## Catatan

- Facebook mewajibkan konten afiliasi tetap mematuhi Kebijakan Konten Bermerek. Cek naskah
  hasil AI sesekali, terutama klaim produk.
- **Biaya:** mode gratis (tanpa `ANTHROPIC_API_KEY`) Rp0. Suara Edge TTS, ffmpeg, Graph API Facebook, YouTube Data API,
  dan GitHub Actions semuanya gratis (repo privat dapat 2.000 menit Actions per bulan, satu video butuh sekitar 2–3 menit).
  Kalau `ANTHROPIC_API_KEY` diisi, ada biaya satu panggilan Claude per video (beberapa sen dolar).
- Naskah template lebih bervariasi kalau `selling_points` di `products.json` diisi dengan bahasa yang enak dibaca,
  karena kalimat itu dibacakan apa adanya.
