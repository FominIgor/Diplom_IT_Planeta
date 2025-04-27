from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QComboBox, 
    QMessageBox, QFileDialog, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import logging
import os
import datetime
from pages.TableFilterSort import TableFilterSort #Импорт класса с поиском 

class AvailableDocuments:
    def __init__(self, table_widget, db_manager, user_id):
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.user_id = user_id
        self.filter_sort = TableFilterSort(table_widget)  # Интеграция поиска
        self.setup_table()
        self.fetch_data_from_db()

    def setup_table(self):
        """Настройка таблицы."""
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(12)  # 11 колонок
        self.table_widget.setHorizontalHeaderLabels([
            "id документа", "Название документа", "Кафедра", "Дисциплина", "Специальность", 
            "Статус выполнения", "Файл без печати", "Файл с печатью", "Дата последнего обновления", 
            "Приоритет выполнения", "Дополнительные материалы", "Комментарий"
        ])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.cellDoubleClicked.connect(self.show_document_details)  # Подключение двойного клика

    def show_document_details(self, row, col):
        """Показать детали документа."""
        item = self.table_widget.item(row, 0)  # Получаем элемент из ячейки
        if item is None:
            QMessageBox.warning(self.table_widget, "Ошибка", "Документ не найден в таблице.")
            return

        document_id = item.text()  # Получаем ID документа

        # Вторичный запрос для получения деталей документа по id
        query = """
            SELECT 
                d.id AS "id документа",
                dis.Name AS "Название документа",
                dep.Name AS "Кафедра",
                dis.Name AS "Дисциплина",
                s.Name AS "Специальность",
                es.Status AS "Статус выполнения",
                d.File_without_printing,
                d.File_with_stamp,
                d.Date_of_last_update,
                d.Execution_priority,
                d.Additional_materials,
                d.Comment
            FROM 
                Documents d
            JOIN 
                Discipline dis ON d.Discipline = dis.id
            JOIN 
                Department dep ON dis.Speciality = dep.id
            JOIN 
                Speciality s ON dis.Speciality = s.id
            JOIN 
                Execution_Status es ON d.Execution_Status = es.id
            WHERE 
                d.id = %s
            LIMIT 1;
        """

        result = self.db_manager.execute_query(query, (document_id,))

        if result:
            document_data = result[0]
            # Открываем диалог с деталями документа
            self.document_details_dialog(document_data=document_data, document_id=document_id)
        else:
            QMessageBox.warning(self.table_widget, "Ошибка", "Документ не найден в базе данных.")

    def fetch_data_from_db(self):
        """Получает данные из базы данных и передает их в таблицу."""
        try:
            # Проверка подключения к базе данных
            if not self.db_manager.is_connected():
                logging.error("Нет подключения к базе данных.")
                return

            # Логирование user_id
            logging.debug(f"User ID: {self.user_id}")

            # SQL-запрос
            query = """
            SELECT 
                d.id AS "id документа",
                dis.Name AS "Название документа",
                dep.Name AS "Кафедра",
                dis.Name AS "Дисциплина",
                s.Name AS "Специальность",
                es.Status AS "Статус выполнения",
                d.File_without_printing AS "Файл без печати",
                d.File_with_stamp AS "Файл с печатью",
                d.Date_of_last_update AS "Дата последнего обновления",
                d.Execution_priority AS "Приоритет выполнения",
                d.Additional_materials AS "Дополнительные материалы",
                d.Comment AS "Комментарий"
            FROM 
                Documents d
            JOIN 
                Discipline dis ON d.Discipline = dis.id
            JOIN 
                Department dep ON dis.Speciality = dep.id
            JOIN 
                Speciality s ON dis.Speciality = s.id
            JOIN 
                Execution_Status es ON d.Execution_Status = es.id
            WHERE 
                d.Teacher = %s AND
                d.File_with_stamp IS NOT NULL;  -- Проверка на наличие файла с печатью
            """
            result = self.db_manager.execute_query(query, (self.user_id,))
            logging.debug(f"Результат запроса: {result}")  # Логируем результат запроса

            if not result:
                logging.warning("Запрос не вернул данных.")
                return

            # Настройка таблицы
            self.table_widget.setRowCount(len(result))
            self.table_widget.setColumnCount(12)
            self.table_widget.setHorizontalHeaderLabels([
                "id документа", "Название документа", "Кафедра", "Дисциплина", "Специальность", 
                "Статус выполнения", "Файл без печати", "Файл с печатью", "Дата последнего обновления", 
                "Приоритет выполнения", "Дополнительные материалы", "Комментарий"
            ])

            # Заполнение таблицы данными
            for row_idx, row_data in enumerate(result):
                logging.debug(f"Данные строки {row_idx}: {row_data}")
                for col_idx, (col_name, cell_data) in enumerate(row_data.items()):
                    if isinstance(cell_data, datetime):  # Преобразование datetime в строку
                        cell_data = cell_data.strftime("%Y-%m-%d %H:%M:%S")
                    item = QTableWidgetItem(str(cell_data) if cell_data is not None else "")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table_widget.setItem(row_idx, col_idx, item)

        except Exception as e:
            logging.error(f"Ошибка при получении данных: {e}")


    def create_download_link(self, row_idx, col_idx, file_type):
        """Создает ссылку для скачивания в ячейке таблицы."""
        download_link = QLabel("Скачать", self.table_widget)
        download_link.setStyleSheet("color: blue; text-decoration: underline;")
        download_link.mousePressEvent = lambda event, row=row_idx: self.download_file(event, row, file_type)
        self.table_widget.setCellWidget(row_idx, col_idx, download_link)


    def download_file(self, event, row, file_type):
        try:
            document_id = self.table_widget.item(row, 0).text()  # Получаем ID документа
            query = f"""
                SELECT 
                    d.File_without_printing, d.File_with_stamp, d.Additional_materials 
                FROM 
                    Documents d
                WHERE 
                    d.id = %s
            """
            result = self.db_manager.execute_query(query, (document_id,))

            if result:
                document_data = result[0]
                file_data = document_data.get(file_type)

                if file_data:  # Проверяем, существует ли BLOB-данные
                    file_dialog = QFileDialog()
                    file_dialog.setAcceptMode(QFileDialog.AcceptSave)
                    file_dialog.setDefaultSuffix('docx')  # Установите правильное расширение
                    file_dialog.setNameFilter("Word Files (*.docx)")  # Укажите фильтр для формата

                    if file_dialog.exec_():
                        save_path = file_dialog.selectedFiles()[0]
                        try:
                            with open(save_path, 'wb') as f:
                                f.write(file_data)  # Записываем бинарные данные в файл
                            QMessageBox.information(None, "Успех", f"Файл успешно скачан в {save_path}.")
                        except Exception as e:
                            QMessageBox.warning(None, "Ошибка", f"Не удалось сохранить файл: {e}")
                else:
                    QMessageBox.warning(None, "Ошибка", f"Файл '{file_type}' не найден в базе данных для документа {document_id}.")
            else:
                QMessageBox.warning(None, "Ошибка", "Документ не найден.")
        except Exception as e:
            logging.error(f"Ошибка при скачивании файла: {e}")
            QMessageBox.critical(None, "Ошибка", f"Не удалось скачать файл: {e}")



    def save_file(self, file_path):
        """Открывает диалог для выбора места сохранения файла."""
        try:
            file_dialog = QFileDialog()
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)  # Режим сохранения
            file_dialog.setDefaultSuffix('pdf')  # Установить стандартное расширение

            if file_dialog.exec_():
                save_path = file_dialog.selectedFiles()[0]
                # Здесь предполагается, что файл существует в указанном пути
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        with open(save_path, 'wb') as out_file:
                            out_file.write(f.read())  # Копируем файл в новое место
                    QMessageBox.information(None, "Успех", f"Файл успешно скачан в {save_path}")
                else:
                    QMessageBox.warning(None, "Ошибка", "Файл не найден.")
        except Exception as e:
            logging.error(f"Ошибка при скачивании файла: {e}")
            QMessageBox.critical(None, "Ошибка", f"Не удалось скачать файл: {e}")


    def color_row_based_on_status(self, row, status):
        """Цветовое выделение строк в зависимости от статуса."""
        if status in ["Создан", "В работе"]:
            color = QColor(255, 99, 71)  # Красный
        elif status == "На проверке":
            color = QColor(255, 255, 0)  # Желтый
        elif status in ["Принят завкафедрой", "Отправлен на печать"]:
            color = QColor(135, 206, 250)  # Синий
        elif status == "Сохранен":
            color = QColor(144, 238, 144)  # Зеленый
        elif status == "Доработать":
            color = QColor(147, 112, 219)  # Фиолетовый
        else:
            color = QColor(255, 255, 255)  # Белый

        for col in range(self.table_widget.columnCount()):
            self.table_widget.item(row, col).setBackground(color)

    def document_details_dialog(self, document_data, document_id):
        """Диалоговое окно для просмотра документа (только для преподавателя)."""
        dialog = QDialog()
        dialog.setWindowTitle("Детали документа")
        layout = QVBoxLayout()

        # Список полей, которые нужно отобразить
        fields = [
            ("Название документа", document_data.get("Название документа", "")),
            ("Кафедра", document_data.get("Кафедра", "")),
            ("Дисциплина", document_data.get("Дисциплина", "")),
            ("Специальность", document_data.get("Специальность", "")),
            ("Статус выполнения", document_data.get("Статус выполнения", "")),
            ("Дата последнего обновления", document_data.get("Дата последнего обновления", "")),
            ("Приоритет выполнения", document_data.get("Приоритет выполнения", "")),
            ("Дополнительные материалы", document_data.get("Дополнительные материалы", "")),
            ("Комментарий", document_data.get("Комментарий", "")),
        ]

        # Отображение данных через двоеточие
        for field_name, field_value in fields:
            label = QLabel(f"{field_name}: {field_value}")
            label.setAlignment(Qt.AlignLeft)  # Выравнивание текста по левому краю
            layout.addWidget(label)

        # Поля для загрузки файлов (изменяемые)
        self.file_without_printing_input = QLineEdit()
        self.file_with_stamp_input = QLineEdit()

        load_button_without_stamp = QPushButton("Загрузить файл без печати", dialog)
        load_button_without_stamp.clicked.connect(lambda: self.load_file("Файл без печати", self.file_without_printing_input))
        layout.addWidget(load_button_without_stamp)
        layout.addWidget(self.file_without_printing_input)

        load_button_with_stamp = QPushButton("Загрузить файл с печатью", dialog)
        load_button_with_stamp.clicked.connect(lambda: self.load_file("Файл с печатью", self.file_with_stamp_input))
        layout.addWidget(load_button_with_stamp)
        layout.addWidget(self.file_with_stamp_input)

        # Кнопка сохранения изменений
        save_button = QPushButton("Сохранить изменения")
        save_button.clicked.connect(lambda: self.save_document_changes(dialog, document_id))
        layout.addWidget(save_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def load_file(self, field_name, field_widget):
        """Обрабатывает выбор файла для загрузки."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setAcceptMode(QFileDialog.AcceptOpen)

        if file_dialog.exec_():
            selected_file = file_dialog.selectedFiles()[0]
            field_widget.setText(selected_file)  # Устанавливаем путь к файлу в поле

    def handle_download(self, document_data):
        """Обрабатывает скачивание документов."""
        # Формируем имя файла по шаблону
        file_name = self.generate_file_name(document_data)
        
        # Проверка столбцов и скачивание файлов
        if document_data.get("Файл без печати"):
            self.download_file(document_data["Файл без печати"], file_name)
        if document_data.get("Файл с печатью"):
            self.download_file(document_data["Файл с печатью"], file_name)


    def generate_file_name(self, document_data):
        """Генерирует имя файла для сохранения."""
        return f"{document_data['Название документа']}.zip"

    def save_document_changes(self, dialog, document_id):
        try:
            # Получаем данные из полей ввода
            file_without_printing_path = self.file_without_printing_input.text()
            file_with_stamp_path = self.file_with_stamp_input.text()

            # Читаем файлы, если они выбраны
            file_without_printing_data = None
            if file_without_printing_path:
                with open(file_without_printing_path, 'rb') as file:
                    file_without_printing_data = file.read()

            file_with_stamp_data = None
            if file_with_stamp_path:
                with open(file_with_stamp_path, 'rb') as file:
                    file_with_stamp_data = file.read()

            # SQL запрос для обновления только файлов
            query = """
                UPDATE Documents
                SET 
                    File_without_printing = %s,
                    File_with_stamp = %s
                WHERE id = %s;
            """

            # Выполняем запрос
            self.db_manager.execute_query(query, (
                file_without_printing_data,  # Бинарные данные файла без печати
                file_with_stamp_data,  # Бинарные данные файла с печатью
                document_id
            ))

            QMessageBox.information(dialog, "Успех", "Документ успешно обновлен.")
            dialog.close()
            self.fetch_data_from_db()  # Обновляем таблицу

        except Exception as e:
            logging.error(f"Ошибка при обновлении документа: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось обновить документ: {e}")