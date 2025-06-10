from sshtunnel import SSHTunnelForwarder
import pymysql
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class DatabaseManager:
    def __init__(self, ssh_user, ssh_host, db_user, db_password, db_name):
        self.ssh_user = ssh_user
        self.ssh_host = ssh_host
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.tunnel = None
        self.connection = None

    def connect(self):
        """Устанавливает SSH-туннель и подключается к базе данных."""
        try:
            self.tunnel = SSHTunnelForwarder(
                (self.ssh_host, 22),
                ssh_username=self.ssh_user,
                ssh_pkey=r"pages\id_ed25519",  # Укажите путь к приватному ключу
                remote_bind_address=('localhost', 3306)
            )
            self.tunnel.start()  # Запуск SSH-туннеля
            logging.info(f"SSH-туннель установлен на localhost:{self.tunnel.local_bind_port}")

            self.connection = pymysql.connect(
                host='localhost',
                port=self.tunnel.local_bind_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                cursorclass=pymysql.cursors.DictCursor
            )
            logging.info("Подключение к базе данных успешно!")
        except Exception as e:
            logging.error(f"Ошибка при подключении к базе данных: {e}")
            raise

    def execute_query(self, query, params=None):
        """Выполняет SQL-запрос и возвращает результат."""
        if not self.connection:
            raise Exception("Нет подключения к базе данных.")
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                if query.strip().upper().startswith("SELECT"):
                    return cursor.fetchall()
                else:
                    self.connection.commit()  # Фиксируем изменения для не-SELECT запросов
                    return cursor.rowcount
        except pymysql.Error as e:
            logging.error(f"Ошибка при выполнении запроса: {e}")
            raise

    def start_transaction(self):
        """Начинает новую транзакцию."""
        if not self.connection:
            raise Exception("Нет подключения к базе данных.")
        try:
            self.connection.begin()  # Начинаем транзакцию
            logging.info("Транзакция начата.")
        except Exception as e:
            logging.error(f"Ошибка при начале транзакции: {e}")
            raise

    def commit_transaction(self):
        """Фиксирует текущую транзакцию."""
        if not self.connection:
            raise Exception("Нет подключения к базе данных.")
        try:
            self.connection.commit()  # Фиксируем транзакцию
            logging.info("Транзакция зафиксирована.")
        except Exception as e:
            logging.error(f"Ошибка при фиксации транзакции: {e}")
            raise

    def rollback_transaction(self):
        """Откатывает текущую транзакцию."""
        if not self.connection:
            raise Exception("Нет подключения к базе данных.")
        try:
            self.connection.rollback()  # Откатываем транзакцию
            logging.info("Транзакция откачена.")
        except Exception as e:
            logging.error(f"Ошибка при откате транзакции: {e}")
            raise

    def close(self):
        """Закрывает соединение с базой данных и SSH-туннель."""
        if self.connection:
            self.connection.close()
            logging.info("Соединение с базой данных закрыто.")
        if self.tunnel:
            self.tunnel.stop()
            logging.info("SSH-туннель закрыт.")

    def is_connected(self):
        """Проверяет, активно ли соединение с БД."""
        return self.connection is not None and self.connection.open
