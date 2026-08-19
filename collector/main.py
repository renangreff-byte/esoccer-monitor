from __future__ import annotations

import asyncio
import sys
import traceback
from datetime import datetime, timezone

from .db import CloudIngest
from .scraper import scrape_all


def main() -> int:
    started_at = datetime.now(timezone.utc).isoformat()
    pages_ok = pages_error = records_seen = 0
    errors: list[str] = []
    all_matches = []

    try:
        results = asyncio.run(scrape_all())
        for league, result in results.items():
            if isinstance(result, Exception):
                pages_error += 1
                errors.append(f"Liga {league}: {result}")
                continue
            pages_ok += 1
            records_seen += len(result)
            all_matches.extend(result)

        status = "error" if pages_ok == 0 else ("partial" if pages_error else "success")
        response = CloudIngest().send(
            all_matches,
            started_at=started_at,
            status=status,
            pages_ok=pages_ok,
            pages_error=pages_error,
            records_seen=records_seen,
            error_message="\n".join(errors) or None,
        )
        print(
            f"status={status} paginas_ok={pages_ok} erros={pages_error} "
            f"vistos={records_seen} recebidos={response.get('received')} salvos={response.get('saved')}"
        )
        if errors:
            print("\n".join(errors), file=sys.stderr)
        return 0 if pages_ok else 2
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
