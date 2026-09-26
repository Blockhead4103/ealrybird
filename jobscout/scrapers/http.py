"""Höfliches HTTP: fester User-Agent, Pausen zwischen Anfragen, robots.txt wird respektiert."""
from __future__ import annotations

import time
from functools import lru_cache
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

USER_AGENT = "JobScout/0.1 (private Stellensuche; respektiert robots.txt)"
TIMEOUT = 20
DELAY_SECONDS = 1.0

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "de-CH,de;q=0.9,en;q=0.8"})
_last_request: dict[str, float] = {}


def _throttle(url: str) -> None:
    host = urlparse(url).netloc
    wait = DELAY_SECONDS - (time.monotonic() - _last_request.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_request[host] = time.monotonic()


@lru_cache(maxsize=256)
def _robots_for(base: str) -> RobotFileParser | None:
    parser = RobotFileParser()
    try:
        resp = _session.get(f"{base}/robots.txt", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if resp.status_code >= 400:
        return None  # keine robots.txt -> alles erlaubt
    parser.parse(resp.text.splitlines())
    return parser


def allowed(url: str) -> bool:
    parts = urlparse(url)
    parser = _robots_for(f"{parts.scheme}://{parts.netloc}")
    return parser is None or parser.can_fetch(USER_AGENT, url)


def get(url: str, check_robots: bool = False, **kwargs) -> requests.Response:
    if check_robots and not allowed(url):
        raise PermissionError(f"robots.txt verbietet: {url}")
    _throttle(url)
    resp = _session.get(url, timeout=TIMEOUT, **kwargs)
    resp.raise_for_status()
    if "charset" not in resp.headers.get("Content-Type", "").lower():
        # Ohne Angabe rät requests "ISO-8859-1" -> Umlaute kaputt. Stattdessen aus dem Inhalt ableiten.
        resp.encoding = resp.apparent_encoding
    return resp


def post_json(url: str, payload: dict) -> requests.Response:
    _throttle(url)
    resp = _session.post(url, json=payload, timeout=TIMEOUT, headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp
