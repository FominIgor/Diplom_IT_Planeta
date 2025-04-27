from PyQt5.QtWidgets import (
    QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox
)
import logging
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QVBoxLayout, QLabel, QLineEdit, QComboBox,
    QMessageBox, QTableWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import logging

from PyQt5 import QtWidgets
import time  # Добавьте это в начало файла, если его там нет

from pages.TableFilterSort import TableFilterSort #Импорт класса с поиском 

class OPOPManager:
    def __init__(self, table_widget, db_manager):
        """
        Инициализация менеджера для работы с таблицей OPOP_UP_Program.
        :param table_widget: Виджет таблицы для отображения данных.
        :param db_manager: Менеджер базы данных.
        """
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.filter_sort = TableFilterSort(table_widget)  # Интеграция поиска
        self.setup_table()
        self.update_table()

    def setup_table(self):
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels(["ID", "ОПОП", "Учебный план", "Шаблоны", "Специальность"])
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.table_widget.cellClicked.connect(lambda row, col: print("Ячейка нажата!") or self.download_file(row, col))

    def update_table(self):
        try:
            query = "SELECT id, OPOP, Syllabus, Program, Speciality FROM OPOP_UP_Program ORDER BY id LIMIT 100;"
            start_time = time.time()  # Засекаем время перед выполнением запроса
            records = self.db_manager.execute_query(query)
            end_time = time.time()  # Засекаем время после выполнения запроса
            
            print(f"Время выполнения запроса: {end_time - start_time:.4f} секунд")  # Выводим время выполнения
            
            records = self.db_manager.execute_query(query)
            speciality_query = "SELECT id, Name FROM Speciality;"
            specialities = self.db_manager.execute_query(speciality_query)
            speciality_dict = {spec["id"]: spec["Name"] for spec in specialities}

            self.table_widget.setRowCount(len(records))
            for row, record in enumerate(records):
                self.table_widget.setItem(row, 0, QTableWidgetItem(str(record['id'])))
                
                # Для каждого столбца, где есть файлы для скачивания, добавляем кнопку "Скачать"
                if record['OPOP']:
                    button_opop = QPushButton("Скачать")
                    button_opop.setStyleSheet("color: rgb(1, 50, 32)")
                    button_opop.clicked.connect(lambda checked, row=row, col=1: self.download_file(row, col))
                    self.table_widget.setCellWidget(row, 1, button_opop)
                else:
                    self.table_widget.setItem(row, 1, QTableWidgetItem(""))

                if record['Syllabus']:
                    button_syllabus = QPushButton("Скачать")
                    button_syllabus.setStyleSheet("color: rgb(1, 50, 32)")
                    button_syllabus.clicked.connect(lambda checked, row=row, col=2: self.download_file(row, col))
                    self.table_widget.setCellWidget(row, 2, button_syllabus)
                else:
                    self.table_widget.setItem(row, 2, QTableWidgetItem(""))

                if record['Program']:
                    button_program = QPushButton("Скачать")
                    button_program.setStyleSheet("color: rgb(1, 50, 32)")
                    button_program.clicked.connect(lambda checked, row=row, col=3: self.download_file(row, col))
                    self.table_widget.setCellWidget(row, 3, button_program)
                else:
                    self.table_widget.setItem(row, 3, QTableWidgetItem(""))


                speciality_name = speciality_dict.get(record['Speciality'], "Не указано")
                self.table_widget.setItem(row, 4, QTableWidgetItem(speciality_name))

        except Exception as e:
            logging.error(f"Ошибка при обновлении таблицы: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось обновить таблицу: {e}")



    def show_context_menu(self, position):
        """Показывает контекстное меню для таблицы."""
        menu = QtWidgets.QMenu()
        upload_action = menu.addAction("Загрузить")
        delete_action = menu.addAction("Удалить")
        modify_action = menu.addAction("Изменить")

        # Привязка действий к методам
        upload_action.triggered.connect(self.upload_record)
        delete_action.triggered.connect(self.delete_record)
        modify_action.triggered.connect(self.modify_record)

        # Показ меню
        menu.exec_(self.table_widget.viewport().mapToGlobal(position))

    def upload_record(self):
        """Загружает новую запись в таблицу OPOP_UP_Program."""
        try:
            # Открываем диалоговое окно для загрузки файлов
            dialog = QDialog()
            dialog.setWindowTitle("Загрузить данные")
            layout = QVBoxLayout()

            # Кнопки для загрузки файлов
            opop_button = QPushButton("Загрузить ОПОП")
            opop_button.clicked.connect(lambda: self.load_file("OPOP"))
            layout.addWidget(opop_button)

            syllabus_button = QPushButton("Загрузить Учебный план")
            syllabus_button.clicked.connect(lambda: self.load_file("Syllabus"))
            layout.addWidget(syllabus_button)

            program_button = QPushButton("Загрузить Щаблон")
            program_button.clicked.connect(lambda: self.load_file("Program", is_archive=True)) # Архив
            layout.addWidget(program_button)

            # Выпадающий список для выбора специальности
            speciality_label = QLabel("Специальность:")
            self.speciality_combo = QComboBox()
            self.load_specialities()  # Загружаем список специальностей
            layout.addWidget(speciality_label)
            layout.addWidget(self.speciality_combo)

            # Кнопка сохранения
            save_button = QPushButton("Сохранить")
            save_button.clicked.connect(lambda: self.save_record(dialog))
            layout.addWidget(save_button)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            logging.error(f"Ошибка при загрузке записи: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить запись: {e}")

    def load_specialities(self):
        """Загружает список специальностей из базы данных."""
        try:
            query = "SELECT id, Name FROM Speciality"
            specialities = self.db_manager.execute_query(query)
            for spec in specialities:
                self.speciality_combo.addItem(spec["Name"], spec["id"])  # Добавляем название и ID
        except Exception as e:
            logging.error(f"Ошибка при загрузке специальностей: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить специальности: {e}")

    def load_file(self, field_name, is_archive=False):
        """Загружает файл для указанного поля. Проверяет, является ли файл архивом, если это нужно."""
        file_path, _ = QFileDialog.getOpenFileName(self.table_widget, f"Выберите файл для {field_name}", "", "Все файлы (*)")
        
        if file_path:
            # Инициализация переменной file_extension
            file_extension = file_path.split('.')[-1].lower()  # Извлекаем расширение файла
            
            # Если файл должен быть архивом, проверяем его расширение
            if is_archive:
                valid_extensions = ['zip', 'tar', 'rar', '7z']
                if file_extension not in valid_extensions:
                    QMessageBox.warning(self.table_widget, "Ошибка", "Пожалуйста, загрузите файл архив в формате .zip, .tar, .rar или .7z.")
                    return

            # Если файл подходит, сохраняем его данные и расширение
            with open(file_path, 'rb') as file:
                setattr(self, f"{field_name.lower()}_data", file.read())  # Сохраняем бинарные данные
                setattr(self, f"{field_name.lower()}_ext", file_extension)  # Сохраняем расширение файла
                QMessageBox.information(self.table_widget, "Успех", f"Файл для {field_name} успешно загружен.")
        else:
            QMessageBox.warning(self.table_widget, "Ошибка", "Файл не был выбран.")


    def save_record(self, dialog):
        """Сохраняет данные в базу."""
        try:
            speciality_id = self.speciality_combo.currentData()  # Получаем ID выбранной специальности
            if not speciality_id:
                QMessageBox.warning(dialog, "Ошибка", "Выберите специальность.")
                return

            # Проверяем, что все файлы загружены
            if not hasattr(self, "opop_data") or not hasattr(self, "syllabus_data") or not hasattr(self, "program_data"):
                QMessageBox.warning(dialog, "Ошибка", "Все файлы должны быть загружены.")
                return

            # SQL-запрос для добавления записи
            query = """
                INSERT INTO OPOP_UP_Program (OPOP, Syllabus, Program, Speciality, OPOP_ext, Syllabus_ext, Program_ext)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.db_manager.execute_query(query, (
                self.opop_data,  # Бинарные данные ОПОП
                self.syllabus_data,  # Бинарные данные Учебного плана
                self.program_data,  # Бинарные данные Программы
                speciality_id,  # ID специальности
                getattr(self, "opop_ext", ""),  # Расширение для ОПОП
                getattr(self, "syllabus_ext", ""),  # Расширение для учебного плана
                getattr(self, "program_ext", "")  # Расширение для программы
            ))
            QMessageBox.information(dialog, "Успех", "Запись успешно добавлена.")
            dialog.close()
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при сохранении записи: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить запись: {e}")

    def delete_record(self):
        """Удаляет выбранную запись из таблицы OPOP_UP_Program."""
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self.table_widget, "Ошибка", "Выберите запись для удаления.")
                return

            record_id = self.table_widget.item(selected_row, 0).text()  # Получаем ID записи
            query = "DELETE FROM OPOP_UP_Program WHERE id = %s"
            self.db_manager.execute_query(query, (record_id,))
            QMessageBox.information(self.table_widget, "Успех", "Запись успешно удалена.")
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при удалении записи: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось удалить запись: {e}")

    def modify_record(self):
        """Изменяет выбранную запись в таблице OPOP_UP_Program."""
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self.table_widget, "Ошибка", "Выберите запись для изменения.")
                return

            record_id = self.table_widget.item(selected_row, 0).text()  # Получаем ID записи

            # Открываем диалоговое окно для изменения данных
            dialog = QDialog()
            dialog.setWindowTitle("Изменить данные")
            layout = QVBoxLayout()

            # Кнопки для загрузки файлов
            opop_button = QPushButton("Изменить ОПОП")
            opop_button.clicked.connect(lambda: self.load_file("OPOP"))
            layout.addWidget(opop_button)

            syllabus_button = QPushButton("Изменить Учебный план")
            syllabus_button.clicked.connect(lambda: self.load_file("Syllabus"))
            layout.addWidget(syllabus_button)

            program_button = QPushButton("Изменить шаблон")
            program_button.clicked.connect(lambda: self.load_file("Program",is_archive=True)) #Архив
            layout.addWidget(program_button)

            # Выпадающий список для выбора специальности
            speciality_label = QLabel("Специальность:")
            self.speciality_combo = QComboBox()
            self.load_specialities()  # Загружаем список специальностей
            layout.addWidget(speciality_label)
            layout.addWidget(self.speciality_combo)

            # Кнопка сохранения
            save_button = QPushButton("Сохранить")
            save_button.clicked.connect(lambda: self.save_modified_record(dialog, record_id))
            layout.addWidget(save_button)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            logging.error(f"Ошибка при изменении записи: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось изменить запись: {e}")

    def save_modified_record(self, dialog, record_id):
        """Сохраняет измененные данные в базу."""
        try:
            speciality_id = self.speciality_combo.currentData()  # Получаем ID выбранной специальности
            if not speciality_id:
                QMessageBox.warning(dialog, "Ошибка", "Выберите специальность.")
                return

            # Проверяем, что все файлы загружены
            if not hasattr(self, "opop_data") or not hasattr(self, "syllabus_data") or not hasattr(self, "program_data"):
                QMessageBox.warning(dialog, "Ошибка", "Все файлы должны быть загружены.")
                return

            # SQL-запрос для обновления записи
            query = """
                UPDATE OPOP_UP_Program
                SET OPOP = %s, Syllabus = %s, Program = %s, Speciality = %s, 
                    OPOP_ext = %s, Syllabus_ext = %s, Program_ext = %s
                WHERE id = %s
            """
            self.db_manager.execute_query(query, (
                self.opop_data,  # Бинарные данные ОПОП
                self.syllabus_data,  # Бинарные данные Учебного плана
                self.program_data,  # Бинарные данные Программы
                speciality_id,  # ID специальности
                getattr(self, "opop_ext", ""),  # Расширение для ОПОП
                getattr(self, "syllabus_ext", ""),  # Расширение для учебного плана
                getattr(self, "program_ext", ""),  # Расширение для программы
                record_id  # ID записи
            ))
            QMessageBox.information(dialog, "Успех", "Запись успешно изменена.")
            dialog.close()
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при сохранении изменений: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось сохранить изменения: {e}")

    def download_file(self, row, column):
        print(f"Клик по ячейке: row={row}, column={column}")  # Отладка

        # Проверяем, есть ли в ячейке кнопка
        button = self.table_widget.cellWidget(row, column)
        if not isinstance(button, QPushButton):  # Проверяем, действительно ли это кнопка
            print("Не кнопка 'Скачать'")  # Отладка
            return

        try:
            column_mapping = {
                1: "OPOP",
                2: "Syllabus",
                3: "Program"
            }
            column_name_mapping = {
                1: "ОПОП",
                2: "Учебный план",
                3: "Шаблоны"
            }

            if column not in column_mapping:
                return

            column_name = column_mapping[column]
            display_name = column_name_mapping[column]
            record_id = self.table_widget.item(row, 0).text()  # Получаем ID записи

            query = f"SELECT {column_name}, {column_name}_ext FROM OPOP_UP_Program WHERE id = %s"
            result = self.db_manager.execute_query(query, (record_id,))

            if result and result[0][column_name]:
                file_data = result[0][column_name]
                file_extension = result[0].get(f"{column_name}_ext", "bin")  

                file_path, _ = QFileDialog.getSaveFileName(
                    self.table_widget, 
                    "Сохранить файл", 
                    f"{display_name}.{file_extension}",
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
