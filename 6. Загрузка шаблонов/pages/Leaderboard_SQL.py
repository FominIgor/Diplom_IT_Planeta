from PyQt5.QtWidgets import QMenu, QAction, QTableWidgetItem, QHeaderView, QProgressBar, QInputDialog,QAbstractItemView
from PyQt5.QtCore import Qt
import logging
from pages.TableFilterSort import TableFilterSort

class Leaderboard_SQL:
    def __init__(self, teachers_progress, db_manager):
        self.teachers_progress = teachers_progress
        self.db_manager = db_manager
        self.filter_sort = TableFilterSort(teachers_progress)  # Интеграция поиска
        self.setup_table()
        self.fetch_data_from_db()

    def setup_table(self):
        """Настройка таблицы и контекстного меню для фильтрации."""
        self.teachers_progress.setRowCount(0)
        self.teachers_progress.setColumnCount(4)
        self.teachers_progress.setHorizontalHeaderLabels(["ФИО", "Всего", "Выполнено", "Успех"])
        self.teachers_progress.horizontalHeader().setStretchLastSection(True)
        self.teachers_progress.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Включаем сортировку по столбцам
        self.teachers_progress.setSortingEnabled(True)
        self.teachers_progress.sortByColumn(3, Qt.AscendingOrder)  # Сортировка по проценту, по возрастанию

        # Запрещаем редактирование данных
        self.teachers_progress.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Запрещаем выделение текста в таблице
        # self.teachers_progress.setSelectionMode(QAbstractItemView.NoSelection)  # Не разрешаем выделение строк и ячеек

    def fetch_data_from_db(self):
        """Получает данные из базы данных и передает их в таблицу."""
        try:
            query = """
                SELECT u.Full_name AS "ФИО", COUNT(d.id) AS "Всего",
                SUM(CASE WHEN d.Execution_Status = 6 THEN 1 ELSE 0 END) AS "Выполнено",
                ROUND((SUM(CASE WHEN d.Execution_Status = 6 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(d.id), 0)), 2) AS "Успех"
                FROM Users u
                LEFT JOIN Documents d ON u.id = d.Teacher
                WHERE u.Teacher = 1
                GROUP BY u.id
                ORDER BY "Успех" ASC;
            """
            result = self.db_manager.execute_query(query)
            self.original_data = result  # Сохраняем оригинальные данные

            self.teachers_progress.setRowCount(len(result))

            for row_idx, row_data in enumerate(result):
                self.teachers_progress.setItem(row_idx, 0, QTableWidgetItem(row_data["ФИО"]))
                self.teachers_progress.setItem(row_idx, 1, QTableWidgetItem(str(row_data["Всего"])))
                self.teachers_progress.setItem(row_idx, 2, QTableWidgetItem(str(row_data["Выполнено"])))

                # Создаем прогресс-бар для процента выполнения
                percentage = float(row_data["Успех"]) if row_data["Всего"] > 0 else 0
                progress_item = QProgressBar()
                progress_item.setValue(int(percentage))
                progress_item.setFormat(f"{percentage}%")
                self.set_progress_bar_color(progress_item, percentage)  # Устанавливаем цвет прогресс-бара
                self.teachers_progress.setCellWidget(row_idx, 3, progress_item)

                # Добавляем подсказки (tooltips) для всех ячеек, чтобы показывать полный текст при наведении
                for col in range(self.teachers_progress.columnCount()):
                    item = self.teachers_progress.item(row_idx, col)
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
