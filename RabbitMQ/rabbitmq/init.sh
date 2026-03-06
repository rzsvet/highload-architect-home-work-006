#!/bin/bash
set -e

# Настройки
MASTER_NODE_NAME="rabbit@db-rabbitmq-node-01"
MASTER_HOST="db-rabbitmq-node-01"
COOKIE="${RABBITMQ_ERLANG_COOKIE:-secret_cookie}"

# Функция для ожидания запуска RabbitMQ (локально)
wait_for_local_rabbit() {
    echo "Waiting for local RabbitMQ to start..."
    until rabbitmqctl status >/dev/null 2>&1; do
        sleep 2
    done
    echo "Local RabbitMQ is UP."
}

# Функция для ожидания доступности мастер-ноды
# Используем rabbitmqctl вместо nc, так как nc отсутствует в образе
wait_for_master() {
    echo "Waiting for Master Node ($MASTER_NODE_NAME) to be available..."
    
    # Цикл проверки: пытаемся получить статус удаленной ноды
    # Переменные окружения для rabbitmqctl уже настроены в контейнере
    until rabbitmqctl -n $MASTER_NODE_NAME status >/dev/null 2>&1; do
        echo "Master node not ready yet... waiting"
        sleep 5
    done
    echo "Master Node is READY."
}

# --- Основная логика ---

# Убедимся, что Cookie установлена (нужна для аутентификации между нодами)
if [ ! -z "$COOKIE" ]; then
    echo "Setting Erlang Cookie..."
    echo "$COOKIE" > /var/lib/rabbitmq/.erlang.cookie
    chmod 400 /var/lib/rabbitmq/.erlang.cookie
    chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie
fi

# Если имя хоста совпадает с мастер-хостом, запускаем как мастер
if [ "$HOSTNAME" = "$MASTER_HOST" ]; then
    echo "Starting as MASTER node..."
    # Запускаем стандартный entrypoint
    exec docker-entrypoint.sh rabbitmq-server
else
    echo "Starting as WORKER node..."
    
    # 1. Запускаем RabbitMQ в фоновом режиме
    # Опция -detached позволяет запустить демон в фоне
    rabbitmq-server -detached
    
    # Ждем локального старта
    wait_for_local_rabbit
    
    # Ждем мастера
    wait_for_master
    
    # Проверяем, мы уже в кластере?
    # Если команда join_cluster выполнится успешно, мы в кластере.
    # Если мы уже в кластере, команда вернет ошибку, мы её проигнорируем или проверим статус.
    
    if rabbitmqctl cluster_status | grep -q "$MASTER_NODE_NAME"; then
        echo "Already in cluster with $MASTER_NODE_NAME."
    else
        echo "Joining cluster $MASTER_NODE_NAME..."
        # Останавливаем приложение (оставляя Erlang VM работающей)
        rabbitmqctl stop_app
        
        # Присоединяемся к мастеру
        rabbitmqctl join_cluster $MASTER_NODE_NAME
        
        # Запускаем приложение обратно
        rabbitmqctl start_app
        echo "Successfully joined cluster."
    fi
    
    # Останавливаем фоновый процесс RabbitMQ, чтобы передать управление PID 1
    rabbitmqctl stop
    
    # Небольшая пауза для корректного завершения процессов
    sleep 2
    
    echo "Restarting RabbitMQ in foreground (PID 1)..."
    # Запускаем основной процесс через стандартный entrypoint
    exec docker-entrypoint.sh rabbitmq-server
fi