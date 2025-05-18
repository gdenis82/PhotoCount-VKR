from typing import Optional

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox

from app import m_params
from app.custom_widgets.sub_count_form import SubCountForm

from app.models.main_db import CountList, SurveyEffort
from app.services.db_manager import SessionFactoryMain

from app.services.helpers import makeDatecreated
from app.controllers.parameters import session_factory_main
from app.view.ui_dialog_create_count import Ui_CreateCountDialog


class CreateCountDialog(QtWidgets.QDialog):
    """
    В режиме учета формирует пользовательский интерфейс модуля
    создания записи учета и обработки информации подучетов.

    Класс CreateCountDialog является подклассом QDialog. Он представляет собой диалоговое окно для создания
    объекта данных учета.
    Конструктор: - принимает параметр `data=None`
    Параметры:
    - `data` (необязательный): Экземпляр класса `CountList`, представляющий существующие данные подсчета.
    По умолчанию равно None.
    Методы:
    - `initUi(self)`: Инициализирует пользовательский интерфейс приложения.
    - `closeEvent(self, event)`: Обрабатывает событие закрытия диалогового окна.
    - `accept(self)`: Обрабатывает событие принятия диалогового окна.
    - `onReject(self)`: Обрабатывает событие отклонения диалогового окна.
    - `loadSubCountRows(self)`: Загружает и отображает строки учета для данных подучетов.
    - `addNewRow(self)`: Добавляет новую строку в список подучетов.
    - `setDateTimeStart(self)`: Устанавливает дату и время начала на основе данных подучета.
    - `deleteRow(self)`: Удаляет выбранные строки из списка подучетов из базы данных.
    - `dateEditFinish(self)`: Обрабатывает событие завершения редактирования даты.
    - `timeEditFinish(self)`: Обрабатывает события завершения редактирования время.
    """
    def __init__(self, data=None):
        super().__init__()

        self.main_session = session_factory_main.get_session()

        self.ui = Ui_CreateCountDialog()
        self.ui.setupUi(self)
        self.initUi()

        self._isClose = False
        self.countData: Optional[CountList] = data
        if not data:
            self.survey_effort = self.main_session.query(SurveyEffort).filter_by(r_year=m_params.year,
                                                                                 site=m_params.site,
                                                                                 species=m_params.species).first()
            if not self.survey_effort:
                self.survey_effort = SurveyEffort(r_year=m_params.year,
                                                  site=m_params.site,
                                                  species=m_params.species,
                                                  )
                self.main_session.add(self.survey_effort)

            self.countData = CountList(r_year=m_params.year,
                                       site=m_params.site,
                                       species=m_params.species,
                                       creator=m_params.creator,
                                       datecreated=makeDatecreated(),
                                       r_date=0,
                                       time_start='000000')
            self.survey_effort.count_list.append(self.countData)

        else:
            self.ui.dateEdit.setText(str(self.countData.r_date))
            self.ui.timeEdit.setText(self.countData.time_start)
            self.ui.comments_count_list.setPlainText(self.countData.comments)
            self.ui.observer.setText(self.countData.creator)
            self.loadSubCountRows()

    def initUi(self):
        """
        Инициализирует пользовательский интерфейс приложения.
        """
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.showMaximized()

        self.ui.dateEdit.setEnabled(True)
        self.ui.timeEdit.setEnabled(True)
        self.ui.timeEdit.setInputMask('00:00:00')
        self.ui.dateEdit.setInputMask('0000-00-00')
        self.ui.dateEdit.editingFinished.connect(self.dateEditFinish)
        self.ui.timeEdit.editingFinished.connect(self.timeEditFinish)

        self.ui.comments_count_list.textChanged.connect(self.commentsEdite)

        self.ui.btn_add.clicked.connect(self.addNewRow)
        self.ui.btn_delete.clicked.connect(self.deleteRow)

        self.ui.year.setText(str(m_params.year))
        self.ui.site.setText(str(m_params.site))
        self.ui.species.setText(m_params.species)
        self.ui.observer.setText(m_params.creator)

        self.ui.buttonBox.rejected.disconnect()
        self.ui.buttonBox.rejected.connect(self.onReject)
        self.show()

    def closeEvent(self, event):
        if self._isClose:
            super().accept()
        else:
            if self.main_session.new or self.main_session.deleted or self.main_session.dirty:
                ret = QMessageBox.question(self, 'Question',
                                           "There are unsaved changes! Are you sure?",
                                           QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
                if ret == QMessageBox.Yes:
                    self.main_session.rollback()
                    super().reject()
                else:
                    event.ignore()
            else:
                self.main_session.rollback()
                super().reject()

    def accept(self):
        try:
            self.countData.validate()

            if self.countData.r_date > 0:
                self.countData.dateupdated = makeDatecreated()
                self.main_session.commit()
            else:
                QMessageBox.information(self, 'Information', "Date and time start are not filled in! ")
                return

        except Exception as ex:

            QMessageBox.warning(self, 'Error', ex.args[0])
            self.main_session.rollback()
        else:
            self._isClose = True

        self.close()

    def onReject(self):
        self.close()

    def loadSubCountRows(self):
        if self.countData:
            for eff_type in self.countData.effort_types:
                subCount = SubCountForm(self.countData)
                subCount.setDateTimeStart.connect(self.setDateTimeStart)

                data_type = m_params.support_count_type_id.itemFromId(eff_type.count_type)
                index_type = subCount.ui.cmbSubCount.findData(data_type, Qt.UserRole)
                subCount.ui.cmbSubCount.setEnabled(False)
                subCount.ui.cmbSubCount.setCurrentIndex(index_type)

                subCount.effortType = eff_type
                subCount.setCheckedEffortCategories(eff_type.effort_categories)
                subCount.addRowsEffortSites(eff_type.effort_sites)
                subCount.addRowsSource(eff_type.count_files)
                subCount.ui.text_comments.setPlainText(eff_type.comments)

                item = QListWidgetItem()
                item.setSizeHint(subCount.sizeHint())
                item.setData(Qt.UserRole, subCount)

                self.ui.listWidget.insertItem(self.ui.listWidget.count(), item)
                self.ui.listWidget.setItemWidget(item, subCount)

    def addNewRow(self):
        subCount = SubCountForm(self.countData)
        subCount.setDateTimeStart.connect(self.setDateTimeStart)
        self.countData.effort_types.append(subCount.effortType)

        subCount.newCountAnimalCategories()

        item = QListWidgetItem()
        item.setSizeHint(subCount.sizeHint())
        item.setData(Qt.UserRole, subCount)

        self.ui.listWidget.insertItem(self.ui.listWidget.count(), item)
        self.ui.listWidget.setItemWidget(item, subCount)
        self.ui.listWidget.setCurrentRow(self.ui.listWidget.count() - 1)

    def setDateTimeStart(self):
        self.ui.dateEdit.setText(str(self.countData.r_date))
        self.dateEditFinish()
        self.ui.timeEdit.setText(self.countData.time_start)
        self.timeEditFinish()

    def deleteRow(self):
        tempRemoveData = []
        for item in self.ui.listWidget.selectedItems():
            itemData = item.data(Qt.UserRole)

            if itemData.ui.cmbSubCount.currentIndex() < 0 or not itemData.effortType.count_type:
                index = self.ui.listWidget.row(item)
                self.ui.listWidget.takeItem(index)
            else:
                tempRemoveData.append(item)

        if tempRemoveData:
            ret = QMessageBox.question(self, 'Question',
                                       "Some rows have been deleted from the table, delete them from the database?",
                                       QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

            if ret == QMessageBox.Yes:
                ret_2 = QMessageBox.question(self, 'Question',
                                             "Are you sure? This will affect the associated data!",
                                             QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
                if ret_2 == QMessageBox.Yes:
                    for item in tempRemoveData:
                        itemData = item.data(Qt.UserRole)
                        self.main_session.delete(itemData.effortType)
                        index = self.ui.listWidget.row(item)
                        self.ui.listWidget.takeItem(index)
        self.main_session.commit()

    def dateEditFinish(self):
        current_date = self.ui.dateEdit.text().replace('-', '')
        if len(current_date) == 8:
            if self.countData:

                if self.countData.r_date != int(current_date):
                    if self.checkUniqueCount(r_date=current_date, time_start=self.countData.time_start):
                        self.ui.dateEdit.setText(str(self.countData.r_date))
                        return
                    self.countData.r_date = int(current_date)

                for eff_type in self.countData.effort_types:
                    if eff_type.r_date != int(current_date):
                        eff_type.r_date = int(current_date)

                    for eff_site in eff_type.effort_sites:
                        if eff_site.r_date != int(current_date):
                            eff_site.r_date = int(current_date)

                    for eff_cat in eff_type.effort_categories:
                        if eff_cat.r_date != int(current_date):
                            eff_cat.r_date = int(current_date)

                    for eff_file in eff_type.count_files:
                        if eff_file.r_date != int(current_date):
                            eff_file.r_date = int(current_date)

    def timeEditFinish(self):

        current_time = self.ui.timeEdit.text().replace(':', '')
        if len(current_time) == 6:
            if self.countData:

                if self.countData.time_start != current_time:
                    if self.checkUniqueCount(r_date=self.countData.r_date, time_start=current_time):
                        self.ui.timeEdit.setText(self.countData.time_start)
                        return
                    self.countData.time_start = current_time

                for eff_type in self.countData.effort_types:
                    if eff_type.time_start != current_time:
                        eff_type.time_start = current_time

                    for eff_site in eff_type.effort_sites:
                        if eff_site.time_start != current_time:
                            eff_site.time_start = current_time

                    for eff_cat in eff_type.effort_categories:
                        if eff_cat.time_start != current_time:
                            eff_cat.time_start = current_time

                    for eff_file in eff_type.count_files:
                        if eff_file.time_start != current_time:
                            eff_file.time_start = current_time

    def commentsEdite(self):
        if self.countData.comments != self.ui.comments_count_list.toPlainText():
            self.countData.comments = self.ui.comments_count_list.toPlainText()

    def checkUniqueCount(self, r_date, time_start):
        temp_session_factory_main = SessionFactoryMain()
        temp_session_factory_main.connect_db(f'sqlite:///{m_params.main_db_path}')
        temp_session = temp_session_factory_main.get_session()
        temp_counts = temp_session.query(CountList).filter_by(r_year=m_params.year,
                                                              site=m_params.site,
                                                              species=m_params.species,
                                                              creator=m_params.creator,
                                                              r_date=r_date,
                                                              time_start=time_start, ).all()
        if temp_counts:
            QMessageBox.warning(self, 'Error', "Counting with such date and time already exists!")
            return True

        return False
