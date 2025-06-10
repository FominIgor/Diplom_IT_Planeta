import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import logging

class FileManager:
    @staticmethod
    def download_file(db_manager, table_widget, table_name, record_id, file_column, display_name, extension_column=None):
        """
        Универсальный метод для скачивания файла из базы данных
        
        :param db_manager: Менеджер базы данных
        :param table_widget: Виджет таблицы (для родительского окна)
        :param table_name: Имя таблицы
        :param record_id: ID записи
        :param file_column: Имя столбца с файлом
        :param display_name: Отображаемое имя файла
        :param extension_column: Имя столбца с расширением (опционально)
        """
        try:
            # Формируем SQL запрос
            if extension_column:
                query = f"SELECT {file_column}, {extension_column} FROM {table_name} WHERE id = %s"
            else:
                query = f"SELECT {file_column} FROM {table_name} WHERE id = %s"
            
            result = db_manager.execute_query(query, (record_id,))
            
            if result and result[0][file_column]:
                file_data = result[0][file_column]
                file_extension = result[0].get(extension_column, "bin") if extension_column else "bin"
                
                file_path, _ = QFileDialog.getSaveFileName(
                    table_widget,
                    "Сохранить файл",
                    f"{display_name}_{record_id}.{file_extension}",
                    "Все файлы (*)"
                )
                
                if file_path:
                    with open(file_path, 'wb') as file:
                        file.write(file_data)
                    QMessageBox.information(table_widget, "Успех", f"Файл успешно скачан: {file_path}")
            else:
                QMessageBox.warning(table_widget, "Ошибка", "Файл отсутствует в базе данных.")
                
        except Exception as e:
            logging.error(f"Ошибка при скачивании файла: {e}")
            QMessageBox.critical(table_widget, "Ошибка", f"Не удалось скачать файл: {e}")

    @staticmethod
    def download_file_from_path(table_widget, file_path, display_name):
        """
        Скачивание файла по его пути в файловой системе
        
        :param table_widget: Виджет таблицы (для родительского окна)
        :param file_path: Путь к файлу
        :param display_name: Отображаемое имя файла
        """
        try:
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(table_widget, "Ошибка", f"Файл {display_name} не найден")
                return
                
            save_path, _ = QFileDialog.getSaveFileName(
                table_widget,
                f"Сохранить {display_name}",
                os.path.basename(file_path),
                "Все файлы (*)"
            )
            
            if save_path:
                with open(file_path, 'rb') as src, open(save_path, 'wb') as dst:
                    dst.write(src.read())
                QMessageBox.information(table_widget, "Успех", f"{display_name} сохранен")
                
        except Exception as e:
            logging.error(f"Ошибка скачивания {display_name}: {e}")
            QMessageBox.critical(table_widget, "Ошибка", f"Не удалось скачать {display_name}: {e}")