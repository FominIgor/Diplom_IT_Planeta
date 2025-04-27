import logging
from PyQt5.QtWidgets import (
    QTableWidgetItem, QHeaderView, QPushButton, QDialog, QFileDialog, QListWidget, QMessageBox, QMenu, QAction, QVBoxLayout, 
    QInputDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt
from pages.TeacherDocumentViewer import TeacherDocumentViewer
from pages.TableFilterSort import TableFilterSort #Импорт класса с поиском 



class DocumentViewer:
    def __init__(self, table_widget, db_manager, user_id):
        """Инициализация класса."""
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.filter_sort = TableFilterSort(table_widget)  # Интеграция поиска
        self.user_id = user_id
        self.setup_table()  # Настройка таблицы

    def setup_table(self):
        """Настройка таблицы."""
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(3)  # 3 колонки: Специальность, Дисциплина, Документ с печатью
        self.table_widget.setHorizontalHeaderLabels(["Специальность", "Дисциплина", "Документ с печатью"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Включаем сортировку по столбцам
        self.table_widget.setSortingEnabled(True)

        # Запрещаем редактирование данных
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Подключаем два контекстных меню
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)        
        self.table_widget.customContextMenuRequested.connect(self.show_row_context_menu)  # Для строк
        self.load_documents()

    def show_row_context_menu(self, pos):
        """Показ контекстного меню при правом клике по строке."""
        index = self.table_widget.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()

        # Получаем ID документа из первой колонки
        item = self.table_widget.item(row, 0)  # Берём из 1-й колонки
        if item is None:
            return

        document_id = item.data(Qt.UserRole)  # ID документа теперь в 1-й колонки

        # Проверяем на валидность document_id
        if document_id is None:
            logging.error("Document ID is None, cannot show context menu.")
            return

        menu = QMenu()

        # Проверяем, есть ли у преподавателя доступ к документу
        if not self.has_access(document_id):
            grant_access_action = QAction("Выдать доступ", menu)
            grant_access_action.triggered.connect(lambda: self.grant_access(document_id))
            menu.addAction(grant_access_action)

        my_documents_action = QAction("Мои документы", menu)
        my_documents_action.triggered.connect(self.show_my_documents)
        menu.addAction(my_documents_action)

        menu.exec_(self.table_widget.viewport().mapToGlobal(pos))

    def has_access(self, document_id):
        """Проверка, есть ли у преподавателя доступ к документу."""
        try:
            query = "SELECT * FROM Documents_Access WHERE Teacher = %s AND Document = %s"
            result = self.db_manager.execute_query(query, (self.user_id, document_id))
            return len(result) > 0
        except Exception as e:
            logging.error(f"Ошибка при проверке доступа к документу: {e}")
            return False

    def load_documents(self):
        """Загрузка данных в таблицу."""
        try:
            query = """
                SELECT d.id AS DocumentID, 
                    s.Name AS Speciality, 
                    disc.Name AS Discipline, 
                    d.Execution_Status, 
                    d.Date_of_last_update,
                    d.File_with_stamp  -- Используем правильное поле
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

                # Проверка наличия файла (если файл существует, добавляем кнопку "Скачать")
                if row_data["File_with_stamp"]:  # Здесь заменили на File_with_stamp
                    btn = QPushButton("Скачать")
                    btn.setStyleSheet("color:  rgb(1, 50, 32)")
                    btn.clicked.connect(lambda _, doc_id=row_data["DocumentID"], discipline=row_data["Discipline"], speciality=row_data["Speciality"]: self.download_file(row_data["File_with_stamp"], discipline, speciality))
                    self.table_widget.setCellWidget(row_idx, 2, btn)
                else:
                    self.table_widget.setItem(row_idx, 2, QTableWidgetItem())  # Если файла нет

                # Устанавливаем ID документа в UserRole
                item = self.table_widget.item(row_idx, 0)
                item.setData(Qt.UserRole, row_data["DocumentID"])

            # Добавляем подсказки для ячеек
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row_idx, col)
                if item:
                    item.setToolTip(item.text())

        except Exception as e:
            logging.error(f"Ошибка при загрузке документов: {e}")

    def grant_access(self, document_id):
        """Выдать доступ к документу."""
        logging.debug(f"Granting access to document_id: {document_id}")  # Log document_id
        if document_id is None:
            logging.error("Document ID is None, cannot grant access.")
            return

        dialog = QDialog(self.table_widget)
        dialog.setWindowTitle("Выберите преподавателя")
        layout = QVBoxLayout()

        teacher_list = QListWidget()
        layout.addWidget(teacher_list)

        # Загружаем преподавателей
        try:
            query = "SELECT id, Full_name FROM Users WHERE Teacher = 1"
            teachers = self.db_manager.execute_query(query)
            for teacher in teachers:
                teacher_list.addItem(f"{teacher['id']}: {teacher['Full_name']}")
        except Exception as e:
            logging.error(f"Ошибка загрузки преподавателей: {e}")

        btn_ok = QPushButton("Выдать доступ")
        btn_ok.setStyleSheet("color:  rgb(1, 50, 32)")
        btn_ok.clicked.connect(lambda: self.on_teacher_selected(teacher_list, document_id, dialog))
        layout.addWidget(btn_ok)

        dialog.setLayout(layout)
        dialog.exec_()

    def on_teacher_selected(self, teacher_list, document_id, dialog):
        """Когда преподаватель выбран, выдаем доступ."""
        logging.debug(f"Teacher selected for document_id: {document_id}")  # Log when teacher is selected
        if document_id is None:
            logging.error("Document ID is None, cannot grant access.")
            return
        
        selected_item = teacher_list.currentItem()
        if selected_item:
            teacher_id = int(selected_item.text().split(":")[0])
            
            # Проверяем, есть ли уже доступ для этого преподавателя и документа
            try:
                # Проверка на существование записи
                query = "SELECT * FROM Documents_Access WHERE Teacher = %s AND Document = %s"
                existing_access = self.db_manager.execute_query(query, (teacher_id, document_id))
                
                if existing_access:
                    logging.info(f"Доступ уже выдан преподавателю с ID {teacher_id} для документа {document_id}.")
                    QMessageBox.information(self.table_widget, "Информация", "Этот преподаватель уже имеет доступ к документу.")
                else:
                    # Если доступа нет, выдаем доступ
                    query = "INSERT INTO Documents_Access (Teacher, Document, Rights) VALUES (%s, %s, 1);"
                    self.db_manager.execute_query(query, (teacher_id, document_id))
                    QMessageBox.information(self.table_widget, "Успех", "Доступ выдан!")
            except Exception as e:
                logging.error(f"Ошибка при проверке/выдаче доступа: {e}")
                QMessageBox.critical(self.table_widget, "Ошибка", f"Ошибка: {e}")
        else:
            QMessageBox.warning(self, "Ошибка", "Выберите преподавателя.")
        dialog.accept()

    def show_my_documents(self):
        """Показать мои документы."""
        
        # Очистим текущие данные в таблице (удаляем все строки и столбцы)
        self.table_widget.setRowCount(0)

        
        # Теперь инициализируем новый объект TeacherDocumentViewer
        obj_class_one = TeacherDocumentViewer(self.table_widget, self.db_manager, self.user_id)
        
        # Настроим таблицу для нового объекта
        obj_class_one.setup_table()
        
        # Теперь вызываем метод для загрузки новых данных
        obj_class_one.fetch_data_from_db()  # Загрузка данных для "Мои документы"
        
        # Показываем информацию, что данные обновлены
        QMessageBox.information(self.table_widget, "Мои документы", "Здесь будут ваши документы.")    

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
