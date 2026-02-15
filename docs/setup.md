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