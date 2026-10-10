import asyncio

import teradio.app as appmod
from teradio.api import Station


def _stations(n=5):
    return [
        Station(
            uuid=f"u{i}", name=f"Radyo {i}", url=f"http://x/{i}", country="TR",
            codec="MP3", bitrate=128, votes=i, tags="", favicon="",
        )
        for i in range(n)
    ]


class FakePlayer:
    instances: list = []

    def __init__(self, on_metadata=None, on_state=None, volume=80):
        self.volume = volume
        self.on_metadata = on_metadata
        self.on_state = on_state
        self.proc = None
        self.play_calls: list[str] = []
        self.paused = False
        self.stopped = False

    @staticmethod
    def available() -> bool:
        return True

    def start(self):
        self.proc = object()
        FakePlayer.instances.append(self)

    def emit(self, state):
        if self.on_state:
            self.on_state(state)

    def play(self, url):
        self.play_calls.append(url)

    def toggle_pause(self):
        self.paused = True

    def stop(self):
        self.stopped = True

    def set_volume(self, v):
        self.volume = v

    def quit(self):
        pass


async def _settle(pilot, cond, timeout=3.0):
    for _ in range(int(timeout * 20)):
        if cond():
            return True
        await pilot.pause(0.05)
    return cond()


def _wire(monkeypatch):
    FakePlayer.instances = []
    monkeypatch.setattr(appmod, "Player", FakePlayer)
    monkeypatch.setattr(appmod.api, "top_click", lambda *a, **k: _stations())
    monkeypatch.setattr(appmod.api, "search", lambda q, *a, **k: _stations(3))
    monkeypatch.setattr(
        appmod.api, "countries",
        lambda *a, **k: [{"name": "Türkiye", "code": "TR", "count": 10}],
    )
    monkeypatch.setattr(appmod.api, "by_country", lambda code, *a, **k: _stations(3))


def test_click_plays_and_language_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _wire(monkeypatch)

    async def scenario():
        app = appmod.Teradio()
        async with app.run_test(size=(100, 30)) as pilot:
            tbl = app.query_one("#stations")
            assert await _settle(pilot, lambda: tbl.row_count == 5)

            # tek fare tıklaması çalmalı
            await pilot.click("#stations", offset=(3, 2))
            assert await _settle(pilot, lambda: bool(FakePlayer.instances and FakePlayer.instances[-1].play_calls))

            # alt barda istasyon görünmeli ama henüz "Çalıyor" DEMEMELİ (ses gelmeden)
            now = str(app.query_one("#now").render())
            assert "Radyo" in now
            assert "bağlanıyor" in now

            # bağlanma sırasında space yok sayılmalı
            fake = FakePlayer.instances[-1]
            await pilot.press("space")
            await pilot.pause(0.1)
            assert fake.paused is False

            # ses başlayınca "Çalıyor" görünmeli
            app._set_player_state("playing")
            await pilot.pause(0.1)
            assert "Çalıyor" in str(app.query_one("#now").render())

            # artık space duraklatmalı
            await pilot.press("space")
            await pilot.pause(0.1)
            assert fake.paused is True

            # alt bar footer ile üst üste binmemeli (ikisi de görünür olmalı)
            now_r = app.query_one("#now").region
            foot_r = app.query_one(appmod.Footer).region
            assert now_r.height >= 1 and foot_r.height >= 1
            assert now_r.y != foot_r.y

            # ayarlara git ve dili değiştir
            app.query_one("#cats").index = appmod._CAT_INDEX["settings"]
            assert await _settle(pilot, lambda: app._mode == "settings")
            app._set_language("en")
            await pilot.pause(0.2)
            assert app.lang == "en"
            assert "Settings" in str(app.query_one("#cat-settings Label").render())
            # footer kısayol açıklaması da değişmeli
            descs = {b.key: b.description for b in app.BINDINGS if b.show}
            assert descs.get("q") == "Quit"

    asyncio.run(scenario())


def test_single_click_triggers_once(tmp_path, monkeypatch):
    """Aynı satıra tıklamak her seferinde TAM bir kez tetiklemeli (çift olay yok)."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _wire(monkeypatch)

    async def scenario():
        app = appmod.Teradio()
        async with app.run_test(size=(100, 30)) as pilot:
            tbl = app.query_one("#stations")
            assert await _settle(pilot, lambda: tbl.row_count == 5)
            tbl.move_cursor(row=0)
            await pilot.pause(0.1)
            await pilot.click("#stations", offset=(2, 2))
            await pilot.pause(0.2)
            await pilot.click("#stations", offset=(2, 2))
            await pilot.pause(0.2)
            fake = FakePlayer.instances[-1]
            assert len(fake.play_calls) == 2  # 1 tıklama = 1 çalma, iki tıklama = 2

    asyncio.run(scenario())


def test_settings_menu_holds_everything(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _wire(monkeypatch)

    async def keys_of(app):
        tbl = app.query_one("#stations")
        return [
            tbl.coordinate_to_cell_key((i, 0)).row_key.value
            for i in range(tbl.row_count)
        ]

    async def scenario():
        app = appmod.Teradio()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.3)

            # komut paleti (Ctrl+P) artık yok
            assert "ctrl+p" not in app.screen.active_bindings

            # "," ayarlar menüsünü açar
            await pilot.press("comma")
            assert await _settle(pilot, lambda: app._mode == "settings")
            menu = await keys_of(app)
            assert "page:language" in menu and "page:theme" in menu and "page:commands" in menu

            # dile gir -> dil seçenekleri listelenir
            app._settings_page = "language"
            app._show_settings()
            await pilot.pause(0.1)
            assert any(k and k.startswith("lang:") for k in await keys_of(app))

            # Esc ile menüye dön
            await pilot.press("escape")
            await pilot.pause(0.1)
            assert app._settings_page == "menu"

            # temaya gir -> tema seçenekleri
            app._settings_page = "theme"
            app._show_settings()
            await pilot.pause(0.1)
            assert any(k and k.startswith("theme:") for k in await keys_of(app))
            app._set_theme("nord")
            assert app.theme == "nord"

            # komutlara gir -> komutlar
            app._settings_page = "commands"
            app._show_settings()
            await pilot.pause(0.1)
            assert any(k and k.startswith("cmd:") for k in await keys_of(app))

    asyncio.run(scenario())


def test_detect_language_from_env(monkeypatch):
    from teradio import i18n
    import importlib
    importlib.reload(i18n)
    monkeypatch.setenv("LANG", "tr_TR.UTF-8")
    assert i18n.detect_language() == "tr"
    monkeypatch.setenv("LANG", "de_DE.UTF-8")
    assert i18n.detect_language() == "en"  # desteklenmeyen -> ingilizce
