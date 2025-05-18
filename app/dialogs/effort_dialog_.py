from typing import Optional

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QIntValidator
from PyQt5.QtWidgets import QShortcut, QMessageBox, QAbstractItemView

from app import m_params
from app.custom_widgets.support_cmb import SupportQComboBox
from app.models.main_db import CountEffortSites, CountEffortTypes
from app.services.helpers import makeDatecreated
from app.controllers.parameters import session_factory_main
from app.view.ui_dialog_add_effort import Ui_EffortDialog

HEADER_LABELS = ('Date', 'Time Start', 'Type', 'Local Site', 'Creator', 'Observer', 'Comments', 'Visibility',
                 'Distance', 'Rain', 'Splash', 'Quality', 'Include to report', 'Coverage', 'Date Created',
                 'Date Update')


class EffortDialog(QtWidgets.QDialog):
    """
    Класс диалога, используемый для ввода и отображения данных усилий для определенного типа подсчета.
    Атрибуты:
    - main_session (Session): Основная сессия, используемая для доступа к базе данных.
    - isClose (bool): Флаг, указывающий, должен ли диалог быть закрытым.
    - effortType (CountEffortTypes): Тип усилий подсчета, для которого используется диалог.
    - countType (Item): Тип подсчета, связанный с типом усилий.
    - savePoint (Savepoint): Точка сохранения для основной сессии.
    Методы:
    - closeEvent (event: QCloseEvent): Обработчик события закрытия диалога.
    - onReject(): Обработчик событий для действия отклонения в кнопочном блоке.
    - accept(): Обработчик событий для действия принятия в кнопочном блоке.
    - checkedFilled() -> bool: Проверяет, заполнены ли все обязательные поля.
    - makeTable(): Настраивает виджет таблицы.
    - checkLocalSite(): Проверяет, существует ли введенный локальный сайт в списке сайтов усилия.
    - updateData(): Обновляет данные локального участка усилия на основе введенной информации.
    - load_effort(): Загружает существующие данные об усилиях в таблицу.

    """
    def __init__(self, effortType: CountEffortTypes):
        super(EffortDialog, self).__init__()

        self.main_session = session_factory_main.get_session()
        self._isClose = False

        self.effortType = effortType
        self.countType = m_params.support_count_type_id.itemFromId(self.effortType.count_type)
        self.savePoint = self.main_session.begin_nested()

        self.ui = Ui_EffortDialog()
        self.ui.setupUi(self)

        self.ui.buttonBox.rejected.disconnect()
        self.ui.buttonBox.rejected.connect(self.onReject)

        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.showMaximized()
        self.setModal(True)

        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidget.setSortingEnabled(True)
        self.ui.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.makeTable()

        self.ui.btn_add.clicked.connect(self.newRow)
        self.ui.btn_delete.clicked.connect(self.deleteRow)

        self.delete_shortcut = QShortcut(QKeySequence.Delete, self.ui.tableWidget)
        self.new_row_shortcut = QShortcut(QKeySequence.New, self.ui.tableWidget)

        self.delete_shortcut.activated.connect(self.deleteRow)
        self.new_row_shortcut.activated.connect(self.newRow)

        self.load_effort()

    def closeEvent(self, event):
        if self._isClose:
            super().accept()
        else:
            is_modified = False
            for item in self.effortType.effort_sites:
                if self.main_session.is_modified(item):
                    is_modified = True
                    break

            if self.main_session.new or self.main_session.deleted or self.main_session.dirty:
                ret = QMessageBox.question(self, 'Question',
                                           "There are unsaved changes! Are you sure?",
                                           QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
                if ret == QMessageBox.Yes:
                    if self.savePoint:
                        self.savePoint.rollback()
                    super().reject()
                else:
                    event.ignore()

    def onReject(self):
        self.close()

    def accept(self):
        if self.checkedFilled():
            self._isClose = True
            self.close()
        else:
            QMessageBox.information(self, 'Information', "Efforts not filled!")

    def checkedFilled(self) -> bool:
        for row in range(self.ui.tableWidget.rowCount()):
            if not self.ui.tableWidget.cellWidget(row, 3).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 3).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 5).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 5).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 7).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 7).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 8).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 8).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 9).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 9).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 10).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 10).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 11).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 11).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 13).text():
                self.ui.tableWidget.cellWidget(row, 13).setFocus()
                return False

        return True

    def makeTable(self):

        self.ui.tableWidget.setColumnCount(len(HEADER_LABELS))
        self.ui.tableWidget.setHorizontalHeaderLabels(HEADER_LABELS)
        self.ui.tableWidget.setColumnWidth(0, 100)
        self.ui.tableWidget.setColumnWidth(1, 100)
        self.ui.tableWidget.setColumnWidth(2, 150)
        self.ui.tableWidget.setColumnWidth(3, 180)
        self.ui.tableWidget.setColumnWidth(4, 100)
        self.ui.tableWidget.setColumnWidth(5, 150)
        self.ui.tableWidget.setColumnWidth(6, 200)
        self.ui.tableWidget.setColumnWidth(7, 120)
        self.ui.tableWidget.setColumnWidth(8, 120)
        self.ui.tableWidget.setColumnWidth(9, 120)
        self.ui.tableWidget.setColumnWidth(10, 120)
        self.ui.tableWidget.setColumnWidth(11, 120)
        self.ui.tableWidget.setColumnWidth(12, 120)
        self.ui.tableWidget.setColumnWidth(13, 120)
        self.ui.tableWidget.setColumnWidth(14, 200)

    def checkLocalSite(self):
        row = self.ui.tableWidget.currentRow()
        if row < 0:
            return

        locSite = self.ui.tableWidget.cellWidget(row, 3).currentData(Qt.UserRole)
        try:
            result = next(item for item in self.effortType.effort_sites if item.local_site == locSite)
            if result:
                self.ui.tableWidget.cellWidget(row, 3).setCurrentIndex(-1)
                return
        except StopIteration:
            self.updateData()

    def updateData(self):
        row = self.ui.tableWidget.currentRow()
        if row < 0:
            return

        local_site = self.ui.tableWidget.cellWidget(row, 3).currentData(Qt.UserRole)
        observer = self.ui.tableWidget.cellWidget(row, 5).currentData(Qt.UserRole)
        comments = self.ui.tableWidget.cellWidget(row, 6).toPlainText()
        visibility = self.ui.tableWidget.cellWidget(row, 7).currentData(Qt.UserRole)
        distance = self.ui.tableWidget.cellWidget(row, 8).currentData(Qt.UserRole)
        rain = self.ui.tableWidget.cellWidget(row, 9).currentData(Qt.UserRole)
        splash = self.ui.tableWidget.cellWidget(row, 10).currentData(Qt.UserRole)
        quality = self.ui.tableWidget.cellWidget(row, 11).currentData(Qt.UserRole)
        count_performed = self.ui.tableWidget.cellWidget(row, 12).currentData(Qt.UserRole)
        coverage = self.ui.tableWidget.cellWidget(row, 13).text()
        if coverage and int(coverage) > 100:
            coverage = 100
            self.ui.tableWidget.cellWidget(row, 13).setText(str(coverage))
        elif coverage:
            coverage = int(coverage)

        data: Optional[CountEffortSites] = self.ui.tableWidget.item(row, 0).data(Qt.UserRole)
        if not data:
            newEffortSite = CountEffortSites(r_year=self.effortType.r_year,
                                             site=self.effortType.site,
                                             r_date=self.effortType.r_date,
                                             time_start=self.effortType.time_start,
                                             creator=self.effortType.creator,
                                             species=self.effortType.species,
                                             observer=m_params.creator,
                                             local_site=local_site,
                                             comments=comments,
                                             visibility=visibility,
                                             distance=distance,
                                             rain=rain,
                                             splash=splash,
                                             quality=quality,
                                             count_performed=count_performed,
                                             coverage=coverage,
                                             datecreated=makeDatecreated(), )
            self.effortType.effort_sites.append(newEffortSite)
            self.ui.tableWidget.item(row, 0).setData(Qt.UserRole, newEffortSite)
        else:
            data.local_site = local_site
            data.observer = observer
            data.comments = comments
            data.visibility = visibility
            data.distance = distance
            data.rain = rain
            data.splash = splash
            data.quality = quality
            data.count_performed = count_performed
            data.coverage = coverage
            data.dateupdated = makeDatecreated()

    def load_effort(self):

        for effort in self.effortType.effort_sites:
            row = self.ui.tableWidget.rowCount()
            self.addRow()

            self.ui.tableWidget.item(row, 0).setData(Qt.UserRole, effort)
            self.ui.tableWidget.item(row, 0).setText(str(effort.r_date))
            self.ui.tableWidget.item(row, 1).setText(effort.time_start)
            self.ui.tableWidget.cellWidget(row, 2).select_data(effort.count_type)
            self.ui.tableWidget.cellWidget(row, 3).select_data(effort.local_site)
            self.ui.tableWidget.item(row, 4).setText(effort.creator)
            self.ui.tableWidget.cellWidget(row, 5).select_data(effort.observer)
            self.ui.tableWidget.cellWidget(row, 6).setText(effort.comments)
            self.ui.tableWidget.cellWidget(row, 7).select_data(effort.visibility)
            self.ui.tableWidget.cellWidget(row, 8).select_data(effort.distance)
            self.ui.tableWidget.cellWidget(row, 9).select_data(effort.rain)
            self.ui.tableWidget.cellWidget(row, 10).select_data(effort.splash)
            self.ui.tableWidget.cellWidget(row, 11).select_data(effort.quality)
            self.ui.tableWidget.cellWidget(row, 12).select_data(effort.count_performed)
            self.ui.tableWidget.cellWidget(row, 13).setText(str(effort.coverage))
            self.ui.tableWidget.item(row, 14).setText(effort.datecreated)
            self.ui.tableWidget.item(row, 15).setText(effort.dateupdated)

    def addRow(self):
        row = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.insertRow(row)

        item_date = QtWidgets.QTableWidgetItem(str(self.effortType.r_date))
        item_date.setFlags(Qt.ItemIsEnabled)

        item_time = QtWidgets.QTableWidgetItem(self.effortType.time_start)
        item_time.setFlags(Qt.ItemIsEnabled)

        item_type = SupportQComboBox()
        for item in m_params.support_count_type_id:
            item_type.addItem(item.description, userData=item.type_id)
        item_type.setCurrentIndex(item_type.findText(self.countType.description))

        item_local_site = SupportQComboBox()
        for item in m_params.support_local_sites:
            item_local_site.addItem(item.local_site_name, userData=item.local_site_id)
        item_local_site.setCurrentIndex(-1)
        item_local_site.activated.connect(self.checkLocalSite)

        item_creator = QtWidgets.QTableWidgetItem(m_params.creator)
        item_creator.setFlags(Qt.ItemIsEnabled)

        item_observers = SupportQComboBox()
        for item in m_params.support_observers:
            item_observers.addItem(item.observer_name, userData=item.observer)
        item_observers.setCurrentIndex(item_observers.findData(m_params.creator, Qt.UserRole))
        item_observers.activated.connect(self.updateData)

        support_effort_items = m_params.support_effort_type_id

        distance_visibility = list(filter(lambda x: x.type_category == 'Distance/Visibility', support_effort_items))
        rain = list(filter(lambda x: x.type_category == 'Rain', support_effort_items))
        splash = list(filter(lambda x: x.type_category == 'Splash', support_effort_items))
        quality = list(filter(lambda x: x.type_category == 'Quality', support_effort_items))

        item_visibility = SupportQComboBox()
        item_distance = SupportQComboBox()
        for item in distance_visibility:
            item_visibility.addItem(item.description, userData=item.type_id)
            item_distance.addItem(item.description, userData=item.type_id)

        item_visibility.setCurrentIndex(-1)
        item_distance.setCurrentIndex(-1)
        item_visibility.activated.connect(self.updateData)
        item_distance.activated.connect(self.updateData)

        item_rain = SupportQComboBox()
        for item in rain:
            item_rain.addItem(item.description, userData=item.type_id)
        item_rain.setCurrentIndex(-1)
        item_rain.activated.connect(self.updateData)

        item_splash = SupportQComboBox()
        for item in splash:
            item_splash.addItem(item.description, userData=item.type_id)
        item_splash.setCurrentIndex(-1)
        item_splash.activated.connect(self.updateData)

        item_quality = SupportQComboBox()
        for item in quality:
            item_quality.addItem(item.description, userData=item.type_id)
            item_quality.setCurrentIndex(-1)
        item_quality.activated.connect(self.updateData)

        item_include_to_report = SupportQComboBox()
        for item in [(0, 'No'), (1, 'Yes')]:
            item_include_to_report.addItem(item[1], userData=item[0])
        item_include_to_report.setCurrentIndex(1)
        item_include_to_report.activated.connect(self.updateData)

        item_date_created = QtWidgets.QTableWidgetItem(makeDatecreated())
        item_date_created.setFlags(Qt.ItemIsEnabled)
        item_date_updated = QtWidgets.QTableWidgetItem()
        item_date_updated.setFlags(Qt.ItemIsEnabled)

        item_comment = QtWidgets.QTextEdit('')
        item_comment.textChanged.connect(self.updateData)

        item_coverage = QtWidgets.QLineEdit()
        onlyInt = QIntValidator()
        onlyInt.setRange(0, 100)
        item_coverage.setValidator(onlyInt)
        item_coverage.setText("100")
        item_coverage.textChanged.connect(self.updateData)

        self.ui.tableWidget.setItem(row, 0, item_date)

        self.ui.tableWidget.setItem(row, 1, item_time)
        self.ui.tableWidget.setCellWidget(row, 2, item_type)
        self.ui.tableWidget.cellWidget(row, 2).setEnabled(False)
        self.ui.tableWidget.setCellWidget(row, 3, item_local_site)
        self.ui.tableWidget.setItem(row, 4, item_creator)
        self.ui.tableWidget.setCellWidget(row, 5, item_observers)
        self.ui.tableWidget.setCellWidget(row, 6, item_comment)

        self.ui.tableWidget.setCellWidget(row, 7, item_visibility)
        self.ui.tableWidget.setCellWidget(row, 8, item_distance)
        self.ui.tableWidget.setCellWidget(row, 9, item_rain)
        self.ui.tableWidget.setCellWidget(row, 10, item_splash)
        self.ui.tableWidget.setCellWidget(row, 11, item_quality)
        self.ui.tableWidget.setCellWidget(row, 12, item_include_to_report)
        self.ui.tableWidget.setCellWidget(row, 13, item_coverage)
        self.ui.tableWidget.setItem(row, 14, item_date_created)
        self.ui.tableWidget.setItem(row, 15, item_date_updated)

    def newRow(self):
        row = self.ui.tableWidget.rowCount()
        self.addRow()

        if self.effortType.effort_sites:
            effort = self.effortType.effort_sites[-1]
            self.ui.tableWidget.cellWidget(row, 7).select_data(effort.visibility)
            self.ui.tableWidget.cellWidget(row, 8).select_data(effort.distance)
            self.ui.tableWidget.cellWidget(row, 9).select_data(effort.rain)
            self.ui.tableWidget.cellWidget(row, 10).select_data(effort.splash)
            self.ui.tableWidget.cellWidget(row, 11).select_data(effort.quality)

    def deleteRow(self):
        ret = QMessageBox.question(self, 'Question',
                                   "Are you sure? This may affect the associated data!",
                                   QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

        if ret == QMessageBox.Yes:
            indices = self.ui.tableWidget.selectionModel().selectedRows()
            for index in reversed(indices):
                data = self.ui.tableWidget.item(index.row(), 0).data(Qt.UserRole)
                if data:
                    self.effortType.effort_sites.remove(data)
                self.ui.tableWidget.model().removeRow(index.row())
