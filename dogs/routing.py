from django.urls import re_path
from app_core.consumers import DogsPlayerConsumer  # Импортируем ваш Consumer

websocket_urlpatterns = [
    re_path(r'ws/dogs/(?P<tg_id>\d+)/$', DogsPlayerConsumer.as_asgi()),
]
