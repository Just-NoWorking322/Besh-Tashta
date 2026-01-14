import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or getattr(user, "is_anonymous", True):
            await self.close(code=4401)
            return

        self.group_name = f"notifications_user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if user and not getattr(user, "is_anonymous", True):
            await self.channel_layer.group_discard(
                f"notifications_user_{user.id}", self.channel_name
            )

    async def notify(self, event):
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps(payload, ensure_ascii=False))
