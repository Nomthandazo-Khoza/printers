# City Printers CRM System

A web-based CRM for a **printing services business** (document printing, photocopying, scanning, laminating, binding, etc.). This system is **not** for selling printer hardware.

## Tech Stack

- **Backend:** Python Flask
- **Frontend:** HTML, CSS, Bootstrap 5, JavaScript
- **Database:** MySQL
- **Libraries:** SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate

## Roles

- **Admin** – Manage users, services, view all data and reports
- **Cashier/Staff** – Register customers, create orders, record payments, receipts
- **Customer** – Register, place service requests, track orders, view receipts

## Setup

1. **Create virtual environment and install dependencies**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. **Configure environment**
   - Copy `.env.example` to `.env`
   - Set `SECRET_KEY` and `DATABASE_URI` for your MySQL server

3. **Database**
   - **Development (default):** If `DATABASE_URI` is not set, the app uses SQLite (`city_printers.db`) so you can run without MySQL.
   - **MySQL:** Set `DATABASE_URI` in `.env`, then create the database:
     ```sql
     CREATE DATABASE city_printers_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```

4. **Run migrations and seed data**
   ```bash
   set FLASK_APP=run:app
   flask db upgrade
   python seed_data.py
   ```

5. **Run the application**
   ```bash
   python run.py
   ```
   Open http://127.0.0.1:5001

## Default login (after seeding)

- **Staff:** admin@cityprinters.com / admin123  
- **Cashier:** cashier@cityprinters.com / cashier123  

## Project structure

```
app/
  models/       # SQLAlchemy models
  routes/       # Blueprints (auth, admin, cashier, customer_portal)
  forms/        # WTForms
  services/     # Business logic
  templates/
  static/
config.py
run.py
```

## Development phases

- **Phase 1** – Setup, models, auth, dashboards (current)
- **Phase 2** – Customer management, Service management
- **Phase 3** – Order creation with multiple services
- **Phase 4** – Payment and receipts
- **Phase 5** – Order tracking, reports
- **Phase 6** – Customer portal (place request, my orders, receipts)
