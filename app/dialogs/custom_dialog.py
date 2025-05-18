from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QToolButton, QSpacerItem, QListWidget, QVBoxLayout, QSizePolicy, QListView

from app import m_params
from app.models.support_db import AnimalCategories, LocalSites
from app.controllers.parameters import support_session


class DialogSelectCountCategory(QtWidgets.QDialog):
    """
    Этот класс представляет собой диалог для выбора категории животного при проведении учета на фотографии.

    """
    def __init__(self, species):
        super().__init__()
        self.setWindowModality(Qt.ApplicationModal)
        self.setMaximumHeight(500)
        self.animal_statuses = support_session.query(AnimalCategories).filter_by(species=species).all()
        self.animal_statuses.sort(key=lambda x: x.order)

        self.button_group = QtWidgets.QButtonGroup()
        self.button_group.buttonClicked[QtWidgets.QAbstractButton].connect(self.b_select)

        list_widget = QListWidget()
        list_layout = QVBoxLayout()
        list_widget.setLayout(list_layout)
        list_layout.setAlignment(Qt.AlignCenter)

        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        list_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        list_widget.setFlow(QListView.LeftToRight)
        list_widget.setMovement(QListView.Static)
        list_widget.setWrapping(False)

        i = 1
        for item in self.animal_statuses:
            btn_category = QToolButton()
            btn_category.setObjectName(item.animal_category)
            btn_category.setAutoExclusive(True)
            btn_category.setCheckable(True)
            btn_category.setFixedWidth(50)
            btn_category.setFixedHeight(50)
            btn_category.setProperty('data', item)

            bt_text = "{0}".format(item.animal_category)
            btn_category.setText(bt_text)
            style_text = 'QToolButton {color:' + item.color_representation_large + '; font: bold;}'
            btn_category.setStyleSheet(style_text)
            btn_category.setToolTip(item.description)

            self.button_group.addButton(btn_category)
            list_layout.addWidget(btn_category)
            i += 1

        self.setLayout(list_layout)
        self.result = False

    @QtCore.pyqtSlot(QtWidgets.QAbstractButton)
    def b_select(self, btn):
        """
        Этот метод 'b_select' является слотовой функцией, которая вызывается при выборе кнопки.

        """
        self.result = btn.property('data')
        super().accept()
        self.close()


class DialogSelectLocalSite(QtWidgets.QDialog):
    """

    Диалоговое окно для выбора локального сайта.

    """
    def __init__(self):
        super().__init__()
        self.setWindowModality(Qt.ApplicationModal)

        self.setMinimumWidth(300)
        self.setMinimumHeight(100)
        self.setMaximumWidth(250)
        self.setMaximumHeight(300)

        self.v_layout = QtWidgets.QVBoxLayout()
        self.v_layout.setAlignment(Qt.AlignTop)

        self.label = QtWidgets.QLabel("Select local site")
        self.label.setAlignment(Qt.AlignCenter)
        self.v_layout.addWidget(self.label)

        self.comboBox = QtWidgets.QComboBox()

        for i, item in enumerate(m_params.support_local_sites):
            self.comboBox.addItem(item.local_site_name)
            self.comboBox.setItemData(i, item.local_site_id, Qt.ToolTipRole)
            self.comboBox.setItemData(i, item, Qt.UserRole)
        self.comboBox.setCurrentIndex(-1)

        self.v_layout.addWidget(self.comboBox)
        self.h_layout = QtWidgets.QHBoxLayout()
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_select = QtWidgets.QPushButton("Ok")

        self.h_layout.addWidget(self.btn_cancel)
        self.h_layout.addWidget(self.btn_select)

        self.h_layout.setAlignment(Qt.AlignRight)

        self.v_layout.addLayout(self.h_layout)

        self.setLayout(self.v_layout)

        self.btn_cancel.clicked.connect(super().reject)
        self.btn_select.clicked.connect(self.selectedLocalSite)
        self.localSite: [LocalSites] = None

    def selectedLocalSite(self):
        """
        Устанавливает локальный участок на основе выбора данных в комбо-боксе.
        """
        self.localSite = self.comboBox.currentData(Qt.UserRole)
        if self.localSite is not None:
            super().accept()
            self.close()
        else:
            return

