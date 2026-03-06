import requests
import random
import time
import json

API_URL = "http://127.0.0.1:8000/posts/"

SAMPLE_CONTENT = [
    "Привет, мир! Это мой первый пост.",
    "Сегодня отличная погода.",
    "Посмотрите, какую классную фотку я сделал.",
    "Кто идет гулять?",
    "Только что закончил новый проект на FastAPI!",
    "Обед был просто отвратительным.",
    "Встречаемся в 18:00.",
    "Скиньте ссылки на крутые книги по Python.",
    "Как вам новый фильм?",
    "Сплю...)"
]

def create_random_post():

    user_id = random.choice([1, 2, 3])
    
    content = random.choice(SAMPLE_CONTENT)
    
    payload = {
        "user_id": user_id,
        "content": content
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] User {data['user_id']} posted: '{data['content'][:20]}...'")
        else:
            print(f"[ERR] Server returned {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        print("[ERR] Не удалось подключиться к серверу. Он запущен?")

if __name__ == "__main__":
    print("Запуск генератора постов...")
    print("Нажмите Ctrl+C для остановки.\n")
    
    try:
        while True:
            create_random_post()
            time.sleep(random.randint(2, 4))
    except KeyboardInterrupt:
        print("\nГенератор остановлен.")