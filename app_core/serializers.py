from adrf.serializers import ModelSerializer
from app_core.models import *


class PlayerSerializer(ModelSerializer):
    """Сериализатор для модели Player"""
    class Meta:
        model = Player
        fields = '__all__'
