import logging
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QFileDialog, QListWidget, QMessageBox, QMenu, QAction, QVBoxLayout,
    QInputDialog, QAbstractItemView
)
import os

from PyQt5.QtCore import Qt
from pages.TableFilterSort import TableFilterSort


class TeacherDocumentViewer:
    def __init__(self, table_widget, db_manager, user_id):
        """
        Инициализация класса TeacherDocumentViewer.
        """
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.user_id = user_id
        self.filter_sort = TableFilterSort(table_widget)
        self.setup_table()
        self.fetch_data_from_db()

    def setup_table(self):
        """Настройка таблицы."""
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels([
            "Кафедра", "Специальность", "Дисциплина", "Файл с печатью"
        ])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSortingEnabled(True)
        self.table_widget.sortByColumn(3, Qt.AscendingOrder)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.BASE_UPLOAD_DIR = "/home/user/uploads/"  # Базовая директория для файлов

    def populate_table(self, data):
        """Заполняет таблицу данными."""
        self.table_widget.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            self.table_widget.setItem(row_idx, 0, QTableWidgetItem(str(row_data["Department"])))
            self.table_widget.setItem(row_idx, 1, QTableWidgetItem(str(row_data["Speciality"])))
            self.table_widget.setItem(row_idx, 2, QTableWidgetItem(str(row_data["Discipline"])))

            file_data = row_data["File_extension_with_stamp"]

            if file_data:
                btn = QPushButton("Скачать")
                btn.setStyleSheet("color: rgb(1, 50, 32)")
                btn.clicked.connect(lambda _, 
                                    file_data=file_data,
                                    discipline=row_data["Discipline"],
                                    speciality=row_data["Speciality"]: 
                                    self.download_file_by_path(file_data, discipline, speciality))
                btn.setProperty('doc_id', row_data["DocumentID"])
                btn.setProperty('field', "File_extension_with_stamp")
                self.table_widget.setCellWidget(row_idx, 3, btn)
            else:
                self.table_widget.setItem(row_idx, 3, QTableWidgetItem("Нет файла"))

            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row_idx, col)
                if item:
                    item.setToolTip(item.text())

    def fetch_data_from_db(self):
        """Получает данные из базы данных и передает их в таблицу."""
        try:
                                    # 1. Сохраняем текущую позицию прокрутки
            scroll_pos = self.table_widget.verticalScrollBar().value()
            
            # 2. Блокируем обновление и сортировку
            self.table_widget.setUpdatesEnabled(False)
            self.table_widget.setSortingEnabled(False)
            
            # 3. Очищаем только содержимое (сохраняя заголовки)
            self.table_widget.clearContents()
            self.table_widget.setRowCount(0)
            
            # 4. Удаляем все оставшиеся кнопки
            for i in range(self.table_widget.rowCount()):
                for j in range(self.table_widget.columnCount()):
                    if widget := self.table_widget.cellWidget(i, j):
                        widget.deleteLater()
            query = """
SELECT 
    d.id AS DocumentID,
    dep.Name AS Department, 
    s.Name AS Speciality, 
    disc.Name AS Discipline, 
    d.File_extension_with_stamp,
    d.Additional_materials
FROM Documents d
JOIN Discipline disc ON d.Discipline = disc.id
JOIN Speciality s ON disc.Speciality = s.id
JOIN Department dep ON s.Department = dep.id
WHERE d.Teacher = %s
   OR d.id IN (
       SELECT Document 
       FROM Documents_Access 
       WHERE Teacher = %s

                   );
            """
            result = self.db_manager.execute_query(query, (self.user_id, self.user_id))
            self.original_data = result
            self.populate_table(result)

                    # 7. Восстанавливаем состояние
            self.table_widget.setSortingEnabled(True)
            self.table_widget.verticalScrollBar().setValue(scroll_pos)
            self.table_widget.setUpdatesEnabled(True)
        except Exception as e:
            logging.error(f"Ошибка при получении данных: {e}")

    def download_file_by_path(self, file_path, discipline, speciality):
        """Скачивание файла документа"""
        try:
            btn = self.table_widget.sender()
            if not btn:
                return

            doc_id = btn.property('doc_id')
            field = btn.property('field')

            # Получаем имя файла из БД
            query = f"SELECT {field} FROM Documents WHERE id = %s"
            result = self.db_manager.execute_query(query, (doc_id,))

            if result and result[0][field]:
                filename = result[0][field].strip()  # Убираем лишние пробелы
                full_path = os.path.join(self.BASE_UPLOAD_DIR, filename)

                print("Путь к файлу:", full_path)
                if not os.path.isfile(full_path):
                    QMessageBox.warning(self.table_widget, "Ошибка", f"Файл не найден:\n{full_path}")
                    return

                # Определяем расширение файла
                _, ext = os.path.splitext(filename)

                # Вызываем диалог сохранения
                file_path, _ = QFileDialog.getSaveFileName(
                    self.table_widget,
                    "Сохранить файл",
                    f"{filename}",
                    f"Файлы (*{ext})"
                )

                if file_path:
                    with open(full_path, 'rb') as src_file:
                        with open(file_path, 'wb') as dest_file:
                            dest_file.write(src_file.read())

                    QMessageBox.information(self.table_widget, "Успех", "Файл сохранен")

            else:
                QMessageBox.warning(self.table_widget, "Ошибка", "Файл не найден в БД")

        except Exception as e:
            logging.error(f"Ошибка скачивания файла: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось скачать файл: {e}")

