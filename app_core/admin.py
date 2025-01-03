from django.contrib import admin
from app_core.models import *


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Player."""
    list_display = ['id', 'tg_id', 'name', 'registration_date', 'coins', 'coins_spent_today', 'daily_bonus_friends',
                    'consecutive_days', 'last_login_date', 'offline_coins', 'start_offline_coins',
                    'finish_offline_coins', 'coins_in_second', 'finish_second_coins', 'lvl', 'daily_bonus',
                    'instruction']


@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели Player."""
    list_display = ['id', 'player', 'name', 'lvl', 'price', 'percent_up_price', 'bonus_second', 'bonus_connection',
                    'dog_field', 'is_active']


@admin.register(ReferralSystem)
class ReferralSystemAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели ReferralSystem."""
    list_display = ['id', 'referral', 'new_player', 'referral_bonus', 'new_player_bonus']





