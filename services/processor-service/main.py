import os
import asyncio
import json
import aio_pika
from aio_pika import ExchangeType

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/") 

# Имитация БД дружбы
FRIENDSHIPS = {
    1: [2, 3],
    2: [1],
    3: [1]
}

async def main():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()

    # 1. Объявляем очередь входящих задач
    processing_queue = await channel.declare_queue("post_processing_queue", durable=True)

    # 2. Объявляем Exchange для рассылки конкретным пользователям (DIRECT)
    feed_exchange = await channel.declare_exchange(
        "user_feed_direct", ExchangeType.DIRECT
    )

    print("Processor Service started")

    async with processing_queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                data = json.loads(message.body)
                author_id = data.get("user_id")
                print(f"Processing post from {author_id}")

                # Находим друзей (бизнес-логика)
                friends = FRIENDSHIPS.get(author_id, [])
                
                for friend_id in friends:
                    # Формируем payload
                    payload = json.dumps({
                        "event": "new_post",
                        "target_user_id": friend_id,
                        "post_data": data
                    }).encode()
                    
                    msg = aio_pika.Message(body=payload)
                    
                    # Отправляем с Routing Key = ID друга
                    await feed_exchange.publish(msg, routing_key=str(friend_id))

if __name__ == "__main__":
    asyncio.run(main())