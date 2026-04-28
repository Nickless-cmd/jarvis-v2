# 🚀 Deployment — Jarvis V2

> Kom hurtigt op og køre med Jarvis på din egen infrastruktur.

---

## 📋 Indholdsfortegnelse

1. [Krav](#krav)
2. [Hurtig start (Docker)](#hurtig-start-docker)
3. [Manuel installation](#manuel-installation)
4. [Konfiguration](#konfiguration)
5. [Produktionsopsætning](#produktionsopsætning)

---

## 🔧 Krav

### Minimum

- Python 3.10+
- 4 GB RAM
- 10 GB diskplads
- Docker (valgfrit)

### Anbefalet

- 8+ GB RAM
- GPU til lokal inference (valgfrit)
- 20+ GB diskplads

---

## 🐳 Hurtig start (Docker)

### 1. Klon repoet

```bash
git clone https://github.com/Nickless-cmd/jarvis-v2.git
cd jarvis-v2
```

### 2. Kopier konfiguration

```bash
cp .env.example .env
# Rediger .env med dine indstillinger
```

### 3. Start med Docker Compose

```bash
docker-compose up -d
```

### 4. Verificer installationen

```bash
# Tjek logs
docker-compose logs -f

# Test API'et
curl http://localhost:8000/api/health
```

---

## 💻 Manuel installation

### 1. Klon repoet

```bash
git clone https://github.com/Nickless-cmd/jarvis-v2.git
cd jarvis-v2
```

### 2. Opret virtuel miljø

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# eller
venv\Scripts\activate  # Windows
```

### 3. Installer afhængigheder

```bash
pip install -r requirements.txt
```

### 4. Konfigurér miljø

```bash
cp .env.example .env
# Rediger .env med dine indstillinger
```

### 5. Start Jarvis

```bash
# Start API'et
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# Start heartbeat daemon (i separat terminal)
python scripts/heartbeat_daemon.py
```

---

## ⚙️ Konfiguration

### Miljøvariabler (.env)

```bash
# Database
DATABASE_URL=sqlite:///./jarvis.db

# API
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=din-hemmelige-api-key

# Model providers
OLLAMA_URL=http://localhost:11434
OPENAI_API_KEY=din-openai-key

# Integrationer
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=din-ha-token

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=jarvis@srvlab.dk
SMTP_PASS=din-adgangskode
```

### Runtime konfiguration (~/.jarvis-v2/config/runtime.json)

```json
{
  "primary_model_lane": "visible",
  "cheap_model_lane": "cheap",
  "heartbeat_interval_minutes": 15,
  "enable_experiments": true
}
```

---

## 🏭 Produktionsopsætning

### Sikkerhed

1. **Skift alle standard-adgangskoder**
2. **Brug HTTPS** — opsæt reverse proxy (nginx/traefik)
3. **Firewall** — begræns adgang til nødvendige porte
4. **API keys** — opbevar sikkert (ikke i git!)

### Reverse proxy (nginx eksempel)

```nginx
server {
    listen 443 ssl;
    server_name jarvis.dit-domæne.dk;

    ssl_certificate /etc/letsencrypt/live/jarvis.dit-domæne.dk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jarvis.dit-domæne.dk/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Systemd service

```ini
# /etc/systemd/system/jarvis-api.service
[Unit]
Description=Jarvis API
After=network.target

[Service]
Type=simple
User=jarvis
WorkingDirectory=/opt/jarvis-v2
ExecStart=/opt/jarvis-v2/venv/bin/uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start og aktiver
systemctl daemon-reload
systemctl start jarvis-api
systemctl enable jarvis-api
```

---

## 🧪 Verificering

```bash
# Tjek sundhedsstatus
curl http://localhost:8000/api/health

# Tjek systemstatus
curl http://localhost:8000/api/status

# Test chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hej Jarvis!"}'
```

---

## 🆘 Fejlfinding

### API starter ikke

```bash
# Tjek logs
journalctl -u jarvis-api -f

# Tjek port er fri
netstat -tlnp | grep 8000
```

### Database fejl

```bash
# Nulstil database (ADVARSEL: sletter alt!)
rm ~/.jarvis-v2/state/jarvis.db
python scripts/init_db.py
```

---

## 📚 Næste skridt

- [BRUGERVEJLEDNING.md](./BRUGERVEJLEDNING.md) — Lær at bruge Jarvis
- [API_REFERENCE.md](./API_REFERENCE.md) — Udforsk API'et
- [CONTRIBUTING.md](./CONTRIBUTING.md) — Bidrag til projektet

*Har du spørgsmål? Åbn en issue på GitHub!*
