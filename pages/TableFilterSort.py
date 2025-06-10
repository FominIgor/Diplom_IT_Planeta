from PyQt5.QtWidgets import QAbstractItemView, QTableWidgetItem, QProgressBar, QMenu, QAction, QInputDialog
from PyQt5.QtCore import Qt

import logging


class TableFilterSort:
    def __init__(self, table_widget):
        """
        Инициализация класса для фильтрации, сортировки и поиска.
        :param table_widget: QTableWidget для отображения данных.
        """
        self.table_widget = table_widget
        self.filters = {}  # Словарь для хранения фильтров
        self.setup_table()

    def setup_table(self):
        """Настройка таблицы и включение сортировки."""
        self.table_widget.setSortingEnabled(True)
        self.table_widget.sortByColumn(0, Qt.AscendingOrder)  # Сортировка по первому столбцу по возрастанию
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Запрещаем редактирование
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.horizontalHeader().customContextMenuRequested.connect(self.show_header_context_menu)
    
    def show_header_context_menu(self, pos):
        """Показ контекстного меню при правом клике по заголовку таблицы для фильтрации."""
        column = self.table_widget.horizontalHeader().logicalIndexAt(pos)
        
        # Логируем, какой столбец был выбран
        logging.debug(f"Right-clicked on column: {column}")
        
        if column == -1:
            return


        menu = QMenu()
        
        # Добавляем действие для поиска
        search_action = QAction("Поиск...", menu)
        search_action.triggered.connect(self.show_search_dialog)
        menu.addAction(search_action)


        column_name = self.table_widget.horizontalHeaderItem(column).text()
        unique_values = self.get_unique_values(column)


        logging.debug(f"Unique values for column {column_name}: {unique_values}")


        # Добавляем действия для каждого уникального значения
        for value in unique_values:
            action = QAction(str(value), menu)
            action.setCheckable(True)
            action.setChecked(value in self.filters.get(column_name, []))
            action.triggered.connect(lambda checked, v=value, col=column_name: self.update_filter(col, v, checked))
            menu.addAction(action)


        # Добавляем действие для сброса фильтров
        reset_action = QAction("Сбросить фильтры", menu)
        reset_action.triggered.connect(self.reset_filters)
        menu.addAction(reset_action)


        # Показываем контекстное меню
        menu.exec_(self.table_widget.viewport().mapToGlobal(pos))


    def show_search_dialog(self):
        """Показ диалога поиска для фильтрации данных."""
        search_text, ok = QInputDialog.getText(self.table_widget, "Поиск", "Введите текст для поиска:")
        if ok and search_text:
            self.apply_search_filter(search_text)


    def apply_search_filter(self, search_text):
        """Применяет фильтрацию по введенному тексту в строке поиска."""
        search_text = search_text.lower()  # Приводим к нижнему регистру для нечувствительности к регистру
        for row in range(self.table_widget.rowCount()):
            should_hide = True  # Скрыть строку, если текст не найден
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                if item and search_text in item.text().lower():
                    should_hide = False  # Показать строку, если текст найден хотя бы в одном столбце
                    break
            self.table_widget.setRowHidden(row, should_hide)




    def get_unique_values(self, column):
        """Получение уникальных значений для фильтрации."""
        values = set()
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, column)
            if item:
                values.add(item.text())
        return list(values)


    def update_filter(self, column_name, value, checked):
        """Обновление фильтров для выбранного столбца и значения."""
        if column_name not in self.filters:
            self.filters[column_name] = []
        if checked and value not in self.filters[column_name]:
            self.filters[column_name].append(value)
        elif not checked and value in self.filters[column_name]:
            self.filters[column_name].remove(value)


        logging.debug(f"Updated filter for column '{column_name}': {self.filters[column_name]}")
        self.apply_filters()


        self.apply_filters()


    def apply_filters(self):
        """Применение фильтров к данным."""
        logging.debug(f"Applying filters: {self.filters}")
        
        for row in range(self.table_widget.rowCount()):
            should_hide = False
            for col in range(self.table_widget.columnCount()):
                column_name = self.table_widget.horizontalHeaderItem(col).text()
                if column_name in self.filters and self.filters[column_name]:
                    item = self.table_widget.item(row, col)
                    if item and item.text() not in self.filters[column_name]:
                        should_hide = True
                        break
            self.table_widget.setRowHidden(row, should_hide)
            logging.debug(f"Row {row} hidden: {should_hide}")


    def reset_filters(self):
        """Сброс фильтров и отображение всех строк."""
        self.filters.clear()  # Очищаем все фильтры
        for row in range(self.table_widget.rowCount()):
            self.table_widget.setRowHidden(row, False)  # Показываем все строки  весь код