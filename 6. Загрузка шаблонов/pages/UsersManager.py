import logging
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox,
    QMessageBox, QAbstractItemView, QMessageBox, QMenu, QAction, QVBoxLayout, QInputDialog
)

from PyQt5.QtCore import Qt
import logging

from PyQt5 import QtWidgets
from pages.TableFilterSort import TableFilterSort #Импорт класса с поиском 

class UsersManager:
    def __init__(self, table_widget, db_manager):
        """
        Инициализация менеджера для работы с таблицей Users.
        :param table_widget: Виджет таблицы для отображения данных.
        :param db_manager: Менеджер базы данных.
        """
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.filter_sort = TableFilterSort(table_widget)  # Интеграция поиска
        self.setup_table()
        self.update_table()

    def setup_table(self):
        """Настройка таблицы для отображения данных."""
        self.table_widget.setColumnCount(9)  # id, Full_name, Administrator, Head_of_the_department, Teacher, Email, Password, Last_login_date, Success_rate
        self.table_widget.setHorizontalHeaderLabels(["ID", "ФИО", "Администратор", "Зав. кафедрой", "Преподаватель", "Email", "Пароль", "Последний вход", "Успешность"])
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Включаем сортировку по столбцам
        self.table_widget.setSortingEnabled(True)
        self.table_widget.sortByColumn(9, Qt.AscendingOrder)  # Сортировка по проценту, по возрастанию

        # Запрещаем редактирование данных
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        """Показывает контекстное меню для таблицы."""
        menu = QtWidgets.QMenu()
        add_action = menu.addAction("Добавить")
        delete_action = menu.addAction("Удалить")
        modify_action = menu.addAction("Изменить")

        # Привязка действий к методам
        add_action.triggered.connect(self.add_record)
        delete_action.triggered.connect(self.delete_record)
        modify_action.triggered.connect(self.modify_record)

        # Показ меню
        menu.exec_(self.table_widget.viewport().mapToGlobal(position))

    def add_record(self):
        """Добавляет новую запись в таблицу Users."""
        try:
            dialog = QDialog()
            dialog.setWindowTitle("Добавить пользователя")
            layout = QVBoxLayout()

            # Поля для ввода данных
            full_name_edit = QLineEdit()
            full_name_edit.setPlaceholderText("ФИО")
            layout.addWidget(full_name_edit)

            administrator_combo = QComboBox()
            administrator_combo.addItem("Нет", 0)
            administrator_combo.addItem("Да", 1)
            layout.addWidget(QLabel("Администратор:"))
            layout.addWidget(administrator_combo)

            teacher_combo = QComboBox()
            teacher_combo.addItem("Нет", 0)
            teacher_combo.addItem("Да", 1)
            layout.addWidget(QLabel("Преподаватель:"))
            layout.addWidget(teacher_combo)

            email_edit = QLineEdit()
            email_edit.setPlaceholderText("Email")
            layout.addWidget(email_edit)

            password_edit = QLineEdit()
            password_edit.setPlaceholderText("Пароль")
            layout.addWidget(password_edit)

            save_button = QPushButton("Сохранить")
            save_button.clicked.connect(lambda: self.save_new_record(
                dialog, full_name_edit.text(), administrator_combo.currentData(),
                teacher_combo.currentData(), email_edit.text(), password_edit.text()
            ))
            layout.addWidget(save_button)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            logging.error(f"Ошибка при добавлении записи: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось добавить запись: {e}")


    def save_new_record(self, dialog, full_name, administrator, teacher, email, password):
        """Сохраняет нового пользователя в базу данных."""
        try:
            query = """
                INSERT INTO Users (Full_name, Administrator, Head_of_the_department, Teacher, Email, Password, Success_rate)
                VALUES (%s, %s, 0, %s, %s, %s, 0)
            """
            self.db_manager.execute_query(query, (full_name, administrator, teacher, email, password))
            QMessageBox.information(dialog, "Успех", "Пользователь успешно добавлен.")
            dialog.close()
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при сохранении записи: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить запись: {e}")


    def delete_record(self):
        """Удаляет пользователя, но корректно обновляет связанные записи."""
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self.table_widget, "Ошибка", "Выберите запись для удаления.")
                return

            user_id = self.table_widget.item(selected_row, 0).text()

            # Проверяем, был ли пользователь зав. кафедрой
            check_department_query = "SELECT id FROM Department WHERE Head_of_the_department = %s"
            department_rows = self.db_manager.execute_query(check_department_query, (user_id,))
            
            if department_rows:
                QMessageBox.warning(self.table_widget, "Внимание",
                                    "Этот пользователь является заведующим кафедрой. Назначьте нового перед удалением.")
                return

            # Обновляем документы, где он был автором
            update_documents_query = """
                UPDATE Documents 
                SET Teacher = NULL, Comment = CONCAT(Comment, '\nУдалённый пользователь (был автором)') 
                WHERE Teacher = %s
            """
            self.db_manager.execute_query(update_documents_query, (user_id,))

            # Удаляем права доступа пользователя
            delete_access_query = "DELETE FROM Documents_Access WHERE Teacher = %s"
            self.db_manager.execute_query(delete_access_query, (user_id,))

            # Удаляем пользователя
            delete_user_query = "DELETE FROM Users WHERE id = %s"
            self.db_manager.execute_query(delete_user_query, (user_id,))

            QMessageBox.information(self.table_widget, "Успех", "Пользователь успешно удалён.")
            self.update_table()
    
        except Exception as e:
            logging.error(f"Ошибка при удалении пользователя: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось удалить пользователя: {e}")


    def modify_record(self):
        """Изменяет выбранную запись в таблице Users (без изменения роли Зав. кафедрой)."""
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self.table_widget, "Ошибка", "Выберите запись для изменения.")
                return

            record_id = self.table_widget.item(selected_row, 0).text()

            dialog = QDialog()
            dialog.setWindowTitle("Изменить пользователя")
            layout = QVBoxLayout()

            full_name_edit = QLineEdit(self.table_widget.item(selected_row, 1).text())
            layout.addWidget(QLabel("ФИО:"))
            layout.addWidget(full_name_edit)

            administrator_combo = QComboBox()
            administrator_combo.addItem("Нет", 0)
            administrator_combo.addItem("Да", 1)
            administrator_combo.setCurrentIndex(int(self.table_widget.item(selected_row, 2).text()))
            layout.addWidget(QLabel("Администратор:"))
            layout.addWidget(administrator_combo)

            teacher_combo = QComboBox()
            teacher_combo.addItem("Нет", 0)
            teacher_combo.addItem("Да", 1)
            teacher_combo.setCurrentIndex(int(self.table_widget.item(selected_row, 4).text()))
            layout.addWidget(QLabel("Преподаватель:"))
            layout.addWidget(teacher_combo)

            email_edit = QLineEdit(self.table_widget.item(selected_row, 5).text())
            layout.addWidget(QLabel("Email:"))
            layout.addWidget(email_edit)

            password_edit = QLineEdit(self.table_widget.item(selected_row, 6).text())
            layout.addWidget(QLabel("Пароль:"))
            layout.addWidget(password_edit)

            save_button = QPushButton("Сохранить")
            save_button.clicked.connect(lambda: self.save_modified_record(
                dialog, record_id, full_name_edit.text(), administrator_combo.currentData(),
                teacher_combo.currentData(), email_edit.text(), password_edit.text()
            ))
            layout.addWidget(save_button)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            logging.error(f"Ошибка при изменении записи: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось изменить запись: {e}")


    def save_modified_record(self, dialog, record_id, full_name, administrator, teacher, email, password):
        """Сохраняет изменения пользователя, не изменяя роль Зав. кафедрой."""
        try:
            query = """
                UPDATE Users
                SET Full_name = %s, Administrator = %s, Teacher = %s, Email = %s, Password = %s
                WHERE id = %s
            """
            self.db_manager.execute_query(query, (full_name, administrator, teacher, email, password, record_id))
            QMessageBox.information(dialog, "Успех", "Пользователь успешно изменен.")
            dialog.close()
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при сохранении изменений: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить изменения: {e}")

    def update_table(self):
        """Обновляет данные в таблице."""
        try:
            self.table_widget.setRowCount(0)
            query = "SELECT id, Full_name, Administrator, Head_of_the_department, Teacher, Email, Password, Last_login_date, Success_rate FROM Users"
            rows = self.db_manager.execute_query(query)
            for row in rows:
                row_position = self.table_widget.rowCount()
                self.table_widget.insertRow(row_position)
                logging.debug(f"Добавление строки {row_position} с данными: {row}")
                for col_idx, col_name in enumerate(["id", "Full_name", "Administrator", "Head_of_the_department", "Teacher", "Email", "Password", "Last_login_date", "Success_rate"]):
                    item = QTableWidgetItem(str(row[col_name]))
                    self.table_widget.setItem(row_position, col_idx, item)

        except Exception as e:
            logging.error(f"Ошибка при обновлении таблицы: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось обновить таблицу: {e}")