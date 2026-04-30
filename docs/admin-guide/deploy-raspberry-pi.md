# Deploying on a Raspberry Pi (Local Network)

## Who this is for
Anyone setting up Autoshop CRM on a Raspberry Pi so staff on the same Wi-Fi or wired network can use it. No prior coding experience required.

## What you will end up with
- The app running on the Pi, always on, auto-starting after reboots.
- Any device on your local network can open it in a browser.
- You can push updates from GitHub and apply them through the app's admin panel — no SSH needed after first setup.

## What you need before you start
- A Raspberry Pi running **Raspberry Pi OS** (any recent version).
- The Pi is connected to your network and you know its IP address.
  - To find it: on the Pi run `hostname -I` and use the first address shown (e.g. `192.168.1.42`).
- The Pi has internet access (to download the app and its dependencies).
- You can open a terminal on the Pi (either directly with a keyboard/monitor, or via SSH from another computer).

---

## Step 1 — Install system packages

Open a terminal on the Pi and run:

```sh
sudo apt update && sudo apt install -y python3 python3-venv git
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

This may take a few minutes on a Pi. Wait for it to finish.

---

## Step 4 — Create your configuration file

```sh
cp .env.example .env
nano .env
```

Replace the entire contents with the following. Change only the `SECRET_KEY` line — everything else can stay as-is for a Pi.

```sh
FLASK_ENV=production
FLASK_APP=autoshop_crm:create_app
PYTHONPATH=src

# Generate a random key by running:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
# then paste the result below.
SECRET_KEY=paste-your-random-key-here

DATABASE_URL=sqlite:////home/pi/autoshop-crm/autoshop.db

SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
PREFERRED_URL_SCHEME=http

UPDATE_ENABLED=true
UPDATE_LOCAL_ONLY=true
UPDATE_CONFIRM_PHRASE=CONFIRM
UPDATE_ALLOWED_COMMAND_PREFIXES=flask db upgrade,sudo systemctl restart autoshop-crm
UPDATE_POST_UPDATE_COMMANDS=flask db upgrade,sudo systemctl restart autoshop-crm
```

To generate the secret key, open a second terminal and run:

```sh
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the value of `SECRET_KEY`.

Save and exit nano: press `Ctrl+X`, then `Y`, then `Enter`.

---

## Step 5 — Set up the database

```sh
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
flask db upgrade
```

You should see lines like `Running upgrade ... -> ...` with no errors.

---

## Step 6 — Set up the background service

This makes the app start automatically when the Pi boots and restart if it crashes.

```sh
sudo nano /etc/systemd/system/autoshop-crm.service
```

Paste the following exactly:

```ini
[Unit]
Description=Autoshop CRM
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/autoshop-crm
EnvironmentFile=/home/pi/autoshop-crm/.env
ExecStart=/home/pi/autoshop-crm/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Save and exit (`Ctrl+X`, `Y`, `Enter`), then enable and start it:

```sh
sudo systemctl daemon-reload
sudo systemctl enable autoshop-crm
sudo systemctl start autoshop-crm
```

Check it started correctly:

```sh
sudo systemctl status autoshop-crm
```

You should see `Active: active (running)`. If it shows an error, see the **Troubleshooting** section below.

---

## Step 7 — Allow the app to restart itself after updates

When you apply an update through the app, it needs to restart the service. Allow it to do so without a password prompt:

```sh
sudo visudo -f /etc/sudoers.d/autoshop-restart
```

Add this single line:

```
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart autoshop-crm
```

Save and exit.

---

## Step 8 — Create the first admin account

On any device on your network, open a browser and go to:

```
http://<pi-ip-address>:5000
```

For example: `http://192.168.1.42:5000`

You will be redirected to a first-time setup page. Create your admin username and password here. This is the account you will use to manage everything.

---

## Done

The app is running. Share `http://<pi-ip-address>:5000` with your staff.

---

## Applying updates

When a new version is available on GitHub:

1. Go to `http://<pi-ip>:5000/updates` (admin login required, `manage_updates` permission).
2. Click **Check for updates**.
3. If an update is available, type `CONFIRM` in the box and click **Apply**.
4. The app will pull the latest code, run any database changes, and restart. You will see a brief connection drop — this is normal. Refresh after a few seconds.

---

## Troubleshooting

**Service failed to start**
```sh
sudo journalctl -u autoshop-crm -n 50
```
Look for the error near the bottom. Common causes:
- Wrong path in the service file (check `WorkingDirectory` and `EnvironmentFile`).
- Missing `.env` file.
- `SECRET_KEY` still set to the placeholder value.

**Can't reach the app from another device**
- Make sure you're using `http://` not `https://`.
- Confirm the Pi's IP hasn't changed — check again with `hostname -I`.
- Confirm the service is running: `sudo systemctl status autoshop-crm`.

**`flask db upgrade` errors**
- Make sure you ran `source venv/bin/activate` first.
- Make sure the `.env` file has a valid `DATABASE_URL`.

**Forgot admin password**
```sh
cd ~/autoshop-crm
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
flask reset-password <your-username>
```
