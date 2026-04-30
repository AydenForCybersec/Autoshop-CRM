#!/bin/bash
set -e

REPO_URL="https://github.com/AydenForCybersec/Autoshop-CRM.git"
INSTALL_DIR="$HOME/autoshop-crm"
SERVICE_NAME="autoshop-crm"
TARGET_REVISION="b2d4f8a1c6e3"

# Detect existing install and offer to reinstall
if [ -d "$INSTALL_DIR" ] || systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "An existing Autoshop CRM install was detected."
    read -rp "Reinstall from scratch? This will erase all data. [y/N]: " REINSTALL </dev/tty
    if [[ "$REINSTALL" =~ ^[Yy]$ ]]; then
        echo "==> Removing existing install"
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
        sudo rm -f "/etc/sudoers.d/autoshop-restart"
        sudo systemctl daemon-reload
        rm -rf "$INSTALL_DIR"
        echo "    Done. Starting fresh install."
    else
        echo "==> Updating existing install"
        git -C "$INSTALL_DIR" pull
        source "$INSTALL_DIR/venv/bin/activate"
        pip install --quiet -r "$INSTALL_DIR/requirements.txt"
        FLASK_APP=autoshop_crm:create_app PYTHONPATH=src DATABASE_URL="sqlite:///${INSTALL_DIR}/autoshop.db" \
            "$INSTALL_DIR/venv/bin/flask" db upgrade "$TARGET_REVISION"
        sudo systemctl restart "$SERVICE_NAME"
        echo "    Update complete."
        exit 0
    fi
fi

read -rp "Port to run on [5000]: " PORT </dev/tty
PORT="${PORT:-5000}"

echo "==> Installing system packages"
sudo apt update -qq
sudo apt install -y python3 python3-venv git

echo "==> Cloning repository"
git clone "$REPO_URL" "$INSTALL_DIR"
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
UPDATE_ALLOWED_COMMAND_PREFIXES="flask db upgrade,sudo systemctl restart autoshop-crm"
UPDATE_POST_UPDATE_COMMANDS="flask db upgrade,sudo systemctl restart autoshop-crm"
EOF

echo "==> Running database migrations"
FLASK_APP=autoshop_crm:create_app PYTHONPATH=src DATABASE_URL="sqlite:///${INSTALL_DIR}/autoshop.db" \
    "$INSTALL_DIR/venv/bin/flask" db upgrade "$TARGET_REVISION"

echo "==> Installing systemd service"
if [ "$PORT" -lt 1024 ]; then
    CAPABILITY_LINES="AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE"
else
    CAPABILITY_LINES=""
fi

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
${CAPABILITY_LINES}

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
