from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
import sys
from PyQt5.QtGui import QIcon, QPixmap
from pages.WelcomeScreen import WelcomeScreen

# Инициализация приложения
app = QApplication(sys.argv)

# Загружаем экран приветствия
welcome = WelcomeScreen()
widget = QtWidgets.QStackedWidget()
widget.addWidget(welcome)  # Добавляем экран в стек виджетов

# Загружаем иконку
icon = QIcon()
icon.addPixmap(QPixmap("media\\icons8-управление-клиентами-96.png"), QIcon.Normal, QIcon.Off)
widget.setWindowIcon(icon)  # Установка иконки окна
widget.show()  # Показываем главное окно

# Запуск приложения
try:
    sys.exit(app.exec_())  # Запуск основного цикла приложения
except:
    print("Вы закрыли приложение")  # Сообщение об ошибке при закрытии приложения