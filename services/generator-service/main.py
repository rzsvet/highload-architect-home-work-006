import requests
import random
import time
import os

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000/posts/")

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
    # Выбираем случайного автора из тех, что есть в "БД" processor_service
    user_id = random.choice([1, 2, 3])
    content = random.choice(SAMPLE_CONTENT)
    
    payload = {
        "user_id": user_id,
        "content": content
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print(f"[HTTP] User {user_id} created post: '{content[:20]}...'")
        else:
            print(f"[HTTP] Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[HTTP] Не удалось подключиться к API сервису.")

if __name__ == "__main__":
    print("=== Генератор постов (API Service) ===")
    print("Нажмите Ctrl+C для остановки.\n")
    
    try:
        while True:
            create_random_post()
            time.sleep(random.randint(2, 4))
    except KeyboardInterrupt:
        print("\nГенератор остановлен.")