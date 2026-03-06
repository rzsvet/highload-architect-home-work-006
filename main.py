import asyncio
import json
import os
from typing import Dict, Set, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import aio_pika
from aio_pika import ExchangeType

# --- Конфигурация ---
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/") 


# --- Модели данных ---
class PostCreate(BaseModel):
    user_id: int
    content: str


class Post(PostCreate):
    id: int


# --- Имитация базы данных ---
posts_db: Dict[int, Post] = {}
post_id_counter = 0

# Граф дружбы
friendships: Dict[int, Set[int]] = {
    1: {2, 3},
    2: {1},
    3: {1},
}


def get_friends(user_id: int) -> List[int]:
    return list(friendships.get(user_id, set()))


# --- RabbitMQ Manager ---
class RabbitMQManager:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            "posts_feed", ExchangeType.FANOUT
        )
        print("Connected to RabbitMQ")

    async def disconnect(self):
        if self.connection:
            await self.connection.close()

    async def publish_post(self, post: dict):
        message = aio_pika.Message(body=json.dumps(post).encode())
        await self.exchange.publish(message, routing_key="")


mq_manager = RabbitMQManager()


# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)


ws_manager = ConnectionManager()


# --- Lifespan Context Manager (Замена on_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await mq_manager.connect()

    consumer_task = asyncio.create_task(consume_messages())

    print("Application started")

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass

    await mq_manager.disconnect()
    print("Application shut down")


# --- Инициализация приложения с lifespan ---
app = FastAPI(lifespan=lifespan)


async def consume_messages():
    """Функция прослушивания RabbitMQ и отправки клиентам."""
    async with mq_manager.connection.channel() as channel:
        queue = await channel.declare_queue(exclusive=True)
        await queue.bind(mq_manager.exchange)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body)
                    author_id = data.get("user_id")

                    friends_ids = get_friends(author_id)

                    for friend_id in friends_ids:
                        await ws_manager.send_personal_message(
                            json.dumps({"event": "new_post", "data": data}),
                            friend_id
                        )


# --- HTTP Endpoints ---

@app.post("/posts/", response_model=Post)
async def create_post(post: PostCreate):
    global post_id_counter
    post_id_counter += 1

    new_post = Post(id=post_id_counter, **post.dict())
    posts_db[new_post.id] = new_post

    # Публикуем событие
    await mq_manager.publish_post(new_post.dict())

    return new_post


# --- WebSocket Endpoint ---

@app.websocket("/ws/feed/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)
        print(f"User {user_id} disconnected")