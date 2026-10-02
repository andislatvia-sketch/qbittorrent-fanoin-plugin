# VERSION: 1.03
# AUTHORS: Grok, improved by andislatvia-sketch
# LICENSING INFORMATION
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the author nor the names of its contributors may be
#      used to endorse or promote products derived from this software without
#      specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
qBittorrent Nova3 search plugin for FANO.IN
https://www.fano.in/

Fano.in is a Latvian private tracker. This plugin follows the official
qBittorrent search-plugin contract and the Jackett indexer definition
(src/Jackett.Common/Definitions/fanoin.yml):

  login  POST  /takelogin.php          username, password
  search GET   /browse_old.php         search, incldead=1, sort=4, type=desc, c<id>=1
  rows         tr.browse_actions
  title        a.tName[href^="details.php?id="]
  download     download.php?id=
  size         td (5th cell in row)
  seeders      td (7th cell - contains a link with seeder count)
  leechers     td (8th cell)
  date         small tag within title cell

Credentials — pick one:
  1. Edit USERNAME / PASSWORD below.
  2. Place fanoin.json next to this file:
       {"username": "you", "password": "secret"}
"""

from __future__ import annotations

import gzip
import html
import http.cookiejar
import io
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Optional

from novaprinter import prettyPrinter

# ---------------------------------------------------------------------------
# SET THESE, or use fanoin.json next to this plugin
# ---------------------------------------------------------------------------
USERNAME = "YOUR_USERNAME"
PASSWORD = "YOUR_PASSWORD"


class fanoin:
    url = "https://www.fano.in"
    name = "FANO.IN"
    # Values are Fano category IDs from Jackett (c<id>=1 on browse_old.php).
    # Multiple IDs are comma-separated so a qBittorrent category maps 1:1 to
    # the tracker groups Jackett uses for the same Newznab bucket.
    supported_categories: dict[str, str] = {
        "all": "all",
        "anime": "27",
        "books": "41,44",
        "games": "7,12,34,43,40,46,51",
        "movies": "20,47,17,24,52,37,53,4,54,55",
        "music": "5,31,19,48",
        "software": "22,1,38",
        "tv": "6,33,25,49,35,32,23",
    }

    _UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    )
    _MAX_PAGES = 8
    _MAX_ROW_LENGTH = 500_000  # Prevent ReDoS attacks

    def __init__(self) -> None:
        self.username = USERNAME
        self.password = PASSWORD
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self._load_config(os.path.join(plugin_dir, "fanoin.json"))
        self.cookie_path = os.path.join(plugin_dir, "fanoin.cookies")
        self.cj = http.cookiejar.LWPCookieJar(self.cookie_path)
        try:
            self.cj.load(ignore_discard=True, ignore_expires=True)
        except OSError:
            pass
        self._set_language_cookie()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj)
        )
        self.logged_in = False

    # -- config / session ---------------------------------------------------

    def _load_config(self, path: str) -> None:
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self.username = str(data.get("username", self.username))
                self.password = str(data.get("password", self.password))
        except (OSError, ValueError) as exc:
            print(f"fanoin: cannot read fanoin.json: {exc}", file=sys.stderr)

    def _set_language_cookie(self) -> None:
        cookie = http.cookiejar.Cookie(
            version=0,
            name="language",
            value="en",
            port=None,
            port_specified=False,
            domain="www.fano.in",
            domain_specified=True,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=True,
            expires=None,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        )
        self.cj.set_cookie(cookie)

    def _save_cookies(self) -> None:
        try:
            self.cj.save(ignore_discard=True, ignore_expires=True)
        except OSError as exc:
            print(f"fanoin: failed to save cookies: {exc}", file=sys.stderr)

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,lv;q=0.8",
        }

    def _request(self, url: str, data: Optional[bytes] = None, retry: int = 1) -> str:
        for attempt in range(retry):
            req = urllib.request.Request(url, data=data, headers=self._headers())
            try:
                with self.opener.open(req, timeout=25) as resp:
                    raw: bytes = resp.read()
            except urllib.error.URLError as exc:
                if attempt < retry - 1:
                    continue
                print(f"fanoin: connection error: {exc.reason}", file=sys.stderr)
                return ""
            if raw[:2] == b"\x1f\x8b":
                with io.BytesIO(raw) as buf, gzip.GzipFile(fileobj=buf) as gz:
                    raw = gz.read()
            return raw.decode("utf-8", "replace")
        return ""

    def _is_logged_in(self, page: str) -> bool:
        if not page:
            return False
        lowered = page.lower()
        if 'href="/logout.php"' in lowered or "href='/logout.php'" in lowered:
            return True
        if "logout.php" in lowered and "not logged in" not in lowered:
            return True
        return False

    def _ensure_login(self) -> bool:
        if self.logged_in:
            return True
        probe = self._request(f"{self.url}/browse_old.php")
        if self._is_logged_in(probe):
            self.logged_in = True
            self._save_cookies()
            return True
        if (
            not self.username
            or self.username == "YOUR_USERNAME"
            or not self.password
            or self.password == "YOUR_PASSWORD"
        ):
            print(
                "fanoin: set USERNAME/PASSWORD in fanoin.py or create fanoin.json",
                file=sys.stderr,
            )
            return False
        payload = urllib.parse.urlencode(
            {
                "username": self.username,
                "password": self.password,
                "returnto": "/browse_old.php",
            }
        ).encode("utf-8")
        page = self._request(f"{self.url}/takelogin.php", data=payload, retry=2)
        if not self._is_logged_in(page):
            page = self._request(f"{self.url}/browse_old.php")
        if not self._is_logged_in(page):
            if re.search(r"<h2>[^<]*fail", page, re.I):
                print(
                    "fanoin: login failed — check username/password", file=sys.stderr
                )
            else:
                print(
                    "fanoin: login failed — not logged in after takelogin.php",
                    file=sys.stderr,
                )
            return False
        self.logged_in = True
        self._save_cookies()
        return True

    # -- public nova3 API ---------------------------------------------------

    def download_torrent(self, info: str) -> None:
        if not self._ensure_login():
            return
        req = urllib.request.Request(info, headers=self._headers())
        try:
            with self.opener.open(req, timeout=25) as resp:
                data: bytes = resp.read()
        except urllib.error.URLError as exc:
            print(f"fanoin: download error: {exc.reason}", file=sys.stderr)
            return
        if data[:2] == b"\x1f\x8b":
            with io.BytesIO(data) as buf, gzip.GzipFile(fileobj=buf) as gz:
                data = gz.read()
        if not data.startswith(b"d") or b"not logged in" in data.lower():
            print("fanoin: download did not return a torrent file", file=sys.stderr)
            return
        handle, path = tempfile.mkstemp(suffix=".torrent")
        with os.fdopen(handle, "wb") as fh:
            fh.write(data)
        print(path + " " + info)

    def search(self, what: str, cat: str = "all") -> None:
        if not self._ensure_login():
            return
        query = urllib.parse.unquote_plus(what)
        cat_ids = self.supported_categories.get(cat, "all")
        seen: set[str] = set()
        for page in range(self._MAX_PAGES):
            params: list[tuple[str, str]] = [
                ("search", query),
                ("incldead", "1"),
                ("sort", "4"),
                ("type", "desc"),
                ("page", str(page)),
            ]
            if cat_ids != "all":
                for cid in cat_ids.split(","):
                    cid = cid.strip()
                    if cid:
                        params.append((f"c{cid}", "1"))
            url = f"{self.url}/browse_old.php?{urllib.parse.urlencode(params)}"
            html_page = self._request(url)
            if not html_page:
                break
            if not self._is_logged_in(html_page):
                self.logged_in = False
                if not self._ensure_login():
                    return
                html_page = self._request(url)
            rows = parse_browse_rows(html_page, self.url)
            if not rows:
                break
            emitted = 0
            for item in rows:
                key = item.get("desc_link") or item.get("link") or item.get("name")
                if not key or key in seen:
                    continue
                seen.add(key)
                prettyPrinter(item)  # type: ignore[arg-type]
                emitted += 1
            if emitted == 0:
                break


# -- HTML parsing ---------------------------------------------------

_ROW_RE = re.compile(
    r"<tr[^>]*class=['\"]browse_actions['\"][^>]*>(.*?)</tr>",
    re.I | re.S,
)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.I | re.S)
_TNAME_RE = re.compile(
    r"""<a\b[^>]*class=['\"]tName['\"][^>]*href=['\"]details\.php\?id=(\d+)[^'\"]*['\"][^>]*>(.*?)</a>""",
    re.I | re.S,
)
_DOWNLOAD_RE = re.compile(
    r"""<a\b[^>]*href=['\"]download\.php\?id=(\d+)[^'\"]*['\"][^>]*>""",
    re.I | re.S,
)
_SMALL_RE = re.compile(r"<small[^>]*>(.*?)</small>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_INT_RE = re.compile(r"-?\d+")


def _strip_tags(blob: str) -> str:
    """Remove HTML tags and unescape entities."""
    blob = _TAG_RE.sub(" ", blob)
    blob = html.unescape(blob)
    return re.sub(r"\s+", " ", blob).strip()


def _to_int(blob: str) -> int:
    """Extract integer from text, handling commas and spaces."""
    cleaned = blob.replace(",", "").replace(" ", "").replace("\n", "")
    match = _INT_RE.search(cleaned)
    if not match:
        return -1
    try:
        return int(match.group(0))
    except ValueError:
        return -1


def _normalize_size(blob: str) -> str:
    """Normalize torrent size format for parsing."""
    text = html.unescape(blob).replace("\xa0", " ").strip()
    if re.match(r"^\d+,\d+\s*[A-Za-z]", text):
        text = text.replace(",", ".", 1)
    else:
        text = text.replace(",", "")
    return text


def parse_pub_date(raw: str) -> int:
    """Parse Fano date strings (Šodien/Vakar/ISO) to a unix timestamp."""
    if not raw:
        return -1
    text = html.unescape(raw)
    text = text.replace("Šodien", "Today").replace("Vakar", "Yesterday")
    text = re.sub(r"^(Added|added|Added on)\s*:\s*", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    now = datetime.now()

    today = re.search(r"Today\s+(\d{1,2}:\d{2}(?::\d{2})?)?", text, re.I)
    if today or re.fullmatch(r"Today", text, re.I):
        stamp = now
        if today and today.group(1):
            stamp = _apply_time(now, today.group(1))
        return int(stamp.timestamp())

    yest = re.search(r"Yesterday\s+(\d{1,2}:\d{2}(?::\d{2})?)?", text, re.I)
    if yest or re.fullmatch(r"Yesterday", text, re.I):
        stamp = now - timedelta(days=1)
        if yest and yest.group(1):
            stamp = _apply_time(stamp, yest.group(1))
        return int(stamp.timestamp())

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%b %d %Y",
        "%b&nbsp;%d&nbsp;%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
    )
    for fmt in formats:
        try:
            return int(datetime.strptime(text, fmt).timestamp())
        except ValueError:
            continue
    return -1


def _apply_time(day: datetime, clock: str) -> datetime:
    """Apply time to a date."""
    parts = clock.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    second = int(parts[2]) if len(parts) > 2 else 0
    return day.replace(hour=hour, minute=minute, second=second, microsecond=0)


def parse_browse_rows(page_html: str, engine_url: str) -> list[dict[str, object]]:
    """Extract search hits from a browse_old.php document."""
    results: list[dict[str, object]] = []
    for row_html in _ROW_RE.findall(page_html):
        item = parse_row(row_html, engine_url)
        if item is not None:
            results.append(item)
    return results


def parse_row(row_html: str, engine_url: str) -> Optional[dict[str, object]]:
    """Parse a single torrent row from browse_actions table."""
    # Prevent ReDoS: skip unusually long rows
    if len(row_html) > fanoin._MAX_ROW_LENGTH:
        return None

    # Find the title using tName class
    title_match = _TNAME_RE.search(row_html)
    if not title_match:
        return None

    torrent_id = title_match.group(1)
    name = _strip_tags(title_match.group(2))
    if not name:
        return None

    # Build links
    download = f"{engine_url}/download.php?id={torrent_id}"
    desc = f"{engine_url}/details.php?id={torrent_id}"

    # Extract all table cells (<td> tags)
    cells = _TD_RE.findall(row_html)
    
    # Parse size, seeds, leech from cells
    # Structure in browse_actions rows:
    # [0] = actions column (category icon + hidden action buttons)
    # [1] = title + date in small tags
    # [2] = comments count
    # [3] = rating image
    # [4] = size
    # [5] = views count
    # [6] = seeders (contains link with count)
    # [7] = leechers
    
    size = "-1"
    seeds = -1
    leech = -1

    if len(cells) >= 5:
        size = _normalize_size(_strip_tags(cells[4]))
    if len(cells) >= 7:
        seeds = _to_int(_strip_tags(cells[6]))
    if len(cells) >= 8:
        leech = _to_int(_strip_tags(cells[7]))

    # Extract date from title cell (contains <small> tags)
    date_raw = ""
    if len(cells) > 1:
        smalls = [_strip_tags(s) for s in _SMALL_RE.findall(cells[1])]
        smalls = [s for s in smalls if s]
        if smalls:
            date_raw = smalls[0]

    return {
        "link": download,
        "name": name,
        "size": size,
        "seeds": seeds,
        "leech": leech,
        "engine_url": engine_url,
        "desc_link": desc,
        "pub_date": parse_pub_date(date_raw),
    }
