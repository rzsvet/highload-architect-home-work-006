import os
import asyncio
import json
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import aio_pika
from aio_pika import ExchangeType

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/") 

# Менеджер соединений (хранит только локальные подключения)
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send(self, user_id: int, message: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

ws_manager = ConnectionManager()

# Глобальный объект для работы с RabbitMQ
class RabbitListener:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        # Эксклюзивная очередь для ЭТОГО инстанса сервиса
        self.queue = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            "user_feed_direct", ExchangeType.DIRECT
        )
        # Важно: exclusive=True означает, что очередь удалится при отключении
        self.queue = await self.channel.declare_queue(exclusive=True)
        
        # Запускаем слушателя в фоне
        asyncio.create_task(self.listen())

    async def listen(self):
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body)
                    target_user = data.get("target_user_id")
                    if target_user:
                        await ws_manager.send(target_user, json.dumps(data))

    async def bind_user(self, user_id: int):
        """Подписываем очередь этого сервера на сообщения для user_id"""
        await self.queue.bind(self.exchange, routing_key=str(user_id))

    async def unbind_user(self, user_id: int):
        """Отписываемся, если пользователь ушел"""
        await self.queue.unbind(self.exchange, routing_key=str(user_id))

rabbit_listener = RabbitListener()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await rabbit_listener.connect()
    yield
    await rabbit_listener.connection.close()

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws/feed/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await ws_manager.connect(websocket, user_id)
    
    # Динамическая подписка в RabbitMQ
    await rabbit_listener.bind_user(user_id)
    print(f"User {user_id} connected and bound")

    try:
        while True:
            # Ждем сообщений от клиента (ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)
        await rabbit_listener.unbind_user(user_id)
        print(f"User {user_id} disconnected")