import logging
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QFileDialog, QMenu, QAction, QInputDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt
from pages.TableFilterSort import TableFilterSort

class TeacherDocumentViewer:
    def __init__(self, table_widget, db_manager, user_id):
        """
        Инициализация класса TeacherDocumentViewer.
        """
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.user_id = user_id  # Добавляем user_id в атрибуты
        self.filter_sort = TableFilterSort(table_widget)  # Интеграция поиска
        self.setup_table()
        self.fetch_data_from_db()

    def setup_table(self):
        """Настройка таблицы."""
        self.table_widget.setColumnCount(4)  # Устанавливаем 4 столбца
        self.table_widget.setHorizontalHeaderLabels([
            "Кафедра", "Специальность", "Дисциплина", "Файл с печатью"
        ])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Включаем сортировку по столбцам
        self.table_widget.setSortingEnabled(True)
        self.table_widget.sortByColumn(3, Qt.AscendingOrder)  # Сортировка по проценту, по возрастанию

        # Запрещаем редактирование данных
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Запрещаем выделение текста в таблице
        # self.table_widget.setSelectionMode(QAbstractItemView.NoSelection)  # Не разрешаем выделение строк и ячеек
    def populate_table(self, data):
        """Заполняет таблицу данными."""
        self.table_widget.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            # Кафедра
            self.table_widget.setItem(row_idx, 0, QTableWidgetItem(str(row_data["Department"])))
            # Специальность
            self.table_widget.setItem(row_idx, 1, QTableWidgetItem(str(row_data["Speciality"])))
            # Дисциплина
            self.table_widget.setItem(row_idx, 2, QTableWidgetItem(str(row_data["Discipline"])))

            # Файл с печатью
            file_with_stamp = row_data["File_with_stamp"]
            
            if file_with_stamp:
                # Если файл с печатью есть, показываем кнопку для скачивания
                btn = QPushButton("Скачать")
                btn.setStyleSheet("color: rgb(1, 50, 32)")
                btn.clicked.connect(lambda _, file_data=file_with_stamp, 
                                        discipline=row_data["Discipline"], 
                                        speciality=row_data["Speciality"]: 
                                    self.download_file(file_data, discipline, speciality))
                # Устанавливаем кнопку в ячейку
                self.table_widget.setCellWidget(row_idx, 3, btn)
            else:
                # Если файла нет, показываем текст "Нет файла"
                self.table_widget.setItem(row_idx, 3, QTableWidgetItem("Нет файла"))

            # Добавляем подсказки (tooltips) для всех ячеек, чтобы показывать полный текст при наведении
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row_idx, col)
                if item:
                    item.setToolTip(item.text())  # Устанавливаем полный текст ячейки как подсказку

    def fetch_data_from_db(self):
        """Получает данные из базы данных и передает их в таблицу."""
        try:
            query = """
                SELECT dep.Name AS Department, s.Name AS Speciality, disc.Name AS Discipline, 
                       d.File_with_stamp, d.File_without_printing, d.Additional_materials
                FROM Documents d
                JOIN Discipline disc ON d.Discipline = disc.id
                JOIN Speciality s ON disc.Speciality = s.id
                JOIN Department dep ON s.Department = dep.id
                WHERE d.Teacher = %s OR d.id IN (
                    SELECT Document FROM Documents_Access WHERE Teacher = %s
                );
            """
            result = self.db_manager.execute_query(query, (self.user_id, self.user_id))
            self.original_data = result
            self.populate_table(result)
        except Exception as e:
            logging.error(f"Ошибка при получении данных: {e}")

    def download_file(self, file_data, discipline, speciality):
        """Сохраняет файл на диск с названием Дисциплина_Специальность."""
        options = QFileDialog.Options()
        file_name = f"{discipline}_{speciality}.pdf"  # Формируем название файла
        file_path, _ = QFileDialog.getSaveFileName(None, "Сохранить файл", file_name, "PDF Files (*.pdf);;All Files (*)", options=options)

        if file_path:
            try:
                with open(file_path, "wb") as file:
                    file.write(file_data)
            except Exception as e:
                logging.error(f"Ошибка при сохранении файла: {e}")
