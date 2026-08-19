# eSoccer Monitor

Coletor automático do eSoccerBet para **FIFA 6, 8, 10 e 12 minutos**. O projeto executa na nuvem pelo GitHub Actions a cada 10 minutos, grava as partidas no Supabase e mantém base histórica para análises de jogadores e confronto direto (H2H).

## Dados coletados

- liga e horário da partida
- jogador da casa e visitante
- equipe de cada jogador
- placar final
- placar do intervalo quando disponível
- total de gols, vencedor e fingerprint anti-duplicidade
- data/hora da coleta e status da execução

## Estatísticas preparadas no banco

Partidas, vitórias, empates, derrotas, percentual de vitória, médias de gols feitos/sofridos/total, Over 1.5 a 5.5, ambas marcam, clean sheet, jogos sem marcar e H2H jogador x jogador com percentuais e últimos confrontos.

## Automação

O workflow `.github/workflows/collect.yml` roda nos minutos `03,13,23,33,43,53` de cada hora. Não depende de computador ligado e não usa senha do Supabase no repositório: a autenticação ocorre por OIDC do GitHub Actions, aceita somente para este repositório e para a branch `main`.

## Estrutura

- `collector/` — Playwright, parser e envio seguro
- `tests/` — testes do parser
- `sql/` — esquema de referência do banco
- `web/` — dashboard estático
- `.github/workflows/collect.yml` — automação 24/7

## Observação

O coletor não tenta contornar CAPTCHA ou controles de acesso. Se o site alterar sua estrutura, os artefatos de diagnóstico ajudam a ajustar o parser.
