BROKERS = "77.232.135.48:9092,77.232.135.48:9094"

KAFKA_CONFIG = {
    "bootstrap.servers": BROKERS,
}

CONSUMER_CONFIG = {
    **KAFKA_CONFIG,
    "group.id": "user_ms",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True,
    "session.timeout.ms": 10000,
}

PRODUCER_CONFIG = {
    **KAFKA_CONFIG,
}

TOPICS = {
    "requests": "user_requests",
    "responses": "user_responses"
}
