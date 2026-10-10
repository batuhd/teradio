# Teradio

Terminalde çalışan, ncspot tarzı internet radyosu. `mpv` ile çalar,
istasyonları [radio-browser.info](https://www.radio-browser.info/) üzerinden
(API anahtarı gerekmeden) bulur.

```
┌ Teradio ───────────────────────────────────────────────┐
│ Ara                │ İstasyon        Ülke     Codec kbps │
│ En Çok Dinlenen    │ Adroit Jazz     USA      MP3   320  │
│ Favoriler          │ 101 Smooth Jazz USA      MP3   128  │
│ Geçmiş             │ ...                                 │
│ Ülkeler            │                                     │
│ Türler             │                                     │
│ Rastgele Çal       │                                     │
├────────────────────────────────────────────────────────┤
│ Adroit Jazz  ·  some track    │ ses 80% │ 100 istasyon   │
└────────────────────────────────────────────────────────┘
```

## Kurulum

### Arch / CachyOS (tek satır, AUR'suz)

```bash
curl -fsSL https://raw.githubusercontent.com/batuhd/teradio/main/install.sh | sh
```

Bu, kaynaktan derleyip `pacman` ile kurar (paket olarak izlenir).

### Arch / CachyOS — hazır paket (derlemesiz)

```bash
sudo pacman -U https://github.com/batuhd/teradio/releases/download/v0.1.0/teradio-0.1.0-1-any.pkg.tar.zst
```

### AUR (yakında)

```bash
yay -S teradio      # veya: paru -S teradio
```

> `pacman -S teradio` yalnızca resmi depodaki paketler için çalışır. AUR
> paketleri `yay`/`paru` ile kurulur; komut deneyimi aynıdır.

### pipx (her dağıtım)

```bash
pipx install git+https://github.com/batuhd/teradio
```

### Gereksinimler

- Python 3.10+
- `mpv` (ses motoru): `sudo pacman -S mpv` / `sudo apt install mpv`

## Kullanım

```bash
teradio
```

| Tuş       | İşlev                          |
|-----------|--------------------------------|
| `/`       | Arama alanına git              |
| `Enter`   | Seçili istasyonu çal / aç      |
| `Space`   | Durdur / devam et              |
| `n` / `p` | Sonraki / önceki istasyonu çal |
| `del`     | Geçmiş/Favoriler'den sil       |
| `s`       | Tamamen durdur                 |
| `+` / `-` | Ses artır / azalt              |
| `m`       | Sessize al                      |
| `f`       | Favorilere ekle / çıkar        |
| `r`       | Rastgele bir istasyon çal      |
| `,`       | Ayarlar (dil, tema, komutlar)  |
| `Esc`     | Ayarlarda geri / üst menü      |
| `q`       | Çıkış                          |

Ok tuşlarıyla liste ve panel arasında gezinebilirsin. İstasyonlar `Enter` ile
veya tek fare tıklamasıyla çalar.

## Ayarlar

`,` ile açılır; kısa bir menüden içine girersin, `Esc` ile geri dönersin:

- **Dil** — Türkçe / English
- **Tema** — Textual'in tüm renk temaları (seçim anında uygulanır)
- **Komutlar** — Ara, En Çok Dinlenen, Favoriler, Geçmiş, Ülkeler, Türler,
  Rastgele Çal, Dur, Çık

`Enter` (veya tık) ile seç; `Esc` bir üst menüye / önceki listeye döner.

## Dil

Uygulama ilk açılışta makinenin dilini (`LANG`/`LC_ALL`) algılar. Desteklenen
diller: Türkçe, English. Ayarlar (`,`) ekranından değiştirilebilir; kenar
çubuğu, başlıklar ve kısayol açıklamaları anında güncellenir.

## Kaynak kullanımı

- mpv süreci **yalnızca çalarken** vardır; gezerken/ilk açılışta hiç başlatılmaz.
- `Space` duraklatır, `s` tamamen durdurur ve **mpv sürecini kapatır** (arkada
  hiçbir şey kalmaz).
- Çalma dışında uygulamanın CPU kullanımı ~%0'dır; ağ isteği sadece liste
  yüklerken yapılır, periyodik yoklama (polling) yapılmaz.

## Veri konumu

Favoriler, geçmiş ve ayarlar `~/.config/teradio/` altında saklanır
(`favorites.json`, `recent.json`, `config.json`).

## Geliştirme

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/python -m teradio
```

## Lisans

MIT
