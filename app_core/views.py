from adrf.generics import GenericAPIView
from adrf.views import APIView
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, inline_serializer, extend_schema_view, extend_schema, OpenApiExample, \
    OpenApiParameter
from rest_framework import status, serializers
from rest_framework.response import Response
from app_core.models import Player, ReferralSystem, Dog
from app_core.serializers import *


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
                player.start_offline_coins = timezone.now()
                player.finish_offline_coins = timezone.now() + timedelta(hours=3)
                player.finish_second_coins = timezone.now()
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
        else:
            if player.instruction:
                player.instruction = False
                await player.asave(update_fields=['instruction'])
        serializer = self.get_serializer(player)
        response_data = {"player_info": serializer.data, "bonus_info": DAILY_BONUSES}
        return Response(response_data, status=status.HTTP_200_OK)

    # # Обновляем ежедневный статус и возвращаем данные игрока
    # response_data = await self.update_player_status(player)
    # await update_top_100()
    # response_data['friends_count'] = friends_count
    # response_data['bonus_info'] = DAILY_BONUSES
    # return Response(response_data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        tags=["Игрок: ежедневный бонус"],
        summary="Получить ежедневный бонус",
        description="Устанавливает флаг 'daily_bonus' в False, что означает, что игрок получил ежедневный бонус.",
        request=inline_serializer(
            name="LoginTodayFlagRequest",
            fields={
                "tg_id": serializers.IntegerField(help_text="Уникальный идентификатор пользователя в Telegram")
            }
        ),
        responses={
            200: OpenApiResponse(
                description="Флаг 'daily_bonus' успешно установлен",
                examples=[
                    OpenApiExample(
                        "Пример ответа",
                        value={"message": "Флаг 'daily_bonus' успешно установлен"}
                    )
                ]
            ),
            404: {"description": "Игрок с указанным tg_id не найден"}
        }
    )
)
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


@extend_schema_view(
    post=extend_schema(
        tags=["Игрок: бонусы"],
        summary="Получить офлайн или ежесекундный бонус",
        description="Позволяет игроку получить офлайн бонус (раз в 3 часа) или ежесекундный бонус.",
        request=inline_serializer(
            name="GetBonusRequest",
            fields={
                "tg_id": serializers.IntegerField(help_text="Уникальный идентификатор пользователя в Telegram"),
                "hour": serializers.BooleanField(help_text="Флаг для получения офлайн бонуса", required=False),
                "second": serializers.BooleanField(help_text="Флаг для получения ежесекундного бонуса", required=False)
            }
        ),
        responses={
            200: OpenApiResponse(
                description="Бонус успешно зачислен",
                examples=[
                    OpenApiExample(
                        "Пример ответа",
                        value={
                            "tg_id": "tg_id пользователя",
                            "player_coins": "Текущее количество монет",
                            "message": "Бонус успешно зачислен"
                        }
                    )
                ]
            ),
            400: {"description": "Неверные данные (например, бонус еще недоступен)"},
            404: {"description": "Игрок с указанным tg_id не найден"}
        }
    )
)
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
            if player.finish_offline_coins and timezone.now() >= player.finish_offline_coins:
                player.coins += player.offline_coins
                player.start_offline_coins = timezone.now()
                player.finish_offline_coins = timezone.now() + timedelta(hours=3)
                await player.asave(update_fields=['coins', 'start_offline_coins', 'finish_offline_coins'])
            else:
                return Response({"error": "Офлайн бонус еще недоступен."}, status=status.HTTP_400_BAD_REQUEST)
        if second:
            # Вычисляем количество секунд с момента последнего получения бонуса
            current_time = timezone.now()
            if player.finish_second_coins:
                time_difference = current_time - player.finish_second_coins
                seconds_passed = time_difference.total_seconds()
                # Умножаем количество секунд на заработок монет в секунду
                earned_coins = int(seconds_passed) * player.coins_in_second
                player.coins += earned_coins
            # Обновляем время последнего сбора бонуса
            player.finish_second_coins = current_time
            await player.asave(update_fields=['coins', 'finish_second_coins'])
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


@extend_schema_view(
    get=extend_schema(
        tags=["Собаки: информация"],
        summary="Получить список собак игрока",
        description="Возвращает список всех активных собак игрока, включая виртуальную собаку.",
        parameters=[
            OpenApiParameter(name="tg_id", type=int, description="Уникальный идентификатор пользователя в Telegram")
        ],
        responses={
            200: OpenApiResponse(
                response=DogSerializer(many=True),
                description="Список собак игрока",
                examples=[
                    OpenApiExample(
                        "Пример ответа",
                        value={
                            "dogs": [
                                {"id": 1, "name": "Собака 1", "lvl": 1, "price": 100, "bonus_second": 3},
                                {"id": 2, "name": "Собака 2", "lvl": 2, "price": 200, "bonus_second": 6}
                            ],
                            "virtual_dog": {"id": 3, "name": "Виртуальная собака", "lvl": 1, "price": 0, "bonus_second": 0}
                        }
                    )
                ]
            ),
            404: {"description": "Игрок не найден"},
            500: {"description": "Внутренняя ошибка сервера"}
        }
    ),
    post=extend_schema(
        tags=["Собаки: создание"],
        summary="Создать новую собаку",
        description="Создает новую собаку для игрока и возвращает информацию о ней.",
        parameters=[
            OpenApiParameter(name="tg_id", type=int, description="Уникальный идентификатор пользователя в Telegram")
        ],
        responses={
            201: OpenApiResponse(
                response=DogSerializer,
                description="Собака успешно создана",
                examples=[
                    OpenApiExample(
                        "Пример ответа",
                        value={
                            "dog": {"id": 1, "name": "Собака 1", "lvl": 1, "price": 100, "bonus_second": 3},
                            "virtual_dog": {"id": 2, "name": "Виртуальная собака", "lvl": 1, "price": 0, "bonus_second": 0}
                        }
                    )
                ]
            ),
            404: {"description": "Игрок не найден"},
            400: {"description": "Неверные данные (например, недостаточно монет)"},
            500: {"description": "Внутренняя ошибка сервера"}
        }
    ),
    put=extend_schema(
        tags=["Собаки: скрещивание"],
        summary="Скрестить собак",
        description="Скрещивает указанные пары собак и возвращает информацию об улучшенных собаках.",
        parameters=[
            OpenApiParameter(name="tg_id", type=int, description="Уникальный идентификатор пользователя в Telegram")
        ],
        request=inline_serializer(
            name="BreedDogsRequest",
            fields={
                "dog_pairs": serializers.ListField(
                    child=serializers.ListField(child=serializers.IntegerField()),
                    help_text="Список пар собак для скрещивания"
                )
            }
        ),
        examples=[
            OpenApiExample(
                "Пример запроса",
                value={"dog_pairs": [[12, 7], [8, 4], [1, 2]]},
                request_only=True,
                summary='{"dog_pairs": [[12, 7], [8, 4], [1, 2]]}'  # Компактный JSON в виде текста
            )
        ],
        responses={
            200: OpenApiResponse(
                response=DogSerializer(many=True),
                description="Собаки успешно скрещены",
                examples=[
                    OpenApiExample(
                        "Пример ответа",
                        value={
                            "upgraded_dogs": [
                                {"id": 1, "name": "Собака 1", "lvl": 2, "price": 200, "bonus_second": 6}
                            ],
                            "virtual_dog": {"id": 2, "name": "Виртуальная собака", "lvl": 1, "price": 0, "bonus_second": 0}
                        }
                    )
                ]
            ),
            404: {"description": "Игрок не найден"},
            400: {"description": "Неверные данные (например, некорректные пары собак)"},
            500: {"description": "Внутренняя ошибка сервера"}
        }
    )
)
class DogsPlayer(GenericAPIView):
    """
    Эндпоинт для работы с собаками игрока.
    Поддерживает создание, скрещивание и получение списка собак.
    """
    serializer_class = DogSerializer

    async def get(self, request, tg_id: int):
        """Получение списка собак игрока."""
        try:
            player = await Player.objects.aget(tg_id=tg_id)
            dogs = player.dogs.filter(is_active=True)
            # Преобразуем QuerySet в список асинхронно
            dogs = [dog async for dog in dogs.aiterator()]
            serializer = DogSerializer(dogs, many=True)
            # Получаем информацию о виртуальной собаке
            virtual_dog = await Dog.get_or_create_virtual_dog(player)
            virtual_dog_serializer = DogSerializer(virtual_dog)

            return Response({
                'dogs': serializer.data,
                'virtual_dog': virtual_dog_serializer.data
            }, status=status.HTTP_200_OK)
        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def post(self, request, tg_id: int):
        """Создание новой собаки для игрока."""
        try:
            player = await Player.objects.aget(tg_id=tg_id)
            dog = await Dog.create_dog(player)
            serializer = DogSerializer(dog)

            # Получаем информацию о виртуальной собаке после создания
            virtual_dog = await Dog.get_or_create_virtual_dog(player)
            virtual_dog_serializer = DogSerializer(virtual_dog)

            return Response({
                'dog': serializer.data,
                'virtual_dog': virtual_dog_serializer.data
            }, status=status.HTTP_201_CREATED)
        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def put(self, request, tg_id: int):
        """
        Скрещивание собак.
        """
        try:
            player = await Player.objects.aget(tg_id=tg_id)
            dog_pairs = request.data.get('dog_pairs', [])
            if not dog_pairs:
                return Response({"error": "Необходимо передать список пар собак."}, status=status.HTTP_400_BAD_REQUEST)
            upgraded_dogs = await Dog.breed_dogs(player, dog_pairs)
            serializer = DogSerializer(upgraded_dogs, many=True)

            # Получаем информацию о виртуальной собаке после скрещивания
            virtual_dog = await Dog.get_or_create_virtual_dog(player)
            virtual_dog_serializer = DogSerializer(virtual_dog)

            return Response({
                'upgraded_dogs': serializer.data,
                'virtual_dog': virtual_dog_serializer.data
            }, status=status.HTTP_200_OK)
        except Player.DoesNotExist:
            return Response({"error": "Игрок не найден."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
