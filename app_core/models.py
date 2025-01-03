import json
from datetime import timedelta
from pathlib import Path
from django.db import models
from django.utils import timezone


def load_daily_bonuses():
    """Загружает ежедневные бонусы из JSON-файла."""
    bonuses_file_path = Path(__file__).resolve().parent / 'daily_bonuses.json'
    with open(bonuses_file_path, 'r') as file:
        bonuses_data = json.load(file)
    return bonuses_data['bonuses']


DAILY_BONUSES = load_daily_bonuses()


class Player(models.Model):
    """Модель игрока"""
    tg_id = models.PositiveBigIntegerField(unique=True, verbose_name="Telegram ID")
    name = models.CharField(max_length=50, verbose_name="Имя игрока")
    registration_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации игрока")
    coins = models.PositiveBigIntegerField(default=0, verbose_name="Текущие монеты игрока")
    coins_spent_today = models.PositiveBigIntegerField(default=0, verbose_name="Потраченные монеты за текущий день")
    daily_bonus_friends = models.IntegerField(default=0, verbose_name="Бонус от рефералов за текущий день")
    consecutive_days = models.IntegerField(default=0, verbose_name="Количество дней входов подряд")
    last_login_date = models.DateField(null=True, blank=True, verbose_name="Последний вход для расчёта дней подряд")
    offline_coins = models.IntegerField(default=0, verbose_name="Офлайн бонусы 1 раз в 3 часа")
    start_offline_coins = models.DateTimeField(null=True, blank=True, verbose_name="Время начала офлайн бонусов")
    finish_offline_coins = models.DateTimeField(null=True, blank=True, verbose_name="Время окончания офлайн бонусов")
    coins_in_second = models.IntegerField(default=0, verbose_name="Заработок монет в секунду")
    finish_second_coins = models.DateTimeField(null=True, blank=True, verbose_name="Время последнего сбора бонуса")
    lvl = models.IntegerField(default=1, verbose_name="Уровень игрока")
    daily_bonus = models.BooleanField(default=True, verbose_name="Выдача ежедневного бонуса")
    instruction = models.BooleanField(default=True, verbose_name="Показ инструкции")

    async def update_daily_status(self):
        """
        Проверяем вход пользователя, если вход подряд увеличиваем количество дней подряд, проверяем какой день подряд
        вошёл пользователь и начисляем ему монеты, проверяем количество дней подряд.
        """
        # Получаем текущее время в UTC
        now_utc = timezone.now()
        # Добавляем 4 часа (смещение для московского времени)
        now_moscow = now_utc + timedelta(hours=4)
        # Получаем дату в московском времени
        today = now_moscow.date()
        # Если пользователь уже заходил сегодня, ничего не делаем
        if not self.daily_bonus:
            return
        # Проверка для расчета consecutive_days
        if self.last_login_date:
            days_diff = (today - self.last_login_date).days
            self.consecutive_days = self.consecutive_days + 1 if days_diff == 1 else 1
        else:
            self.consecutive_days = 1
        # Получаем бонус для текущего дня
        daily_bonuses = DAILY_BONUSES
        bonus = next((b for b in daily_bonuses if b["day"] == self.consecutive_days), {"coins": 0})
        self.coins += bonus.get("coins", 0)
        self.last_login_date = today
        await self.asave()

    class Meta:
        verbose_name = "Игрок"
        verbose_name_plural = "Игроки"

    def __str__(self):
        return f"name:{self.name}, tg_id:{self.tg_id}"


class Dog(models.Model):
    """Модель собаки игрового поля"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='dogs', verbose_name='Игрок')
    name = models.CharField(max_length=50, default='', verbose_name='Имя собаки')
    lvl = models.IntegerField(default=1, verbose_name='Уровень собаки')
    price = models.IntegerField(default=100, verbose_name='Цена создания собаки')
    percent_up_price = models.FloatField(default=7.0, verbose_name='Процент увеличения цены')
    bonus_second = models.IntegerField(default=3, verbose_name='Бонус в секунду за создание собаки')
    bonus_connection = models.IntegerField(default=0, verbose_name='Бонус в секунду за cкрещивание собак')
    dog_field = models.IntegerField(null=True, blank=True, verbose_name='Место на игровом поле')
    is_active = models.BooleanField(default=True, verbose_name="Активная собака")

    @classmethod
    async def get_or_create_virtual_dog(cls, player):
        """Получаем или создаем виртуальную собаку для игрока"""
        virtual_dog = await cls.objects.filter(player=player, is_active=False).afirst()
        if not virtual_dog:
            virtual_dog = await cls.objects.acreate(player=player, is_active=False)
        return virtual_dog

    @classmethod
    async def find_free_field(cls, player):
        """Находим первое свободное место на поле игрока"""
        # Получаем все занятые места с помощью асинхронного итератора
        occupied_fields = set()
        async for dog_field in player.dogs.filter(is_active=True).values_list('dog_field', flat=True).aiterator():
            occupied_fields.add(dog_field)
        # Ищем первое свободное место (от 1 до 12)
        for field in range(1, 13):
            if field not in occupied_fields:
                return field
        return None

    @classmethod
    async def create_dog(cls, player):
        """Создание активной собаки для игрока"""
        # Проверяем, что у игрока меньше 12 собак
        if await player.dogs.filter(is_active=True).acount() >= 12:
            raise ValueError("У игрока уже максимальное количество собак (12).")
        # Получаем виртуальную собаку и используем её данные
        virtual_dog = await cls.get_or_create_virtual_dog(player)
        if player.coins >= virtual_dog.price:
            player.coins -= virtual_dog.price
            player.coins_spent_today += virtual_dog.price
            player.coins_in_second += virtual_dog.bonus_second
            await player.asave(update_fields=['coins', 'coins_spent_today', 'coins_in_second'])
            # Создаем активную собаку
            dog = await cls.objects.acreate(
                player=player,
                lvl=virtual_dog.lvl,
                price=virtual_dog.price,
                percent_up_price=virtual_dog.percent_up_price,
                bonus_second=virtual_dog.bonus_second,
                bonus_connection=virtual_dog.bonus_connection,
                dog_field=await cls.find_free_field(player),
                is_active=True
            )
            # Обновляем виртуальную собаку для следующей покупки
            await cls.update_virtual_dog(player)
            return dog
        else:
            raise ValueError("У игрока недостаточно денег для создания собаки.")

    @classmethod
    async def update_virtual_dog(cls, player):
        """Обновляем виртуальную собаку (уровень и цену)"""
        virtual_dog = await cls.get_or_create_virtual_dog(player)
        # Определяем уровень следующей собаки
        max_lvl_result = await player.dogs.filter(is_active=True).aaggregate(models.Max('lvl'))
        max_lvl_dog = max_lvl_result.get('lvl__max')
        if max_lvl_dog is None:
            max_lvl_dog = 1
        if max_lvl_dog >= virtual_dog.lvl:
            virtual_dog.lvl = max_lvl_dog // 5 + 1 if max_lvl_dog >= 5 else 1
            virtual_dog.bonus_second = virtual_dog.bonus_second * virtual_dog.lvl
            virtual_dog.bonus_connection = virtual_dog.lvl - 1
        virtual_dog.price = int(virtual_dog.price * (1 + virtual_dog.percent_up_price / 100))
        # Обновляем процент увеличения цены
        if virtual_dog.lvl == 2:
            virtual_dog.percent_up_price = 17.5
        await virtual_dog.asave()
        return virtual_dog

    @classmethod
    async def update_virtual_dog_level(cls, player):
        """Обновляем уровень виртуальной собаки (без изменения цены)"""
        virtual_dog = await cls.get_or_create_virtual_dog(player)
        # Определяем уровень следующей собаки
        max_lvl_result = await player.dogs.filter(is_active=True).aaggregate(models.Max('lvl'))
        max_lvl_dog = max_lvl_result.get('lvl__max')
        if max_lvl_dog is None:
            max_lvl_dog = 1
        if max_lvl_dog >= virtual_dog.lvl:
            virtual_dog.lvl = max_lvl_dog // 5 + 1 if max_lvl_dog >= 5 else 1
            virtual_dog.bonus_second = virtual_dog.bonus_second * virtual_dog.lvl
            virtual_dog.bonus_connection = virtual_dog.lvl - 1
            if virtual_dog.lvl == 2:
                virtual_dog.percent_up_price = 17.5
            await virtual_dog.asave()
        return virtual_dog

    @classmethod
    async def breed_dogs(cls, player, dog_pairs):
        """Скрещивание собак"""
        upgraded_dogs = []
        for dog_ids in dog_pairs:
            # Получаем собак по их ID
            dogs_query = cls.objects.filter(id__in=dog_ids, player=player, is_active=True)
            # # Преобразуем QuerySet в список асинхронно
            dogs = [dog async for dog in dogs_query.aiterator()]
            # Проверяем, что найдены ровно две собаки
            if len(dogs) != 2:
                raise ValueError(f"Для скрещивания необходимо ровно две собаки. Найдено: {len(dogs)}")
            # Проверяем, что все собаки одного уровня
            if len(set(dog.lvl for dog in dogs)) != 1:
                raise ValueError("Скрещивать можно только собак одного уровня.")
            # Удаляем одну собаку и повышаем уровень другой
            dog_to_upgrade = dogs[0]
            dog_to_delete = dogs[1]
            dog_to_upgrade.lvl += 1
            await dog_to_upgrade.asave()
            await dog_to_delete.adelete()
            upgraded_dogs.append(dog_to_upgrade)
            player.coins_in_second += dog_to_upgrade.lvl - 1
            await player.asave(update_fields=['coins_in_second'])
        # Обновляем виртуальную собаку после скрещивания
        await cls.update_virtual_dog_level(player)
        return upgraded_dogs

    class Meta:
        verbose_name = "Собака"
        verbose_name_plural = "Собаки"


class ReferralSystem(models.Model):
    """Модель реферальной системы"""
    referral = models.ForeignKey(Player, null=True, blank=True, on_delete=models.CASCADE, related_name='referral',
                                 verbose_name="Реферал")
    new_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='new_person',
                                   verbose_name="Новый игрок")
    referral_bonus = models.BooleanField(default=True, verbose_name="Бонус для реферала")
    new_player_bonus = models.BooleanField(default=True, verbose_name="Бонус для нового игрока")

    class Meta:
        verbose_name = "Реферальная система"
        verbose_name_plural = "Реферальная системы"


# class PromoCode(models.Model):
#     """Модель промокода"""
#     player = models.ForeignKey(Player, null=True, blank=True, on_delete=models.CASCADE, related_name="promo_codes",
#                                verbose_name="Игрок")
#     code = models.CharField(max_length=50, unique=True, verbose_name="Промокод")
#     description = models.TextField(default='', verbose_name="Описание промокода")
#     is_active = models.BooleanField(default=True, verbose_name="Активен ли промокод")
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
#     expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата истечения")
#
#     def __str__(self):
#         return self.code
