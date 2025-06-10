import logging
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QFileDialog, QListWidget, QMessageBox, QMenu, QAction, QVBoxLayout,
    QInputDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt
from pages.TeacherDocumentViewer import TeacherDocumentViewer
from pages.TableFilterSort import TableFilterSort
import os


class DocumentViewer:
    def __init__(self, table_widget, db_manager, user_id):
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.filter_sort = TableFilterSort(table_widget)
        self.user_id = user_id
        self.setup_table()

    def setup_table(self):
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["Специальность", "Дисциплина", "Документ с печатью"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSortingEnabled(True)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_row_context_menu)
        self.load_documents()
        self.BASE_UPLOAD_DIR = "/home/user/uploads/"  # Базовая директория для файлов


    def show_row_context_menu(self, pos):
        index = self.table_widget.indexAt(pos)
        if not index.isValid():
            logging.debug("Невалидный индекс при правом клике.")
            return

        row = index.row()
        document_id = None

        # Пытаемся найти document_id в любой ячейке строки
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

        if not self.has_access(document_id):
            grant_access_action = QAction("Выдать доступ", menu)
            grant_access_action.triggered.connect(lambda: self.grant_access(document_id))
            menu.addAction(grant_access_action)

        my_documents_action = QAction("Мои документы", menu)
        my_documents_action.triggered.connect(self.show_my_documents)
        menu.addAction(my_documents_action)

        menu.exec_(self.table_widget.viewport().mapToGlobal(pos))


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
                SELECT d.id AS DocumentID,
                       s.Name AS Speciality,
                       disc.Name AS Discipline,
                       d.File_extension_with_stamp
                FROM Documents d
                JOIN Discipline disc ON d.Discipline = disc.id
                JOIN Speciality s ON disc.Speciality = s.id
                JOIN Department dept ON s.Department = dept.id
                JOIN Users u ON dept.Head_of_the_department = u.id
                WHERE u.id = %s;
            """
            result = self.db_manager.execute_query(query, (self.user_id,))
            self.table_widget.setRowCount(len(result))

            for row_idx, row_data in enumerate(result):
                self.table_widget.setItem(row_idx, 0, QTableWidgetItem(row_data["Speciality"]))
                self.table_widget.setItem(row_idx, 1, QTableWidgetItem(row_data["Discipline"]))

                file_path = row_data["File_extension_with_stamp"]
                if file_path:
                    btn = QPushButton("Скачать")
                    btn.setStyleSheet("color: rgb(1, 50, 32)")
                    btn.clicked.connect(lambda _, 
                                        path=file_path,
                                        disc=row_data["Discipline"],
                                        spec=row_data["Speciality"]: 
                                        self.download_file_by_path(path, disc, spec))
                    btn.setProperty('doc_id', row_data["DocumentID"])
                    btn.setProperty('field', "File_extension_with_stamp")
                    self.table_widget.setCellWidget(row_idx, 2, btn)
                else:
                    self.table_widget.setItem(row_idx, 2, QTableWidgetItem("Нет файла"))

                item = self.table_widget.item(row_idx, 0)
                item.setData(Qt.UserRole, row_data["DocumentID"])

                # Подсказки для всех ячеек строки
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row_idx, col)
                    if item:
                        item.setToolTip(item.text())
                    # 7. Восстанавливаем состояние
            self.table_widget.setSortingEnabled(True)
            self.table_widget.verticalScrollBar().setValue(scroll_pos)
            self.table_widget.setUpdatesEnabled(True)

        except Exception as e:
            logging.error(f"Ошибка при загрузке документов: {e}")

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

    def show_my_documents(self):
        self.table_widget.setRowCount(0)
        viewer = TeacherDocumentViewer(self.table_widget, self.db_manager, self.user_id)
        viewer.setup_table()
        viewer.fetch_data_from_db()
        QMessageBox.information(self.table_widget, "Мои документы", "Здесь будут ваши документы.")

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
