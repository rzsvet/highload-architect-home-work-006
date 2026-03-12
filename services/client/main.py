import asyncio
import websockets
import json
import os

WS_URL = os.environ.get("WS_URL", "ws://127.0.0.1:8000/ws/feed/1")

async def listen_feed():
    print(f"=== WebSocket Client ===")
    print(f"Подключение к {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("Соединение установлено. Ожидание обновлений ленты...")
            
            # Запускаем задачу на отправку пингов (чтобы держать соединение)
            async def ping_loop():
                while True:
                    await asyncio.sleep(30)
                    # await websocket.send("ping")
                    # print("Sent ping")

            asyncio.create_task(ping_loop())

            # Слушаем входящие сообщения
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                # if data == "pong":
                #     print("Get pong")
                #     continue
                    
                print(f"\n[WS EVENT] Получено обновление!")
                print(f"  Target User: {data.get('target_user_id')}")
                print(f"  Author ID:   {data.get('post_data', {}).get('user_id')}")
                print(f"  Content:     {data.get('post_data', {}).get('content')}")
                
    except websockets.exceptions.ConnectionClosed:
        print("\nСоединение разорвано сервером.")
    except Exception as e:
        print(f"\nОшибка: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(listen_feed())
    except KeyboardInterrupt:
        print("\nКлиент остановлен.")