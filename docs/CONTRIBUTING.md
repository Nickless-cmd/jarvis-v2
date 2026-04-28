# 🤝 Bidrag til Jarvis V2

> Tak fordi du overvejer at bidrage! Dette dokument forklarer hvordan du kommer i gang.

---

## 📋 Indholdsfortegnelse

1. [Kom i gang](#kom-i-gang)
2. [Udviklingsmiljø](#udviklingsmiljø)
3. [Kode-standarder](#kode-standarder)
4. [Pull Requests](#pull-requests)
5. [Rapportering af bugs](#rapportering-af-bugs)

---

## 🚀 Kom i gang

### 1. Fork repoet

```bash
# Fork først på GitHub, klon derefter:
git clone https://github.com/DIT_BRUGERNAVN/jarvis-v2.git
cd jarvis-v2
```

### 2. Opsæt udviklingsmiljø

```bash
# Installer afhængigheder
pip install -r requirements.txt

# Kør tests for at verificere opsætningen
pytest tests/
```

### 3. Opret en branche

```bash
# Brug beskrivende branchnavne
git checkout -b feature/min-ny-funktion
# eller
git checkout -b fix/ret-en-fejl
```

---

## 🛠️ Udviklingsmiljø

### Krav

- Python 3.10+
- Docker (valgfrit, til container-deployment)
- Git

### Pre-commit hooks

Vi bruger pre-commit hooks til at sikre kodekvalitet:

```bash
# Installer pre-commit
pip install pre-commit
pre-commit install

# Kør manuelt hvis nødvendigt
pre-commit run --all-files
```

---

## 📝 Kode-standarder

### Python

- Følg [PEP 8](https://pep8.org/)
- Brug type hints hvor muligt
- Skriv docstrings til offentlige funktioner

### Tests

- Skriv tests for ny funktionalitet
- Brug pytest
- Sørg for grønne tests før PR

```bash
# Kør tests
pytest tests/ -v

# Kør med coverage
pytest tests/ --cov=core
```

---

## 🔀 Pull Requests

### Før du åbner en PR

- [ ] Tests kører grønne
- [ ] Pre-commit hooks passerer
- [ ] Kode er formatteret korrekt
- [ ] Dokumentation er opdateret (hvis relevant)

### PR beskrivelse

Brug denne skabelon:

```markdown
## Hvad ændrer denne PR?

Kort beskrivelse af ændringen.

## Hvorfor er dette nødvendigt?

Forklar problemet eller use case.

## Testet hvordan?

Beskriv hvordan du har testet ændringen.

## Checklist

- [ ] Tests skrevet/opdateret
- [ ] Dokumentation opdateret
- [ ] Pre-commit hooks passerer
```

---

## 🐛 Rapportering af bugs

Åbn en issue på GitHub med følgende information:

1. **Beskrivelse** — Hvad sker der?
2. **Forventet opførsel** — Hvad skulle der ske?
3. **Steps to reproduce** — Hvordan kan vi gentage fejlen?
4. **Miljø** — Python version, OS, etc.

---

## 📚 Dokumentation

Gode dokumentationer er lige så vigtige som god kode!

- Skriv klare, konkrete eksempler
- Hold sproget enkelt og direkte
- Opdater INDEX.md hvis du tilføjer nye docs

---

## ❓ Spørgsmål?

- Åbn en issue på GitHub
- Kontakt: jarvis@srvlab.dk

*Tak for dit bidrag! 🎉*
