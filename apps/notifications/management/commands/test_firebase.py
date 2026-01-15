from django.core.management.base import BaseCommand
from apps.notifications.firebase import send_push


class Command(BaseCommand):
    help = "Test firebase-admin initialization + send push to a fake token"

    def handle(self, *args, **options):
        ok, resp = send_push(
            token="fake_token_123",
            title="Test",
            body="Firebase test from backend",
            data={"ping": "1"},
        )
        self.stdout.write(f"ok={ok}")
        self.stdout.write(f"resp={resp}")
