import logging
from PyQt5.QtWidgets import QAbstractItemView, QTableWidgetItem, QHeaderView, QMenu, QAction, QProgressBar, QInputDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from pages.TableFilterSort import TableFilterSort

class Speciality_SQL:
    def __init__(self, speciality_table, db_manager):
        """
        Инициализация класса Speciality_SQL.
        :param speciality_table: Виджет QTableWidget для отображения данных.
        :param db_manager: Менеджер базы данных для выполнения запросов.
        """
        self.speciality_table = speciality_table
        self.db_manager = db_manager
        self.filter_sort = TableFilterSort(speciality_table)  # Интеграция поиска
        self.setup_table()
        self.fetch_data_from_db()

    def setup_table(self):
        """Настройка таблицы и контекстного меню для фильтрации."""
        self.speciality_table.setRowCount(0)
        self.speciality_table.setColumnCount(5)
        self.speciality_table.setHorizontalHeaderLabels(
            ["Специальность", "Кафедра", "Всего", "Выполнено", "Успех"]
        )
        # self.speciality_table.horizontalHeader().setStretchLastSection(True)

        self.speciality_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Включаем сортировку по столбцам
        self.speciality_table.setSortingEnabled(True)
        self.speciality_table.sortByColumn(3, Qt.AscendingOrder)  # Сортировка по проценту, по возрастанию

        # Запрещаем редактирование данных
        self.speciality_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Запрещаем выделение текста в таблице
        # self.speciality_table.setSelectionMode(QAbstractItemView.NoSelection)  # Не разрешаем выделение строк и ячеек

    def fetch_data_from_db(self):
        """Получает данные из таблицы Speciality и передает их в QTableWidget."""
        try:
            query = """
                SELECT 
                    s.Name AS "Специальность",
                    d.Name AS "Кафедра",
                    COUNT(doc.id) AS "Всего",
                    SUM(CASE WHEN doc.Execution_Status = 6 THEN 1 ELSE 0 END) AS "Выполнено",
                    ROUND((SUM(CASE WHEN doc.Execution_Status = 6 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(doc.id), 0)), 2) AS "Успех"
                FROM 
                    Speciality s
                LEFT JOIN 
                    Department d ON s.Department = d.id
                LEFT JOIN 
                    Discipline disc ON s.id = disc.Speciality
                LEFT JOIN 
                    Documents doc ON disc.id = doc.Discipline
                GROUP BY 
                    s.id
                ORDER BY 
                    s.id ASC;
            """
            result = self.db_manager.execute_query(query)
            self.original_data = result  # Сохраняем оригинальные данные

            self.speciality_table.setRowCount(len(result))

            for row_idx, row_data in enumerate(result):
                # Заполняем таблицу
                self.speciality_table.setItem(row_idx, 0, QTableWidgetItem(row_data["Специальность"]))
                self.speciality_table.setItem(row_idx, 1, QTableWidgetItem(row_data["Кафедра"]))
                self.speciality_table.setItem(row_idx, 2, QTableWidgetItem(str(row_data["Всего"])))
                self.speciality_table.setItem(row_idx, 3, QTableWidgetItem(str(row_data["Выполнено"])))

                # Создаем прогресс-бар для процента успеха
                percentage = float(row_data["Успех"]) if row_data["Всего"] > 0 else 0
                progress_item = QProgressBar()
                progress_item.setValue(int(percentage))
                progress_item.setFormat(f"{percentage}%")
                self.set_progress_bar_color(progress_item, percentage)  # Устанавливаем цвет прогресс-бара
                self.speciality_table.setCellWidget(row_idx, 4, progress_item)

                # Добавляем подсказки (tooltips) для всех ячеек, чтобы показывать полный текст при наведении
                for col in range(self.speciality_table.columnCount()):
                    item = self.speciality_table.item(row_idx, col)
                    if item:
                        item.setToolTip(item.text())  # Устанавливаем полный текст ячейки как подсказку

        except Exception as e:
            logging.error(f"Ошибка при получении данных: {e}")


    def set_progress_bar_color(self, progress_bar, percentage):
        """Устанавливает цвет прогресс-бара в зависимости от процента."""
        if percentage >= 90:
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: rgba(144, 238, 144, 255); }")  # Светло-зеленый
        elif percentage >= 50:
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: rgba(173, 216, 230, 255); }")  # Светло-голубой
        else:
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: rgba(255, 182, 193, 255); }")  # Светло-розовый