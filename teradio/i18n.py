"""Basit çoklu dil desteği (i18n). Makinenin diline göre otomatik seçer."""
from __future__ import annotations

import os

# Desteklenen diller: kod -> görünen ad
LANGUAGES: dict[str, str] = {
    "tr": "Türkçe",
    "en": "English",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # kenar çubuğu
        "cat_search": "Search",
        "cat_top": "Top Stations",
        "cat_favorites": "Favorites",
        "cat_recent": "Recently Played",
        "cat_countries": "Countries",
        "cat_tags": "Genres",
        "cat_random": "Play Random",
        "cat_settings": "Settings",
        # tuş açıklamaları
        "b_quit": "Quit",
        "b_search": "Search",
        "b_play": "Play",
        "b_pause": "Pause/Resume",
        "b_stop": "Stop",
        "b_volup": "Vol+",
        "b_voldown": "Vol-",
        "b_mute": "Mute",
        "b_fav": "Favorite",
        "b_random": "Random",
        "b_settings": "Settings",
        "b_open": "Open",
        "b_next": "Next",
        "b_prev": "Previous",
        "b_delete": "Delete",
        # tablo başlıkları
        "col_station": "Station",
        "col_country": "Country",
        "col_codec": "Codec",
        "col_kbps": "kbps",
        "col_votes": "Votes",
        "col_stations": "Stations",
        "col_genre": "Genre",
        "col_language": "Language",
        "col_option": "Option",
        "col_value": "Value",
        "col_quality": "Quality",
        "sec_language": "Language",
        "sec_theme": "Theme",
        "sec_commands": "Commands",
        "b_back": "Back",
        # diğer
        "ph_search": "Search stations, then Enter…",
        "st_loading": "Loading…",
        "st_stations": "{n} stations",
        "st_countries": "{n} countries · Enter to open",
        "st_tags": "{n} genres · Enter to open",
        "st_error": "Error",
        "st_opening": "opening: {name}…",
        "st_live": "live",
        "st_stopped": "Stopped",
        "st_playing": "Playing",
        "st_connecting": "connecting…",
        "st_paused": "Paused",
        "st_failed": "Failed to open",
        "st_livestream": "live stream",
        "st_vol": "vol",
        "set_hint": "Enter: select · Esc: back",
        "set_active": "active",
        "st_lang_set": "Language: {name}",
        "n_mpv_missing": "mpv not found. Install: sudo pacman -S mpv",
        "n_net_error": "Network error: {err}",
        "n_no_mpv": "mpv missing; can't play.",
        "n_playing": "Playing: {name}",
        "n_play_error": "Couldn't play: {name}",
        "n_fav_add": "Added to favorites: {name}",
        "n_fav_del": "Removed from favorites: {name}",
        "n_deleted": "Removed: {name}",
    },
    "tr": {
        "cat_search": "Ara",
        "cat_top": "En Çok Dinlenen",
        "cat_favorites": "Favoriler",
        "cat_recent": "Geçmiş",
        "cat_countries": "Ülkeler",
        "cat_tags": "Türler",
        "cat_random": "Rastgele Çal",
        "cat_settings": "Ayarlar",
        "b_quit": "Çık",
        "b_search": "Ara",
        "b_play": "Çal",
        "b_pause": "Durdur/Devam",
        "b_stop": "Dur",
        "b_volup": "Ses+",
        "b_voldown": "Ses-",
        "b_mute": "Sessiz",
        "b_fav": "Favori",
        "b_random": "Rastgele",
        "b_settings": "Ayarlar",
        "b_open": "Aç",
        "b_next": "Sonraki",
        "b_prev": "Önceki",
        "b_delete": "Sil",
        "col_station": "İstasyon",
        "col_country": "Ülke",
        "col_codec": "Codec",
        "col_kbps": "kbps",
        "col_votes": "Oy",
        "col_stations": "İstasyon",
        "col_genre": "Tür",
        "col_language": "Dil",
        "col_option": "Seçenek",
        "col_value": "Değer",
        "col_quality": "Kalite",
        "sec_language": "Dil",
        "sec_theme": "Tema",
        "sec_commands": "Komutlar",
        "b_back": "Geri",
        "ph_search": "İstasyon ara, sonra Enter…",
        "st_loading": "Yükleniyor…",
        "st_stations": "{n} istasyon",
        "st_countries": "{n} ülke · Enter ile aç",
        "st_tags": "{n} tür · Enter ile aç",
        "st_error": "Hata",
        "st_opening": "açılıyor: {name}…",
        "st_live": "canlı",
        "st_stopped": "Durduruldu",
        "st_playing": "Çalıyor",
        "st_connecting": "bağlanıyor…",
        "st_paused": "Duraklatıldı",
        "st_failed": "Açılamadı",
        "st_livestream": "canlı yayın",
        "st_vol": "ses",
        "set_hint": "Enter: seç · Esc: geri",
        "set_active": "seçili",
        "st_lang_set": "Dil: {name}",
        "n_mpv_missing": "mpv bulunamadı. Kur: sudo pacman -S mpv",
        "n_net_error": "Ağ hatası: {err}",
        "n_no_mpv": "mpv yok; çalınamıyor.",
        "n_playing": "Çalıyor: {name}",
        "n_play_error": "Açılamadı: {name}",
        "n_fav_add": "Favorilere eklendi: {name}",
        "n_fav_del": "Favoriden çıkarıldı: {name}",
        "n_deleted": "Silindi: {name}",
    },
}


def detect_language() -> str:
    """Ortam değişkenlerinden makinenin dilini tespit eder (yoksa İngilizce)."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            code = value.split(".")[0].split("_")[0].lower()
            if code in STRINGS:
                return code
    return "en"


def get(key: str, lang: str = "en", **kw) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    text = table.get(key) or STRINGS["en"].get(key) or key
    return text.format(**kw) if kw else text
