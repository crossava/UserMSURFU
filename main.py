import threading
import signal
import sys
from app.cli.consumer import consume_messages

# Глобальная переменная для управления Consumer
consumer_running = True


def signal_handler(sig, frame):
    """Обрабатывает сигнал завершения программы (Ctrl+C)"""
    global consumer_running
    print("\n⏹️ Остановка Consumer...")
    consumer_running = False


def start_consumer():
    """Запускает Consumer в отдельном потоке"""
    thread = threading.Thread(target=consume_messages, daemon=True)
    thread.start()
    print("🔄 Consumer запущен...")


if __name__ == "__main__":
    # Перехватываем сигналы остановки (Ctrl+C, kill)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    start_consumer()

    try:
        while consumer_running:
            pass
    except KeyboardInterrupt:
        signal_handler(None, None)

    print("✅ Программа завершена.")
    sys.exit(0)
