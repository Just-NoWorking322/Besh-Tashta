from urllib.parse import parse_qs

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def get_user_by_id(user_id: int):
    User = get_user_model()
    return User.objects.filter(id=user_id).first()


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()

        raw_qs = scope.get("query_string", b"").decode(errors="ignore")
        query = parse_qs(raw_qs)
        token = query.get("token", [None])[0]

        if not token:
            return await super().__call__(scope, receive, send)

        token = token.strip().strip('"').strip("'")

        try:
            auth = JWTAuthentication()
            validated = auth.get_validated_token(token)

            user_id = validated.get("user_id")
            if user_id is None:
                return await super().__call__(scope, receive, send)

            user_id = int(user_id)  # у тебя user_id в токене строкой "5"
            user = await get_user_by_id(user_id)

            if user:
                scope["user"] = user

        except Exception:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
