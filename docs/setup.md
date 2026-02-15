# Setup Guide

## Requirements
- Python 3.10+
- Virtualenv recommended

## Installation

```zsh
git clone https://github.com/AydenForCybersec/Autoshop-CRM
cd Autoshop-CRM
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
## Environment Variables
Copy the example file:
```zsh
cp .env.example .env
```
### Required variables:

SECRET_KEY
DATABASE_URL
FLASK_APP

`DATABASE_URL` is the canonical database setting used by the app.
Example for local MySQL:

```zsh
DATABASE_URL=mysql+mysqlclient://autoshop_user:your_db_password@localhost/autoshop
```

## Initialize Database
```zsh
flask --app autoshop_crm:create_app db upgrade
```
Run the App
```zsh
flask --app autoshop_crm:create_app run --host=0.0.0.0 --port=5000
```
