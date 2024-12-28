from celery import shared_task
from app_core.models import *


@shared_task(acks_late=True, reject_on_worker_lost=True)
def reset_login_today():
    """Сбрасывает поле daily_bonus у всех игроков."""
    Player.objects.update(daily_bonus=True)
