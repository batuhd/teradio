# Maintainer: Sen <senin@email.com>
pkgname=teradio
pkgver=0.1.0
pkgrel=1
pkgdesc="Terminalde çalışan internet radyosu (ncspot tarzı, mpv tabanlı)"
arch=('any')
url="https://github.com/KULLANICI_ADIN/teradio"
license=('MIT')
depends=('python' 'mpv')
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
  cd "$pkgname-$pkgver"
  python -m venv --clear "$srcdir/venv"
  "$srcdir/venv/bin/pip" install --no-compile --no-cache-dir .
}

package() {
  cd "$pkgname-$pkgver"

  # Uygulama ve Python bağımlılıkları (textual vb.) tek dizine kurulur.
  install -d "$pkgdir/usr/lib/$pkgname"
  cp -a "$srcdir/venv/lib/"python*/site-packages/. "$pkgdir/usr/lib/$pkgname/"

  # Gereksizleri at: pip/setuptools ve derlenmiş .pyc dosyaları.
  rm -rf "$pkgdir/usr/lib/$pkgname"/{pip,pip-*,setuptools,setuptools-*,pkg_resources,_distutils_hack,distutils-precedence.pth}
  find "$pkgdir/usr/lib/$pkgname" -name '__pycache__' -type d -prune -exec rm -rf {} +

  # Başlatıcı: 'teradio' komutu
  install -d "$pkgdir/usr/bin"
  printf '%s\n' \
    '#!/bin/sh' \
    'export PYTHONPATH="/usr/lib/teradio${PYTHONPATH:+:$PYTHONPATH}"' \
    'exec python3 -m teradio "$@"' \
    > "$pkgdir/usr/bin/$pkgname"
  chmod 755 "$pkgdir/usr/bin/$pkgname"

  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
