# 🏛 Production Deployment (`aurora` server)

Guide for deploying Home Genie in production on your home server (`aurora`) using Docker Compose and Systemd.

---

## 1. Prerequisites on Server

- **Docker & Docker Compose** installed
- Access to your homelab networks (`docs.petera9a.id.lv`, `home.petera9a.id.lv`)

---

## 2. Server Installation Steps

```bash
# SSH into your home server
ssh user@aurora

# Create application directory
mkdir -p /opt/home-genie && cd /opt/home-genie

# Download compose definition
curl -o docker-compose.yml https://raw.githubusercontent.com/rabestro/home-genie/main/docker-compose.yml

# Create production .env file
nano .env
```

Fill in production credentials in `.env`:

```env
TELEGRAM_BOT_TOKEN="your_bot_token"
GEMINI_API_KEY="your_gemini_api_key"
GEMINI_MODEL="gemini-3.1-flash-lite"
PAPERLESS_URL="https://docs.petera9a.id.lv"
HOME_ASSISTANT_URL="https://home.petera9a.id.lv"
FAMILY_USERS='{
  "123456789": {
    "name": "Jegors",
    "paperless_token": "secret_token",
    "github_token": "ghp_secret",
    "home_assistant_token": "eyJ...",
    "home_connect_token": "token_hc..."
  }
}'
```

---

## 3. Launching Container

```bash
docker compose pull
docker compose up -d
```

---

## 4. Systemd Auto-Restart Service

To ensure Home Genie automatically starts on server boot:

```ini
# /etc/systemd/system/home-genie.service
[Unit]
Description=Home Genie AI Telegram Assistant
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/home-genie
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now home-genie
```
