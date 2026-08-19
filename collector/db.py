from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Iterable

import httpx

from .models import Match


class CloudIngest:
    def __init__(self):
        self.ingest_url = os.environ.get("INGEST_URL", "").strip()
        self.request_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "").strip()
        self.request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "").strip()
        if not self.ingest_url:
            raise RuntimeError("INGEST_URL não configurada.")
        if not self.request_url or not self.request_token:
            raise RuntimeError("OIDC do GitHub Actions indisponível. Verifique permissions: id-token: write.")
        self.client = httpx.Client(timeout=45)

    def _oidc_token(self) -> str:
        sep = "&" if "?" in self.request_url else "?"
        url = f"{self.request_url}{sep}audience=esoccer-monitor-ingest"
        r = self.client.get(url, headers={"Authorization": f"Bearer {self.request_token}"})
        r.raise_for_status()
        token = r.json().get("value")
        if not token:
            raise RuntimeError("GitHub não retornou token OIDC.")
        return token

    def send(self, matches: Iterable[Match], *, started_at: str, status: str,
             pages_ok: int, pages_error: int, records_seen: int,
             error_message: str | None = None) -> dict:
        rows = [m.to_db() for m in matches]
        payload = {
            "matches": rows,
            "run": {
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "pages_ok": pages_ok,
                "pages_error": pages_error,
                "records_seen": records_seen,
                "error_message": (error_message or "")[:4000] or None,
            },
        }
        token = self._oidc_token()
        r = self.client.post(
            self.ingest_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        return r.json()
