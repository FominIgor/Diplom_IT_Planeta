import os
from PyQt5.QtWidgets import (
    QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidgetItem, QHeaderView
)
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
import logging
import datetime
from pages.TableFilterSort import TableFilterSort #Импорт класса с поиском 


class DocumentManager:
    def __init__(self, table_widget, db_manager, teacher_id):
        """
        Инициализация менеджера для работы с таблицей Documents.
        :param table_widget: Виджет таблицы для отображения данных.
        :param db_manager: Менеджер базы данных.
        :param teacher_id: Идентификатор текущего пользователя (преподавателя).
        """
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.teacher_id = teacher_id
        self.filter_sort = TableFilterSort(table_widget)  # Интеграция поиска

        # Для хранения дополнительных материалов (загружаемых при желании)
        self.additional_materials_data = None
        self.additional_materials_filename = None
        
        self.setup_table()
        self.update_table()

    def setup_table(self):
        """Настройка таблицы для отображения документов."""
        # Здесь можно оставить число столбцов таким, какое нужно отображать в таблице
        # Например, оставляем 11 столбцов как в предыдущем варианте
        self.table_widget.setColumnCount(11)
        self.table_widget.setHorizontalHeaderLabels([
            "ID", "Дисциплина", "Статус выполнения", "Дата обновления", "Кафедра", "Преподаватель", 
            "Приоритет исполнения", "Комментарий", "Файл (без печати)", "Файл с печатью", "Дополнительные материалы"
        ])
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.table_widget.cellDoubleClicked.connect(self.download_file)

    def show_context_menu(self, position):
        """Отображает контекстное меню для работы с документами."""
        menu = QtWidgets.QMenu()
        add_action = menu.addAction("Добавить")
        delete_action = menu.addAction("Удалить")
        modify_action = menu.addAction("Изменить")
        add_action.triggered.connect(self.add_record)
        delete_action.triggered.connect(self.delete_record)
        modify_action.triggered.connect(self.modify_record)
        menu.exec_(self.table_widget.viewport().mapToGlobal(position))

    def add_record(self):
        """
        Добавление нового документа.
        Пользователю предлагается указать:
          - Дисциплину
          - Кафедру
          - Приоритет исполнения
          - Дополнительные материалы (при желании)
        Остальные поля устанавливаются по умолчанию.
        """
        dialog = QDialog()
        dialog.setWindowTitle("Добавить документ")
        layout = QVBoxLayout()

        # Выбор дисциплины
        discipline_label = QLabel("Дисциплина:")
        self.discipline_combo = QComboBox()
        self.load_disciplines()
        layout.addWidget(discipline_label)
        layout.addWidget(self.discipline_combo)

        # Выбор кафедры
        dept_label = QLabel("Кафедра:")
        self.dept_combo = QComboBox()
        self.load_departments()
        layout.addWidget(dept_label)
        layout.addWidget(self.dept_combo)

        # Ввод приоритета исполнения
        priority_label = QLabel("Приоритет исполнения:")
        self.priority_input = QLineEdit()
        layout.addWidget(priority_label)
        layout.addWidget(self.priority_input)

        # Кнопка для загрузки дополнительных материалов (необязательно)
        additional_button = QPushButton("Загрузить дополнительные материалы (необязательно)")
        additional_button.clicked.connect(lambda: self.load_file("additional"))
        layout.addWidget(additional_button)

        # Кнопка сохранения
        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(lambda: self.save_record(dialog))
        layout.addWidget(save_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def load_disciplines(self):
        """Загружает список дисциплин из базы данных."""
        try:
            query = "SELECT id, Name FROM Discipline"
            disciplines = self.db_manager.execute_query(query)
            self.discipline_combo.clear()
            for disc in disciplines:
                self.discipline_combo.addItem(disc["Name"], disc["id"])
        except Exception as e:
            logging.error(f"Ошибка при загрузке дисциплин: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить дисциплины: {e}")

    def load_departments(self):
        """Загружает список кафедр из базы данных."""
        try:
            query = "SELECT id, Name FROM Department"
            departments = self.db_manager.execute_query(query)
            self.dept_combo.clear()
            for dept in departments:
                self.dept_combo.addItem(dept["Name"], dept["id"])
        except Exception as e:
            logging.error(f"Ошибка при загрузке кафедр: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить кафедры: {e}")

    def load_file(self, file_type):
        """
        Загружает файл и сохраняет его данные и имя.
        :param file_type: В данном случае используется только для дополнительных материалов.
        """
        file_path, _ = QFileDialog.getOpenFileName(self.table_widget, f"Выберите файл для {file_type}", "", "Все файлы (*)")
        if file_path:
            try:
                with open(file_path, 'rb') as file:
                    data = file.read()
                filename = os.path.basename(file_path)
                if file_type == "additional":
                    self.additional_materials_data = data
                    self.additional_materials_filename = filename
            except Exception as e:
                logging.error(f"Ошибка при загрузке файла: {e}")
                QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить файл: {e}")

    def save_record(self, dialog):
        """
        Сохраняет новый документ.
        Устанавливаются следующие значения:
          - Дисциплина, кафедра и приоритет – введены пользователем.
          - Дополнительные материалы – загружаются при желании (иначе NULL).
          - Статус выполнения устанавливается по умолчанию (например, 1 – «Создан»).
          - Файлы (без печати и с печатью) остаются NULL.
          - Комментарий – пустая строка.
        """
        try:
            discipline_id = self.discipline_combo.currentData()
            department_id = self.dept_combo.currentData()
            priority = self.priority_input.text().strip()
            date_of_update = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            teacher_id = self.teacher_id

            # Устанавливаем значения по умолчанию:
            default_status_id = 1  # например, статус "Создан"
            comment = ""
            query = """
                INSERT INTO Documents (
                    Discipline, Execution_Status, File_without_printing, File_with_stamp,
                    Date_of_last_update, Head_of_the_department, Teacher, Execution_priority,
                    Additional_materials, Comment
                )
                VALUES (%s, %s, NULL, NULL, %s, %s, NULL, %s, %s, %s)
            """
            params = (
                discipline_id,
                default_status_id,
                date_of_update,
                department_id,
                priority,
                self.additional_materials_data,  # может быть None, если материал не загружен
                comment
            )

            self.db_manager.execute_query(query, params)
            QMessageBox.information(dialog, "Успех", "Документ успешно добавлен.")
            dialog.close()
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при сохранении документа: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить документ: {e}")

    def delete_record(self):
        """Удаляет выбранную запись документа."""
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self.table_widget, "Ошибка", "Выберите запись для удаления.")
                return

            record_id = self.table_widget.item(selected_row, 0).text()
            query = "DELETE FROM Documents WHERE id = %s"
            self.db_manager.execute_query(query, (record_id,))
            QMessageBox.information(self.table_widget, "Успех", "Документ удалён.")
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при удалении документа: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось удалить документ: {e}")

    def modify_record(self):
        """Изменяет выбранную запись документа (реализуйте по аналогии, если требуется)."""
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self.table_widget, "Ошибка", "Выберите запись для изменения.")
                return

            record_id = self.table_widget.item(selected_row, 0).text()
            dialog = QDialog()
            dialog.setWindowTitle("Изменить документ")
            layout = QVBoxLayout()

            # Для примера предлагается редактировать дисциплину, кафедру и приоритет
            discipline_label = QLabel("Дисциплина:")
            self.discipline_combo = QComboBox()
            self.load_disciplines()
            layout.addWidget(discipline_label)
            layout.addWidget(self.discipline_combo)

            dept_label = QLabel("Кафедра:")
            self.dept_combo = QComboBox()
            self.load_departments()
            layout.addWidget(dept_label)
            layout.addWidget(self.dept_combo)

            priority_label = QLabel("Приоритет исполнения:")
            self.priority_input = QLineEdit()
            layout.addWidget(priority_label)
            layout.addWidget(self.priority_input)

            additional_button = QPushButton("Изменить дополнительные материалы")
            additional_button.clicked.connect(lambda: self.load_file("additional"))
            layout.addWidget(additional_button)

            save_button = QPushButton("Сохранить изменения")
            save_button.clicked.connect(lambda: self.save_modified_record(dialog, record_id))
            layout.addWidget(save_button)

            dialog.setLayout(layout)
            dialog.exec_()
        except Exception as e:
            logging.error(f"Ошибка при изменении документа: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось изменить документ: {e}")

    def save_modified_record(self, dialog, record_id):
        """Сохраняет изменения документа в базе данных."""
        try:
            discipline_id = self.discipline_combo.currentData()
            department_id = self.dept_combo.currentData()
            priority = self.priority_input.text().strip()
            date_of_update = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            teacher_id = self.teacher_id
            comment = ""  # либо можно добавить поле для комментария

            query = """
                UPDATE Documents
                SET Discipline = %s,
                    Date_of_last_update = %s,
                    Head_of_the_department = %s,
                    Teacher = %s,
                    Execution_priority = %s,
                    Additional_materials = %s,
                    Comment = %s
                WHERE id = %s
            """
            params = (
                discipline_id,
                date_of_update,
                department_id,
                teacher_id,
                priority,
                self.additional_materials_data,
                comment,
                record_id
            )
            self.db_manager.execute_query(query, params)
            QMessageBox.information(dialog, "Успех", "Документ изменён.")
            dialog.close()
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при сохранении изменений документа: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить изменения: {e}")

    def download_file(self, row, column):
        """
        Скачивает файл из ячейки, если она содержит информацию о файле.
        Для каждого файла используется своё сохранённое имя (если имеется) в качестве имени по умолчанию.
        Столбцы для скачивания:
          - 8: Файл (без печати)
          - 9: Файл с печатью
          - 10: Дополнительные материалы
        """
        try:
            default_filename = None
            field_name = None
            if column == 8:
                field_name = "File_without_printing"
                default_filename = "file_without_printing"
            elif column == 9:
                field_name = "File_with_stamp"
                default_filename = "file_with_stamp"
            elif column == 10:
                field_name = "Additional_materials"
                default_filename = self.additional_materials_filename if self.additional_materials_filename else "additional_materials"
            else:
                return

            item = self.table_widget.item(row, column)
            if not item or item.text() != "Скачать":
                return

            record_id = self.table_widget.item(row, 0).text()
            query = f"SELECT {field_name} FROM Documents WHERE id = %s"
            result = self.db_manager.execute_query(query, (record_id,))
            if result and result[0][field_name]:
                file_data = result[0][field_name]
                file_path, _ = QFileDialog.getSaveFileName(
                    self.table_widget,
                    f"Сохранить {field_name}",
                    default_filename,
                    "Все файлы (*)"
                )
                if file_path:
                    with open(file_path, 'wb') as file:
                        file.write(file_data)
                    QMessageBox.information(self.table_widget, "Успех", f"Файл успешно скачан: {file_path}")
            else:
                QMessageBox.warning(self.table_widget, "Ошибка", "Файл отсутствует в базе данных.")
        except Exception as e:
            logging.error(f"Ошибка при скачивании файла: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось скачать файл: {e}")

    def update_table(self):
        """Обновляет данные в таблице документов и отображает все столбцы."""
        try:
            self.table_widget.setRowCount(0)
            query = """
                SELECT d.id, 
                       (SELECT Name FROM Discipline WHERE id = d.Discipline) AS Discipline,
                       (SELECT Status FROM Execution_Status WHERE id = d.Execution_Status) AS Status,
                       d.Date_of_last_update,
                       (SELECT Name FROM Department WHERE id = d.Head_of_the_department) AS Department,
                       (SELECT Full_name FROM Users WHERE id = d.Teacher) AS Teacher,
                       d.Execution_priority,
                       d.Comment,
                       d.File_without_printing,
                       d.File_with_stamp,
                       d.Additional_materials
                FROM Documents d
            """
            rows = self.db_manager.execute_query(query)
            for row in rows:
                row_position = self.table_widget.rowCount()
                self.table_widget.insertRow(row_position)
                self.table_widget.setItem(row_position, 0, QTableWidgetItem(str(row["id"])))
                self.table_widget.setItem(row_position, 1, QTableWidgetItem(str(row["Discipline"])))
                self.table_widget.setItem(row_position, 2, QTableWidgetItem(str(row["Status"])))
                self.table_widget.setItem(row_position, 3, QTableWidgetItem(str(row["Date_of_last_update"])))
                self.table_widget.setItem(row_position, 4, QTableWidgetItem(str(row["Department"])))
                self.table_widget.setItem(row_position, 5, QTableWidgetItem(str(row["Teacher"])))
                self.table_widget.setItem(row_position, 6, QTableWidgetItem(str(row["Execution_priority"])))
                self.table_widget.setItem(row_position, 7, QTableWidgetItem(str(row["Comment"])))
                # Столбец 8 - Файл (без печати)
                if row["File_without_printing"]:
                    item = QTableWidgetItem("Скачать")
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                else:
                    item = QTableWidgetItem("Нет файла")
                self.table_widget.setItem(row_position, 8, item)
                # Столбец 9 - Файл с печатью
                if row["File_with_stamp"]:
                    item = QTableWidgetItem("Скачать")
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                else:
                    item = QTableWidgetItem("Нет файла")
                self.table_widget.setItem(row_position, 9, item)
                # Столбец 10 - Дополнительные материалы
                if row["Additional_materials"]:
                    item = QTableWidgetItem("Скачать")
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                else:
                    item = QTableWidgetItem("Нет файла")
                self.table_widget.setItem(row_position, 10, item)
        except Exception as e:
            logging.error(f"Ошибка при обновлении таблицы документов: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось обновить таблицу: {e}")
