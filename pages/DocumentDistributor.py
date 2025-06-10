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


class DocumentDistributor:
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

    def show_row_context_menu(self, pos):
        index = self.table_widget.indexAt(pos)
        if not index.isValid():
            logging.debug("Невалидный индекс при правом клике.")
            return

        row = index.row()
        document_id = None

        # Ищем document_id в любой ячейке строки
        for col in range(self.table_widget.columnCount()):
            item = self.table_widget.item(row, col)
            if item is not None:
                document_id = item.data(Qt.UserRole)
                if document_id is not None:
                    break

        if document_id is None:
            logging.warning("Не удалось найти document_id в строке.")
            return

        menu = QMenu(self.table_widget)

        # Новый пункт — Назначить исполнителя
        assign_executor_action = QAction("Назначить исполнителя", menu)
        assign_executor_action.triggered.connect(lambda: self.assign_executor(document_id))
        menu.addAction(assign_executor_action)

        menu.exec_(self.table_widget.viewport().mapToGlobal(pos))

    def has_access(self, document_id):
        try:
            query = "SELECT * FROM Documents_Access WHERE Teacher = %s AND Document = %s"
            result = self.db_manager.execute_query(query, (self.user_id, document_id))
            return len(result) > 0
        except Exception as e:
            logging.error(f"Ошибка при проверке доступа: {e}")
            return False

    def assign_executor(self, document_id):
        dialog = QDialog(self.table_widget)
        dialog.setWindowTitle("Назначить исполнителя")
        dialog.resize(300, 400)
        layout = QVBoxLayout(dialog)

        label = QLabel("Выберите преподавателя:")
        layout.addWidget(label)

        teacher_list = QListWidget()
        layout.addWidget(teacher_list)

        # Загружаем список преподавателей
        try:
            query = "SELECT id, Full_name FROM Users WHERE Teacher = 1"
            teachers = self.db_manager.execute_query(query)
            for teacher in teachers:
                teacher_list.addItem(f"{teacher['id']}: {teacher['Full_name']}")
        except Exception as e:
            logging.error(f"Ошибка загрузки преподавателей: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось загрузить список преподавателей:\n{e}")
            dialog.reject()
            return

        btn_save = QPushButton("Сохранить")
        btn_save.setStyleSheet("color: rgb(1, 50, 32)")
        layout.addWidget(btn_save)

        btn_save.clicked.connect(lambda: self.save_executor_selection(teacher_list, document_id, dialog))

        dialog.setLayout(layout)
        dialog.exec_()

    def save_executor_selection(self, teacher_list, document_id, dialog):
        selected_item = teacher_list.currentItem()
        if not selected_item:
            QMessageBox.warning(dialog, "Ошибка", "Пожалуйста, выберите преподавателя.")
            return

        try:
            teacher_id = int(selected_item.text().split(":")[0])
            # Здесь выполняем обновление документа — назначаем выбранного преподавателя исполнителем
            update_query = "UPDATE Documents SET Teacher = %s WHERE id = %s"
            self.db_manager.execute_query(update_query, (teacher_id, document_id))
            QMessageBox.information(dialog, "Успех", "Исполнитель успешно назначен.")
            dialog.accept()
            self.load_documents()  # обновляем таблицу
        except Exception as e:
            logging.error(f"Ошибка при назначении исполнителя: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось назначить исполнителя:\n{e}")



    def grant_access(self, document_id):
        if document_id is None:
            logging.error("Document ID is None, cannot grant access.")
            return

        dialog = QDialog(self.table_widget)
        dialog.setWindowTitle("Выберите преподавателя")
        layout = QVBoxLayout()
        teacher_list = QListWidget()
        layout.addWidget(teacher_list)

        try:
            query = "SELECT id, Full_name FROM Users WHERE Teacher = 1"
            teachers = self.db_manager.execute_query(query)
            for teacher in teachers:
                teacher_list.addItem(f"{teacher['id']}: {teacher['Full_name']}")
        except Exception as e:
            logging.error(f"Ошибка загрузки преподавателей: {e}")

        btn_ok = QPushButton("Выдать доступ")
        btn_ok.setStyleSheet("color: rgb(1, 50, 32)")

        btn_ok.clicked.connect(lambda: self.on_teacher_selected(teacher_list, document_id, dialog))
        layout.addWidget(btn_ok)

        dialog.setLayout(layout)
        dialog.exec_()

    def on_teacher_selected(self, teacher_list, document_id, dialog):
        if document_id is None:
            logging.error("Document ID is None, cannot grant access.")
            return

        selected_item = teacher_list.currentItem()
        if selected_item:
            teacher_id = int(selected_item.text().split(":")[0])
            try:
                query = "SELECT * FROM Documents_Access WHERE Teacher = %s AND Document = %s"
                existing_access = self.db_manager.execute_query(query, (teacher_id, document_id))
                if existing_access:
                    QMessageBox.information(self.table_widget, "Информация", "Этот преподаватель уже имеет доступ к документу.")
                else:
                    insert_query = "INSERT INTO Documents_Access (Teacher, Document, Rights) VALUES (%s, %s, 1);"
                    self.db_manager.execute_query(insert_query, (teacher_id, document_id))
                    QMessageBox.information(self.table_widget, "Успех", "Доступ выдан!")
            except Exception as e:
                logging.error(f"Ошибка при выдаче доступа: {e}")
                QMessageBox.critical(self.table_widget, "Ошибка", f"Ошибка: {e}")
        else:
            QMessageBox.warning(self.table_widget, "Ошибка", "Выберите преподавателя.")
        dialog.accept()
   
    def load_documents(self):
        try:
            scroll_pos = self.table_widget.verticalScrollBar().value()
            self.table_widget.setUpdatesEnabled(False)
            self.table_widget.setSortingEnabled(False)

            self.table_widget.clearContents()
            self.table_widget.setRowCount(0)

            for i in range(self.table_widget.rowCount()):
                for j in range(self.table_widget.columnCount()):
                    if widget := self.table_widget.cellWidget(i, j):
                        widget.deleteLater()

            # Получаем id кафедры, которой заведует пользователь
            query = "SELECT id FROM Department WHERE Head_of_the_department = %s"
            department_result = self.db_manager.execute_query(query, (self.user_id,))

            if not department_result:
                logging.warning("Пользователь не является заведующим кафедрой")
                return

            department_id = department_result[0]["id"]

            # Получаем документы этой кафедры
            query = """
SELECT 
    Documents.id AS ID,
    es.Status AS ExecutionStatus,
    Documents.Date_of_last_update AS LastUpdate,
    Documents.Execution_priority AS Priority,
    Documents.Comment,
    Documents.File_extension_without_printing AS FileNoStamp,
    Documents.File_extension_with_stamp AS FileWithStamp,
    Discipline.Name AS Discipline_Name,
    Speciality.Name AS Speciality_Name,
    Users.Full_name AS Teacher_Name
FROM 
    Documents
LEFT JOIN Discipline ON Documents.Discipline = Discipline.id
LEFT JOIN Speciality ON Discipline.Speciality = Speciality.id
LEFT JOIN Users ON Documents.Teacher = Users.id
LEFT JOIN Execution_Status es ON Documents.Execution_Status = es.id
WHERE 
    Documents.Head_of_the_department = %s
    AND Documents.Teacher IS NULL

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
                self.table_widget.setItem(row_idx, 0, QTableWidgetItem(row["Speciality_Name"] or "—"))
                self.table_widget.setItem(row_idx, 1, QTableWidgetItem(row["Discipline_Name"] or "—"))
                self.table_widget.setItem(row_idx, 2, QTableWidgetItem(row["Teacher_Name"] or "—"))
                self.table_widget.setItem(row_idx, 3, QTableWidgetItem(row["ExecutionStatus"] or "—"))
                self.table_widget.setItem(row_idx, 4, QTableWidgetItem(str(row["LastUpdate"]) if row["LastUpdate"] else "—"))
                self.table_widget.setItem(row_idx, 5, QTableWidgetItem(str(row["Priority"]) if row["Priority"] else "—"))
                self.table_widget.setItem(row_idx, 6, QTableWidgetItem(row["Comment"] or "—"))

                field_map = {
                    "FileNoStamp": "File_extension_without_printing",
                    "FileWithStamp": "File_extension_with_stamp"
                }

                for col_idx, field_alias in [(7, "FileNoStamp"), (8, "FileWithStamp")]:
                    file_path = row[field_alias]
                    if file_path:
                        btn = QPushButton("Скачать")
                        btn.setStyleSheet("color: rgb(1, 50, 32);")
                        btn.setProperty('file_path', file_path)
                        btn.setProperty('discipline', row["Discipline_Name"])
                        btn.setProperty('speciality', row["Speciality_Name"])
                        btn.setProperty('field', field_map[field_alias])  # <== реальное имя поля в БД
                        btn.setProperty('doc_id', row["ID"])
                        btn.clicked.connect(self.download_document_file)
                        self.table_widget.setCellWidget(row_idx, col_idx, btn)
                    else:
                        self.table_widget.setItem(row_idx, col_idx, QTableWidgetItem("Нет файла"))

                # Привязка document ID к первой ячейке строки
                item = self.table_widget.item(row_idx, 0)
                item.setData(Qt.UserRole, row["ID"])

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
