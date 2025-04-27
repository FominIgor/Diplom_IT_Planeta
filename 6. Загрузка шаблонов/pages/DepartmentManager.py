from PyQt5 import QtWidgets
import logging
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QComboBox, QMessageBox, QMenu, QAction, QVBoxLayout,
    QInputDialog, QLabel, QLineEdit,QAbstractItemView
)
from PyQt5.QtCore import Qt
from pages.TableFilterSort import TableFilterSort #Импорт класса с поиском 


class DepartmentManager:
    def __init__(self, table_widget, db_manager):
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.filter_sort = TableFilterSort(table_widget)  # Интеграция поиска
        self.setup_table()
        self.update_table()

    def setup_table(self):
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["ID", "Название", "Руководитель"])
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            # Включаем сортировку по столбцам
        self.table_widget.setSortingEnabled(True)
        self.table_widget.sortByColumn(3, Qt.AscendingOrder)  # Сортировка по проценту, по возрастанию

        # Запрещаем редактирование данных
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)
    
    def update_table(self):
        self.table_widget.setRowCount(0)
        query = """
            SELECT Department.id, Department.Name, Users.Full_name
            FROM Department
            LEFT JOIN Users ON Department.Head_of_the_department = Users.id
        """
        rows = self.db_manager.execute_query(query)
        for row in rows:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)
            for col_idx, col_name in enumerate(["id", "Name", "Full_name"]):
                item = QTableWidgetItem(str(row[col_name]))
                self.table_widget.setItem(row_position, col_idx, item)

    def show_context_menu(self, position):
        menu = QMenu()
        add_action = menu.addAction("Добавить")
        delete_action = menu.addAction("Удалить")
        modify_action = menu.addAction("Изменить")
        
        add_action.triggered.connect(self.add_department)
        delete_action.triggered.connect(self.delete_department)
        modify_action.triggered.connect(self.modify_department)
        
        menu.exec_(self.table_widget.viewport().mapToGlobal(position))

    def add_department(self):
        self.show_department_dialog("Добавить кафедру")

    def modify_department(self):
        selected_row = self.table_widget.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self.table_widget, "Ошибка", "Выберите кафедру для изменения.")
            return
        
        record_id = self.table_widget.item(selected_row, 0).text()
        current_name = self.table_widget.item(selected_row, 1).text()
        current_head_id = self.db_manager.execute_query(
            "SELECT Head_of_the_department FROM Department WHERE id = %s", (record_id,)
        )[0]["Head_of_the_department"]
        self.show_department_dialog("Изменить кафедру", record_id, current_name, current_head_id)

    def show_department_dialog(self, title, department_id=None, current_name="", current_head_id=None):
        dialog = QDialog()
        dialog.setWindowTitle(title)
        layout = QVBoxLayout()

        name_label = QLabel("Название:")
        name_input = QLineEdit()
        name_input.setText(current_name)
        layout.addWidget(name_label)
        layout.addWidget(name_input)
        
        head_label = QLabel("Руководитель:")
        head_input = QComboBox()
        layout.addWidget(head_label)
        layout.addWidget(head_input)
        
        # Получаем список всех пользователей, которые не являются заведующими кафедрой
        users = self.db_manager.execute_query("SELECT id, Full_name FROM Users WHERE Head_of_the_department = 0")
        user_mapping = {str(user['id']): user['Full_name'] for user in users}
        
        head_input.addItems(user_mapping.values())
        
        # Если текущий руководитель указан и его ID есть в списке пользователей, выбираем его
        if current_head_id and str(current_head_id) in user_mapping:
            head_input.setCurrentIndex(list(user_mapping.keys()).index(str(current_head_id)))
        else:
            # Если текущий руководитель не найден в списке, устанавливаем первый элемент как выбранный
            head_input.setCurrentIndex(0)
        
        save_button = QPushButton("Сохранить")
        layout.addWidget(save_button)
        dialog.setLayout(layout)
        
        def save():
            name = name_input.text().strip()
            new_head_id = list(user_mapping.keys())[head_input.currentIndex()]
            
            if not name:
                QMessageBox.warning(dialog, "Ошибка", "Введите название кафедры.")
                return
            
            if department_id:
                query = "UPDATE Department SET Name = %s, Head_of_the_department = %s WHERE id = %s"
                params = (name, new_head_id, department_id)
                self.db_manager.execute_query(query, params)
                
                # Сбросить статус руководителя у старого завкафедрой
                if current_head_id and current_head_id != new_head_id:
                    self.db_manager.execute_query("UPDATE Users SET Head_of_the_department = 0 WHERE id = %s", (current_head_id,))
            else:
                query = "INSERT INTO Department (Name, Head_of_the_department) VALUES (%s, %s)"
                params = (name, new_head_id)
                self.db_manager.execute_query(query, params)
            
            # Назначить нового руководителя
            self.db_manager.execute_query("UPDATE Users SET Head_of_the_department = 1 WHERE id = %s", (new_head_id,))
            
            QMessageBox.information(dialog, "Успех", "Кафедра сохранена.")
            dialog.close()
            self.update_table()
        
        save_button.clicked.connect(save)
        dialog.exec_()



    def delete_department(self):
        selected_row = self.table_widget.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self.table_widget, "Ошибка", "Выберите кафедру для удаления.")
            return

        record_id = self.table_widget.item(selected_row, 0).text()
        department_name = self.table_widget.item(selected_row, 1).text()

        # Получаем ID текущего руководителя кафедры
        head_query = "SELECT Head_of_the_department FROM Department WHERE id = %s"
        head_result = self.db_manager.execute_query(head_query, (record_id,))
        
        if head_result and head_result[0]["Head_of_the_department"]:
            current_head_id = head_result[0]["Head_of_the_department"]

            # Сбрасываем статус "завкафедрой" у текущего руководителя
            reset_head_query = "UPDATE Users SET Head_of_the_department = 0 WHERE id = %s"
            self.db_manager.execute_query(reset_head_query, (current_head_id,))

        # Подтверждение удаления
        confirmation = QMessageBox.warning(
            self.table_widget, "Удаление кафедры",
            "Все связанные данные (специальности, программы, документы) будут удалены!\n"
            "Введите название кафедры для подтверждения удаления.",
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if confirmation == QMessageBox.Ok:
            text, ok = QInputDialog.getText(
                self.table_widget, "Подтверждение удаления",
                f"Введите название кафедры для удаления:\n\n {department_name}"
            )

            if ok and text.strip() == department_name:
                try:
                    # Отключаем проверки внешних ключей
                    self.db_manager.execute_query("SET FOREIGN_KEY_CHECKS=0", ())

                    # Удаляем доступы к документам
                    delete_doc_access_query = """
                        DELETE FROM Documents_Access 
                        WHERE Document IN (SELECT id FROM Documents WHERE Head_of_the_department = %s)
                    """
                    self.db_manager.execute_query(delete_doc_access_query, (record_id,))

                    # Удаляем все документы, связанные с кафедрой
                    delete_docs_query = """
                        DELETE FROM Documents 
                        WHERE Head_of_the_department = %s
                    """
                    self.db_manager.execute_query(delete_docs_query, (record_id,))

                    # Удаляем образовательные программы
                    delete_opop_query = """
                        DELETE FROM OPOP_UP_Program
                        WHERE Speciality IN (
                            SELECT id FROM Speciality WHERE Department = %s
                        )
                    """
                    self.db_manager.execute_query(delete_opop_query, (record_id,))

                    # Удаляем дисциплины, привязанные к специальностям кафедры
                    delete_disciplines_query = """
                        DELETE FROM Discipline 
                        WHERE Speciality IN (
                            SELECT id FROM Speciality WHERE Department = %s
                        )
                    """
                    self.db_manager.execute_query(delete_disciplines_query, (record_id,))

                    # Удаляем специальности, относящиеся к кафедре
                    delete_specialities_query = "DELETE FROM Speciality WHERE Department = %s"
                    self.db_manager.execute_query(delete_specialities_query, (record_id,))

                    # Удаляем саму кафедру
                    delete_department_query = "DELETE FROM Department WHERE id = %s"
                    self.db_manager.execute_query(delete_department_query, (record_id,))

                    # Включаем проверки внешних ключей обратно
                    self.db_manager.execute_query("SET FOREIGN_KEY_CHECKS=1", ())

                    QMessageBox.information(self.table_widget, "Успех", "Кафедра и связанные данные удалены.")
                    self.update_table()
                except Exception as e:
                    QMessageBox.critical(self.table_widget, "Ошибка", f"Ошибка при удалении: {str(e)}")
            else:
                QMessageBox.warning(self.table_widget, "Ошибка", "Неправильное название. Удаление отменено.")
