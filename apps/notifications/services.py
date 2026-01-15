from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification, DeviceToken
from .firebase import send_push


def broadcast_ws(user_id: int, payload: dict):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notifications_user_{user_id}",
        {"type": "notify", "payload": payload},
    )


def create_and_send_notification(*, user, title: str, body: str, type_: str = "SYSTEM", payload: dict | None = None):
    payload = payload or {}

    n = Notification.objects.create(
        user=user,
        type=type_,
        title=title,
        body=body,
        payload=payload,
    )

    try:
        broadcast_ws(user.id, {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "payload": n.payload,
            "created_at": n.created_at.isoformat(),
        })
    except Exception:
        pass

    tokens = DeviceToken.objects.filter(user=user, is_active=True).values_list("token", flat=True)
    for token in tokens:
        try:
            ok, _ = send_push(token, title=title, body=body, data={"notification_id": n.id, **payload})
            if not ok:
                break
        except Exception:
            pass

    return n
