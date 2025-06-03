# app/cli/consumer.py

from app.utils.kafka_helper import get_consumer
from app.cli.producer import *
from app.core.kafka_config import TOPICS
from pydantic import ValidationError

from app.services.user_service import *

TOPIC_LIST = [TOPICS["requests"]]


def process_new_message(action, request_id, message):
    """Обрабатывает новое сообщение или создание чата"""
    try:
        print(f"📩 Обработка нового сообщения: {json.dumps(message, indent=2)}")
        source = message.get("source")

        if "body" in message:
            message = message["body"]

        print("message:", message)

        if action == "registration":
            result = register_user(message["data"], action)
            send_response(request_id, result["message"])
        elif action == "confirm_email":
            result = confirm_email(message["data"], action)
            send_response(request_id, result["message"])
        elif action == "login":
            result = login_user(message["data"], action)
            send_response(request_id, result["message"])
        elif action == "refresh_token":
            result = refresh_token_handler(message, action)
            send_response(request_id, result["message"])
        elif action == "get_all_users":
            result = get_all_users(action)
            send_response(request_id, result["message"])

    except ValidationError as ve:
        print(f"⚠️ Ошибка валидации данных: {ve}")
        pass
    except Exception as e:
        print(f"⚠️ Ошибка обработки сообщения: {str(e)}")
        pass


def consume_messages():
    consumer = get_consumer(TOPIC_LIST)

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"⚠️ Ошибка Kafka Consumer: {msg.error()}")
                continue

            message = json.loads(msg.value().decode("utf-8"))
            print(f"📩 Получено сообщение из {msg.topic()}:\n{json.dumps(message, indent=2)}")

            request_id = message.get("request_id")
            action = message["message"].get("action")

            process_new_message(action, request_id, message["message"])

    except KeyboardInterrupt:
        print("⏹️ Остановка Consumer")
    finally:
        consumer.close()
