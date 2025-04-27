from locust import HttpUser, task, between
from sshtunnel import SSHTunnelForwarder
import pymysql
import logging
import os
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test.log'),
        logging.StreamHandler()
    ]
)

class DBStressUser(HttpUser):
    """
    Класс для нагрузочного тестирования БД через SSH-туннель
    """
    wait_time = between(1, 3)  # Интервал между запросами (1-3 сек)
    host = ""  # Не требуется для тестов БД

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tunnel = None
        self.connection = None

    def on_start(self):
        """Вызывается при запуске каждого виртуального пользователя"""
        self.setup_db_connection()

    def setup_db_connection(self):
        """Установка SSH-туннеля и подключение к MySQL"""
        try:
            # 1. Пути и параметры подключения (ЗАМЕНИТЕ НА СВОИ!)
            ssh_host = "176.108.248.26"  # IP сервера с SSH
            ssh_user = "user1"          # SSH пользователь
            db_user = "db_user"         # Пользователь MySQL
            db_pass = "db_password"     # Пароль MySQL
            db_name = "db_name"         # Имя базы данных
            
            # 2. Получаем абсолютный путь к SSH ключу
            current_dir = Path(__file__).parent
            ssh_key_path = str(current_dir / "pages" / "id_ed25519")
            
            # 3. Проверяем существование ключа
            if not os.path.exists(ssh_key_path):
                raise FileNotFoundError(f"SSH key not found at {ssh_key_path}")

            # 4. Создаем SSH-туннель
            self.tunnel = SSHTunnelForwarder(
                (ssh_host, 22),
                ssh_username=ssh_user,
                ssh_pkey=ssh_key_path,
                remote_bind_address=('127.0.0.1', 3306),
                set_keepalive=60  # Поддержание соединения
            )
            self.tunnel.start()
            logging.info(f"SSH tunnel established on port {self.tunnel.local_bind_port}")

            # 5. Подключаемся к MySQL через туннель
            self.connection = pymysql.connect(
                host='127.0.0.1',
                port=self.tunnel.local_bind_port,
                user=db_user,
                password=db_pass,
                database=db_name,
                connect_timeout=10,
                cursorclass=pymysql.cursors.DictCursor
            )
            logging.info("Successfully connected to MySQL via SSH tunnel")

        except Exception as e:
            logging.error(f"Connection failed: {str(e)}")
            self.close_connections()
            raise

    @task(weight=3)  # Частота выполнения (относительно других @task)
    def insert_data(self):
        """Тест вставки данных"""
        try:
            with self.connection.cursor() as cursor:
                query = """
                INSERT INTO test_table (data, timestamp) 
                VALUES (%s, NOW())
                """
                cursor.execute(query, ("load_test_data"))
                self.connection.commit()
                logging.debug("Insert successful")
        except Exception as e:
            logging.error(f"Insert failed: {str(e)}")
            self.reconnect()

    @task(weight=1)
    def select_data(self):
        """Тест выборки данных"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM test_table")
                result = cursor.fetchone()
                logging.debug(f"Row count: {result['count']}")
        except Exception as e:
            logging.error(f"Select failed: {str(e)}")
            self.reconnect()

    def reconnect(self):
        """Переподключение при сбое"""
        logging.info("Attempting to reconnect...")
        self.close_connections()
        self.setup_db_connection()

    def close_connections(self):
        """Корректное закрытие соединений"""
        try:
            if self.connection and self.connection.open:
                self.connection.close()
            if self.tunnel and self.tunnel.is_active:
                self.tunnel.stop()
        except Exception as e:
            logging.error(f"Error closing connections: {str(e)}")

    def on_stop(self):
        """Вызывается при завершении работы пользователя"""
        self.close_connections()