import asyncio
import websockets
import json

async def listen_feed():
    uri = "ws://127.0.0.1:8000/ws/feed/1"
    
    async with websockets.connect(uri) as websocket:
        print(f"Подключено к {uri}")
        
        # await websocket.send("ping")
        
        while True:
            try:
                message = await websocket.recv()

                data = json.loads(message)
                print(f"Получено сообщение: {data}")
            except websockets.exceptions.ConnectionClosed:
                print("Соединение разорвано")
                break

if __name__ == "__main__":
    asyncio.run(listen_feed())