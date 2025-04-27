from PyQt5 import QtWidgets

import logging
from PyQt5.QtWidgets import (
   QTableWidgetItem, QHeaderView, QPushButton, QDialog, QComboBox, QMessageBox, QMenu, QAction, QVBoxLayout,
   QInputDialog, QLabel, QLineEdit

)
from PyQt5.QtCore import Qt
from pages.TableFilterSort import TableFilterSort


class SpecialityManager:
   def __init__(self, table_widget, db_manager):
       """
       Инициализация менеджера для работы с таблицей Speciality.
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
       self.table_widget.setColumnCount(3)  # id, Name, Department
       self.table_widget.setHorizontalHeaderLabels(["ID", "Название", "Кафедра"])
       self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
       self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
      
       self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
       self.table_widget.customContextMenuRequested.connect(self.show_context_menu)
   
   def show_context_menu(self, position):
       """Показывает контекстное меню для таблицы."""
       menu = QtWidgets.QMenu()
       add_action = menu.addAction("Добавить")
       delete_action = menu.addAction("Удалить")
       modify_action = menu.addAction("Изменить")


       add_action.triggered.connect(self.add_speciality)
       delete_action.triggered.connect(self.delete_speciality)
       modify_action.triggered.connect(self.modify_speciality)


       menu.exec_(self.table_widget.viewport().mapToGlobal(position))


   def add_speciality(self):
       """Добавляет новую специальность."""
       dialog = QDialog()
       dialog.setWindowTitle("Добавить специальность")
       layout = QVBoxLayout()
      
       name_label = QLabel("Название:")
       self.name_input = QLineEdit()
       layout.addWidget(name_label)
       layout.addWidget(self.name_input)
      
       department_label = QLabel("Кафедра:")
       self.department_combo = QComboBox()
       self.load_departments()
       layout.addWidget(department_label)
       layout.addWidget(self.department_combo)
      
       save_button = QPushButton("Сохранить")
       save_button.clicked.connect(lambda: self.save_speciality(dialog))
       layout.addWidget(save_button)
      
       dialog.setLayout(layout)
       dialog.exec_()


   def load_departments(self):
       """Загружает список кафедр из базы данных."""
       query = "SELECT id, Name FROM Department"
       departments = self.db_manager.execute_query(query)
       for dept in departments:
           self.department_combo.addItem(dept["Name"], dept["id"])


   def save_speciality(self, dialog):
       """Сохраняет новую специальность в базу данных."""
       name = self.name_input.text().strip()
       department_id = self.department_combo.currentData()
       if not name:
           QMessageBox.warning(dialog, "Ошибка", "Введите название специальности.")
           return
      
       query = "INSERT INTO Speciality (Name, Department) VALUES (%s, %s)"
       self.db_manager.execute_query(query, (name, department_id))
       QMessageBox.information(dialog, "Успех", "Специальность добавлена.")
       dialog.close()
       self.update_table()


   def delete_speciality(self):
        """Удаляет выбранную специальность после подтверждения с вводом названия."""
        selected_row = self.table_widget.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self.table_widget, "Ошибка", "Выберите специальность для удаления.")
            return

        record_id = self.table_widget.item(selected_row, 0).text()
        speciality_name = self.table_widget.item(selected_row, 1).text()

        # Предупреждение о связанных данных
        confirmation_msg = QMessageBox()
        confirmation_msg.setIcon(QMessageBox.Warning)
        confirmation_msg.setText("Внимание!")
        confirmation_msg.setInformativeText(
            "Все документы и связанные с ними записи будут удалены. "
            "Нажмите OK для подтверждения."
        )
        confirmation_msg.setWindowTitle("Подтверждение удаления")
        confirmation_msg.addButton(QMessageBox.Ok)
        confirmation_msg.addButton(QMessageBox.Cancel)

        if confirmation_msg.exec_() == QMessageBox.Ok:
            # Запрос ввода названия специальности
            text, ok = QInputDialog.getText(
                self.table_widget, "Подтверждение удаления",
                f"Введите название специальности для подтверждения удаления:\n\n {speciality_name}"
            )

            if ok and text.strip() == speciality_name:
                try:
                    # Удаление документов, связанных с этой специальностью через OPOP_UP_Program
                    delete_docs_query = """
                        DELETE FROM Documents
                        WHERE id IN (
                            SELECT Documents.id FROM Documents
                            JOIN OPOP_UP_Program ON Documents.Discipline = OPOP_UP_Program.Speciality
                            WHERE OPOP_UP_Program.Speciality = %s
                        )
                    """
                    self.db_manager.execute_query(delete_docs_query, (record_id,))

                    # Удаление записей из OPOP_UP_Program
                    delete_opop_query = """
                        DELETE FROM OPOP_UP_Program
                        WHERE Speciality = %s
                    """
                    self.db_manager.execute_query(delete_opop_query, (record_id,))

                    # Удаление специальности
                    delete_speciality_query = "DELETE FROM Speciality WHERE id = %s"
                    self.db_manager.execute_query(delete_speciality_query, (record_id,))

                    QMessageBox.information(self.table_widget, "Успех", "Специальность и связанные с ней данные удалены.")
                    self.update_table()
                except Exception as e:
                    QMessageBox.critical(self.table_widget, "Ошибка", f"Ошибка при удалении: {str(e)}")
            else:
                QMessageBox.warning(self.table_widget, "Ошибка", "Неправильное название. Удаление отменено.")



   def modify_speciality(self):
       """Изменяет выбранную специальность."""
       selected_row = self.table_widget.currentRow()
       if selected_row == -1:
           QMessageBox.warning(self.table_widget, "Ошибка", "Выберите специальность для изменения.")
           return
      
       record_id = self.table_widget.item(selected_row, 0).text()
       current_name = self.table_widget.item(selected_row, 1).text()
      
       dialog = QDialog()
       dialog.setWindowTitle("Изменить специальность")
       layout = QVBoxLayout()
      
       name_label = QLabel("Название:")
       self.name_input = QLineEdit()
       self.name_input.setText(current_name)
       layout.addWidget(name_label)
       layout.addWidget(self.name_input)
      
       department_label = QLabel("Кафедра:")
       self.department_combo = QComboBox()
       self.load_departments()
       layout.addWidget(department_label)
       layout.addWidget(self.department_combo)
      
       save_button = QPushButton("Сохранить")
       save_button.clicked.connect(lambda: self.save_modified_speciality(dialog, record_id))
       layout.addWidget(save_button)
      
       dialog.setLayout(layout)
       dialog.exec_()


   def save_modified_speciality(self, dialog, record_id):
       """Сохраняет изменения специальности в базе данных."""
       name = self.name_input.text().strip()
       department_id = self.department_combo.currentData()
       if not name:
           QMessageBox.warning(dialog, "Ошибка", "Введите название специальности.")
           return
      
       query = "UPDATE Speciality SET Name = %s, Department = %s WHERE id = %s"
       self.db_manager.execute_query(query, (name, department_id, record_id))
       QMessageBox.information(dialog, "Успех", "Специальность изменена.")
       dialog.close()
       self.update_table()


   def update_table(self):
       """Обновляет данные в таблице."""
       self.table_widget.setRowCount(0)
       query = """
           SELECT Speciality.id, Speciality.Name, Department.Name AS Department
           FROM Speciality
           JOIN Department ON Speciality.Department = Department.id
       """
       rows = self.db_manager.execute_query(query)
       for row in rows:
           row_position = self.table_widget.rowCount()
           self.table_widget.insertRow(row_position)
          
           # Выводим полные данные
           for col_idx, col_name in enumerate(["id", "Name", "Department"]):
               item = QTableWidgetItem(str(row[col_name]))
               self.table_widget.setItem(row_position, col_idx, item)