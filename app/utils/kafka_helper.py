from confluent_kafka import Producer, Consumer
from app.core.kafka_config import PRODUCER_CONFIG, CONSUMER_CONFIG, TOPICS


def get_producer():
    """Создает Kafka Producer"""
    return Producer(PRODUCER_CONFIG)


def get_consumer(topics):
    """Создает Kafka Consumer"""
    consumer = Consumer(CONSUMER_CONFIG)
    consumer.subscribe(topics)
    return consumer


def send_message(topic, message):
    """Отправляет сообщение в Kafka"""
    producer = get_producer()
    producer.produce(topic, key="chat", value=message)
    producer.flush()
