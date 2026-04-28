# 🔒 Sikkerhedspolitik — Jarvis V2

> Sikkerhed er en prioritet. Dette dokument beskriver hvordan vi håndterer sikkerhedsspørgsmål.

---

## 📋 Indholdsfortegnelse

1. [Rapportering af sikkerhedsbrud](#rapportering-af-sikkerhedsbrud)
2. [Sikkerhedspraksis](#sikkerhedspraksis)
3. [Known issues](#known-issues)
4. [Kontakt](#kontakt)

---

## 🚨 Rapportering af sikkerhedsbrud

Hvis du finder et sikkerhedsproblem, bedes du:

1. **IKKE** åbne en offentlig issue på GitHub
2. Send email til: **jarvis@srvlab.dk**
3. Inkluder så mange detaljer som muligt:
   - Beskrivelse af problemet
   - Steps til at reproducere
   - Mulig impact
   - Foreslået fix (hvis du har et)

Vi svarer typisk inden for 48 timer.

---

## 🛡️ Sikkerhedspraksis

### Hvad vi gør

| Praksis | Status |
|---------|--------|
| Pre-commit secrets detection | ✅ Aktiv |
| Afhængigheds-scanning | ✅ Aktiv |
| Regelmæssige security updates | ✅ Aktiv |
| HTTPS enforcement (prod) | ✅ Anbefalet |
| API key authentication | ✅ Krævet |

### Hvad du bør gøre

1. **Opdater regelmæssigt** — Hold din installation opdateret
2. **Brug stærke API keys** — Generer nye keys periodisk
3. **Beskyt din .env fil** — Aldrig commit til git!
4. **Brug HTTPS** — Især i produktion
5. **Begræns netværksadgang** — Brug firewall

---

## 🔍 Known issues

Ingen kendte sikkerhedsproblemer på nuværende tidspunkt.

*Sidst tjekket: 2026-04-28*

---

## 📦 Afhængigheder

Vi scanner regelmæssigt for kendte sårbarheder i vores afhængigheder:

```bash
# Kør selv
pip-audit
# eller
safety check
```

---

## 🔐 Bedste praksis for brugere

### API Keys

```bash
# Generer et stærkt key
openssl rand -hex 32

# Opbevar sikkert
# Brug ikke samme key på tværs af miljøer
```

### Database

```bash
# Backup regelmæssigt
cp ~/.jarvis-v2/state/jarvis.db /backup/jarvis-$(date +%Y%m%d).db

# Kryptér backups
gpg -c /backup/jarvis-*.db
```

### Netværk

```bash
# Firewall eksempel (ufw)
ufw allow 443/tcp    # HTTPS
ufw allow 22/tcp     # SSH
ufw deny 8000/tcp    # Bloker direkte API adgang
```

---

## 📞 Kontakt

- **Email:** jarvis@srvlab.dk
- **GitHub Issues:** For ikke-fortrolige spørgsmål
- **Discord:** (hvis konfigureret)

---

*Sidst opdateret: 2026-04-28*
