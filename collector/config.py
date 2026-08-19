from dataclasses import dataclass


@dataclass(frozen=True)
class League:
    code: str
    label: str
    slug: str
    url: str


LEAGUES = [
    League("6", "Fifa 6 Minutos", "fifa-6-minutos", "https://esoccerbet.com.br/fifa-6-minutos/"),
    League("8", "Fifa 8 Minutos", "fifa-8-minutos", "https://esoccerbet.com.br/fifa-8-minutos/"),
    League("10", "Fifa 10 Minutos", "fifa-10-minutos", "https://esoccerbet.com.br/fifa-10-minutos/"),
    League("12", "Fifa 12 Minutos", "fifa-12-minutos", "https://esoccerbet.com.br/fifa-12-minutos/"),
]

TIMEZONE = "America/Sao_Paulo"
REQUEST_TIMEOUT_SECONDS = 30
BROWSER_TIMEOUT_MS = 35_000
