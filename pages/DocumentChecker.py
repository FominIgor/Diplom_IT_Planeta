import logging
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QFileDialog, QListWidget, QMessageBox, QMenu, QAction, QVBoxLayout,
    QInputDialog, QAbstractItemView, QLabel
)
from PyQt5.QtCore import Qt
from pages.TeacherDocumentViewer import TeacherDocumentViewer
from pages.TableFilterSort import TableFilterSort
import os
from functools import partial  # убедись, что это есть вверху файла


class DocumentChecker:
    def __init__(self, table_widget, db_manager, user_id):
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.filter_sort = TableFilterSort(table_widget)
        self.user_id = user_id
        self.BASE_UPLOAD_DIR = "/home/user/uploads/"  # Базовая директория для файлов
        self.setup_table()

    def setup_table(self):
        self.table_widget.setRowCount(0)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSortingEnabled(True)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_row_context_menu)
        self.load_documents()


    def has_access(self, document_id):
        try:
            query = "SELECT * FROM Documents_Access WHERE Teacher = %s AND Document = %s"
            result = self.db_manager.execute_query(query, (self.user_id, document_id))
            return len(result) > 0
        except Exception as e:
            logging.error(f"Ошибка при проверке доступа: {e}")
            return False

   
    def load_documents(self):
        try:
            scroll_pos = self.table_widget.verticalScrollBar().value()
            self.table_widget.setUpdatesEnabled(False)
            self.table_widget.setSortingEnabled(False)

            self.table_widget.clearContents()
            self.table_widget.setRowCount(0)

            # Очистка виджетов в ячейках, если есть
            for i in range(self.table_widget.rowCount()):
                for j in range(self.table_widget.columnCount()):
                    widget = self.table_widget.cellWidget(i, j)
                    if widget:
                        widget.deleteLater()

            # Получаем id кафедры, которой заведует пользователь
            query = "SELECT id FROM Department WHERE Head_of_the_department = %s"
            department_result = self.db_manager.execute_query(query, (self.user_id,))

            if not department_result:
                logging.warning("Пользователь не является заведующим кафедрой")
                return

            department_id = department_result[0]['id']

            # Получаем документы кафедры пользователя, сортируем по статусу и дате
            query = """
            SELECT
                spec.Name AS speciality,
                dis.Name AS discipline,
                u.Full_name AS teacher,
                es.Status AS execution_status,
                d.Date_of_last_update AS last_update,
                d.Execution_priority AS priority,
                d.Comment AS comment,
                d.id AS document_id,
                d.File_extension_without_printing AS file_no_print,
                d.File_extension_with_stamp AS file_with_stamp,
                CASE WHEN es.Status = 'На проверке' THEN 1 ELSE 0 END AS highlight
            FROM Documents d
            LEFT JOIN Discipline dis ON d.Discipline = dis.id
            LEFT JOIN Speciality spec ON dis.Speciality = spec.id
            LEFT JOIN Department dep ON spec.Department = dep.id
            LEFT JOIN Users u ON d.Teacher = u.id
            LEFT JOIN Execution_Status es ON d.Execution_Status = es.id
            WHERE dep.id = %s
            ORDER BY highlight DESC, d.Date_of_last_update DESC
            """
            result = self.db_manager.execute_query(query, (department_id,))

            headers = [
                "Специальность", "Дисциплина", "Преподаватель", "Статус выполнения",
                "Дата обновления", "Приоритет", "Комментарий",
                "Файл (без печати)", "Файл с печатью"
            ]
            self.table_widget.setColumnCount(len(headers))
            self.table_widget.setHorizontalHeaderLabels(headers)
            self.table_widget.setRowCount(len(result))

            for row_idx, row in enumerate(result):
                # Заполняем данные
                self.table_widget.setItem(row_idx, 0, QTableWidgetItem(row["speciality"] or "—"))
                self.table_widget.setItem(row_idx, 1, QTableWidgetItem(row["discipline"] or "—"))
                self.table_widget.setItem(row_idx, 2, QTableWidgetItem(row["teacher"] or "—"))
                self.table_widget.setItem(row_idx, 3, QTableWidgetItem(row["execution_status"] or "—"))
                self.table_widget.setItem(row_idx, 4, QTableWidgetItem(str(row["last_update"]) if row["last_update"] else "—"))
                self.table_widget.setItem(row_idx, 5, QTableWidgetItem(str(row["priority"]) if row["priority"] else "—"))
                self.table_widget.setItem(row_idx, 6, QTableWidgetItem(row["comment"] or "—"))

                field_map = {
                    "file_no_print": "File_extension_without_printing",
                    "file_with_stamp": "File_extension_with_stamp"
                }
                # Кнопки для скачивания файлов
                for col_idx, field_alias in [(7, "file_no_print"), (8, "file_with_stamp")]:
                    file_path = row[field_alias]
                    if file_path:
                        btn = QPushButton("Скачать")
                        btn.setStyleSheet("color: rgb(1, 50, 32);")
                        btn.setProperty('file_path', file_path)
                        btn.setProperty('discipline', row["discipline"])
                        btn.setProperty('speciality', row["speciality"])
                        btn.setProperty('field', field_map[field_alias])  # <== реальное имя поля в БД
                        btn.setProperty('doc_id', row["document_id"])
                        btn.clicked.connect(self.download_document_file)
                        self.table_widget.setCellWidget(row_idx, col_idx, btn)
                    else:
                        self.table_widget.setItem(row_idx, col_idx, QTableWidgetItem("Нет файла"))

                # Привязка document ID к первой ячейке строки
                item = self.table_widget.item(row_idx, 0)
                item.setData(Qt.UserRole, row["document_id"])

                # Подсветка строки, если статус "На проверке"
                if row["highlight"]:
                    for col in range(self.table_widget.columnCount()):
                        item = self.table_widget.item(row_idx, col)
                        if item:
                            item.setBackground(Qt.yellow)

                # Привязка document_id к первой ячейке для контекстного меню
                first_item = self.table_widget.item(row_idx, 0)
                if first_item:
                    first_item.setData(Qt.UserRole, row["document_id"])

                # Подсказки для всех ячеек
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row_idx, col)
                    if item:
                        item.setToolTip(item.text())

            self.table_widget.setSortingEnabled(True)
            self.table_widget.verticalScrollBar().setValue(scroll_pos)
            self.table_widget.setUpdatesEnabled(True)

        except Exception as e:
            logging.error(f"Ошибка при загрузке документов: {e}")



    def download_document_file(self):
        try:
            btn = self.table_widget.sender()
            if not btn:
                return

            doc_id = btn.property('doc_id')
            field = btn.property('field')
            file_path_alias = btn.property('file_path')  # уже полученный путь

            query = f"SELECT {field} FROM Documents WHERE id = %s"
            result = self.db_manager.execute_query(query, (doc_id,))

            if result and result[0][field]:
                filename = result[0][field].strip()
                full_path = os.path.join(self.BASE_UPLOAD_DIR, filename)

                if not os.path.isfile(full_path):
                    QMessageBox.warning(self.table_widget, "Ошибка", f"Файл не найден:\n{full_path}")
                    return

                _, ext = os.path.splitext(filename)
                save_path, _ = QFileDialog.getSaveFileName(
                    self.table_widget,
                    "Сохранить файл",
                    f"{filename}",
                    f"Файлы (*{ext})"
                )

                if save_path:
                    with open(full_path, 'rb') as src, open(save_path, 'wb') as dst:
                        dst.write(src.read())
                    QMessageBox.information(self.table_widget, "Успех", "Файл сохранен")
            else:
                QMessageBox.warning(self.table_widget, "Ошибка", "Файл не найден в БД")

        except Exception as e:
            logging.error(f"Ошибка скачивания файла: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось скачать файл: {e}")


    def show_row_context_menu(self, pos):
        index = self.table_widget.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        document_id = None

        for col in range(self.table_widget.columnCount()):
            item = self.table_widget.item(row, col)
            if item:
                document_id = item.data(Qt.UserRole)
                if document_id:
                    break

        if not document_id:
            return

        menu = QMenu(self.table_widget)
        review_action = QAction("Проверить документ", menu)
        review_action.triggered.connect(lambda: self.review_document_dialog(document_id))
        menu.addAction(review_action)
        menu.exec_(self.table_widget.viewport().mapToGlobal(pos))

    def review_document_dialog(self, document_id):
        dialog = QDialog(self.table_widget)
        dialog.setWindowTitle("Проверка документа")
        layout = QVBoxLayout(dialog)

        label = QLabel("Выберите действие с документом:")
        layout.addWidget(label)

        # Кнопка: Принять документ
        accept_button = QPushButton("Принять документ")
        accept_button.setStyleSheet("color: rgb(1, 50, 32);")

        layout.addWidget(accept_button)
        accept_button.clicked.connect(lambda: self.update_document_status(document_id, "Принят завкафедрой", dialog))

        # Кнопка: Отправить на доработку
        reject_button = QPushButton("Доработать документ")
        reject_button.setStyleSheet("color: rgb(1, 50, 32);")

        layout.addWidget(reject_button)
        reject_button.clicked.connect(lambda: self.request_revision(document_id, dialog))

        dialog.setLayout(layout)
        dialog.exec_()


    def update_document_status(self, document_id, new_status, dialog=None, comment=None):
        try:
            # Получаем id статуса
            query = "SELECT id FROM Execution_Status WHERE Status = %s"
            result = self.db_manager.execute_query(query, (new_status,))
            if not result:
                QMessageBox.warning(self.table_widget, "Ошибка", f"Не найден статус: {new_status}")
                return
            status_id = result[0]["id"]

            update_query = "UPDATE Documents SET Execution_Status = %s, Date_of_last_update = NOW(), Comment = %s WHERE id = %s"
            self.db_manager.execute_query(update_query, (status_id, comment, document_id))
            QMessageBox.information(self.table_widget, "Успешно", "Статус документа обновлён.")
            if dialog:
                dialog.accept()
            self.load_documents()

        except Exception as e:
            logging.error(f"Ошибка при обновлении статуса: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", "Не удалось обновить статус документа.")


    def request_revision(self, document_id, parent_dialog):
        text, ok = QInputDialog.getText(
            self.table_widget, "Комментарий к доработке", "Укажите, что нужно доработать:"
        )
        if ok and text.strip():
            self.update_document_status(document_id, "Доработать", parent_dialog, comment=text.strip())
        elif ok:
            QMessageBox.warning(self.table_widget, "Ошибка", "Комментарий обязателен для доработки.")
