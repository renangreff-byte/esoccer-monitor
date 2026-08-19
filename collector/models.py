from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import re
import unicodedata


def norm(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def key_norm(value: str | None) -> str:
    value = norm(value).casefold()
    value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


@dataclass
class Match:
    league: str
    league_label: str
    played_at: datetime
    home_player: str
    away_player: str
    home_team: str | None
    away_team: str | None
    home_score: int
    away_score: int
    home_ht_score: int | None
    away_ht_score: int | None
    source_url: str
    source_match_id: str | None = None
    status: str = "final"

    @property
    def total_goals(self) -> int:
        return self.home_score + self.away_score

    @property
    def winner(self) -> str:
        if self.home_score > self.away_score:
            return "home"
        if self.away_score > self.home_score:
            return "away"
        return "draw"

    @property
    def fingerprint(self) -> str:
        base = "|".join([
            self.league,
            self.played_at.isoformat(timespec="minutes"),
            key_norm(self.home_player),
            key_norm(self.away_player),
            key_norm(self.home_team),
            key_norm(self.away_team),
        ])
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def to_db(self) -> dict:
        d = asdict(self)
        d["played_at"] = self.played_at.isoformat()
        d["fingerprint"] = self.fingerprint
        d["total_goals"] = self.total_goals
        d["winner"] = self.winner
        return d
