import importlib

import teradio.store as store_mod


def test_favorites_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    importlib.reload(store_mod)
    s = store_mod.Store()

    station = {"uuid": "abc", "name": "Test FM", "url": "http://x"}
    assert not s.is_favorite("abc")
    assert s.toggle_favorite(station) is True
    assert s.is_favorite("abc")
    assert s.toggle_favorite(station) is False
    assert not s.is_favorite("abc")


def test_favorites_persist(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    importlib.reload(store_mod)
    s = store_mod.Store()
    s.toggle_favorite({"uuid": "1", "name": "A"})

    importlib.reload(store_mod)
    assert store_mod.Store().is_favorite("1")


def test_recent_dedup_and_order(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    importlib.reload(store_mod)
    s = store_mod.Store()
    s.add_recent({"uuid": "1", "name": "A"})
    s.add_recent({"uuid": "2", "name": "B"})
    s.add_recent({"uuid": "1", "name": "A"})
    assert [r["uuid"] for r in s.recent()] == ["1", "2"]


def test_config_set_get(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    importlib.reload(store_mod)
    s = store_mod.Store()
    assert s.get("volume", 80) == 80
    s.set("volume", 55)
    assert s.get("volume") == 55
