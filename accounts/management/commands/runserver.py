from django.core.management import call_command
from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    def handle(self, *args, **options):
        call_command("migrate", interactive=False)
        return super().handle(*args, **options)
