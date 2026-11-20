# FixIT Repair Management System

FixIT is a Django application for repair-shop staff to manage customers,
devices, repair requests, diagnoses, work performed, inventory, payments, and
device pickups.

## Core feature: repair workflow

Staff can register a repair, follow it from intake through diagnosis and work,
record parts and payments, and close it when the device is picked up. Staff can
view and change repairs they received; Managers can view and manage all repairs
and access repair/payment reports. Repair records are stored in the configured
database and linked to the staff member who received them.

Customers, devices, and parts are shared shop records that authenticated staff
use when managing repairs. The workflow validates required fields, unique
device serial numbers, non-negative costs, available part quantities, payment
balances, and the work/pickup prerequisites for advancing a repair.

## Requirements

- Python 3.12 or later
- PostgreSQL 15 or later for a shared/Supabase database (optional for local use)

## Local setup (PowerShell)

1. Create and activate a Python environment, then install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Start the server:

   ```powershell
   python manage.py runserver 127.0.0.1:8080
   ```

   With no database environment variables set, the app uses local SQLite in
   `db.sqlite3`. The `runserver` command applies pending migrations
   automatically before starting. Open <http://127.0.0.1:8080/>.

3. Register a Staff account through the sign-up page. To create a Manager
   account for local testing, create a superuser:

   ```powershell
   python manage.py createsuperuser
   ```

   Superusers have Manager access. A superuser can also promote another account
   to Manager in Django admin.

## Use Supabase/PostgreSQL

1. In Supabase, copy the PostgreSQL connection URI from the project's database
   connection settings. Do not use the REST URL or an anon/service-role API
   key. Use the session-pooler URI if direct connections are unavailable.
   Keep the database password private; URL-encode special characters in it.
2. In the PowerShell terminal where you will run Django, set the connection URI:

   ```powershell
   $env:DATABASE_URL = "paste-your-supabase-postgres-uri-here"
   ```

3. Run the server. Pending migrations are applied automatically:

   ```powershell
   python manage.py runserver 127.0.0.1:8080
   ```

   Environment variables are local to the current terminal. Set `DATABASE_URL`
   again in another terminal before running management commands such as
   `createsuperuser`.

## Standard account features

- Public Staff registration; Managers are assigned by an existing superuser.
- Email-and-password login and POST-only logout.
- Role-aware dashboard and Manager-only reports.
- Authenticated users can view and edit their own profile.

## Tests

Run the automated suite with the in-memory SQLite test database:

```powershell
python manage.py test --settings=campusconnect.test_settings
```

PostgreSQL-backed tests can be run with `python manage.py test` when
`DATABASE_URL` is configured and the database user can create test databases.
