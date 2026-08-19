from __future__ import annotations

import asyncio
from pathlib import Path
import random

from playwright.async_api import async_playwright, Page

from .config import BROWSER_TIMEOUT_MS, LEAGUES, League
from .parser import parse_matches

ARTIFACTS = Path("artifacts")


async def _block_heavy(route):
    if route.request.resource_type in {"image", "media", "font"}:
        await route.abort()
    else:
        await route.continue_()


async def scrape_league(page: Page, league: League, attempts: int = 3):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            response = await page.goto(league.url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT_MS)
            status = response.status if response else None
            if status and status >= 400:
                raise RuntimeError(f"HTTP {status} em {league.url}")
            await page.wait_for_timeout(1400 + random.randint(0, 900))
            html = await page.content()
            matches = parse_matches(html, league)
            if not matches:
                raise RuntimeError("Página abriu, mas nenhum resultado de partida foi reconhecido.")
            return matches
        except Exception as exc:
            last_exc = exc
            ARTIFACTS.mkdir(exist_ok=True)
            try:
                await page.screenshot(path=str(ARTIFACTS / f"league-{league.code}-attempt-{attempt}.png"), full_page=True)
                (ARTIFACTS / f"league-{league.code}-attempt-{attempt}.html").write_text(await page.content(), encoding="utf-8")
            except Exception:
                pass
            if attempt < attempts:
                await asyncio.sleep(attempt * 3)
    raise RuntimeError(f"Falha após {attempts} tentativas em {league.label}: {last_exc}")


async def scrape_all():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-dev-shm-usage", "--no-sandbox"])
        context = await browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1440, "height": 1200},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        await page.route("**/*", _block_heavy)
        for league in LEAGUES:
            try:
                results[league.code] = await scrape_league(page, league)
            except Exception as exc:
                results[league.code] = exc
        await context.close()
        await browser.close()
    return results
