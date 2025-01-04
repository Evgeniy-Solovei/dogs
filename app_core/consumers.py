from channels.generic.websocket import AsyncWebsocketConsumer
import json


class DogsPlayerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from app_core.models import Player, Dog
        self.tg_id = self.scope['url_route']['kwargs']['tg_id']
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        from app_core.models import Player, Dog
        from app_core.serializers import DogSerializer
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'get_dogs':
                await self.get_dogs()
            elif action == 'create_dog':
                await self.create_dog()
            elif action == 'update_dogs':
                dog_pairs = data.get('dog_pairs', [])
                await self.update_dogs(dog_pairs)
            elif action == 'delete_dog':
                dog_id = data.get('dog_id')
                await self.delete_dog(dog_id)
            else:
                await self.send(json.dumps({"error": "Неизвестное действие"}))
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def get_dogs(self):
        from app_core.models import Player, Dog
        from app_core.serializers import DogSerializer
        try:
            player = await Player.objects.aget(tg_id=self.tg_id)
            dogs = player.dogs.filter(is_active=True)
            dogs = [dog async for dog in dogs.aiterator()]
            serializer = DogSerializer(dogs, many=True)
            virtual_dog = await Dog.get_or_create_virtual_dog(player)
            virtual_dog_serializer = DogSerializer(virtual_dog)

            await self.send(json.dumps({
                'action': 'get_dogs',
                'dogs': serializer.data,
                'virtual_dog': virtual_dog_serializer.data
            }))
        except Player.DoesNotExist:
            await self.send(json.dumps({"error": "Игрок не найден."}))
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def create_dog(self):
        from app_core.models import Player, Dog
        try:
            player = await Player.objects.aget(tg_id=self.tg_id)
            dog = await Dog.create_dog(player)
            await self.get_dogs()
        except Player.DoesNotExist:
            await self.send(json.dumps({"error": "Игрок не найден."}))
        except ValueError as e:
            await self.send(json.dumps({"error": str(e)}))
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def update_dogs(self, dog_pairs):
        from app_core.models import Player, Dog
        try:
            player = await Player.objects.aget(tg_id=self.tg_id)
            if not dog_pairs:
                await self.send(json.dumps({"error": "Необходимо передать список пар собак."}))
                return
            await Dog.breed_dogs(player, dog_pairs)
            await self.get_dogs()
        except Player.DoesNotExist:
            await self.send(json.dumps({"error": "Игрок не найден."}))
        except ValueError as e:
            await self.send(json.dumps({"error": str(e)}))
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def delete_dog(self, dog_id):
        from app_core.models import Player, Dog
        try:
            player = await Player.objects.aget(tg_id=self.tg_id)
            await Dog.delete_dog(player, dog_id)
            await self.get_dogs()
        except Player.DoesNotExist:
            await self.send(json.dumps({"error": "Игрок не найден."}))
        except ValueError as e:
            await self.send(json.dumps({"error": str(e)}))
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))
