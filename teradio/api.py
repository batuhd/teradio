"""radio-browser.info istemcisi (API anahtarı gerekmez)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

USER_AGENT = "Teradio/0.1"
BASE = "https://all.api.radio-browser.info"


@dataclass
class Station:
    uuid: str
    name: str
    url: str
    country: str
    codec: str
    bitrate: int
    votes: int
    tags: str
    favicon: str

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_api(cls, raw: dict) -> "Station":
        return cls(
            uuid=raw.get("stationuuid") or "",
            name=(raw.get("name") or "?").strip(),
            url=raw.get("url_resolved") or raw.get("url") or "",
            country=raw.get("country") or "",
            codec=(raw.get("codec") or "").upper(),
            bitrate=int(raw.get("bitrate") or 0),
            votes=int(raw.get("votes") or 0),
            tags=raw.get("tags") or "",
            favicon=raw.get("favicon") or "",
        )


def _get(path: str, params: dict | None = None, timeout: int = 15):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _stations(path: str, params: dict | None = None) -> list[Station]:
    out: list[Station] = []
    for item in _get(path, params):
        s = Station.from_api(item)
        if s.url:
            out.append(s)
    return out


_ORDER = {"hidebroken": "true", "order": "votes", "reverse": "true", "limit": 200}


def search(name: str, limit: int = 100) -> list[Station]:
    p = dict(_ORDER, name=name, limit=limit)
    return _stations("/json/stations/search", p)


def top_click(limit: int = 100) -> list[Station]:
    return _stations(f"/json/stations/topclick/{limit}", {"hidebroken": "true"})


def by_country(code: str, limit: int = 200) -> list[Station]:
    p = dict(_ORDER, limit=limit)
    return _stations(f"/json/stations/bycountrycodeexact/{urllib.parse.quote(code)}", p)


def by_tag(tag: str, limit: int = 200) -> list[Station]:
    p = dict(_ORDER, limit=limit)
    return _stations(f"/json/stations/bytagexact/{urllib.parse.quote(tag)}", p)


def countries() -> list[dict]:
    raw = _get("/json/countries")
    out = [
        {"name": c["name"], "code": c["iso_3166_1"], "count": int(c["stationcount"])}
        for c in raw
    ]
    out.sort(key=lambda c: c["count"], reverse=True)
    return out


def tags(limit: int = 80) -> list[dict]:
    raw = _get("/json/tags")
    raw.sort(key=lambda t: int(t.get("stationcount") or 0), reverse=True)
    return [
        {"name": t["name"], "count": int(t["stationcount"])}
        for t in raw[:limit]
    ]


if __name__ == "__main__":
    res = search("jazz", limit=3)
    assert res and all(s.url for s in res), "arama başarısız"
    print("ok:", res[0].name, "->", res[0].url)
