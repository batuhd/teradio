# Teradio'yu yayınlama (CachyOS / Arch + AUR)

Hedef: kullanıcı terminalde `yay -S teradio` (veya `paru -S teradio`) yazınca
kursun, sonra `teradio` yazınca açılsın.

> `pacman -S teradio` yalnızca resmi depodaki paketler için çalışır. AUR paketi
> `yay`/`paru` ile kurulur; deneyim aynıdır. İstersen ileride resmi depoya da
> başvurabilirsin (aşağıda not).

Not: `textual` Arch depolarında yok, bu yüzden paket onu **kendi içinde**
barındırır — kullanıcının ek bir şey kurmasına gerek kalmaz. Tek sistem
gereksinimi `mpv` (PKGBUILD `depends` ile çeker).

---

## 1) Kodu GitHub'a koy

> Önemli: Bu klasör şu an üst dizindeki bir git deposunun içinde ve kendi
> `.git`'i yok. Yayın için Teradio'nun **kendi** deposunu oluştur.

```bash
cd ~/Belgeler/git/Teradio
git init                       # Teradio'yu kendi deposu yapar
git add -A
git commit -m "Teradio 0.1.0"

# GitHub'da boş bir repo oluştur (ad: teradio), sonra:
git remote add origin git@github.com:KULLANICI_ADIN/teradio.git
git branch -M main
git push -u origin main

# Sürüm etiketi (PKGBUILD bunu indirir):
git tag v0.1.0
git push origin v0.1.0
```

## 2) PKGBUILD'ı kendine göre doldur

`PKGBUILD` içinde şu satırları düzenle:
- `# Maintainer:` → adın ve e-postan
- `url=` → GitHub repo adresin

## 3) Sağlama toplamı ve `.SRCINFO` üret

```bash
cd ~/Belgeler/git/Teradio
updpkgsums                 # sha256sums=('SKIP') yerine gerçek değeri yazar
makepkg --printsrcinfo > .SRCINFO
```

## 4) AUR'a yükle

Not: AUR'a **yalnızca** `PKGBUILD` ve `.SRCINFO` gider (kaynak kod GitHub'da kalır).

```bash
# AUR hesabı: https://aur.archlinux.org  → hesap + SSH anahtarı ekle
git clone ssh://aur@aur.archlinux.org/teradio.git ~/aur/teradio
cp PKGBUILD .SRCINFO ~/aur/teradio/
cd ~/aur/teradio
git add PKGBUILD .SRCINFO
git commit -m "teradio 0.1.0"
git push
```

Artık herkes:

```bash
yay -S teradio        # veya: paru -S teradio
teradio               # arayüz açılır
```

## 5) Kurulumu yerel test et (AUR'a koymadan önce)

```bash
cd ~/Belgeler/git/Teradio
makepkg -si            # derler + paketler + kurar (sudo ister)
teradio
sudo pacman -Rns teradio   # kurulumu geri al
```

## 6) `-git` (rolling) paket — opsiyonel

Ayrıca `teradio-git/PKGBUILD` var; her zaman en son commit'i derler. Yayınlamak için:

```bash
git clone ssh://aur@aur.archlinux.org/teradio-git.git ~/aur/teradio-git
cd ~/Belgeler/git/Teradio/teradio-git
updpkgsums
makepkg --printsrcinfo > .SRCINFO
cp PKGBUILD .SRCINFO ~/aur/teradio-git/
cd ~/aur/teradio-git && git add -A && git commit -m "teradio-git" && git push
```

Kullanıcı: `yay -S teradio-git`

## 7) Yeni sürüm yayınlama

1. `teradio/__init__.py` ve `pyproject.toml` içindeki `__version__`'ı artır.
2. Commit + yeni etiket: `git tag v0.2.0 && git push origin v0.2.0`
3. `PKGBUILD` içinde `pkgver=0.2.0` yap, `pkgrel=1`'e sıfırla.
4. `updpkgsums`
5. AUR deposunda `PKGBUILD`'ı güncelle, `makepkg --printsrcinfo > .SRCINFO`, commit + push.

---

## Notlar

- **Resmi depo:** İleride `extra` deposuna alınmasını istersen Arch paket
  gönderim sürecini izleyebilirsin; ama bu daha uzun ve `textual` bağımlılığı
  ayrı bir paket gerektirdiği için AUR en pratik yoldur.
- **Kendi küçük depon (pacman -S):** Gerçekten `pacman -S teradio` istiyorsan
  `repo-add` ile kişisel bir binary depo kurup kullanıcılara `[teradio]`
  bölümünü `pacman.conf`'a ekletmen gerekir. AUR çok daha az zahmetlidir.
- Paket, uygulamayı `/usr/lib/teradio` altına kurar; `teradio` başlatıcısı
  `python3 -m teradio` çalıştırır. Sistem gereksinimi sadece `python` ve `mpv`.
