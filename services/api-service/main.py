import os
import json
from fastapi import FastAPI
from pydantic import BaseModel
import aio_pika

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/") 

class PostCreate(BaseModel):
    user_id: int
    content: str

app = FastAPI()

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        # Объявляем обменник для обработки задач
        await self.channel.declare_exchange("post_processing", aio_pika.ExchangeType.DIRECT)

    async def send_task(self, data: dict):
        message = aio_pika.Message(body=json.dumps(data).encode())
        # Отправляем в дефолтный обменник с routing_key на очередь процессора
        await self.channel.default_exchange.publish(
            message, routing_key="post_processing_queue"
        )

mq_client = RabbitMQClient()

@app.on_event("startup")
async def startup():
    await mq_client.connect()
    # Объявляем очередь, чтобы она существовала
    await mq_client.channel.declare_queue("post_processing_queue", durable=True)

@app.post("/posts/")
async def create_post(post: PostCreate):
    # Имитация сохранения в БД
    post_data = post.dict()
    post_data["id"] = 123 # присвоен ID
    
    # Отправляем задачу на обработку (отложенная мат-ция)
    await mq_client.send_task(post_data)
    return {"status": "queued", "post": post_data}