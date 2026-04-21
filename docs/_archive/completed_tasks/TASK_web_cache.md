# TASK: Web Search Result Cache & Prompt Cache

## Beskrivelse

Implementer en lokal web cache i Jarvis' database så allerede hentede søgeresultater gemmes og genbruges med en udløbsdato (TTL). Når et resultat er for gammelt, skal web search tool'et hente friske data og opdatere databasen. Dette giver Jarvis en form for "akkumuleret internet-hukommelse" mellem sessioner.

## Del 1: Database tabel — `web_cache`

```sql
CREATE TABLE IF NOT EXISTS web_cache (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    source_url TEXT,
    title TEXT,
    body TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ttl_policy TEXT NOT NULL DEFAULT 'medium',  -- 'short', 'medium', 'long', 'static'
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_web_cache_query ON web_cache(query);
CREATE INDEX IF NOT EXISTS idx_web_cache_expires ON web_cache(expires_at);
```

### TTL policies

| Policy | Eksempler | TTL |
|--------|-----------|-----|
| `short` | Vejr, valutakurser, nyheder | 6 timer |
| `medium` | Priser, begivenheder, artikler | 7 dage |
| `long` | Dokumentation, bystørrelser | 90 dage |
| `static` | Matematik, historie, faste fakta | 365 dage |

## Del 2: Cache-opslag i web_search tool

Når `web_search` kaldes:

1. **Slå op** i `web_cache` hvor `query = <søgeord>` og `expires_at > NOW()`
2. **Hvis fundet** → returner cached resultat, increment `hit_count`
3. **Hvis ikke fundet** eller **udløbet** → kald Tavily API, gem resultat i `web_cache` med passende TTL, returner frisk resultat

TTL-policy vælges automatisk ud fra query-indhold (simple heuristik: "vejr" → short, "hvad er" → static, osv.) eller default til `medium`.

## Del 3: Cache-rydning

Tilføj en daemon eller cron-lignende mekanisme der periodisk sletter rækker hvor `expires_at < NOW()`. Kan integreres i eksisterende heartbeat/dæmon system.

## Del 4 (optional): Prompt caching

Overvej om dele af system-prompten der er statiske kan caches/memoizes for at spare token-forbrug. Lav en separat opgave hvis det giver mening.

## Noter

- Eksisterende `web_search` tool findes i Jarvis' tool-system og skal modificeres
- Brug eksisterende database-forbindelse (Sebastian-style DB via `db_query` eller ny write-enabled variant)
- Query-matching skal være fuzzy-nok til at "vejr København" og "København vejr" rammer samme cache-entry, men start med exact match og udvid senere
- Alt skal testes med eksisterende test-framework (pytest)