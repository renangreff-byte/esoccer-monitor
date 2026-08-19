from __future__ import annotations

import asyncio
from pathlib import Path
import random

from playwright.async_api import async_playwright, Page, BrowserContext

from .config import BROWSER_TIMEOUT_MS, LEAGUES, League
from .parser import parse_matches

ARTIFACTS = Path("artifacts")


async def _block_heavy(route):
    if route.request.resource_type in {"image", "media", "font"}:
        await route.abort()
    else:
        await route.continue_()


async def scrape_league(page: Page, league: League, attempts: int = 2):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            response = await page.goto(league.url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT_MS)
            initial_status = response.status if response else None

            # Alguns sites respondem 403 inicialmente e liberam o conteúdo após
            # scripts/cookies do navegador. Não abortamos imediatamente: esperamos
            # alguns segundos e tentamos ler o DOM final.
            await page.wait_for_timeout(3500 + random.randint(0, 1200))
            html = await page.content()
            matches = parse_matches(html, league)
            if matches:
                return matches

            status_text = f"HTTP inicial {initial_status}; " if initial_status else ""
            title = await page.title()
            raise RuntimeError(
                f"{status_text}nenhum resultado reconhecido. Título final: {title[:120]!r}"
            )
        except Exception as exc:
            last_exc = exc
            ARTIFACTS.mkdir(exist_ok=True)
            try:
                await page.screenshot(path=str(ARTIFACTS / f"league-{league.code}-attempt-{attempt}.png"), full_page=False)
                (ARTIFACTS / f"league-{league.code}-attempt-{attempt}.html").write_text(await page.content(), encoding="utf-8")
            except Exception:
                pass
            if attempt < attempts:
                await asyncio.sleep(2)
    raise RuntimeError(f"Falha após {attempts} tentativas em {league.label}: {last_exc}")


async def _run_one(context: BrowserContext, league: League):
    page = await context.new_page()
    await page.route("**/*", _block_heavy)
    try:
        return await scrape_league(page, league)
    finally:
        await page.close()


async def scrape_all():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1440, "height": 1200},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        tasks = {league.code: asyncio.create_task(_run_one(context, league)) for league in LEAGUES}
        for code, task in tasks.items():
            try:
                results[code] = await task
            except Exception as exc:
                results[code] = exc
        await context.close()
        await browser.close()
    return results
