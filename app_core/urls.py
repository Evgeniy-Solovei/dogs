from django.urls import path
from app_core.views import *

urlpatterns = [
    path('player-info/<int:tg_id>/<str:name>/<int:referral_id>/', PlayerInfo.as_view(), name='player_info_referral'),
    path('player-info/<int:tg_id>/<str:name>/', PlayerInfo.as_view(), name='player-info'),
    path('daily-bonus/', LoginTodayFlag.as_view(), name='daily-bonus'),
    path('collecting_bonuses/', GetBonus.as_view(), name='collecting_bonuses'),

]
