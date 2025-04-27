import logging
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDialog, QMessageBox
from datetime import datetime  
from PyQt5.uic import loadUi

from pages.DatabaseManager import DatabaseManager
from pages.Leaderboard_SQL import Leaderboard_SQL  # Импорт класса из модуля
from pages.Speciality_SQL import Speciality_SQL  # Импорт класса из модуля
from pages.DocumentViewer import DocumentViewer
from pages.TeacherDocumentViewer import TeacherDocumentViewer
from pages.AvailableDocuments import AvailableDocuments
from pages.UsersManager import UsersManager


from pages.OPOPManager import OPOPManager
from pages.SpecialityManager import SpecialityManager
from pages.DocumentManager import DocumentManager 
from pages.DepartmentManager import DepartmentManager 
from pages.TableFilterSort import TableFilterSort



# Настройка логирования
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class WelcomeScreen(QDialog):
    def __init__(self):
        super(WelcomeScreen, self).__init__()
        loadUi("views/diplom.ui", self)
        # Словарь ролей и связанных элементов
        self.Leaderboard.clicked.connect(self.Leaderboard_button)
        self.Leaderboard1.clicked.connect(self.Leaderboard_button)
        self.AssignedDocuments.clicked.connect(self.AssignedDocuments_button)
        self.AssignedDocuments1.clicked.connect(self.AssignedDocuments_button)
        self.AvailableDocuments.clicked.connect(self.AvailableDocuments_button)
        self.AvailableDocuments1.clicked.connect(self.AvailableDocuments_button)
        self.AddDiscipline.clicked.connect(self.AddDiscipline_button)
        self.AddDiscipline1.clicked.connect(self.AddDiscipline_button)
        self.DistributeDocuments.clicked.connect(self.DistributeDocuments_button)
        self.DistributeDocuments1.clicked.connect(self.DistributeDocuments_button)
        self.CheckDocuments.clicked.connect(self.CheckDocuments_button)
        self.CheckDocuments1.clicked.connect(self.CheckDocuments_button)
        self.CreateDepartment.clicked.connect(self.CreateDepartment_button)
        self.CreateDepartment1.clicked.connect(self.CreateDepartment_button)
        self.CreateSpecialty.clicked.connect(self.CreateSpecialty_button)
        self.CreateSpecialty1.clicked.connect(self.CreateSpecialty_button)
        self.AddUser.clicked.connect(self.AddUser_button)
        self.AddUser1.clicked.connect(self.AddUser_button)
        self.DownloadTemplate.clicked.connect(self.DownloadTemplate_button)
        self.DownloadTemplate1.clicked.connect(self.DownloadTemplate_button)
        self.CreateDocument.clicked.connect(self.CreateDocument_button)
        self.CreateDocument1.clicked.connect(self.CreateDocument_button)

        self.role_elements = {
            "администратор": [
                self.CreateSpecialty, self.CreateSpecialty1,
                self.AddUser, self.AddUser1,
                self.DownloadTemplate, self.DownloadTemplate1,
                self.CreateDocument, self.CreateDocument1,
                self.CreateDepartment, self.CreateDepartment1
            ],
            "завкафедрой": [
                self.AddDiscipline, self.AddDiscipline1,
                self.DistributeDocuments, self.DistributeDocuments1,
                self.CheckDocuments, self.CheckDocuments1
            ],
            "преподаватель": [
                self.widget_4, self.widget_5, self.widget_6,
                self.tableWidget
            ]
        }

        # Кнопки, видимые по умолчанию
        self.default_elements = [self.test]

        # Инициализация страницы авторизации
        self.page_Avtorisation()
        self.db_manager = None
        self.setup_ui()

    def setup_ui(self):
        """Настройка интерфейса и привязка сигналов."""
        self.Leaderboard.clicked.connect(self.Leaderboard_button)
        self.SignInButton.clicked.connect(self.authorize_user)
        self.Exit.clicked.connect(self.exit)
        self.Exit1.clicked.connect(self.exit)


    def Leaderboard_button(self):
        self.stackedWidget.setCurrentWidget(self.Leaderboards)
        self.tableWidget.hide()
        
        self.stackedWidget.show()


        # Находим виджет TeachersProgress внутри Leaderboards
        self.teachers_progress = self.Leaderboards.findChild(QtWidgets.QTableWidget, 'TeachersProgress')

        # Создаем экземпляр Leaderboard_SQL и передаем ему TeachersProgress и db_manager
        self.leaderboard_sql = Leaderboard_SQL(self.teachers_progress, self.db_manager)

        # Находим виджет для отображения данных о специальностях
        self.speciality_table = self.Leaderboards.findChild(QtWidgets.QTableWidget, 'ProgressSpecialty')

        # Создаем экземпляр Speciality_SQL и передаем ему таблицу и db_manager
        self.speciality_sql = Speciality_SQL(self.speciality_table, self.db_manager)

    
    def AssignedDocuments_button(self):
        self.stackedWidget.hide()
        self.tableWidget.show()
        
        # Находим виджет для отображения данных
        self.table_widget = self.findChild(QtWidgets.QTableWidget, 'tableWidget')

        # Проверяем, является ли текущий пользователь преподавателем, завкафедрой или администратором
        if hasattr(self, 'current_user_id'):
            # Получаем роли пользователя
            user_roles = self.get_user_roles(self.current_user_id)

            # Проверяем роли пользователя, учитывая приоритет
            if "завкафедрой" in user_roles:
                self.document_viewer = DocumentViewer(self.table_widget, self.db_manager, self.current_user_id)
            elif "преподаватель" in user_roles or "администратор" in user_roles:
                self.document_viewer = TeacherDocumentViewer(self.table_widget, self.db_manager, self.current_user_id)
            else:
                logging.error("У пользователя нет подходящей роли.")
                QMessageBox.warning(self, "Ошибка", "У вас недостаточно прав для просмотра документов.")
        else:
            logging.error("User ID не установлен. Пожалуйста, авторизуйтесь.")

    def get_user_roles(self, user_id):
        """
        Получает роли пользователя из базы данных.
        :param user_id: ID пользователя.
        :return: Список ролей пользователя.
        """
        try:
            query = """
                SELECT Administrator, Head_of_the_department, Teacher 
                FROM Users 
                WHERE id = %s;
            """
            result = self.db_manager.execute_query(query, (user_id,))
            if result:
                roles = []
                if result[0]["Administrator"] == 1:
                    roles.append("администратор")
                if result[0]["Head_of_the_department"] == 1:
                    roles.append("завкафедрой")
                if result[0]["Teacher"] == 1:
                    roles.append("преподаватель")
                return roles
            return []
        except Exception as e:
            logging.error(f"Ошибка при получении ролей пользователя: {e}")
            return []
        
    def reset_table_widget(self):
        """Полностью очищает tableWidget, включая контекстное меню и соединения."""
        
        # Очистить содержимое таблицы
        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(0)  # Удаляем все строки

        # Отключить все соединения сигналов
        try:
            self.tableWidget.customContextMenuRequested.disconnect()
        except TypeError:
            pass  # Если не было соединений, просто продолжаем

        try:
            self.tableWidget.clicked.disconnect()
        except TypeError:
            pass

        try:
            self.tableWidget.doubleClicked.disconnect()
        except TypeError:
            pass
        
        # Очистить контекстное меню
        self.tableWidget.setContextMenuPolicy(QtCore.Qt.NoContextMenu)




    def AvailableDocuments_button(self, user_id):
        self.stackedWidget.hide()
        self.tableWidget.show()
        self.reset_table_widget()
        

        # Находим виджет для отображения данных
        self.table_widget = self.findChild(QtWidgets.QTableWidget, 'tableWidget')

        # Проверяем, является ли текущий пользователь преподавателем, завкафедрой или администратором
        if hasattr(self, 'current_user_id'):
            # Получаем роли пользователя
            user_roles = self.get_user_roles(self.current_user_id)

            # Создаем экземпляр TeacherDocumentViewer и передаем ему таблицу, db_manager, user_id и user_roles

            self.document_viewer = AvailableDocuments(self.table_widget, self.db_manager, self.current_user_id)
           
        else:
            logging.error("User ID не установлен. Пожалуйста, авторизуйтесь.")
            QMessageBox.warning(self, "Ошибка", "User ID не установлен. Пожалуйста, авторизуйтесь.")

    def AddDiscipline_button(self):
        self.stackedWidget.setCurrentWidget(self.HeadDepartment)


    def DistributeDocuments_button(self):
        self.stackedWidget.setCurrentWidget(self.HeadDepartment)
        self.stackedWidget.hide()
        self.tableWidget.show()

    def CheckDocuments_button(self):
        self.stackedWidget.setCurrentWidget(self.HeadDepartment)
        self.stackedWidget.hide()
        self.tableWidget.show()
        
        
    def CreateSpecialty_button(self):
        self.stackedWidget.setCurrentWidget(self.Administration)
        self.stackedWidget.hide()
        self.tableWidget.show()

        self.reset_table_widget()

        self.table_widget = self.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.document_viewer = SpecialityManager(self.table_widget, self.db_manager)

    def CreateDepartment_button(self):
        self.stackedWidget.setCurrentWidget(self.Administration)
        self.stackedWidget.hide()
        self.tableWidget.show()

        self.reset_table_widget()

        self.table_widget = self.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.document_viewer = DepartmentManager(self.table_widget, self.db_manager)

    def AddUser_button(self):
        self.stackedWidget.setCurrentWidget(self.Administration)
        self.stackedWidget.hide()
        self.tableWidget.show()


        self.reset_table_widget()

        self.table_widget = self.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.document_viewer = UsersManager(self.table_widget, self.db_manager)

    def DownloadTemplate_button(self):
        self.stackedWidget.setCurrentWidget(self.Administration)
        self.stackedWidget.hide()
        self.tableWidget.show()

        self.reset_table_widget()
        self.table_widget = self.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.document_viewer = OPOPManager(self.table_widget, self.db_manager)
        
    def CreateDocument_button(self):
        self.stackedWidget.setCurrentWidget(self.Administration)
        self.stackedWidget.hide()
        self.tableWidget.show()

        self.reset_table_widget()

        self.table_widget = self.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.document_viewer = DocumentManager(self.table_widget, self.db_manager, self.current_user_id)

    def authorize_user(self):
        """Авторизация пользователя и запись даты последнего входа."""
        user = self.LoginField.text().strip()
        password = self.PasswordField.text()

        if not user or not password:
            self.ErrorField.setText("Заполните все поля")
            return

        self.ErrorField.setText(" ")

        try:
            self.db_manager = DatabaseManager(
                ssh_user="user1",
                ssh_host="176.108.248.26",
                db_user="root",
                db_password="12345",
                db_name="diplom"
            )
            self.db_manager.connect()

            query = '''
                SELECT id, Full_name, Administrator, Head_of_the_department, Teacher, Password 
                FROM Users 
                WHERE Email = %s;
            '''
            result = self.db_manager.execute_query(query, (user,))

            if not result:
                self.ErrorField.setText("Пользователь с такими данными не найден")
                return

            user_data = result[0]
            stored_password = user_data['Password']

            if password != stored_password:
                self.ErrorField.setText("Неверный пароль")
                return

            # Обновляем дату последнего входа
            user_id = user_data['id']
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            update_query = "UPDATE Users SET Last_login_date = %s WHERE id = %s"
            self.db_manager.execute_query(update_query, (now, user_id))

            logging.info(f"Пользователь {user} (ID: {user_id}) вошел в систему.")

            # Обработка успешной авторизации
            full_name = user_data['Full_name']
            roles = []
            if user_data['Administrator'] == 1:
                roles.append("администратор")
            if user_data['Head_of_the_department'] == 1:
                roles.append("завкафедрой")
            if user_data['Teacher'] == 1:
                roles.append("преподаватель")

            if roles:
                self.handle_user_access(user_id, full_name, roles)
            else:
                self.ErrorField.setText("Роли пользователя не определены.")

        except Exception as e:
            logging.error(f"Ошибка при авторизации: {e}")
            self.ErrorField.setText(f"Ошибка при выполнении запроса: {e}")
            logging.error(f"Ошибка авторизации: {e}")
            return False  # Неудачная авторизация
            if self.db_manager:
                self.db_manager.close()
                self.db_manager = None

    
    def handle_user_access(self, user_id, full_name, roles):
        # Установить видимость элементов в зависимости от ролей
        self.set_visibility_by_roles(roles)

        # Переход на соответствующую страницу
        if "администратор" in roles:
            self.Leaderboard_button()
        elif "преподаватель" in roles:
            self.Leaderboard_button()
        else:
            self.Leaderboard_button()

        # Установить текст с именем и ролями
        roles_display = ", ".join(roles)
        self.rol.setText(f"{full_name}\n{roles_display}.")

        # Сохраняем user_id для использования в других методах
        self.current_user_id = user_id

    def set_visibility_by_roles(self, roles):
        # Скрыть все элементы
        for role, elements in self.role_elements.items():
            for element in elements:
                element.hide()

        # Показать элементы для всех ролей пользователя
        for role in roles:
            if role in self.role_elements:
                for element in self.role_elements[role]:
                    element.show()

        # Показать элементы по умолчанию
        for element in self.default_elements:
            element.show()

        self.test.setHidden(True)

    def page_Avtorisation(self):
        self.test.setHidden(True)  # скрыть панель test всегда на странице авторизации
        if self.stackedWidget.currentWidget() == self.Avtorisation:
            # Скрыть все элементы, включая по умолчанию
            for role, elements in self.role_elements.items():
                for element in elements:
                    element.hide()
            for element in self.default_elements:
                element.hide()
        else:
            # Показать только элементы по умолчанию
            for element in self.default_elements:
                element.show()

    def exit(self):
        """Возврат на страницу авторизации."""
        self.stackedWidget.setCurrentWidget(self.Avtorisation)
        if self.db_manager:
            self.db_manager.close()
            self.db_manager = None

    def closeEvent(self, event):
        """Закрывает подключение к базе данных при закрытии приложения."""
        if self.db_manager:
            self.db_manager.close()
            self.exit()
        event.accept()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    welcome = WelcomeScreen()
    welcome.show()
    sys.exit(app.exec_())