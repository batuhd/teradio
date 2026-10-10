from teradio.api import Station
from teradio.player import Player


def test_station_from_api_normalizes():
    raw = {
        "stationuuid": "u1",
        "name": "  Jazz FM  ",
        "url": "http://a/stream",
        "url_resolved": "http://b/stream",
        "country": "Turkey",
        "codec": "mp3",
        "bitrate": 128,
        "votes": 42,
        "tags": "jazz,smooth",
        "favicon": "http://x/i.png",
    }
    s = Station.from_api(raw)
    assert s.uuid == "u1"
    assert s.name == "Jazz FM"
    assert s.url == "http://b/stream"  # url_resolved tercih edilir
    assert s.codec == "MP3"
    assert s.bitrate == 128
    assert s.votes == 42


def test_station_from_api_handles_missing_fields():
    s = Station.from_api({})
    assert s.uuid == ""
    assert s.name == "?"
    assert s.url == ""
    assert s.bitrate == 0


def test_title_from_metadata_event():
    evt = {"event": "property-change", "name": "metadata",
           "data": {"icy-title": ["Artist - Song"]}}
    assert Player._title_from(evt) == "Artist - Song"


def test_title_from_media_title_event():
    evt = {"event": "property-change", "name": "media-title",
           "data": "Some Radio"}
    assert Player._title_from(evt) == "Some Radio"


def test_title_ignores_raw_url_media_title():
    evt = {"event": "property-change", "name": "media-title",
           "data": "http://stream.example/;"}
    assert Player._title_from(evt) is None


def test_title_ignores_other_events():
    assert Player._title_from({"event": "start-file"}) is None
    assert Player._title_from({"name": "metadata", "data": {}}) is None
