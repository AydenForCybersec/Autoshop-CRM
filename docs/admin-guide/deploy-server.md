# Deploying on a Linux Server (VPS / Cloud)

## Who this is for
Anyone setting up Autoshop CRM on a cloud server (DigitalOcean, Linode, AWS, etc.) so it is accessible over the internet. No prior coding experience required, but you will need SSH access to a server running **Ubuntu 22.04 or 24.04**.

## What you will end up with
- The app running at a domain name or public IP address, accessible from anywhere.
- HTTPS (secure connection) via Nginx.
- Auto-start on reboot, auto-restart on crash.
- In-app update panel so you can deploy new versions without SSH.

## What you need before you start
- A server running Ubuntu 22.04 or 24.04 with at least 512 MB RAM (1 GB recommended).
- SSH access to that server as a non-root user with sudo privileges.
  - If you only have a `root` user, create a regular user first:
    ```sh
    adduser autoshop
    usermod -aG sudo autoshop
    su - autoshop
    ```
- A domain name pointed at your server's public IP (optional but strongly recommended for HTTPS). If you don't have one yet, you can use the raw IP address with HTTP only.

All commands below are run **on the server** over SSH unless otherwise noted.

---

## Step 1 — Install system packages

```sh
sudo apt update && sudo apt install -y python3 python3-venv git nginx
```

---

## Step 2 — Download the app

```sh
cd ~
git clone https://github.com/AydenForCybersec/Autoshop-CRM.git autoshop-crm
cd autoshop-crm
```

---

## Step 3 — Create a Python environment and install dependencies

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Step 4 — Create your configuration file

```sh
cp .env.example .env
nano .env
```

Replace the entire contents with the following. Fill in the three values marked with `<angle brackets>`.

```sh
FLASK_ENV=production
FLASK_APP=autoshop_crm:create_app
PYTHONPATH=src

# Run this to generate a key, then paste the result below:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<paste-a-long-random-string-here>

# SQLite is fine for a small shop. For high traffic, switch to PostgreSQL or MySQL.
DATABASE_URL=sqlite:////home/<your-linux-username>/autoshop-crm/autoshop.db

SESSION_COOKIE_SECURE=true
REMEMBER_COOKIE_SECURE=true
PREFERRED_URL_SCHEME=https

UPDATE_ENABLED=true
UPDATE_LOCAL_ONLY=false
UPDATE_CONFIRM_PHRASE=CONFIRM
UPDATE_ALLOWED_COMMAND_PREFIXES=flask db upgrade,sudo systemctl restart autoshop-crm
UPDATE_POST_UPDATE_COMMANDS=flask db upgrade,sudo systemctl restart autoshop-crm
```

**Important:** Replace `<your-linux-username>` in `DATABASE_URL` with your actual Linux username (e.g. `autoshop`). You can check your username by running `whoami`.

To generate `SECRET_KEY`:
```sh
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Save and exit nano: `Ctrl+X`, then `Y`, then `Enter`.

Lock down the config file so only your user can read it:
```sh
chmod 600 .env
```

---

## Step 5 — Set up the database

```sh
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
flask db upgrade
```

---

## Step 6 — Set up the background service

```sh
sudo nano /etc/systemd/system/autoshop-crm.service
```

Paste the following. Replace `<your-linux-username>` with your actual username in all three places.

```ini
[Unit]
Description=Autoshop CRM
After=network.target

[Service]
User=<your-linux-username>
WorkingDirectory=/home/<your-linux-username>/autoshop-crm
EnvironmentFile=/home/<your-linux-username>/autoshop-crm/.env
ExecStart=/home/<your-linux-username>/autoshop-crm/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Note: unlike the Pi setup, this binds to `127.0.0.1` (localhost only) — Nginx will handle the public-facing traffic.

```sh
sudo systemctl daemon-reload
sudo systemctl enable autoshop-crm
sudo systemctl start autoshop-crm
sudo systemctl status autoshop-crm
```

You should see `Active: active (running)`.

---

## Step 7 — Allow the app to restart itself after updates

```sh
sudo visudo -f /etc/sudoers.d/autoshop-restart
```

Add this line, replacing `<your-linux-username>`:

```
<your-linux-username> ALL=(ALL) NOPASSWD: /bin/systemctl restart autoshop-crm
```

---

## Step 8 — Configure Nginx

Nginx sits in front of the app and handles HTTPS, compression, and forwarding requests.

```sh
sudo nano /etc/nginx/sites-available/autoshop-crm
```

**If you have a domain name**, paste this (replace `your-domain.com` in two places):

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**If you don't have a domain name yet**, use this (HTTP only, accessible via raw IP):

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the config and restart Nginx:

```sh
sudo ln -s /etc/nginx/sites-available/autoshop-crm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

`nginx -t` should say `syntax is ok`. If it shows an error, re-check the config file for typos.

---

## Step 9 — Enable HTTPS (domain name required)

Skip this step if you don't have a domain yet. You can always come back and do it later.

```sh
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts. Certbot will automatically update your Nginx config and renew the certificate before it expires.

After this, change `PREFERRED_URL_SCHEME` in `.env` to `https` if it isn't already, then restart the app:

```sh
sudo systemctl restart autoshop-crm
```

---

## Step 10 — Create the first admin account

Open a browser and go to:
- `http://your-server-ip` (if no domain)
- `https://your-domain.com` (if you set up a domain and HTTPS)

You will be redirected to a first-time setup page. Create your admin username and password here.

---

## Done

The app is live. Share the URL with your staff.

---

## Applying updates

When a new version is pushed to GitHub:

1. Log in and go to `/updates`.
2. Click **Check for updates**.
3. If an update is available, type `CONFIRM` and click **Apply**.
4. The app will pull the new code, run database changes, and restart. Refresh after a few seconds.

---

## Troubleshooting

**Service failed to start**
```sh
sudo journalctl -u autoshop-crm -n 50
```
Common causes:
- `<your-linux-username>` placeholder was not replaced in the service file.
- `.env` file is missing or has the placeholder `SECRET_KEY`.
- Wrong path in `DATABASE_URL`.

**502 Bad Gateway from Nginx**
The app isn't running. Check:
```sh
sudo systemctl status autoshop-crm
sudo journalctl -u autoshop-crm -n 20
```

**Can't reach the app at all**
Check your server's firewall allows ports 80 and 443:
```sh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

**Certbot fails**
- Your domain must be pointed at your server's IP before running Certbot.
- Port 80 must be open and Nginx must be running.

**Forgot admin password**
```sh
cd ~/autoshop-crm
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
flask reset-password <your-username>
```
