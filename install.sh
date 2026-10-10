#!/bin/sh
# Teradio kurulum betiği (Arch / CachyOS). AUR'a gerek yok: kaynaktan
# derleyip pacman ile kurar (paket olarak izlenir, güncellemesi de kolay).
#
# Kullanım:
#   curl -fsSL https://raw.githubusercontent.com/batuhd/teradio/main/install.sh | sh
#
set -eu

REPO="https://github.com/batuhd/teradio.git"

if ! command -v pacman >/dev/null 2>&1; then
    echo "Bu betik Arch/CachyOS içindir. Diğer dağıtımlarda:"
    echo "  pipx install git+$REPO"
    exit 1
fi

if ! command -v makepkg >/dev/null 2>&1; then
    echo "makepkg bulunamadı. Önce: sudo pacman -S base-devel"
    exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM

echo ">> Teradio indiriliyor..."
git clone --depth=1 "$REPO" "$tmp/teradio" >/dev/null

cd "$tmp/teradio/teradio-git"
echo ">> Derleniyor ve kuruluyor (sudo parolası istenecek)..."
makepkg -si --noconfirm

echo
echo ">> Kuruldu! Başlatmak için:  teradio"
