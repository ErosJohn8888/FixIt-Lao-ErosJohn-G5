# FixIT Repair Management System

FixIT is a Django application for tracking customers, devices, repair requests,
diagnoses, work performed, inventory, payments, and device pickups. It uses
PostgreSQL for application data.

## Requirements

- Python 3.12 or later
- PostgreSQL 15 or later

## Connect to Supabase (PowerShell)

1. In Supabase, open your project and find its **Postgres connection string**
   (URI) in the project connection settings. Copy the URI connection string,
   not the `/rest/v1/` URL or an anon/service-role API key. Use the Supabase
   session pooler URI if direct connections are unavailable from your network.
   Keep the database password private and do not paste it into source files,
   chat, or commits.

2. Create and activate a Python environment, then install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. In the VS Code PowerShell terminal, set `DATABASE_URL` to the connection
   string you copied. This environment variable applies to this terminal
   session and is not saved in the project:

   ```powershell
   $env:DATABASE_URL = "paste-your-supabase-postgres-uri-here"
   ```

   Django requires SSL for this connection unless the URI explicitly specifies
   an `sslmode`.

4. Create the tables and a manager account:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

   Public registration creates Staff accounts. A superuser can promote other
   accounts to Manager in Django admin.

5. Start the server and open <http://127.0.0.1:8080/>:

   ```powershell
   python manage.py runserver 127.0.0.1:8080
   ```

Sign in using the account's email address and password. Managers can open the
repair/payment report; staff can manage the repair workflow and inventory.

## Tests

Production settings always use PostgreSQL. To run the automated test suite
without a local PostgreSQL service, use the test-only SQLite settings:

```powershell
python manage.py test --settings=campusconnect.test_settings
```

For PostgreSQL-backed tests, run `python manage.py test` with the database
environment configured and a PostgreSQL test database user that can create
databases.
