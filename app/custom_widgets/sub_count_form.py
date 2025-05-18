from typing import Optional

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QAbstractItemView, QDialog, QHeaderView, QTableWidgetItem, QListWidgetItem, \
    QCheckBox, QMessageBox

from app import m_params
from app.dialogs.add_photos_dialog import AddPhotosDialog
from app.dialogs.effort_dialog_ import EffortDialog
from app.models.main_db import CountEffortSites, CountEffortTypes, CountEffortCategories, CountFiles, CountList, \
    GroupsCount, PatternCount, PointsCount
from app.services.db_manager import SessionFactoryMain
from app.services.helpers import makeDatecreated
from app.controllers.parameters import session_factory_main
from app.view import ui_form_sub_count

TABLE_SOURCE_LABELS = ['NAME']
TABLE_SITES_LABELS = ['ID', 'NAME']


class SubCountForm(QWidget):
    """
    Класс SubCountForm
    Класс QWidget, представляющий пользовательский интерфейс для сбора данных о подучете.
    Переменные экземпляра:
    - countData: Объект CountList, представляющий данные подсчета.
    - ui: Экземпляр класса Ui_Form для настройки пользовательского интерфейса.
    - main_session: Объект сессии для операций с базой данных.
    - savePoint: Точка сохранения для отслеживания изменений в базе данных.
    - effortType: Объект CountEffortTypes, представляющий тип усилия.
    Сигналы:
    - setDateTimeStart: Возникает, когда установлены дата и время начала.
    Методы:
    - __init__(countData: CountList): Конструктор.
    - editSource(): Открывает диалоговое окно для добавления или редактирования фотографий учета.
    - addRowsSource(eff_files: list[CountFiles]): Добавляет строки в таблицу фотографий учета.
    - editEfforts(): Открывает диалоговое окно для редактирования усилий учета.
    - addRowsEffortSites(efforts: list[CountEffortSites]): Добавляет строки в таблицу локальных участков лежбища учета.
    - countTypeSelected(): Срабатывает, когда выбран тип учета в комбинированном поле.
    - editComment(): Обновление комментариев.
    - loadCountTypes(): Загружает типы учета в комбинированное поле.
    - loadCategories(): Загружает категории в виджет списка категорий животных.
    - newCountAnimalCategories(): Создает новые категории учета животных.
    """
    setDateTimeStart = pyqtSignal()

    def __init__(self, countData: CountList):
        super().__init__()
        self.countData = countData
        self.ui = ui_form_sub_count.Ui_Form()
        self.ui.setupUi(self)

        self.main_session = session_factory_main.get_session()

        self.savePoint = self.main_session.begin_nested()

        self.effortType: Optional[CountEffortTypes] = CountEffortTypes(
            r_year=self.countData.r_year,
            site=self.countData.site,
            species=self.countData.species,
            r_date=self.countData.r_date,
            time_start=self.countData.time_start,
            creator=self.countData.creator,
            observer=m_params.creator,
            datecreated=makeDatecreated()
        )

        self.loadCountTypes()
        self.loadCategories()

        self.ui.btn_add_edit_source.clicked.connect(self.editSource)
        self.ui.btn_add_edit_effort.clicked.connect(self.editEfforts)

        # self.ui.cmbSubCount.activated.connect(self.countTypeSelected)
        self.ui.cmbSubCount.currentIndexChanged.connect(self.countTypeSelected)

        self.ui.table_source.setColumnCount(len(TABLE_SOURCE_LABELS))
        self.ui.table_source.setHorizontalHeaderLabels(TABLE_SOURCE_LABELS)
        self.ui.table_source.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.table_source.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.ui.table_sites.setColumnCount(len(TABLE_SITES_LABELS))
        self.ui.table_sites.setHorizontalHeaderLabels(TABLE_SITES_LABELS)

        self.ui.table_sites.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.table_sites.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.ui.text_comments.textChanged.connect(self.editComment)

    def editSource(self):
        if not self.ui.cmbSubCount.currentData(Qt.UserRole):
            return

        addPhotosDialog = AddPhotosDialog(self.effortType)
        addPhotosDialog.setModal(True)

        if addPhotosDialog.exec() == QDialog.Rejected:
            return
        else:
            addedSource = [addPhotosDialog.addedPhotos.item(row).text() for row in
                           range(addPhotosDialog.addedPhotos.count())]

            tempDeleteSource = []
            for item in self.effortType.count_files:
                if item.file_name not in addedSource:
                    tempDeleteSource.append(item)
                else:
                    addedSource.remove(item.file_name)

            if tempDeleteSource:
                ret = QMessageBox.question(self, 'Question',
                                           "Some files have been deleted from the list, delete them from the database?",
                                           QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

                if ret == QMessageBox.Yes:
                    ret_2 = QMessageBox.question(self, 'Question',
                                                 "Are you sure? This will affect the associated data!",
                                                 QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

                    if ret_2 == QMessageBox.Yes:
                        for item in tempDeleteSource:
                            self.effortType.count_files.remove(item)
                    else:
                        return
                else:
                    return

            for file in addedSource:
                self.effortType.count_files.append(CountFiles(r_year=self.effortType.r_year,
                                                              site=self.effortType.site,
                                                              species=self.effortType.species,
                                                              creator=self.effortType.creator,
                                                              r_date=self.effortType.r_date,
                                                              time_start=self.effortType.time_start,
                                                              observer=self.effortType.observer,
                                                              file_name=file,
                                                              count_type=self.effortType.count_type,
                                                              datecreated=makeDatecreated()))
            if self.effortType.count_files:
                time_start = str(min(list(map(lambda x: str(x.file_name).split('_')[1], self.effortType.count_files))))
                r_date = int(str(self.effortType.count_files[0].file_name)[0:8])

                if self.checkUniqueCount(r_date=r_date, time_start=time_start):
                    self.effortType.count_files = []
                    return

                if self.countData.r_date != r_date:
                    self.countData.r_date = r_date

                if self.countData.time_start and len(self.countData.effort_types) > 1:
                    if self.countData.time_start > time_start:
                        self.countData.time_start = time_start
                else:
                    self.countData.time_start = time_start

                self.setDateTimeStart.emit()

            self.addRowsSource(self.effortType.count_files)

    def addRowsSource(self, eff_files: list[CountFiles]):
        eff_files.sort(key=lambda x: str(x.file_name).split('_')[1])
        self.ui.table_source.setRowCount(len(eff_files))
        self.ui.table_source.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        row = 0
        for item in eff_files:
            if item.file_name != 'no_file':
                table_item = QTableWidgetItem(item.file_name)
                table_item.setData(Qt.UserRole, item)
                self.ui.table_source.setItem(row, 0, table_item)
                row += 1

    def editEfforts(self):
        index = self.ui.cmbSubCount.currentIndex()
        if index < 0 or not self.countData.r_date or not self.countData.time_start:
            QMessageBox.information(self, 'Information',
                                    "Date and time start are not filled in")
            return

        effort_dialog = EffortDialog(self.effortType)
        effort_dialog.setModal(True)
        effort_dialog.show()

        if effort_dialog.exec() == QDialog.Accepted:
            self.addRowsEffortSites(self.effortType.effort_sites)

    def addRowsEffortSites(self, efforts: list[CountEffortSites]):

        self.ui.table_sites.clear()
        self.ui.table_sites.setRowCount(len(efforts))

        row = 0

        for item in efforts:
            lc_site = m_params.support_local_sites.itemFromId(item.local_site)
            table_item_id = QTableWidgetItem(item.local_site)
            table_item_name = QTableWidgetItem(lc_site.local_site_name)
            table_item_id.setData(Qt.UserRole, item)

            self.ui.table_sites.setItem(row, 0, table_item_id)
            self.ui.table_sites.setItem(row, 1, table_item_name)
            row += 1

        self.ui.table_sites.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def countTypeSelected(self):
        count_type = self.ui.cmbSubCount.currentData(Qt.UserRole)
        if not count_type:
            return
        if self.ui.cmbSubCount.isEnabled():
            if any(item.count_type == count_type.type_id for item in self.countData.effort_types):
                self.ui.cmbSubCount.setCurrentIndex(-1)
                return

        if self.ui.table_source.rowCount() > 0:
            self.ui.table_source.clear()
            self.effortType.count_files.clear()

        if not count_type.folder:
            self.ui.btn_add_edit_source.setEnabled(False)
        else:
            self.ui.btn_add_edit_source.setEnabled(True)

        if self.effortType.count_type != count_type.type_id:
            self.effortType.count_type = count_type.type_id

            for eff_site in self.effortType.effort_sites:
                if eff_site.count_type != self.effortType.count_type:
                    eff_site.count_type = self.effortType.count_type

            for eff_cat in self.effortType.effort_categories:
                if eff_cat.count_type != self.effortType.count_type:
                    eff_cat.count_type = self.effortType.count_type

    def editComment(self):
        if self.effortType.comments != self.ui.text_comments.toPlainText():
            self.effortType.comments = self.ui.text_comments.toPlainText()

    def loadCountTypes(self):
        for item in m_params.support_count_type_id:
            self.ui.cmbSubCount.addItem(item.description, userData=item)
        self.ui.cmbSubCount.setCurrentIndex(-1)

    def loadCategories(self):

        for category in m_params.support_categories_points:
            item = QListWidgetItem()
            item.setToolTip(category.description)
            item_widget = QCheckBox(category.animal_category)

            item_widget.setChecked(True)
            item_widget.clicked.connect(lambda state, cb=item_widget: self.updateCountCategories(state, cb))

            self.ui.listWidget_categories_count.addItem(item)
            self.ui.listWidget_categories_count.setItemWidget(item, item_widget)

    def newCountAnimalCategories(self):
        for category in m_params.support_categories_points:
            effort_categories = CountEffortCategories(r_year=self.effortType.r_year,
                                                      site=self.effortType.site,
                                                      r_date=self.effortType.r_date,
                                                      time_start=self.effortType.time_start,
                                                      creator=self.effortType.creator,
                                                      species=self.effortType.species,
                                                      animal_category=category.animal_category,
                                                      count_type=self.effortType.count_type,
                                                      datecreated=makeDatecreated(), )
            self.effortType.effort_categories.append(effort_categories)

    def setCheckedEffortCategories(self, effort_categories: list[CountEffortCategories]):
        temp_categories = list(map(lambda x: x.animal_category, effort_categories))
        for index in range(self.ui.listWidget_categories_count.count()):
            item = self.ui.listWidget_categories_count.item(index)
            item_widget = self.ui.listWidget_categories_count.itemWidget(item)

            if item_widget.text() in temp_categories:
                if not item_widget.checkState():
                    item_widget.setChecked(True)
            else:
                if item_widget.checkState():
                    item_widget.setChecked(False)

    def updateCountCategories(self, state, cb):
        item_widget = cb
        category = item_widget.text()
        temp_categories = list(
            filter(lambda x: x.animal_category == category, self.effortType.effort_categories))

        if state:
            if not temp_categories:
                effort_categories = CountEffortCategories(r_year=self.effortType.r_year,
                                                          site=self.effortType.site,
                                                          r_date=self.effortType.r_date,
                                                          time_start=self.effortType.time_start,
                                                          creator=self.effortType.creator,
                                                          species=self.effortType.species,
                                                          animal_category=category,
                                                          count_type=self.effortType.count_type,
                                                          datecreated=makeDatecreated(), )
                self.effortType.effort_categories.append(effort_categories)
        elif not state and temp_categories:

            groupCount = self.main_session.query(GroupsCount).filter_by(
                r_year=self.effortType.r_year,
                site=self.effortType.site,
                r_date=self.effortType.r_date,
                time_start=self.effortType.time_start,
                creator=self.effortType.creator,
                species=self.effortType.species,
                animal_category=category,
                count_type=self.effortType.count_type, ).all()

            patternCount = self.main_session.query(PatternCount).filter_by(
                r_year=self.effortType.r_year,
                site=self.effortType.site,
                r_date=self.effortType.r_date,
                time_start=self.effortType.time_start,
                creator=self.effortType.creator,
                species=self.effortType.species,
                animal_category=category,
                count_type=self.effortType.count_type, ).all()

            pointsCount = self.main_session.query(PointsCount).filter_by(
                r_year=self.effortType.r_year,
                site=self.effortType.site,
                r_date=self.effortType.r_date,
                time_start=self.effortType.time_start,
                creator=self.effortType.creator,
                species=self.effortType.species,
                animal_category=category,
                count_type=self.effortType.count_type, ).all()

            deleteRows = groupCount + patternCount + pointsCount

            if deleteRows:
                ret = QMessageBox.question(self, 'Question',
                                           "There is related data with the category! Are you sure?",
                                           QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
                if ret == QMessageBox.Yes:
                    for item in deleteRows:
                        self.main_session.delete(item)
                else:
                    item_widget.setChecked(True)
                    return

            self.effortType.effort_categories.remove(temp_categories[0])

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
