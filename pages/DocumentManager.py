import os
from PyQt5.QtWidgets import (
    QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidgetItem, QHeaderView,QHBoxLayout, QGroupBox,
    QTextEdit, QDialogButtonBox
)
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
import logging
from pathlib import Path
from PyQt5.QtWidgets import QFileDialog, QMessageBox  # <-- Сразу импортируем

import traceback
import shutil
import uuid
import datetime
from pages.TableFilterSort import TableFilterSort


class DocumentManager:
    def __init__(self, table_widget, db_manager, teacher_id):
        self.table_widget = table_widget
        self.db_manager = db_manager
        self.teacher_id = teacher_id        
        self.BASE_UPLOAD_DIR = "/home/user/uploads/"  # Базовая директория для файлов
        # Проверяем и создаем директорию при инициализации
        try:
            os.makedirs(self.BASE_UPLOAD_DIR, exist_ok=True)
            # Устанавливаем правильные права
            os.chmod(self.BASE_UPLOAD_DIR, 0o777)
        except Exception as e:
            logging.error(f"Ошибка при создании upload директории: {e}")

        self.filter_sort = TableFilterSort(table_widget)
        self.setup_table()
        self.update_table()

    def setup_table(self):
        """Настройка таблицы с колонками для ОПОП, учебных планов и шаблонов"""
        self.table_widget.setColumnCount(14)
        headers = [
            "ID", "Дисциплина", "Статус выполнения", "Дата обновления", "Кафедра", 
            "Преподаватель", "Приоритет исполнения", "Комментарий", 
            "Файл (без печати)", "Файл с печатью", "Дополнительные материалы",
            "ОПОП", "Учебный план", "Шаблоны"
        ]
        
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.table_widget.cellDoubleClicked.connect(self.download_opop_file)

    def setup_file_columns(self, row_idx, doc):
        """Настройка колонок с файлами документов"""
        file_columns = [
            ('File_extension_without_printing', 8),
            ('File_extension_with_stamp', 9),
            ('Additional_materials', 10)
        ]
        
        for field, col in file_columns:
            if doc.get(field):
                btn = QPushButton("Скачать")
                btn.setStyleSheet("color: rgb(1, 50, 32)")
                btn.setProperty('doc_id', doc['id'])
                btn.setProperty('field', field)
                btn.clicked.connect(self.download_document_file)
                self.table_widget.setCellWidget(row_idx, col, btn)
            else:
                self.table_widget.setItem(row_idx, col, QTableWidgetItem("Нет файла"))



    def download_document_file(self):
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




    def show_context_menu(self, position):
        """Отображает контекстное меню для работы с документами."""
        menu = QtWidgets.QMenu()
        add_action = menu.addAction("Добавить")
        delete_action = menu.addAction("Удалить")
        modify_action = menu.addAction("Изменить")
        add_action.triggered.connect(self.add_record)
        delete_action.triggered.connect(self.delete_record)
        modify_action.triggered.connect(self.modify_record)
        menu.exec_(self.table_widget.viewport().mapToGlobal(position))
    
    def add_record(self):
        """Добавление нового документа с выбором кафедры, специальности и дисциплины"""
        dialog = QDialog()
        dialog.setWindowTitle("Добавить документ")
        layout = QVBoxLayout()

        # 1. Выбор кафедры
        dept_label = QLabel("Кафедра:")
        self.dept_combo = QComboBox()
        layout.addWidget(dept_label)
        layout.addWidget(self.dept_combo)

        # 2. Выбор специальности (появится после выбора кафедры)
        spec_label = QLabel("Специальность:")
        self.spec_combo = QComboBox()
        self.spec_combo.setEnabled(False)
        layout.addWidget(spec_label)
        layout.addWidget(self.spec_combo)

        # 3. Выбор дисциплины (появится после выбора специальности)
        disc_label = QLabel("Дисциплина:")
        self.disc_combo = QComboBox()
        self.disc_combo.setEnabled(False)
        layout.addWidget(disc_label)
        layout.addWidget(self.disc_combo)

        # 4. Приоритет исполнения
        priority_label = QLabel("Приоритет исполнения:")
        self.priority_input = QLineEdit()
        layout.addWidget(priority_label)
        layout.addWidget(self.priority_input)

        # 5. Комментарий (необязательное поле)
        comment_label = QLabel("Комментарий (необязательно):")
        self.comment_input = QLineEdit()
        layout.addWidget(comment_label)
        layout.addWidget(self.comment_input)

        # Кнопка сохранения
        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet("color: rgb(1, 50, 32)")
        save_btn.clicked.connect(lambda: self.save_new_document(dialog))
        layout.addWidget(save_btn)

        # Подключаем сигналы
        self.dept_combo.currentIndexChanged.connect(self.load_specialities)
        self.spec_combo.currentIndexChanged.connect(self.load_disciplines)

        # Загружаем кафедры
        self.load_departments()

        dialog.setLayout(layout)
        dialog.exec_()

    def load_departments(self):
        """Загрузка списка кафедр"""
        try:
            self.dept_combo.clear()
            query = "SELECT id, Name FROM Department"
            departments = self.db_manager.execute_query(query)
            self.dept_combo.addItem("-- Выберите кафедру --", None)
            
            for dept in departments:
                self.dept_combo.addItem(dept["Name"], dept["id"])
        except Exception as e:
            logging.error(f"Ошибка загрузки кафедр: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить кафедры: {e}")

    def load_specialities(self):
        """Загрузка специальностей для выбранной кафедры"""
        dept_id = self.dept_combo.currentData()
        if not dept_id:
            self.spec_combo.clear()
            self.spec_combo.setEnabled(False)
            return

        try:
            self.spec_combo.clear()
            query = "SELECT id, Name FROM Speciality WHERE Department = %s"
            specialities = self.db_manager.execute_query(query, (dept_id,))
            self.spec_combo.addItem("-- Выберите специальность --", None)
            
            for spec in specialities:
                self.spec_combo.addItem(spec["Name"], spec["id"])
            
            self.spec_combo.setEnabled(bool(specialities))
        except Exception as e:
            logging.error(f"Ошибка загрузки специальностей: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить специальности: {e}")

    def load_disciplines(self):
        """Загрузка дисциплин для выбранной специальности"""
        spec_id = self.spec_combo.currentData()
        if not spec_id:
            self.disc_combo.clear()
            self.disc_combo.setEnabled(False)
            return

        try:
            self.disc_combo.clear()
            query = "SELECT id, Name FROM Discipline WHERE Speciality = %s"
            disciplines = self.db_manager.execute_query(query, (spec_id,))
            self.disc_combo.addItem("-- Выберите дисциплину --", None)
            
            for disc in disciplines:
                self.disc_combo.addItem(disc["Name"], disc["id"])
            
            self.disc_combo.setEnabled(bool(disciplines))
        except Exception as e:
            logging.error(f"Ошибка загрузки дисциплин: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить дисциплины: {e}")

    def save_new_document(self, dialog):
        """Сохранение нового документа в БД"""
        try:
            # Проверяем обязательные поля
            if not self.dept_combo.currentData():
                QMessageBox.warning(dialog, "Ошибка", "Выберите кафедру")
                return
                
            if not self.spec_combo.currentData():
                QMessageBox.warning(dialog, "Ошибка", "Выберите специальность")
                return
                
            if not self.disc_combo.currentData():
                QMessageBox.warning(dialog, "Ошибка", "Выберите дисциплину")
                return
                
            if not self.priority_input.text().strip():
                QMessageBox.warning(dialog, "Ошибка", "Укажите приоритет исполнения")
                return

            # Подготавливаем данные
            data = {
                'discipline_id': self.disc_combo.currentData(),
                'department_id': self.dept_combo.currentData(),
                'priority': self.priority_input.text().strip(),
                'comment': self.comment_input.text().strip(),
                'teacher_id': self.teacher_id,
                'status_id': 1,  # Статус "Создан"
                'update_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # SQL запрос
            query = """
                INSERT INTO Documents (
                    Discipline, Execution_Status, Date_of_last_update, 
                    Head_of_the_department, Teacher, Execution_priority, 
                    Comment
                )
                VALUES (%(discipline_id)s, %(status_id)s, %(update_date)s, 
                    %(department_id)s, NULL, %(priority)s, 
                    %(comment)s)
            """

            # Выполняем запрос
            self.db_manager.execute_query(query, data)
            QtCore.QTimer.singleShot(100, self.update_table)
    
            dialog.close()
            QMessageBox.information(dialog, "Успех", "Документ успешно добавлен")
            dialog.close()
            self.update_table()
            
        except Exception as e:
            logging.error(f"Ошибка сохранения документа: {e}")
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить документ: {e}")


    def modify_record(self):
        """Редактирование существующего документа"""
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self.table_widget, "Ошибка", "Выберите запись для редактирования.")
                return

            record_id = self.table_widget.item(selected_row, 0).text()
            
            # Получаем текущие данные документа
            query = """
                SELECT d.id, d.Discipline, d.Execution_Status, d.Teacher, 
                    d.Execution_priority, d.Comment, d.File_extension_without_printing,
                    d.File_extension_with_stamp, d.Additional_materials,
                    disc.Speciality AS speciality_id, sp.Department AS department_id
                FROM Documents d
                JOIN Discipline disc ON d.Discipline = disc.id
                JOIN Speciality sp ON disc.Speciality = sp.id
                WHERE d.id = %s
            """
            current_data = self.db_manager.execute_query(query, (record_id,))[0]

            dialog = QDialog()
            dialog.setWindowTitle(f"Редактирование документа ID: {record_id}")
            layout = QVBoxLayout()

            # 1. Кафедра (только просмотр)
            dept_label = QLabel("Кафедра:")
            self.dept_combo = QComboBox()
            self.dept_combo.setEnabled(False)
            layout.addWidget(dept_label)
            layout.addWidget(self.dept_combo)

            # 2. Специальность (только просмотр)
            spec_label = QLabel("Специальность:")
            self.spec_combo = QComboBox()
            self.spec_combo.setEnabled(False)
            layout.addWidget(spec_label)
            layout.addWidget(self.spec_combo)

            # 3. Дисциплина (можно изменить)
            disc_label = QLabel("Дисциплина:")
            self.disc_combo = QComboBox()
            layout.addWidget(disc_label)
            layout.addWidget(self.disc_combo)

            # Загружаем данные для выпадающих списков
            self._load_initial_data(current_data)

            # 4. Статус выполнения
            status_label = QLabel("Статус выполнения:")
            self.status_combo = QComboBox()
            self._load_statuses(current_data['Execution_Status'])
            layout.addWidget(status_label)
            layout.addWidget(self.status_combo)

            # 5. Преподаватель
            teacher_label = QLabel("Преподаватель:")
            self.teacher_combo = QComboBox()
            self._load_teachers(current_data['Teacher'])
            layout.addWidget(teacher_label)
            layout.addWidget(self.teacher_combo)

            # 6. Приоритет исполнения
            priority_label = QLabel("Приоритет исполнения:")
            self.priority_input = QLineEdit(str(current_data['Execution_priority']))
            layout.addWidget(priority_label)
            layout.addWidget(self.priority_input)

            # 7. Комментарий
            comment_label = QLabel("Комментарий:")
            self.comment_input = QTextEdit()
            self.comment_input.setPlainText(current_data['Comment'] or "")
            layout.addWidget(comment_label)
            layout.addWidget(self.comment_input)

            # 8. Файлы
            self._add_file_controls(layout, current_data, record_id)

            # Кнопки сохранения/отмены
            btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            btn_box.accepted.connect(lambda: self._save_modified_record(dialog, record_id))
            btn_box.rejected.connect(dialog.reject)
            layout.addWidget(btn_box)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            logging.error(f"Ошибка при открытии редактирования: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось открыть редактирование: {e}")

    def check_disk_space(self, required_size):
        """Проверяет, достаточно ли места на диске для загрузки файла"""
        try:
            # Получаем статистику по диску, куда загружаются файлы
            disk_usage = shutil.disk_usage(self.BASE_UPLOAD_DIR)
            free_space = disk_usage.free
            
            # Оставляем 10% места в качестве буфера
            buffer_space = disk_usage.total * 0.1
            available_space = free_space - buffer_space
            
            if required_size > available_space:
                QMessageBox.warning(None, "Недостаточно места", 
                                f"Недостаточно места на диске. Требуется: {required_size//(1024*1024)} МБ\n"
                                f"Доступно: {available_space//(1024*1024)} МБ")
                return False
            return True
        except Exception as e:
            logging.error(f"Ошибка проверки места на диске: {e}")
            QMessageBox.critical(None, "Ошибка", "Не удалось проверить место на диске")
            return False

    def _upload_file(self, file_type):
        """Загрузка файлов с проверкой места на диске и автообновлением статуса"""
        try:
            path, _ = QFileDialog.getOpenFileName(
                None, 
                f"Выберите файл ({file_type})", 
                "", 
                "Все файлы (*)"
            )
            if not path:
                return

            logging.info(f"Начата загрузка файла: {path}")

            # Проверка размера файла
            file_size = os.path.getsize(path)
            if not self.check_disk_space(file_size):
                return

            # Сохраняем оригинальное расширение
            original_name = Path(path).name
            file_ext = Path(path).suffix
            
            # Копирование файла
            src_path = Path(path).resolve().as_posix()
            filename = f"{uuid.uuid4().hex}{file_ext}"
            dest_path = os.path.join(self.BASE_UPLOAD_DIR, filename)

            os.makedirs(self.BASE_UPLOAD_DIR, exist_ok=True)
            shutil.copy2(src_path, dest_path)
            os.chmod(dest_path, 0o666)

            # Сохраняем имя файла и оригинальное имя
            self.file_data[file_type] = {
                'server_name': filename,
                'original_name': original_name
            }

            # Устанавливаем статус "Сохранен", если загружается файл с печатью
            if file_type == "with_stamp":
                query = "SELECT id FROM Execution_Status WHERE Status = %s"
                result = self.db_manager.execute_query(query, ("Сохранен",))
                if result:
                    status_id = result[0]['id']
                    self.status_combo.setCurrentIndex(self.status_combo.findData(status_id))
                    logging.info("Статус 'Сохранен' установлен автоматически")

            QMessageBox.information(
                None, 
                "Успешно", 
                f"Файл успешно загружен:\n{original_name}"
            )

        except Exception as e:
            logging.error(f"Ошибка загрузки: {traceback.format_exc()}")
            QMessageBox.critical(
                None, 
                "Ошибка загрузки", 
                f"Не удалось загрузить файл:\n{str(e)}"
            )

    def _load_initial_data(self, current_data):
        """Загружает начальные данные в выпадающие списки"""
        # Загружаем кафедры и выбираем текущую
        self.dept_combo.clear()
        query = "SELECT id, Name FROM Department"
        departments = self.db_manager.execute_query(query)
        for dept in departments:
            self.dept_combo.addItem(dept['Name'], dept['id'])
            if dept['id'] == current_data['department_id']:
                self.dept_combo.setCurrentIndex(self.dept_combo.count()-1)

        # Загружаем специальности для текущей кафедры
        self.spec_combo.clear()
        query = "SELECT id, Name FROM Speciality WHERE Department = %s"
        specialities = self.db_manager.execute_query(query, (current_data['department_id'],))
        for spec in specialities:
            self.spec_combo.addItem(spec['Name'], spec['id'])
            if spec['id'] == current_data['speciality_id']:
                self.spec_combo.setCurrentIndex(self.spec_combo.count()-1)

        # Загружаем дисциплины для текущей специальности
        self.disc_combo.clear()
        query = "SELECT id, Name FROM Discipline WHERE Speciality = %s"
        disciplines = self.db_manager.execute_query(query, (current_data['speciality_id'],))
        for disc in disciplines:
            self.disc_combo.addItem(disc['Name'], disc['id'])
            if disc['id'] == current_data['Discipline']:
                self.disc_combo.setCurrentIndex(self.disc_combo.count()-1)

    def _load_statuses(self, current_status):
        """Загружает статусы выполнения"""
        self.status_combo.clear()
        query = "SELECT id, Status FROM Execution_Status"
        statuses = self.db_manager.execute_query(query)
        for status in statuses:
            self.status_combo.addItem(status['Status'], status['id'])
            if status['id'] == current_status:
                self.status_combo.setCurrentIndex(self.status_combo.count()-1)

    def _load_teachers(self, current_teacher_id):
        """Загружает список преподавателей"""
        self.teacher_combo.clear()
        query = "SELECT id, Full_name FROM Users WHERE Teacher = 1"
        teachers = self.db_manager.execute_query(query)
        self.teacher_combo.addItem("Не назначен", None)
        for teacher in teachers:
            self.teacher_combo.addItem(teacher['Full_name'], teacher['id'])
            if teacher['id'] == current_teacher_id:
                self.teacher_combo.setCurrentIndex(self.teacher_combo.count()-1)

    def _add_file_controls(self, layout, current_data, record_id):
        """Добавляет элементы управления для файлов"""
        file_types = [
            ("Файл без печати", "without_printing", current_data['File_extension_without_printing']),
            ("Файл с печатью", "with_stamp", current_data['File_extension_with_stamp']),
            ("Доп. материалы", "additional", current_data['Additional_materials'])
        ]
        
        self.file_data = {}
        
        for label, file_type, current_file in file_types:
            group = QGroupBox(label)
            group_layout = QHBoxLayout()
            
            # Кнопка загрузки нового файла
            btn_upload = QPushButton("Загрузить новый")
            btn_upload.clicked.connect(lambda _, t=file_type: self._upload_file(t))
            
            # Кнопка скачивания текущего файла
            btn_download = QPushButton("Скачать текущий")
            btn_download.setEnabled(bool(current_file))
            btn_download.clicked.connect(lambda _, t=file_type: self._download_file(record_id, t))
            
            group_layout.addWidget(btn_upload)
            group_layout.addWidget(btn_download)
            group.setLayout(group_layout)
            layout.addWidget(group)
            
            # Сохраняем текущие данные файла
            self.file_data[file_type] = current_file
    def _download_file(self, doc_id, file_type):
        """Скачивает текущий файл с сервера"""
        try:
            filename = self.file_data[file_type]
            if not filename:
                return
                
            source_path = os.path.join(self.BASE_UPLOAD_DIR, filename)
            
            if not os.path.exists(source_path):
                QMessageBox.warning(None, "Ошибка", "Файл не найден на сервере")
                return
                
            path, _ = QFileDialog.getSaveFileName(
                None, 
                "Сохранить файл", 
                filename, 
                "Все файлы (*)"
            )
            
            if path:
                shutil.copy2(source_path, path)
                QMessageBox.information(None, "Успех", "Файл сохранен")
        except Exception as e:
            logging.error(f"Ошибка скачивания файла: {e}")
            QMessageBox.critical(None, "Ошибка", f"Не удалось сохранить файл: {e}")
    def _save_modified_record(self, dialog, record_id):
        try:
            # Проверяем обязательные поля
            if None in (self.disc_combo.currentData(), self.status_combo.currentData()):
                QMessageBox.warning(dialog, "Ошибка", "Не все обязательные поля заполнены")
                return

            # Подготавливаем данные
            params = [
                self.disc_combo.currentData(),
                self.status_combo.currentData(),
                self.teacher_combo.currentData() if self.teacher_combo.currentData() else None,
                int(self.priority_input.text()) if self.priority_input.text().isdigit() else 0,
                self.comment_input.toPlainText(),
                self.file_data.get('without_printing', {}).get('server_name') if isinstance(self.file_data.get('without_printing'), dict) else self.file_data.get('without_printing'),
                self.file_data.get('with_stamp', {}).get('server_name') if isinstance(self.file_data.get('with_stamp'), dict) else self.file_data.get('with_stamp'),
                self.file_data.get('additional', {}).get('server_name') if isinstance(self.file_data.get('additional'), dict) else self.file_data.get('additional'),
                record_id
            ]


            # Логируем параметры для отладки
            logging.debug(f"Params to save: {params}")

            query = """
                UPDATE Documents SET
                    Discipline = %s,
                    Execution_Status = %s,
                    Teacher = %s,
                    Execution_priority = %s,
                    Comment = %s,
                    File_extension_without_printing = %s,
                    File_extension_with_stamp = %s,
                    Additional_materials = %s,
                    Date_of_last_update = NOW()
                WHERE id = %s
            """
            
            # Логируем запрос для отладки
            logging.debug(f"Executing query: {query}")
            
            self.db_manager.execute_query(query, tuple(params))
            QMessageBox.information(dialog, "Успех", "Изменения сохранены")
            dialog.accept()
            self.update_table()
            
        except Exception as e:
            logging.error(f"Ошибка сохранения изменений: {str(e)}", exc_info=True)
            QMessageBox.critical(dialog, "Ошибка", f"Не удалось сохранить изменения: {str(e)}")

    def load_file(self, file_type):
        """Загружает файл и сохраняет его данные и имя."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.table_widget, 
            f"Выберите файл для {file_type}", 
            "", 
            "Все файлы (*)"
        )
        if file_path:
            try:
                with open(file_path, 'rb') as file:
                    data = file.read()
                filename = os.path.basename(file_path)
                if file_type == "additional":
                    self.additional_materials_data = data
                    self.additional_materials_filename = filename
            except Exception as e:
                logging.error(f"Ошибка при загрузке файла: {e}")
                QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось загрузить файл: {e}")

    def delete_record(self):
        """Удаляет выбранную запись документа и связанные с ним данные."""
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self.table_widget, "Ошибка", "Выберите запись для удаления.")
                return

            record_id = self.table_widget.item(selected_row, 0).text()

            # Удаляем связи из таблицы Documents_Access
            delete_access_query = "DELETE FROM Documents_Access WHERE Document = %s"
            self.db_manager.execute_query(delete_access_query, (record_id,))

            # Удаляем сам документ
            delete_document_query = "DELETE FROM Documents WHERE id = %s"
            self.db_manager.execute_query(delete_document_query, (record_id,))

            QMessageBox.information(self.table_widget, "Успех", "Документ и связанные данные удалены.")
            self.update_table()
        except Exception as e:
            logging.error(f"Ошибка при удалении документа: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось удалить документ: {e}")

        

    def update_table(self):
        """Обновление таблицы с исправлением проблем переключения страниц"""
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
            
            # 5. Получаем данные (ваш существующий код)
            opop_data = self.db_manager.execute_query("SELECT Speciality, OPOP_path, Syllabus_path, Program_path FROM OPOP_UP_Program")
            speciality_opop_map = {item['Speciality']: {'opop': item['OPOP_path'], 'syllabus': item['Syllabus_path'], 'program': item['Program_path']} for item in opop_data}
            
            documents = self.db_manager.execute_query("""
                SELECT d.id, disc.Name AS Discipline, es.Status AS Execution_Status,
                    d.Date_of_last_update, dept.Name AS Department,
                    u.Full_name AS Teacher, d.Execution_priority, d.Comment,
                    d.File_extension_without_printing, d.File_extension_with_stamp,
                    d.Additional_materials, disc.Speciality AS Speciality_id
                FROM Documents d
                LEFT JOIN Discipline disc ON d.Discipline = disc.id
                LEFT JOIN Execution_Status es ON d.Execution_Status = es.id
                LEFT JOIN Department dept ON d.Head_of_the_department = dept.id
                LEFT JOIN Users u ON d.Teacher = u.id
                ORDER BY d.id DESC
            """)

            # 6. Заполняем таблицу
            for row_idx, doc in enumerate(documents):
                self.table_widget.insertRow(row_idx)
                
                  # Заполнение текстовых данных (первые 8 колонок)
                text_columns = [
                    'id', 'Discipline', 'Execution_Status', 'Date_of_last_update',
                    'Department', 'Teacher', 'Execution_priority', 'Comment'
                ]
                for col_idx, key in enumerate(text_columns):
                    item = QTableWidgetItem(str(doc.get(key, '')))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.table_widget.setItem(row_idx, col_idx, item)

                # Кнопки скачивания файлов (колонки 8–10)
                file_columns = [
                    ('File_extension_without_printing', 8),
                    ('File_extension_with_stamp', 9),
                    ('Additional_materials', 10)
                ]
                for field, col in file_columns:
                    if doc.get(field):
                        btn = QPushButton("Скачать")
                        btn.setStyleSheet("color: rgb(1, 50, 32);")
                        btn.setProperty('doc_id', doc['id'])
                        btn.setProperty('field', field)
                        btn.clicked.connect(self.download_document_file)
                        self.table_widget.setCellWidget(row_idx, col, btn)
                    else:
                        self.table_widget.setItem(row_idx, col, QTableWidgetItem("Нет файла"))

                # Данные ОПОП по специальности
                speciality_id = doc.get('Speciality_id')
                opop_info = speciality_opop_map.get(speciality_id, {})

                # Колонка ОПОП (11)
                if opop_info.get('opop'):
                    btn = QPushButton("Скачать")
                    btn.setStyleSheet("color: rgb(1, 50, 32);")
                    btn.setProperty('file_path', opop_info['opop'])
                    btn.clicked.connect(lambda _, r=row_idx, c=11: self.download_opop_file(r, c))
                    self.table_widget.setCellWidget(row_idx, 11, btn)
                else:
                    self.table_widget.setItem(row_idx, 11, QTableWidgetItem("Нет данных"))

                # Колонка Учебный план (12)
                if opop_info.get('syllabus'):
                    btn = QPushButton("Скачать")
                    btn.setStyleSheet("color: rgb(1, 50, 32);")
                    btn.setProperty('file_path', opop_info['syllabus'])
                    btn.clicked.connect(lambda _, r=row_idx, c=12: self.download_opop_file(r, c))
                    self.table_widget.setCellWidget(row_idx, 12, btn)
                else:
                    self.table_widget.setItem(row_idx, 12, QTableWidgetItem("Нет данных"))

                # Колонка Шаблоны (13)
                if opop_info.get('program'):
                    btn = QPushButton("Скачать")
                    btn.setStyleSheet("color: rgb(1, 50, 32);")
                    btn.setProperty('file_path', opop_info['program'])
                    btn.clicked.connect(lambda _, r=row_idx, c=13: self.download_opop_file(r, c))
                    self.table_widget.setCellWidget(row_idx, 13, btn)
                else:
                    self.table_widget.setItem(row_idx, 13, QTableWidgetItem("Нет данных"))
                
                for col in range(self.table_widget.columnCount()):
                    item = self.table_widget.item(row_idx, col)
                    if item:
                        item.setToolTip(item.text())

            # 7. Восстанавливаем состояние
            self.table_widget.setSortingEnabled(True)
            self.table_widget.verticalScrollBar().setValue(scroll_pos)
            self.table_widget.setUpdatesEnabled(True)
            
        except Exception as e:
            logging.error(f"Ошибка обновления таблицы: {e}")
            self.table_widget.setSortingEnabled(True)
            self.table_widget.setUpdatesEnabled(True)


    def download_opop_file(self, row, column):
        try:
            import os
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            from paramiko import SSHClient, AutoAddPolicy
            from scp import SCPClient
            import logging

            button = self.table_widget.cellWidget(row, column)
            logging.debug(f"Попытка получить кнопку из ячейки: row={row}, column={column}")
            if not isinstance(button, QPushButton):
                QMessageBox.warning(self.table_widget, "Ошибка", "Кнопка не найдена в ячейке.")
                return

            file_path = button.property('file_path')
            logging.debug(f"file_path из property кнопки: {file_path}")
            if not file_path:
                QMessageBox.warning(self.table_widget, "Ошибка", "Путь к файлу не задан.")
                return

            filename = os.path.basename(file_path)

            # --- Выбор места сохранения ---
            save_path, _ = QFileDialog.getSaveFileName(
                self.table_widget,
                "Сохранить файл как",
                filename,
                "Все файлы (*)"
            )
            if not save_path:
                return

            # --- SSH-параметры из объекта подключения ---
            ssh_host = self.db_manager.ssh_host
            ssh_user = self.db_manager.ssh_user
            ssh_key_path = r"pages/id_ed25519"  # Путь к приватному ключу

            # --- Подключение по SSH и SCP ---
            ssh = SSHClient()
            ssh.set_missing_host_key_policy(AutoAddPolicy())
            logging.debug(f"Подключение к SSH: {ssh_user}@{ssh_host} с ключом {ssh_key_path}")

            ssh.connect(
                hostname=ssh_host,
                username=ssh_user,
                key_filename=ssh_key_path
            )
            logging.debug("SSH-подключение успешно установлено.")

            with SCPClient(ssh.get_transport()) as scp:
                logging.debug(f"Скачивание {file_path} на {save_path}")
                scp.get(file_path, save_path)

            QMessageBox.information(self.table_widget, "Успех", f"Файл успешно сохранён:\n{save_path}")
            logging.info(f"Файл успешно скачан с сервера в: {save_path}")

        except FileNotFoundError:
            logging.error(f"Файл не существует на сервере: {file_path}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Файл не найден:\n{file_path}")
        except Exception as e:
            logging.error(f"Ошибка при скачивании файла: {e}")
            QMessageBox.critical(self.table_widget, "Ошибка", f"Не удалось скачать файл:\n{e}")
