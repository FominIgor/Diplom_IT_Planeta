import unittest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication
import logging

class TestAuthRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])
        # Устанавливаем уровень логирования, чтобы избежать лишних сообщений
        logging.basicConfig(level=logging.CRITICAL)

    def setUp(self):
        # Патчим логгер перед импортом WelcomeScreen
        with patch('logging.getLogger'):
            from pages.WelcomeScreen import WelcomeScreen
            self.window = WelcomeScreen()
        
        # Мокаем DatabaseManager
        self.db_patch = patch('pages.WelcomeScreen.DatabaseManager')
        self.mock_db = self.db_patch.start()
        self.mock_instance = self.mock_db.return_value
        self.mock_instance.connect.return_value = None
        self.mock_instance.execute_query.return_value = []

    def _get_complete_user_data(self, role_data):
        """Возвращает полный набор данных пользователя с заполненными обязательными полями"""
        base_data = {
            'ФИО': 'Тестовый Пользователь',
            'Специальность': 'Тестовая специальность',
            'Всего': 0,
            'Кафедра': 'Тестовая кафедра',
            'Выполнено': 0,
            'Full_name': 'Test User'  # Добавляем недостающее поле
        }
        return {**base_data, **role_data}

    def _test_successful_login(self, role_data, login, password, expected_role):
        """Тест успешного входа"""
        complete_data = self._get_complete_user_data(role_data)
        self.mock_instance.execute_query.return_value = [complete_data]
        
        self.window.LoginField.setText(login)
        self.window.PasswordField.setText(password)

        self.window.authorize_user()
        self.assertEqual(self.window.ErrorField.text().strip(), "")

    def test_teacher_login(self):
        """Тест входа учителя"""
        self._test_successful_login(
            role_data={
                'id': 1, 
                'Teacher': 1,
                'Administrator': 0,
                'Head_of_the_department': 0,
                'Password': '12345'
            },
            login="teacher@mail.ru",
            password="12345",
            expected_role='teacher'
        )

    def test_head_login(self):
        """Тест входа заведующего кафедрой"""
        self._test_successful_login(
            role_data={
                'id': 2,
                'Head_of_the_department': 1,
                'Teacher': 0,
                'Administrator': 0,
                'Password': '12345'
            },
            login="head@mail.ru",
            password="12345",
            expected_role='head'
        )

    def test_admin_login(self):
        """Тест входа администратора"""
        self._test_successful_login(
            role_data={
                'id': 3,
                'Administrator': 1,
                'Teacher': 0,
                'Head_of_the_department': 0,
                'Password': '12345'
            },
            login="admin@mail.ru",
            password="12345",
            expected_role='admin'
        )

    def test_invalid_login(self):
        """Тест неверных учетных данных"""
        self.mock_instance.execute_query.return_value = []
        
        self.window.LoginField.setText("invalid@mail.ru")
        self.window.PasswordField.setText("wrong")

        self.window.authorize_user()
        self.assertEqual(self.window.ErrorField.text(), 
                        "Пользователь с такими данными не найден")

    def test_missing_data_fields(self):
        """Тест обработки отсутствия обязательных полей"""
        self.mock_instance.execute_query.return_value = [{
            'id': 1,
            'Teacher': 1,
            'Password': '12345'
            # Нет обязательных полей
        }]
        
        self.window.LoginField.setText("test@mail.ru")
        self.window.PasswordField.setText("12345")

        self.window.authorize_user()
        error_text = self.window.ErrorField.text()
        self.assertTrue("Ошибка" in error_text)

    def tearDown(self):
        self.db_patch.stop()
        self.window.deleteLater()
        # Очищаем handlers логгера чтобы избежать дублирования сообщений
        logging.getLogger().handlers.clear()

if __name__ == '__main__':
    unittest.main()