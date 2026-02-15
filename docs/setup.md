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

## Initialize Database
```zsh
flask db upgrade
```
Run the App
```zsh
python run.py
```


## Demo quickstart

Use the built-in CLI seed command to create realistic demo data:

```zsh
flask db upgrade
flask seed-demo-data
python run.py
```

This inserts:
- one login user (`demo` / `demo123` by default)
- several customers
- vehicles for each customer
- jobs in mixed statuses (`open`, `in_progress`, `completed`, `on_hold`)

Optional: customize the login credentials when seeding:

```zsh
flask seed-demo-data --username shopadmin --password 'ChangeMe123!'
```

