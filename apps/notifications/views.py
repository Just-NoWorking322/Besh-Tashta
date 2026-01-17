from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import CalendarEvent, Notification, DeviceToken
from apps.notifications.serializers import CalendarEventSerializer, NotificationSerializer, DeviceTokenSerializer, NotificationSerializer
from apps.notifications.services import create_and_send_notification

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample


class EventListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CalendarEventSerializer
    @extend_schema(
        tags=['Notifications'],
        summary="Список событий календаря",
        parameters=[
            OpenApiParameter("from", OpenApiTypes.DATE, description="Начало периода (YYYY-MM-DD)"),
            OpenApiParameter("to", OpenApiTypes.DATE, description="Конец периода (YYYY-MM-DD)"),
        ]
    )
    def get_queryset(self):
        qs = CalendarEvent.objects.filter(user=self.request.user)

        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")

        if date_from:
            d = parse_date(date_from)
            if d:
                qs = qs.filter(starts_at__date__gte=d)

        if date_to:
            d = parse_date(date_to)
            if d:
                qs = qs.filter(starts_at__date__lte=d)

        return qs.order_by("starts_at", "id")

    def perform_create(self, serializer):
        event = serializer.save()

        Notification.objects.create(
            user=self.request.user,
            type=Notification.Type.CALENDAR,
            title="Создано событие",
            body=event.title,
            payload={"event_id": event.id, "starts_at": event.starts_at.isoformat()},
        )


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CalendarEventSerializer

    def get_queryset(self):
        return CalendarEvent.objects.filter(user=self.request.user)


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=['Notifications'],
        summary="Прочитать одно уведомление",
        # Вместо просто "string" показываем объект
        responses={200: OpenApiTypes.OBJECT}, 
        examples=[OpenApiExample('Success', value={"detail": "ok"})]
    )
    def post(self, request, pk: int):
        n = Notification.objects.filter(user=request.user, pk=pk).first()
        if not n:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        if not n.is_read:
            n.is_read = True
            n.save(update_fields=["is_read"])

        return Response({"detail": "ok"})


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "ok"})



class DeviceTokenUpsertView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceTokenSerializer

    def perform_create(self, serializer):
        # upsert по token
        token = serializer.validated_data["token"]
        platform = serializer.validated_data.get("platform", DeviceToken.Platform.ANDROID)

        obj, _ = DeviceToken.objects.update_or_create(
            token=token,
            defaults={"user": self.request.user, "platform": platform, "is_active": True},
        )
        return obj


class TestNotifyView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        tags=['Notifications'],
        summary="Отправить тестовое пуш-уведомление",
        responses={201: OpenApiTypes.OBJECT},
        examples=[OpenApiExample('Success', value={"id": 105})]
    )
    def post(self, request):
        title = request.data.get("title", "Тест")
        body = request.data.get("body", "Проверка уведомлений")
        n = create_and_send_notification(
            user=request.user,
            title=title,
            body=body,
            type_="SYSTEM",
            payload={"source": "postman"},
        )
        return Response({"id": n.id}, status=status.HTTP_201_CREATED)


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)