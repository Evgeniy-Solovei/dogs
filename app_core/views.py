from datetime import timedelta

from adrf.generics import GenericAPIView
from adrf.views import APIView
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from app_core.models import Player, ReferralSystem, Dog
from app_core.serializers import PlayerSerializer


# async def update_player_status(self, player):
#     """Функция для обновления ежедневного бонуса и получение бонусов от друзей 10%"""
#     if player.daily_bonus_friends != 0:
#         player.points += player.daily_bonus_friends
#         player.points_all += player.daily_bonus_friends
#         player.daily_bonus_friends = 0
#     elif player.is_new:
#         player.is_new = False
#     # Обновляем ежедневный статус
#     await player.update_daily_status()
#     await player.asave()
#     serializer = self.get_serializer(player)
#     return await serializer.adata
#
# async def create_tasks_new_player(self, player):
#     """Функция для присваивания всех существующих задач игроку."""
#     tasks = [task async for task in Task.objects.all()]
#     await PlayerTask.objects.abulk_create([PlayerTask(player=player, task=task) for task in tasks])

class PlayerInfo(GenericAPIView):
    """
    Представление для входа/создания пользователя.
    Принимает GET-запрос с идентификатором пользователя (tg_id) и именем пользователя (name).
    Необходимые переменные для корректной работы:
    - `tg_id`: Уникальный идентификатор пользователя в Telegram.
    - `name`: Имя пользователя.
    - `referral_id`: Id-друга который пригласил. (Не обязательный аргумент)
    Возвращает:
    - Информацию о пользователе.
    """
    serializer_class = PlayerSerializer

    async def get(self, request, tg_id: int, name: str, referral_id: int = None):
        # Пытаемся получить игрока или создаем нового
        player, created = await Player.objects.aget_or_create(tg_id=tg_id, name=name)
        # Если игрок только что создан проверяем реферальную систему
        if created:
            try:
                # ТУТ ПРИСВОИМ ВСЕ СУЩЕСТВУЮЩИЕ ЗАДАЧИ ДЛЯ ИГРОКОВ
                # await self.create_tasks_new_player(player)  # Присваиваем все задачи игроку
                player.start_offline_coins = timezone.now() + timedelta(hours=4)
                player.finish_offline_coins = timezone.now() + timedelta(hours=7)
                player.finish_second_coins = timezone.now() + timedelta(hours=4)
                await player.asave()
                # Создаем виртуальную собаку для игрока
                await Dog.get_or_create_virtual_dog(player)
            except Exception as e:
                return Response({"Error": f"Ошибка при присвоении задач: {str(e)}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            if referral_id and referral_id != tg_id:
                referral = await Player.objects.aget(tg_id=referral_id)
                # Проверяем, что реферальная связь ещё не существует
                exists = await ReferralSystem.objects.filter(referral=referral, new_player=player).aexists()
                if not exists:
                    await ReferralSystem.objects.acreate(referral=referral, new_player=player)
                else:
                    return Response({"Error": "Игрок уже в друзьях у реферала."}, status=status.HTTP_400_BAD_REQUEST)
            elif referral_id == tg_id:
                return Response({"Error": "Нельзя добавить самого себя в друзья!"}, status=status.HTTP_400_BAD_REQUEST)
        # Проверяем поля для инструкции
        if player.instruction:
            player.instruction = False
            await player.aupdate(update_fields=['instruction'])
        serializer = self.get_serializer(player)
        return Response(serializer.adata, status=status.HTTP_200_OK)


class LoginTodayFlag(APIView):
    """Представление для получения ежедневного бонуса"""
    async def post(self, request):
        tg_id = request.data.get('tg_id')
        try:
            player = await Player.objects.aget(tg_id=tg_id)
        except Player.DoesNotExist:
            return Response({"error": "Игрок с указанным tg_id не найден."}, status=status.HTTP_404_NOT_FOUND)
        # Обновляем ежедневный статус
        await player.update_daily_status()
        player.daily_bonus = False  # Обновляем флаг, что пользователь не надо показывать ежедневный бонус
        await player.asave(update_fields=['daily_bonus'])
        return Response({"message": "Флаг 'daily_bonus' успешно установлен"}, status=status.HTTP_200_OK)


class GetBonus(APIView):
    """Представление для получения офлайн бонуса 1 раз в 3 часа и ежесекундного бонуса"""
    async def post(self, request):
        tg_id = request.data.get('tg_id')
        hour = request.data.get('hour', False)  # Флаг для офлайн бонуса
        second = request.data.get('second', False)  # Флаг для ежесекундного бонуса
        try:
            player = await Player.objects.aget(tg_id=tg_id)
        except Player.DoesNotExist:
            return Response({"error": "Игрок с указанным tg_id не найден."}, status=status.HTTP_404_NOT_FOUND)
        if not hour and not second:
            return Response({"error": "Не указаны hour или second."}, status=status.HTTP_400_BAD_REQUEST)
        if hour:
            if player.finish_offline_coins and timezone.now() + timedelta(hours=4) >= player.finish_offline_coins:
                player.coins += player.offline_coins
                player.start_offline_coins = timezone.now() + timedelta(hours=4)
                player.finish_offline_coins = timezone.now() + timedelta(hours=7)
                await player.aupdate(update_fields=['coins', 'start_offline_coins', 'finish_offline_coins'])
            else:
                return Response({"error": "Офлайн бонус еще недоступен."}, status=status.HTTP_400_BAD_REQUEST)
        if second:
            player.coins += player.second_coins
            player.finish_second_coins = timezone.now() + timedelta(hours=4)
            await player.aupdate(update_fields=['coins', 'finish_second_coins'])
        response_data = {
            'tg_id': player.tg_id,
            'player_coins': player.coins,
            'message': '',
        }
        if hour and second:
            response_data["message"] = "Офлайн и ежесекундный бонусы успешно зачислены."
        elif hour:
            response_data["message"] = "Офлайн бонус успешно зачислен."
        elif second:
            response_data["message"] = "Ежесекундный бонус успешно зачислен."

        return Response(response_data, status=status.HTTP_200_OK)
