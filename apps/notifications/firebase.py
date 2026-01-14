import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

_app = None

def get_firebase_app():
    global _app
    if _app:
        return _app

    path = getattr(settings, "FIREBASE_SERVICE_ACCOUNT", None) or os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if not path:
        return None

    cred = credentials.Certificate(path)
    _app = firebase_admin.initialize_app(cred)
    return _app


def send_push(token: str, title: str, body: str, data: dict | None = None):
    app = get_firebase_app()
    if not app:
        return False, "Firebase not configured"

    msg = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
    )
    resp = messaging.send(msg, app=app)
    return True, resp
