# KINGS.CO – Django E-commerce Store

KINGS.CO is a menswear online store built with Python and Django. It covers the full shopping flow: browsing products, adding items to a cart, checking out and creating orders, with customer accounts and an admin back office.

Built by Lawal Busayo Quadri as a portfolio project after training in Python full-stack web development at Anchorsoft Academy (2026).

## Features

| Area | What it does |
| --- | --- |
| Product catalogue | Categories, brands, image galleries and size/colour variants with their own SKUs and prices |
| Inventory | Stock tracked per variant, low-stock alerts and an audit trail of every stock movement |
| Cart | Works for guests (session-based) and logged-in users; add and update items without reloading the page |
| Checkout and orders | Orders created from the cart in one step, stock deducted, unique order numbers (e.g. KNG-20260815-1A2B3C4D) |
| Coupons | Percentage or fixed discounts with date ranges, minimum order amounts and usage limits |
| Customer accounts | Sign up, log in, email verification, saved addresses and a wishlist |
| Security | Role-based profiles (customer, staff, super admin), lockout after repeated failed logins, secure cookies in production |
| Reviews | Star ratings and comments, shown only after admin approval |
| Newsletter | Email sign-up on the storefront |
| Payments | Payment records are modelled; gateway integration is the next step |

## Tech stack

Python, Django 4.2, SQLite (local) with PostgreSQL support via psycopg2, Gunicorn, Tailwind CSS (Tailwind CLI) and Pillow.

## Run it locally

```bash
git clone https://github.com/busayolawal1311-ctrl/kings.git
cd kings
python -m venv env
source env/Scripts/activate
pip install -r requirements.txt
npm install
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

On macOS/Linux, activate with `source env/bin/activate`. In a second terminal, build the CSS with `npm run tailwind`, then open http://127.0.0.1:8000 (admin at /admin).

## Environment variables (production)

| Variable | Purpose |
| --- | --- |
| DJANGO_SECRET_KEY | Secret key (required when DJANGO_DEBUG is false) |
| DJANGO_DEBUG | Set to false in production |
| DJANGO_ALLOWED_HOSTS | Comma-separated list of allowed hosts |

## Tests

Run `python manage.py test`. Tests cover the main storefront pages, the cart add/update endpoints, and checkout (order creation, stock deduction and cart clearing).

## Roadmap

Payment gateway integration, a REST API with Django REST Framework, and PostgreSQL with Docker-based deployment.
