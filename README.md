# 🐴 Autoreitbuch Bot

Telegram-Bot der automatisch Reitstunden bucht (Dressur Standard 09:00) sobald Plätze frei werden.

## Deployment (GCP Free Tier)

Läuft auf einer **e2-micro VM** in `us-central1` — kostet dauerhaft nichts.
Kein Docker, kein Artifact Registry — Python läuft direkt via systemd auf der VM.

### Einmalig: GCP-Projekt anlegen

```bash
gcloud projects create autoreitbuch-bot --name="Autoreitbuch Bot"
gcloud config set project autoreitbuch-bot
gcloud billing projects link autoreitbuch-bot --billing-account=DEINE_BILLING_ACCOUNT_ID
```

### Einmalig: Pulumi Setup

```bash
pip install pulumi pulumi-gcp
cd infra
pulumi stack init dev

# Credentials als verschlüsselte Secrets hinterlegen
pulumi config set --secret telegram_token      <TOKEN>
pulumi config set --secret telegram_chat_id    <CHAT_ID>
pulumi config set --secret reitbuch_user       <USER>
pulumi config set --secret reitbuch_password   <PASSWORD>
```

### Infrastruktur hochfahren (einmalig)

```bash
make infra
```

### Code deployen + Bot starten

```bash
make deploy
```

### Nützliche Befehle

```bash
make logs    # Live-Logs des Bots
make ssh     # SSH in die VM
make redeploy  # Bot neustarten (ohne Code-Upload)
```

## Lokale Entwicklung

```bash
uv sync
cp .env.example .env   # Credentials eintragen

# Dry-run (keine echte Buchung)
uv run python src/main.py

# Echte Buchung
uv run python src/main.py --book

# Telegram-Bot starten
uv run python src/bot.py
```
