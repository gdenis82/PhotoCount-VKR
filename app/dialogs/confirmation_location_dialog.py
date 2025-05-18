# -*- coding : utf-8 -*-
import os
from PyQt5 import QtWidgets
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut, QMessageBox

from app.view.ui_dialog_location import Ui_LocationDialog


class ConfirmationLocationDialog(QtWidgets.QDialog):
    """
    Класс ConfirmationLocationDialog представляет диалоговое окно для подтверждения местоположения.
    Параметры:
    - num_best (int): количество лучших фотографий.
    Свойства:
    - isBestPhoto (bool): флаг, указывающий, является ли фотография лучшей.
    - status (str): статус подтверждения.
    - numBest (int): количество лучших фотографий.

    Методы:
    - confirmation(self, pressed): обрабатывает событие нажатия кнопки подтверждения.
    - location_active(self): обрабатывает событие активации подтверждения местоположения животного.
    - best_photo_changed(self): обрабатывает изменение состояния флажка лучшей фотографии.
    - closeEvent(self, event): обрабатывает событие закрытия диалогового окна.
    - accept(self): обрабатывает событие принятия диалогового окна.

    """
    def __init__(self, num_best):
        super().__init__()
        self.ui = Ui_LocationDialog()
        self.ui.setupUi(self)

        self.isBestPhoto: bool = False
        self.status = None
        self.numBest: int = num_best
        self.ui.cb_best_photo.setText(f"Best Photos: {num_best}")

        self.shortcut_ctrl_enter = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self.shortcut_ctrl_enter.activated.connect(self.location_active)

        self.shortcut_ctrl_return = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_ctrl_return.activated.connect(self.location_active)

        self.ui.btn_location_confirmation.setCheckable(True)
        self.ui.btn_location_confirmation.clicked[bool].connect(self.confirmation)

        self.ui.cb_best_photo.stateChanged.connect(self.best_photo_changed)

    def confirmation(self, pressed):
        source = self.sender()
        if pressed:
            self.status = source.text()
            if self.ui.cb_best_photo.isChecked():
                self.isBestPhoto = True
            self.accept()

    def location_active(self):
        self.ui.btn_location_confirmation.click()

    def best_photo_changed(self):
        if self.ui.cb_best_photo.isChecked():
            self.numBest += 1
        else:
            self.numBest -= 1
        self.ui.cb_best_photo.setText(f"Best Photos: {self.numBest}")

    def closeEvent(self, event):
        if self.status:
            event.accept()
        else:
            event.ignore()

    def accept(self):
        if self.status:
            super().accept()

        else:
            QMessageBox.information(self, 'Information', "Confirmation not filled!")
