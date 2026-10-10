"""Teradio Textual arayüzü."""
from __future__ import annotations

import random

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable,
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from teradio import api, i18n
from teradio.player import Player, PlayerError
from teradio.store import Store

CATEGORY_KEYS = [
    "search",
    "top",
    "favorites",
    "recent",
    "countries",
    "tags",
    "random",
    "settings",
]
_CAT_INDEX = {key: i for i, key in enumerate(CATEGORY_KEYS)}

# (key, action, açıklama_anahtarı, footer'da görünsün mü)
_BINDING_SPECS = [
    ("q", "quit", "b_quit", True),
    ("ctrl+q", "quit", "", False),
    ("/", "focus_search", "", False),
    ("enter", "play_selected", "b_play", True),
    ("space", "toggle_pause", "b_pause", True),
    ("n", "next_station", "b_next", True),
    ("p", "prev_station", "b_prev", True),
    ("s", "stop", "", False),
    ("+", "vol_up", "b_volup", True),
    ("=", "vol_up", "", False),
    ("-", "vol_down", "b_voldown", True),
    ("m", "mute", "", False),
    ("f", "favorite", "b_fav", True),
    ("r", "random", "", False),
    ("delete", "delete_item", "b_delete", True),
    ("comma", "open_settings", "b_settings", True),
    ("escape", "settings_back", "", False),
]


class StationTable(DataTable):
    """Tek tıklamada satırı seçer (varsayılan DataTable ikinci tıklamayı bekler).

    Tek tıklamada TAM BİR kez seçim olayı yayınlar; varsayılan davranış zaten
    seçili satıra tıklayınca ayrıca olay yaydığı için onu atlarız (çift tetikleme olmasın).
    """

    async def _on_click(self, event) -> None:
        meta = event.style.meta
        row = meta.get("row", -1)
        col = meta.get("column", -1)
        if row is not None and row >= 0 and col is not None and col >= 0 and self.row_count:
            self.cursor_coordinate = (row, col)
            self._post_selected_message()
        else:
            await super()._on_click(event)


class Teradio(App):
    CSS_PATH = "tui.tcss"
    TITLE = "Teradio"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS: list = []  # __init__ içinde dile göre doldurulur

    def __init__(self) -> None:
        super().__init__()
        self.store = Store()
        self.lang = self.store.get("language") or i18n.detect_language()
        self.store.set("language", self.lang)
        self._install_bindings()
        self.volume = int(self.store.get("volume", 80))
        self.player: Player | None = None
        self._mode = "stations"
        self._stations: list[api.Station] = []
        self._countries: list[dict] = []
        self._tags: list[dict] = []
        self._current_category = ""
        self._prev_category = "top"
        self._settings_page = "menu"
        self._load_seq = 0
        self._now: api.Station | None = None
        self._metadata = ""
        self._player_state = "stopped"
        self._prev_volume = self.volume
        self._status = ""

    # -- dil / kısayollar ----------------------------------------
    def t(self, key: str, **kw) -> str:
        return i18n.get(key, self.lang, **kw)

    def _binding_specs(self) -> list[Binding]:
        return [
            Binding(key, action, self.t(label_key) if label_key else "", show=show)
            for key, action, label_key, show in _BINDING_SPECS
        ]

    def _install_bindings(self) -> None:
        type(self).BINDINGS = self._binding_specs()
        self._bindings = self._merge_bindings()

    def _set_language(self, code: str) -> None:
        if code not in i18n.LANGUAGES or code == self.lang:
            return
        self.lang = code
        self.store.set("language", code)
        self._install_bindings()
        self._retranslate()
        self.notify(self.t("st_lang_set", name=i18n.LANGUAGES[code]))

    def _retranslate(self) -> None:
        for key in CATEGORY_KEYS:
            try:
                self.query_one(f"#cat-{key} Label", Label).update(self.t(f"cat_{key}"))
            except Exception:
                pass
        self.query_one("#search", Input).placeholder = self.t("ph_search")
        self.refresh_bindings()
        self._render_current()
        self._update_now()

    # -- yaşam döngüsü -------------------------------------------
    def compose(self) -> ComposeResult:
        yield Static("TERADIO", id="titlebar")
        with Horizontal(id="body"):
            yield ListView(
                *[
                    ListItem(Label(self.t(f"cat_{key}")), id=f"cat-{key}")
                    for key in CATEGORY_KEYS
                ],
                id="cats",
            )
            with Vertical(id="main"):
                yield Input(placeholder=self.t("ph_search"), id="search")
                yield StationTable(id="stations", cursor_type="row", zebra_stripes=True)
        with Vertical(id="bottom"):
            yield Static(id="now")
            yield Footer()

    def on_mount(self) -> None:
        saved_theme = self.store.get("theme")
        if saved_theme in self.available_themes:
            self.theme = saved_theme
        self.query_one("#stations", StationTable).focus()
        self.query_one("#search", Input).display = False
        if not Player.available():
            self.notify(self.t("n_mpv_missing"), severity="error", timeout=10)
        # mpv süreci TALEP üzerine (ilk çalmada) başlatılır; boşta hiç yoktur.
        self._update_now()
        # başlangıç: en çok dinlenenler (index değişimi yüklemeyi tetikler)
        self.query_one("#cats", ListView).index = _CAT_INDEX["top"]

    def on_unmount(self) -> None:
        if self.player:
            self.player.quit()

    # -- kategori yükleme ----------------------------------------
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        key = (event.item.id or "").removeprefix("cat-")
        if key and key != self._current_category:
            self.load_category(key)

    def load_category(self, key: str) -> None:
        self._load_seq += 1  # uçuştaki eski istekleri geçersiz kıl
        if key != "settings":
            self._prev_category = key
        else:
            self._settings_page = "menu"
        self._current_category = key
        self._mode = "stations"
        self.query_one("#search", Input).display = key == "search"
        if key == "search":
            return
        if key == "top":
            self._load("top", None, self._load_seq)
        elif key == "favorites":
            self._show_stations([api.Station(**d) for d in self.store.favorites()])
        elif key == "recent":
            self._show_stations([api.Station(**d) for d in self.store.recent()])
        elif key == "countries":
            self._load("countries", None, self._load_seq)
        elif key == "tags":
            self._load("tags", None, self._load_seq)
        elif key == "random":
            self.action_random()
        elif key == "settings":
            self._show_settings()

    def _begin_load(self, kind: str, arg: str | None = None) -> None:
        self._load_seq += 1
        self._load(kind, arg, self._load_seq)

    @work(thread=True, exclusive=True, group="load")
    def _load(self, kind: str, arg: str | None, seq: int) -> None:
        self.call_from_thread(self._set_status, self.t("st_loading"))
        try:
            if kind == "top":
                data = api.top_click()
            elif kind == "countries":
                data = api.countries()
            elif kind == "tags":
                data = api.tags()
            elif kind == "search":
                data = api.search(arg or "")
            elif kind == "country":
                data = api.by_country(arg or "")
            elif kind == "tag":
                data = api.by_tag(arg or "")
            else:
                return
        except Exception as exc:  # ağ hataları
            if seq == self._load_seq:
                self.call_from_thread(
                    self.notify, self.t("n_net_error", err=exc), severity="error"
                )
                self.call_from_thread(self._set_status, self.t("st_error"))
            return
        self.call_from_thread(self._apply, kind, data, seq)

    def _apply(self, kind: str, data, seq: int) -> None:
        if seq != self._load_seq:
            return  # daha yeni bir istek/gezinme oldu, eski sonucu at
        if kind == "countries":
            self._show_countries(data)
        elif kind == "tags":
            self._show_tags(data)
        else:
            self._show_stations(data)

    # -- tablo doldurma ------------------------------------------
    def _reset_table(self, *columns: str) -> StationTable:
        table = self.query_one("#stations", StationTable)
        table.clear(columns=True)
        table.add_columns(*columns)
        table.cursor_type = "row"
        return table

    def _show_stations(self, stations: list[api.Station]) -> None:
        self._mode = "stations"
        self._stations = stations
        table = self._reset_table(
            self.t("col_station"), self.t("col_country"), self.t("col_quality")
        )
        for s in stations:
            table.add_row(
                s.name,
                (s.country or "")[:18],
                self._quality(s),
                key=s.uuid,
            )
        self._set_status(self.t("st_stations", n=len(stations)))
        if stations:
            table.focus()
            table.move_cursor(row=0)

    @staticmethod
    def _quality(station: api.Station) -> str:
        if station.bitrate:
            return f"{station.codec} {station.bitrate}k".strip()
        return station.codec or ""

    def _show_countries(self, data: list[dict]) -> None:
        self._mode = "countries"
        self._countries = data
        table = self._reset_table(self.t("col_country"), self.t("col_stations"))
        for c in data:
            name = c["name"] or c["code"] or "?"
            table.add_row(name, str(c["count"]), key=c["code"] or name)
        self._set_status(self.t("st_countries", n=len(data)))

    def _show_tags(self, data: list[dict]) -> None:
        self._mode = "tags"
        self._tags = data
        table = self._reset_table(self.t("col_genre"), self.t("col_stations"))
        for t in data:
            if t["name"]:
                table.add_row(t["name"], str(t["count"]), key=t["name"])
        self._set_status(self.t("st_tags", n=len(data)))

    def _show_settings(self) -> None:
        self._mode = "settings"
        if self._settings_page == "language":
            self._render_language_page()
        elif self._settings_page == "theme":
            self._render_theme_page()
        elif self._settings_page == "commands":
            self._render_commands_page()
        else:
            self._render_settings_menu()
        self._set_status(self.t("set_hint"))

    def _render_settings_menu(self) -> None:
        table = self._reset_table(self.t("col_option"), self.t("col_value"))
        table.add_row(self.t("sec_language"), i18n.LANGUAGES.get(self.lang, self.lang), key="page:language")
        table.add_row(self.t("sec_theme"), self.theme, key="page:theme")
        table.add_row(self.t("sec_commands"), "", key="page:commands")
        table.focus()
        table.move_cursor(row=0)

    def _render_language_page(self) -> None:
        table = self._reset_table(self.t("col_option"), self.t("col_value"))
        for code, name in i18n.LANGUAGES.items():
            mark = self.t("set_active") if code == self.lang else ""
            table.add_row(name, mark, key=f"lang:{code}")
        table.focus()
        self._focus_key(table, f"lang:{self.lang}")

    def _render_theme_page(self) -> None:
        table = self._reset_table(self.t("col_option"), self.t("col_value"))
        for theme in self.available_themes:
            mark = self.t("set_active") if theme == self.theme else ""
            table.add_row(theme, mark, key=f"theme:{theme}")
        table.focus()
        self._focus_key(table, f"theme:{self.theme}")

    def _render_commands_page(self) -> None:
        table = self._reset_table(self.t("col_option"), self.t("col_value"))
        cmds = ["top", "favorites", "recent", "countries", "tags", "search", "random"]
        for cmd in cmds:
            table.add_row(self.t(f"cat_{cmd}"), "", key=f"cmd:{cmd}")
        table.add_row(self.t("b_stop"), "", key="cmd:stop")
        table.add_row(self.t("b_quit"), "", key="cmd:quit")
        table.focus()
        table.move_cursor(row=0)

    def _focus_key(self, table: StationTable, key: str) -> None:
        for i in range(table.row_count):
            if table.coordinate_to_cell_key((i, 0)).row_key.value == key:
                table.move_cursor(row=i)
                return

    def action_settings_back(self) -> None:
        if self._mode != "settings":
            return
        if self._settings_page != "menu":
            self._settings_page = "menu"
            self._show_settings()
        else:
            self.load_category(self._prev_category or "top")

    def _set_theme(self, name: str) -> None:
        if name in self.available_themes:
            self.theme = name
            self.store.set("theme", name)
            self._show_settings()

    def _run_setting_command(self, cmd: str) -> None:
        if cmd == "quit":
            self.exit()
        elif cmd == "stop":
            self.action_stop()
        elif cmd == "random":
            self.action_random()
        elif cmd == "search":
            self.action_focus_search()
        else:
            self._goto(cmd)

    def _render_current(self) -> None:
        if self._mode == "settings":
            self._show_settings()
        elif self._mode == "countries":
            self._show_countries(self._countries)
        elif self._mode == "tags":
            self._show_tags(self._tags)
        elif self._mode == "stations":
            self._show_stations(self._stations)

    # -- olaylar -------------------------------------------------
    def _activate_row(self, key: str) -> None:
        if self._mode == "stations":
            station = self._by_uuid(key)
            if station:
                self.play_station(station)
        elif self._mode == "countries":
            self._begin_load("country", key)
        elif self._mode == "tags":
            self._begin_load("tag", key)
        elif self._mode == "settings":
            if key.startswith("page:"):
                self._settings_page = key[5:]
                self._show_settings()
            elif key.startswith("lang:"):
                self._set_language(key[5:])
            elif key.startswith("theme:"):
                self._set_theme(key[6:])
            elif key.startswith("cmd:"):
                self._run_setting_command(key[4:])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._activate_row(event.row_key.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if text:
            self._begin_load("search", text)
            self.query_one("#stations", StationTable).focus()

    # -- çalma ---------------------------------------------------
    def play_station(self, station: api.Station) -> None:
        self._now = station
        self._metadata = ""
        self._player_state = "connecting"
        self.store.add_recent(station.as_dict())
        self._update_now()  # hemen "bağlanıyor…" göster, "çalıyor" ses gelince
        self._start_and_play(station)

    @work(thread=True, exclusive=True, group="play")
    def _start_and_play(self, station: api.Station) -> None:
        player = self._get_player()
        if player is None:
            return
        player.set_volume(self.volume)
        if self._now is not station:
            return  # daha yeni bir seçim yapıldı
        player.play(station.url)

    def _get_player(self) -> Player | None:
        """mpv'yi (gerekirse) burada oluşturup başlatır. Boşta süreç tutulmaz."""
        if self.player is None:
            if not Player.available():
                return None
            self.player = Player(
                on_metadata=self._on_metadata,
                on_state=self._on_player_state,
                volume=self.volume,
            )
        try:
            self.player.start()  # zaten çalışıyorsa dokunmaz
        except PlayerError as exc:
            self.call_from_thread(self.notify, str(exc), severity="error", timeout=10)
            self.player = None
            return None
        return self.player

    def _on_player_state(self, state: str) -> None:
        self.call_from_thread(self._set_player_state, state)

    def _set_player_state(self, state: str) -> None:
        previous = self._player_state
        self._player_state = state
        if state == "error" and previous != "error":
            name = self._now.name if self._now else ""
            self.notify(self.t("n_play_error", name=name), severity="error")
        self._update_now()

    def _on_metadata(self, title: str) -> None:
        self.call_from_thread(self._set_metadata, title)

    def _set_metadata(self, title: str) -> None:
        self._metadata = title
        self._update_now()

    def _by_uuid(self, uuid: str) -> api.Station | None:
        for s in self._stations:
            if s.uuid == uuid:
                return s
        return None

    def _playing_station(self) -> api.Station | None:
        if self._mode == "stations" and self._stations:
            table = self.query_one("#stations", StationTable)
            try:
                key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            except Exception:
                return None
            return self._by_uuid(key)
        return None

    # -- aksiyonlar ----------------------------------------------
    def action_focus_search(self) -> None:
        self.query_one("#cats", ListView).index = _CAT_INDEX["search"]
        self.load_category("search")
        self.query_one("#search", Input).focus()

    def action_open_settings(self) -> None:
        self._goto("settings")

    def _goto(self, key: str) -> None:
        lv = self.query_one("#cats", ListView)
        lv.index = _CAT_INDEX[key]
        lv.focus()

    def action_play_selected(self) -> None:
        station = self._playing_station()
        if station:
            self.play_station(station)

    def action_next_station(self) -> None:
        self._step_station(1)

    def action_prev_station(self) -> None:
        self._step_station(-1)

    def _step_station(self, delta: int) -> None:
        """Listedeki bir sonraki/önceki istasyona geç ve çal (başa döner)."""
        if self._mode != "stations" or not self._stations:
            return
        table = self.query_one("#stations", StationTable)
        row = (table.cursor_coordinate.row + delta) % len(self._stations)
        table.move_cursor(row=row)
        station = self._by_uuid(
            table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        )
        if station:
            self.play_station(station)

    def action_delete_item(self) -> None:
        """Geçmiş/Favoriler listesinden seçili istasyonu sil."""
        if self._mode != "stations" or self._current_category not in ("recent", "favorites"):
            return
        station = self._playing_station()
        if not station:
            return
        table = self.query_one("#stations", StationTable)
        row = table.cursor_coordinate.row
        if self._current_category == "recent":
            self.store.remove_recent(station.uuid)
            self._show_stations([api.Station(**d) for d in self.store.recent()])
        else:
            self.store.remove_favorite(station.uuid)
            self._show_stations([api.Station(**d) for d in self.store.favorites()])
        self.notify(self.t("n_deleted", name=station.name))
        if table.row_count:
            table.move_cursor(row=min(row, table.row_count - 1))

    def action_toggle_pause(self) -> None:
        # Yalnızca yayın gerçekten çalarken/duraklatılmışken geçerli.
        # Bağlanma sırasında basılan space kaybolmaz, sessizce yok sayılır.
        if self.player and self._player_state in ("playing", "paused"):
            self.player.toggle_pause()

    def action_stop(self) -> None:
        if self.player:
            # Tamamen durdur: mpv sürecini de kapat, arkada kaynak kalmasın.
            self.player.quit()
            self.player = None
        self._now = None
        self._metadata = ""
        self._player_state = "stopped"
        self._update_now()

    def action_vol_up(self) -> None:
        self._set_volume(self.volume + 5)

    def action_vol_down(self) -> None:
        self._set_volume(self.volume - 5)

    def action_mute(self) -> None:
        if self.volume > 0:
            self._prev_volume = self.volume
            self._set_volume(0)
        else:
            self._set_volume(self._prev_volume or 80)

    def _set_volume(self, value: int) -> None:
        self.volume = max(0, min(130, int(value)))
        if self.player:
            self.player.set_volume(self.volume)
        self.store.set("volume", self.volume)
        self._update_now()

    def action_favorite(self) -> None:
        station = self._playing_station() or self._now
        if not station:
            return
        if self.store.toggle_favorite(station.as_dict()):
            self.notify(self.t("n_fav_add", name=station.name))
        else:
            self.notify(self.t("n_fav_del", name=station.name))

    def action_random(self) -> None:
        if self._stations:
            self.play_station(random.choice(self._stations))
        else:
            self._random_from_top()

    @work(thread=True, group="play")
    def _random_from_top(self) -> None:
        try:
            pool = api.top_click(50)
        except Exception:
            return
        if pool:
            self.call_from_thread(self.play_station, random.choice(pool))

    # -- durum çubuğu --------------------------------------------
    def _set_status(self, text: str) -> None:
        self._status = text
        self._update_now()

    def _update_now(self) -> None:
        if self._now is None:
            body = f"[dim]○ {self.t('st_stopped')}[/dim]"
        else:
            name = self._now.name
            state = self._player_state
            if state == "playing":
                meta = self._metadata or self.t("st_livestream")
                body = (
                    f"[bold green]●[/] [bold green]{self.t('st_playing')}[/]: "
                    f"[b]{name}[/b]  ·  {meta}"
                )
            elif state == "paused":
                body = f"[bold yellow]○[/] [bold yellow]{self.t('st_paused')}[/]: {name}"
            elif state == "error":
                body = f"[bold red]![/] [bold red]{self.t('st_failed')}[/]: {name}"
            else:  # connecting
                body = f"[dim]○ {name}  ·  {self.t('st_connecting')}[/dim]"
        self.query_one("#now", Static).update(
            f"{body}    [dim]{self.t('st_vol')}[/dim] [b]{self._vol_bar()}[/b]"
            f"  [dim]│ {self._status}[/dim]"
        )

    def _vol_bar(self) -> str:
        filled = max(0, min(10, round(self.volume / 10)))
        return "█" * filled + "░" * (10 - filled) + f" {self.volume}%"


def main() -> None:
    Teradio().run()


if __name__ == "__main__":
    main()
