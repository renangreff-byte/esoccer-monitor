from __future__ import annotations

from datetime import datetime
import re
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

from .config import League, TIMEZONE
from .models import Match, norm

SCORE_RE = re.compile(r"(?:\((?P<hht>\d+)\))?\s*(?P<hs>\d+)\s*[-xX:]\s*(?P<as>\d+)\s*(?:\((?P<aht>\d+)\))?")
DATE_RE = re.compile(r"(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{2,4}))?\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})")


def _profile_slug(href: str, league: League) -> str | None:
    if not href:
        return None
    path = urlparse(urljoin("https://esoccerbet.com.br", href)).path.rstrip("/")
    prefix = f"/{league.slug}/"
    if not path.startswith(prefix):
        return None
    tail = path[len(prefix):].strip("/")
    if not tail or "/" in tail or tail in {"page", "feed", "amp"}:
        return None
    return tail


def _parse_played_at(m: re.Match, now: datetime) -> datetime:
    day, month = int(m.group("day")), int(m.group("month"))
    year_raw = m.group("year")
    if year_raw:
        year = int(year_raw)
        if year < 100:
            year += 2000
    else:
        year = now.year
        candidate = datetime(year, month, day, int(m.group("hour")), int(m.group("minute")), tzinfo=now.tzinfo)
        if candidate > now.replace(microsecond=0) and (candidate - now).days > 7:
            year -= 1
    return datetime(year, month, day, int(m.group("hour")), int(m.group("minute")), tzinfo=now.tzinfo)


def _small_context(anchor: Tag, other_player: str) -> str:
    best = anchor.get_text(" ", strip=True)
    node: Tag | None = anchor
    for _ in range(4):
        parent = node.parent if isinstance(node, Tag) else None
        if not isinstance(parent, Tag):
            break
        text = norm(parent.get_text(" ", strip=True))
        if len(text) <= 120 and other_player.casefold() not in text.casefold():
            best, node = text, parent
        else:
            break
    return best


def _team_from_context(context: str, player: str) -> str | None:
    text = norm(context)
    text = re.sub(re.escape(player), " ", text, count=1, flags=re.IGNORECASE)
    text = SCORE_RE.sub(" ", text)
    text = DATE_RE.sub(" ", text)
    text = re.sub(r"^[\s·•|\-–—:]+|[\s·•|\-–—:]+$", "", text)
    return norm(text) or None


def _candidate_containers(soup: BeautifulSoup, league: League):
    seen: set[int] = set()
    for tag in soup.find_all(["tr", "li", "article"]):
        seen.add(id(tag))
        yield tag
    for tag in soup.find_all("div"):
        text = norm(tag.get_text(" ", strip=True))
        if 12 <= len(text) <= 300 and SCORE_RE.search(text) and DATE_RE.search(text):
            anchors = [a for a in tag.find_all("a", href=True) if _profile_slug(a.get("href", ""), league)]
            if len(anchors) >= 2 and id(tag) not in seen:
                seen.add(id(tag))
                yield tag


def parse_matches(html: str, league: League, now: datetime | None = None) -> list[Match]:
    now = now or datetime.now(ZoneInfo(TIMEZONE))
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, Match] = {}

    for container in _candidate_containers(soup, league):
        text = norm(container.get_text(" ", strip=True))
        score, date = SCORE_RE.search(text), DATE_RE.search(text)
        if not score or not date:
            continue

        anchors: list[Tag] = []
        slugs: set[str] = set()
        for a in container.find_all("a", href=True):
            slug = _profile_slug(a.get("href", ""), league)
            name = norm(a.get_text(" ", strip=True))
            if slug and name and slug not in slugs:
                slugs.add(slug)
                anchors.append(a)
        if len(anchors) < 2:
            continue

        home_a, away_a = anchors[0], anchors[1]
        home_player = norm(home_a.get_text(" ", strip=True))
        away_player = norm(away_a.get_text(" ", strip=True))
        if home_player.casefold() == away_player.casefold():
            continue

        source_id = None
        for attr in ("data-id", "data-match-id", "id"):
            val = container.get(attr)
            if val and re.search(r"\d", str(val)):
                source_id = str(val)
                break

        match = Match(
            league=league.code,
            league_label=league.label,
            played_at=_parse_played_at(date, now),
            home_player=home_player,
            away_player=away_player,
            home_team=_team_from_context(_small_context(home_a, away_player), home_player),
            away_team=_team_from_context(_small_context(away_a, home_player), away_player),
            home_score=int(score.group("hs")),
            away_score=int(score.group("as")),
            home_ht_score=int(score.group("hht")) if score.group("hht") else None,
            away_ht_score=int(score.group("aht")) if score.group("aht") else None,
            source_url=league.url,
            source_match_id=source_id,
        )
        found[match.fingerprint] = match

    return sorted(found.values(), key=lambda m: m.played_at, reverse=True)
