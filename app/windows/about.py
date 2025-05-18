import os
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont, QIcon

from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QGridLayout, QDialog

from app import PRODUCT_NAME, VERSION, SUPPORT


class AboutWindow(QDialog):
    """
    Окно о программе
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("About")
        self.setMaximumSize(450, 300)

        logo = QLabel()
        logo.setMaximumWidth(200)
        logo.setMaximumHeight(200)
        pixmap = QPixmap(':/images/logo-npwc.png')
        pixmap = pixmap.scaled(logo.size(), Qt.KeepAspectRatio)
        logo.setPixmap(pixmap)
        self.setWindowIcon(QIcon(pixmap))

        exe_ctime = os.path.getmtime(os.path.abspath(__file__))
        exe_date = datetime.fromtimestamp(exe_ctime)

        product = QLabel(PRODUCT_NAME)
        font_product = QFont()
        font_product.setBold(True)
        font_product.setPointSize(18)
        product.setFont(font_product)

        version = QLabel(f'version: {VERSION}')
        date_update = QLabel(f'date update: {exe_date.strftime("%d.%m.%Y %H:%M:%S")}')
        email = QLabel(f'support: {SUPPORT}')

        button = QPushButton("Close")
        button.clicked.connect(self.close)

        layout = QGridLayout()
        layout.addWidget(logo, 0, 0, 1, 2)

        widget_right = QWidget()
        layout_right = QGridLayout()
        widget_right.setLayout(layout_right)
        layout_right.addWidget(product, 0, 0)
        layout_right.addWidget(version, 1, 0)
        layout_right.addWidget(date_update, 2, 0)
        layout_right.addWidget(email, 3, 0)

        layout.addWidget(widget_right, 0, 3)
        layout.addWidget(button, 1, Qt.AlignCenter)

        self.setLayout(layout)
        self.show()
