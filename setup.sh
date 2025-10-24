#!/bin/bash
# ================================================
# 🚗 AutoShop CRM — Full Setup Script
# ================================================
# Safe for both dev and production environments.
# ================================================

set -e

echo "============================================"
echo " 🚗 AutoShop CRM — Automated Setup"
echo "============================================"
sleep 0.5

# --- Root check ---
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo)."
  exit 1
fi

# --- Verify project root ---
if [ ! -f "manage.py" ]; then
  echo "❌ Run this from the project root (where manage.py is)."
  exit 1
fi

# --- Install dependencies ---
echo "📦 Installing system dependencies..."
apt update -y
apt install -y python3 python3-venv python3-pip python3-dev default-libmysqlclient-dev build-essential mariadb-server mariadb-client curl

# --- Start MySQL ---
echo "⚙️ Ensuring MySQL is running..."
systemctl enable mysql
systemctl start mysql

# --- Gather environment info ---
read -p "Enter environment type (dev/prod) [dev]: " ENV
ENV=${ENV:-dev}

DEVELOPMENT="true"
if [[ "$ENV" =~ ^(prod|production)$ ]]; then
  DEVELOPMENT="false"
fi

# --- Create MySQL database + user ---
DB_NAME="autoshop"
DB_USER="autoshop_user"
DB_PASS=$(openssl rand -base64 16)

echo "🗄 Creating MySQL database and user..."
mysql -u root <<MYSQL_SCRIPT
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

# --- Python environment setup ---
echo "🐍 Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# --- Python dependencies ---
echo "📦 Installing Python dependencies..."
if [ ! -f "requirements.txt" ]; then
  cat > requirements.txt <<EOF
Flask
Flask-Login
Flask-Migrate
Flask-SQLAlchemy
python-dotenv
mysqlclient
bcrypt
EOF
fi
pip install -r requirements.txt

# --- Create instance folder ---
mkdir -p instance/uploads logs

# --- Create .env file ---
echo "🧾 Writing .env file..."
cat > .env <<EOF
# ============================================
# AutoShop CRM Configuration
# ============================================
FLASK_APP=manage.py
FLASK_ENV=$( [ "$DEVELOPMENT" = "true" ] && echo "development" || echo "production" )
SECRET_KEY=$(openssl rand -hex 16)
DEVELOPMENT=${DEVELOPMENT}

HOST=0.0.0.0
PORT=5000

DB_HOST=localhost
DB_PORT=3306
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
SQLALCHEMY_DATABASE_URI=mysql+mysqlclient://${DB_USER}:${DB_PASS}@localhost/${DB_NAME}

LOG_FILE=logs/app.log
EOF

# --- Run migrations ---
echo "🧱 Initializing database..."
flask db init || true
flask db migrate -m "Initial tables" || true
flask db upgrade

# --- Systemd setup (only if not development) ---
if [ "$DEVELOPMENT" = "false" ]; then
  echo "🧩 Setting up systemd service..."

  SERVICE_FILE="/etc/systemd/system/autoshop.service"
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=AutoShop CRM Flask Service
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/flask run --host=0.0.0.0 --port=5000
Restart=always
RestartSec=5
StandardOutput=append:$(pwd)/logs/autoshop.log
StandardError=append:$(pwd)/logs/autoshop-error.log

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable autoshop.service
  systemctl start autoshop.service
  echo "✅ Systemd service installed and started."
else
  echo "⚙️ DEVELOPMENT=true — Skipping systemd auto-start setup."
fi

# --- Final output ---
echo ""
echo "✅ Setup Complete!"
echo "---------------------------------------------"
echo " Database: ${DB_NAME}"
echo " User:     ${DB_USER}"
echo " Password: ${DB_PASS}"
echo "---------------------------------------------"
if [ "$DEVELOPMENT" = "true" ]; then
  echo "To start the app manually:"
  echo "  source venv/bin/activate"
  echo "  flask run --host=0.0.0.0"
else
  echo "App is now managed by systemd:"
  echo "  systemctl status autoshop"
  echo "  systemctl restart autoshop"
fi
echo ""
echo "🎉 Visit http://<server-ip>:5000/setup to configure your shop!"
