#!/bin/bash
set -e

REPO_URL="https://github.com/AydenForCybersec/Autoshop-CRM.git"
INSTALL_DIR="$HOME/autoshop-crm"
SERVICE_NAME="autoshop-crm"

read -rp "Port to run on [5000]: " PORT
PORT="${PORT:-5000}"

echo "==> Installing system packages"
sudo apt update -qq
sudo apt install -y python3 python3-venv git

echo "==> Cloning repository"
if [ -d "$INSTALL_DIR" ]; then
    echo "    Directory $INSTALL_DIR already exists — pulling latest instead"
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo "==> Creating Python environment"
python3 -m venv venv
source venv/bin/activate
pip install --quiet -r requirements.txt

echo "==> Generating configuration"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > .env <<EOF
FLASK_ENV=production
FLASK_APP=autoshop_crm:create_app
PYTHONPATH=src

SECRET_KEY=${SECRET_KEY}

DATABASE_URL=sqlite:///${INSTALL_DIR}/autoshop.db

SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
PREFERRED_URL_SCHEME=http

UPDATE_ENABLED=true
UPDATE_LOCAL_ONLY=true
UPDATE_CONFIRM_PHRASE=CONFIRM
UPDATE_ALLOWED_COMMAND_PREFIXES=flask db upgrade,sudo systemctl restart autoshop-crm
UPDATE_POST_UPDATE_COMMANDS=flask db upgrade,sudo systemctl restart autoshop-crm
EOF

echo "==> Running database migrations"
export $(grep -v '^#' .env | xargs)
flask db upgrade

echo "==> Installing systemd service"
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Autoshop CRM
After=network.target

[Service]
User=${USER}
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${INSTALL_DIR}/venv/bin/gunicorn -w 2 -b 0.0.0.0:${PORT} wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo "==> Allowing passwordless service restart for updates"
echo "${USER} ALL=(ALL) NOPASSWD: /bin/systemctl restart ${SERVICE_NAME}" \
    | sudo tee /etc/sudoers.d/autoshop-restart > /dev/null

PI_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "Setup complete."
echo ""
echo "Open http://${PI_IP}:${PORT} on any device on this network to create your admin account."
echo ""
