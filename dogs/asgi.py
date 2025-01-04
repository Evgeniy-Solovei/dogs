"""
ASGI config for dogs project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from dogs import routing  # Импортируем маршруты для WebSocket

# Устанавливаем настройки Django по умолчанию
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dogs.settings')

django_application = get_asgi_application()
# Создаем ASGI-приложение, которое поддерживает как HTTP, так и WebSocket
application = ProtocolTypeRouter({
    "http": django_application,  # Обработка HTTP-запросов
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns  # Маршруты для WebSocket
        )
    ),
})
