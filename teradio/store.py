"""Kalıcı veri: favoriler, geçmiş ve ayarlar (~/.config/teradio)."""
from __future__ import annotations

import json
import os
from pathlib import Path


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    d = Path(base) / "teradio"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(name: str, default):
    try:
        return json.loads((config_dir() / name).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(name: str, data) -> None:
    tmp = config_dir() / (name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(config_dir() / name)


class Store:
    def __init__(self) -> None:
        self._favs: list[dict] = _load("favorites.json", [])
        self._recent: list[dict] = _load("recent.json", [])
        self._config: dict = _load("config.json", {})

    # -- favoriler ------------------------------------------------
    def favorites(self) -> list[dict]:
        return list(self._favs)

    def is_favorite(self, uuid: str) -> bool:
        return any(s["uuid"] == uuid for s in self._favs)

    def toggle_favorite(self, station: dict) -> bool:
        if self.is_favorite(station["uuid"]):
            self._favs = [s for s in self._favs if s["uuid"] != station["uuid"]]
        else:
            self._favs.append(station)
        _save("favorites.json", self._favs)
        return self.is_favorite(station["uuid"])

    # -- geçmiş ---------------------------------------------------
    def recent(self) -> list[dict]:
        return list(self._recent)

    def add_recent(self, station: dict, limit: int = 25) -> None:
        self._recent = [s for s in self._recent if s["uuid"] != station["uuid"]]
        self._recent.insert(0, station)
        self._recent = self._recent[:limit]
        _save("recent.json", self._recent)

    def remove_recent(self, uuid: str) -> None:
        self._recent = [s for s in self._recent if s["uuid"] != uuid]
        _save("recent.json", self._recent)

    def remove_favorite(self, uuid: str) -> None:
        self._favs = [s for s in self._favs if s["uuid"] != uuid]
        _save("favorites.json", self._favs)

    # -- ayarlar --------------------------------------------------
    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value) -> None:
        self._config[key] = value
        _save("config.json", self._config)
