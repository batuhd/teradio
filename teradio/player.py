"""mpv'yi kalıcı süreç olarak çalıştırır ve JSON IPC ile kontrol eder.

Tek bir mpv süreci --idle modunda açılır; istasyon değiştirmek süreci
öldürmez, sadece yeni dosya yüklenir. Böylece durdurma/ses anlık olur ve
yayının ICY metadata'sı (çalan şarkı) dinlenebilir.

Durum (state) mpv'nin core-idle / pause / idle-active / end-file olaylarından
türetilir: connecting -> playing/paused, hata olursa error.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from typing import Callable


class PlayerError(RuntimeError):
    pass


class Player:
    def __init__(
        self,
        on_metadata: Callable[[str], None] | None = None,
        on_state: Callable[[str], None] | None = None,
        volume: int = 80,
    ) -> None:
        self.on_metadata = on_metadata
        self.on_state = on_state
        self.volume = max(0, min(130, int(volume)))
        self.sock_path = os.path.join(
            tempfile.gettempdir(), f"teradio-mpv-{os.getpid()}.sock"
        )
        self.proc: subprocess.Popen | None = None
        self.state = "stopped"
        self._sock: socket.socket | None = None
        self._file = None
        self._lock = threading.Lock()
        self._req = 0
        self._pause = False
        self._core_idle = True
        self._idle = True
        self._play_token = 0
        self._reached_playing = False

    @staticmethod
    def available() -> bool:
        return shutil.which("mpv") is not None

    def start(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            return  # zaten çalışıyor
        if not self.available():
            raise PlayerError("mpv bulunamadı. Kur: sudo pacman -S mpv")
        try:
            os.unlink(self.sock_path)
        except FileNotFoundError:
            pass
        self.proc = subprocess.Popen(
            [
                "mpv",
                "--no-config",            # kullanıcı ayarlarını okuma
                "--load-scripts=no",      # lua scriptlerini yükleme
                "--no-video",
                "--audio-display=no",
                "--force-window=no",
                "--idle=yes",
                # Küçük tampon: güvenilir bağlanır, belleği şişirmez.
                "--cache=yes",
                "--cache-secs=2",
                "--demuxer-max-bytes=1MiB",
                "--demuxer-max-back-bytes=512KiB",
                "--audio-buffer=0.2",
                "--osd-level=0",
                "--really-quiet",
                "--no-terminal",
                "--no-input-default-bindings",
                "--network-timeout=15",
                f"--volume={self.volume}",
                f"--input-ipc-server={self.sock_path}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            if os.path.exists(self.sock_path):
                break
            if self.proc.poll() is not None:
                raise PlayerError("mpv başlatılamadı")
            time.sleep(0.05)

        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(self.sock_path)
        self._file = self._sock.makefile("rwb")
        threading.Thread(target=self._reader, daemon=True).start()
        self._cmd(["observe_property", 1, "metadata"])
        self._cmd(["observe_property", 2, "media-title"])
        self._cmd(["observe_property", 3, "pause"])
        self._cmd(["observe_property", 4, "core-idle"])
        self._cmd(["observe_property", 5, "idle-active"])

    def _cmd(self, args: list) -> None:
        if not self._file:
            return
        with self._lock:
            self._req += 1
            msg = json.dumps({"command": args, "request_id": self._req}) + "\n"
            try:
                self._file.write(msg.encode())
                self._file.flush()
            except (BrokenPipeError, ValueError):
                pass

    def _reader(self) -> None:
        assert self._file is not None
        try:
            for line in self._file:
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._handle(evt)
        except (OSError, ValueError):
            pass  # mpv kapandı / soket sıfırlandı

    def _handle(self, evt: dict) -> None:
        event = evt.get("event")
        if event == "property-change":
            name = evt.get("name")
            if name in ("metadata", "media-title"):
                title = self._title_from(evt)
                if title and self.on_metadata:
                    self.on_metadata(title)
            elif name == "pause":
                self._pause = bool(evt.get("data"))
                self._emit_state()
            elif name == "core-idle":
                self._core_idle = bool(evt.get("data"))
                self._emit_state()
            elif name == "idle-active":
                self._idle = bool(evt.get("data"))
                self._emit_state()
        elif event == "start-file":
            self._idle = False
            self._core_idle = True
            self._pause = False
            self._set_state("connecting")
        elif event == "end-file":
            if evt.get("reason") == "error":
                self._set_state("error")
            else:
                self._set_state("stopped")

    def _emit_state(self) -> None:
        if self._idle:
            self._set_state("stopped")
        elif self._core_idle:
            self._set_state("connecting")
        elif self._pause:
            self._set_state("paused")
        else:
            self._set_state("playing")

    def _set_state(self, state: str) -> None:
        if state == "playing":
            self._reached_playing = True
        if state == self.state:
            return
        self.state = state
        if self.on_state:
            self.on_state(state)

    def _watchdog(self, token: int, seconds: float = 15.0) -> None:
        """Bu yükleme için hiç çalmaya geçilemediyse hata olarak işaretle."""
        time.sleep(seconds)
        if token == self._play_token and not self._reached_playing:
            self._set_state("error")

    @staticmethod
    def _title_from(evt: dict) -> str | None:
        data = evt.get("data")
        if evt.get("name") == "metadata" and isinstance(data, dict):
            for key, value in data.items():
                if key.lower() in ("title", "streamtitle", "icy-title") and value:
                    return value[0] if isinstance(value, list) else str(value)
        elif evt.get("name") == "media-title" and data:
            text = str(data)
            # ICY metadata yoksa mpv media-title olarak ham URL verir; onu gösterme
            if not text.startswith(("http://", "https://")):
                return text
        return None

    # -- kontrol --------------------------------------------------
    def play(self, url: str) -> None:
        self._play_token += 1
        self._reached_playing = False
        self._set_state("connecting")
        self._cmd(["loadfile", url, "replace"])
        threading.Thread(
            target=self._watchdog, args=(self._play_token,), daemon=True
        ).start()

    def toggle_pause(self) -> None:
        self._cmd(["cycle", "pause"])

    def stop(self) -> None:
        self._play_token += 1  # bekleyen watchdog'u iptal et
        self._cmd(["stop"])
        self._set_state("stopped")

    def set_volume(self, value: int) -> None:
        self.volume = max(0, min(130, int(value)))
        self._cmd(["set_property", "volume", self.volume])

    def quit(self) -> None:
        self._play_token += 1  # bekleyen watchdog'u iptal et
        self._cmd(["quit"])
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=2)  # zombiyi topla (reap)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        self._file = None
        try:
            os.unlink(self.sock_path)
        except FileNotFoundError:
            pass
