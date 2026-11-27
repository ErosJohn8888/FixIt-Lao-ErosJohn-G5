from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models.functions import Lower
from django.db.models import Count


class Command(BaseCommand):
    help = "Read-only health check of the configured database (changes nothing)."

    def handle(self, *args, **options):
        ok = True
        db = connection.settings_dict
        self.stdout.write(f"Engine: {db['ENGINE']}  Host: {db.get('HOST') or 'local file'}")
        try:
            connection.ensure_connection()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"CONNECTION FAILED: {exc}"))
            self.stderr.write(
                "Hints: remove the [ ] around the password; use the Session pooler "
                "URI; check the password was not changed/reset."
            )
            return
        self.stdout.write(self.style.SUCCESS("Connection OK"))

        executor = MigrationExecutor(connection)
        pending = [f"{m.app_label}.{m.name}" for m, _ in executor.migration_plan(executor.loader.graph.leaf_nodes())]
        if pending:
            ok = False
            self.stdout.write(self.style.WARNING("Pending migrations: " + ", ".join(pending)))
        else:
            self.stdout.write(self.style.SUCCESS("All migrations applied"))

        tables = set(connection.introspection.table_names())
        missing = [m._meta.db_table for m in apps.get_models() if m._meta.db_table not in tables]
        if missing:
            ok = False
            self.stdout.write(self.style.WARNING("Missing tables: " + ", ".join(missing)))

        User = apps.get_model("accounts", "CustomUser")
        if User._meta.db_table in tables:
            cols = {c.name for c in connection.introspection.get_table_description(connection.cursor(), User._meta.db_table)}
            if "role" in cols and "email" in cols:
                bad_roles = User.objects.exclude(role__in=["STAFF", "MANAGER"]).count()
                blank = User.objects.filter(email="").count()
                dupes = (User.objects.annotate(e=Lower("email")).values("e")
                         .annotate(n=Count("id")).filter(n__gt=1, e__gt=""))
                for label, value in (("users with invalid role", bad_roles),
                                     ("users with blank email", blank),
                                     ("duplicate emails (case-insensitive)", len(dupes))):
                    if value:
                        ok = False
                        self.stdout.write(self.style.WARNING(f"{label}: {value}"))

        if connection.vendor == "postgresql":
            with connection.cursor() as c:
                c.execute("select tablename from pg_tables where schemaname='public' and not rowsecurity")
                no_rls = [r[0] for r in c.fetchall()]
            if no_rls:
                ok = False
                self.stdout.write(self.style.WARNING(
                    f"{len(no_rls)} public tables have Row Level Security OFF "
                    "(readable through Supabase's public API). Run supabase/fix_database.sql."))
        self.stdout.write(self.style.SUCCESS("Database looks healthy") if ok else self.style.WARNING("Issues found (see above)"))