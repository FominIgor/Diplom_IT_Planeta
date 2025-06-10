from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QComboBox, QMessageBox, QVBoxLayout,
    QLabel, QLineEdit, QAbstractItemView, QMenu, QAction
)
from PyQt5.QtCore import Qt
from pages.TableFilterSort import TableFilterSort  # Импорт класса с поиском

class DisciplineManager:
    def __init__(self, table_widget, db_manager, current_user_id):
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.current_user_id = current_user_id
        self.filter_sort = TableFilterSort(table_widget)  # Интеграция поиска
        self.setup_table()
        self.update_table()

    def setup_table(self):
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["Кафедра", "Специальность", "Дисциплина"])
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.table_widget.setSortingEnabled(True)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)

    def update_table(self):
        self.table_widget.setSortingEnabled(False)  # Отключаем сортировку перед обновлением
        self.table_widget.setRowCount(0)  # Очищаем таблицу

        query = """
            SELECT dep.Name AS Department, sp.Name AS Speciality, dis.Name AS Discipline
            FROM Discipline dis
            LEFT JOIN Speciality sp ON dis.Speciality = sp.id
            LEFT JOIN Department dep ON sp.Department = dep.id
        """
        rows = self.db_manager.execute_query(query)

        for row in rows:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)

            # Создаем новые QTableWidgetItem
            department_item = QTableWidgetItem(row["Department"])
            speciality_item = QTableWidgetItem(row["Speciality"])
            discipline_item = QTableWidgetItem(row["Discipline"])

            # Устанавливаем элементы в таблицу
            self.table_widget.setItem(row_position, 0, department_item)
            self.table_widget.setItem(row_position, 1, speciality_item)
            self.table_widget.setItem(row_position, 2, discipline_item)

        self.table_widget.setSortingEnabled(True)  # Включаем сортировку обратно

    def show_context_menu(self, position):
        menu = QMenu()
        add_action = menu.addAction("Добавить")
        edit_action = menu.addAction("Изменить")  
        delete_action = menu.addAction("Удалить")

        add_action.triggered.connect(self.add_discipline)
        edit_action.triggered.connect(self.edit_discipline) 
        delete_action.triggered.connect(self.delete_discipline)

        menu.exec_(self.table_widget.viewport().mapToGlobal(position))

    def add_discipline(self):
        self.show_discipline_dialog("Добавить дисциплину")

    def show_discipline_dialog(self, title):
        dialog = QDialog()
        dialog.setWindowTitle(title)
        layout = QVBoxLayout()

        # Кафедра
        department_label = QLabel("Кафедра:")
        department_input = QComboBox()
        layout.addWidget(department_label)
        layout.addWidget(department_input)

        # Специальность
        speciality_label = QLabel("Специальность:")
        speciality_input = QComboBox()
        layout.addWidget(speciality_label)
        layout.addWidget(speciality_input)

        # Дисциплина
        discipline_label = QLabel("Название дисциплины:")
        discipline_input = QLineEdit()
        layout.addWidget(discipline_label)
        layout.addWidget(discipline_input)

        # Получаем кафедры
        departments = self.db_manager.execute_query("SELECT id, Name FROM Department")
        department_mapping = {str(dep["id"]): dep["Name"] for dep in departments}
        department_input.addItems(department_mapping.values())

        # При изменении кафедры обновлять список специальностей
        def update_specialities():
            speciality_input.clear()
            selected_department_id = list(department_mapping.keys())[department_input.currentIndex()]
            specialities = self.db_manager.execute_query(
                "SELECT id, Name FROM Speciality WHERE Department = %s", (selected_department_id,)
            )
            global speciality_mapping  # Добавляем глобальную переменную, чтобы избежать ошибки
            speciality_mapping = {str(sp["id"]): sp["Name"] for sp in specialities}
            speciality_input.addItems(speciality_mapping.values())

        department_input.currentIndexChanged.connect(update_specialities)
        update_specialities()  # Заполняем специальности при открытии

        save_button = QPushButton("Сохранить")
        layout.addWidget(save_button)
        dialog.setLayout(layout)

        def save():
            discipline_name = discipline_input.text().strip()
            if not discipline_name:
                QMessageBox.warning(dialog, "Ошибка", "Введите название дисциплины.")
                return

            if not speciality_mapping:
                QMessageBox.warning(dialog, "Ошибка", "Выберите специальность.")
                return

            speciality_id = list(speciality_mapping.keys())[speciality_input.currentIndex()]
            query = "INSERT INTO Discipline (Name, Speciality) VALUES (%s, %s)"
            self.db_manager.execute_query(query, (discipline_name, speciality_id))

            QMessageBox.information(dialog, "Успех", "Дисциплина добавлена.")
            dialog.close()
            self.update_table()

        save_button.clicked.connect(save)
        dialog.exec_()

    def edit_discipline(self):
        selected_row = self.table_widget.currentRow()

        if selected_row == -1:
            QMessageBox.warning(self.table_widget, "Ошибка", "Выберите дисциплину для редактирования.")
            return

        current_department = self.table_widget.item(selected_row, 0).text()
        current_speciality = self.table_widget.item(selected_row, 1).text()
        current_discipline = self.table_widget.item(selected_row, 2).text()

        dialog = QDialog()
        dialog.setWindowTitle("Изменить дисциплину")
        layout = QVBoxLayout()

        # Поля редактирования
        department_label = QLabel("Кафедра:")
        department_input = QComboBox()
        layout.addWidget(department_label)
        layout.addWidget(department_input)

        speciality_label = QLabel("Специальность:")
        speciality_input = QComboBox()
        layout.addWidget(speciality_label)
        layout.addWidget(speciality_input)

        discipline_label = QLabel("Название дисциплины:")
        discipline_input = QLineEdit()
        discipline_input.setText(current_discipline)
        layout.addWidget(discipline_label)
        layout.addWidget(discipline_input)

        # Получаем кафедры
        departments = self.db_manager.execute_query("SELECT id, Name FROM Department")
        department_mapping = {str(dep["id"]): dep["Name"] for dep in departments}
        department_input.addItems(department_mapping.values())

        # Устанавливаем текущую кафедру
        if current_department in department_mapping.values():
            department_input.setCurrentText(current_department)

        # Функция обновления списка специальностей
        def update_specialities():
            speciality_input.clear()
            selected_department_id = list(department_mapping.keys())[department_input.currentIndex()]
            specialities = self.db_manager.execute_query(
                "SELECT id, Name FROM Speciality WHERE Department = %s", (selected_department_id,)
            )
            global speciality_mapping
            speciality_mapping = {str(sp["id"]): sp["Name"] for sp in specialities}
            speciality_input.addItems(speciality_mapping.values())

            # Устанавливаем текущую специальность
            if current_speciality in speciality_mapping.values():
                speciality_input.setCurrentText(current_speciality)

        department_input.currentIndexChanged.connect(update_specialities)
        update_specialities()

        save_button = QPushButton("Сохранить")
        layout.addWidget(save_button)
        dialog.setLayout(layout)

        def save():
            new_discipline_name = discipline_input.text().strip()

            if not new_discipline_name:
                QMessageBox.warning(dialog, "Ошибка", "Введите название дисциплины.")
                return

            if not speciality_mapping:
                QMessageBox.warning(dialog, "Ошибка", "Выберите специальность.")
                return

            speciality_id = list(speciality_mapping.keys())[speciality_input.currentIndex()]

            # Обновление в базе данных
            query_update = "UPDATE Discipline SET Name = %s, Speciality = %s WHERE Name = %s"
            self.db_manager.execute_query(query_update, (new_discipline_name, speciality_id, current_discipline))

            QMessageBox.information(dialog, "Успех", "Дисциплина обновлена.")
            dialog.close()
            self.update_table()

        save_button.clicked.connect(save)
        dialog.exec_()

    def delete_discipline(self):
        selected_row = self.table_widget.currentRow()
        
        if selected_row == -1:
            QMessageBox.warning(self.table_widget, "Ошибка", "Выберите дисциплину для удаления.")
            return

        item = self.table_widget.item(selected_row, 2)
        
        if item is None:
            QMessageBox.warning(self.table_widget, "Ошибка", "Ошибка выбора дисциплины.")
            return

        discipline_name = item.text()

        # Запрашиваем у пользователя ввод названия для подтверждения
        text, ok = QtWidgets.QInputDialog.getText(
            self.table_widget, "Подтверждение удаления",
            f"Введите название дисциплины для подтверждения удаления: {discipline_name}"
        )

        if not ok or text.strip() != discipline_name:
            QMessageBox.warning(self.table_widget, "Ошибка", "Название дисциплины введено неверно. Удаление отменено.")
            return

        confirmation = QMessageBox.question(
            self.table_widget, "Удаление дисциплины",
            f"Вы уверены, что хотите удалить дисциплину '{discipline_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            try:
                # Получаем ID дисциплины
                query_get_id = "SELECT id FROM Discipline WHERE Name = %s"
                result = self.db_manager.execute_query(query_get_id, (discipline_name,))
                
                if not result:
                    QMessageBox.warning(self.table_widget, "Ошибка", "Дисциплина не найдена в базе.")
                    return
                
                discipline_id = result[0]["id"]

                # Выполняем транзакцию удаления
                delete_queries = [
                    "DELETE DA FROM Documents_Access DA JOIN Documents D ON DA.Document = D.id WHERE D.Discipline = %s",
                    "DELETE FROM Documents WHERE Discipline = %s",
                    "DELETE FROM Discipline WHERE id = %s"
                ]

                self.db_manager.start_transaction()
                for query in delete_queries:
                    self.db_manager.execute_query(query, (discipline_id,))
                self.db_manager.commit_transaction()

                QMessageBox.information(self.table_widget, "Успех", "Дисциплина удалена.")
                self.update_table()

            except Exception as e:
                self.db_manager.rollback_transaction()
                QMessageBox.critical(self.table_widget, "Ошибка", f"Ошибка при удалении: {str(e)}")