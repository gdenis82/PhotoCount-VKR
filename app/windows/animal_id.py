import os
import subprocess

from datetime import datetime

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, Qt, QTime
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QMessageBox, QListWidgetItem

from app import m_params
from app.custom_widgets.support_cmb import CustomQComboBox
from app.custom_widgets.image_viewer import PreviewImageViewer
from app.models.model_registration_animal import ModelRegistrationAnimal
from app.controllers.parameters import session_factory_main
from app.view.ui_window_animal_id import Ui_MainWindow
from app.windows.animal_Id_report import AnimalIdReportWindow
from app.windows.animal_registration import AnimalRegistration
from app.models.main_db import Resight, Daily, Location, AnimalInfo

from app.services.helpers import select_project_folders, makeDatecreated

HEADER_LABELS_DAILY = ('Year', 'Site', 'Name', 'Date', 'Status', 'LocalSite', 'Comments', 'Observer', 'DateCreated')
HEADER_LABELS_RESIGHT = ('Name', 'Sex', 'Status', 'Age', 'QBrand', 'Seen', 'IdStatus')
BRAND_CHARS = ['+', '-', '$', '0']


class AnimalIDWindow(QtWidgets.QMainWindow):
    """
    Модуль проверки и правки регистраций животных
    """
    open_location = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(AnimalIDWindow, self).__init__(parent=parent)

        self.main_session = session_factory_main.get_session()

        self.animal_photos = []
        self.animal_names = []
        self.resight = []

        self.report_win = None
        self.selected_image = 0
        self.locations_animal = None

        self.drivers = select_project_folders(m_params)
        self.view = PreviewImageViewer()
        self.table_info = QtWidgets.QTableWidget()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.initUI()
        self.showMaximized()

        self.load_animals_resight()

        for item in ('BestPhoto', 'NoBest'):
            self.ui.comboBox_type_photo.addItem(item)
        self.ui.comboBox_type_photo.setCurrentIndex(-1)

        for item in m_params.support_animal_statuses:
            self.ui.comboBox_animal_type.addItem(item.status)
        self.ui.comboBox_animal_type.addItem("L")
        self.ui.comboBox_animal_type.addItem("CL")
        self.ui.comboBox_animal_type.addItem("PB")
        self.ui.comboBox_animal_type.addItem("DL")
        self.ui.comboBox_animal_type.setCurrentIndex(-1)

        self.load_sex_status()

    def initUI(self):
        """

        Инициализирует элементы пользовательского интерфейса.

        """
        self.ui.table_animals_list.setColumnCount(len(HEADER_LABELS_RESIGHT))
        self.ui.table_animals_list.setHorizontalHeaderLabels(HEADER_LABELS_RESIGHT)
        self.ui.table_animals_list.setColumnWidth(0, 65)
        self.ui.table_animals_list.setColumnWidth(2, 80)
        self.ui.table_animals_list.setColumnWidth(4, 55)
        self.ui.table_animals_list.setColumnWidth(6, 60)

        self.ui.table_daily.setColumnCount(len(HEADER_LABELS_DAILY))
        self.ui.table_daily.setHorizontalHeaderLabels(HEADER_LABELS_DAILY)

        self.ui.vLayoutAdditionalInfo.addWidget(self.table_info)
        self.table_info.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_info.verticalHeader().customContextMenuRequested.connect(self.context_menu_additional_info)

        self.ui.actionRefresh_Data.triggered.connect(self.refresh)

        self.ui.actionRepot.triggered.connect(self.open_report)

        self.ui.imageLayout.addWidget(self.view, 0, 0, 1, 1)

        self.ui.table_animals_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.table_animals_list.customContextMenuRequested.connect(self.context_menu_resight_list)

        self.ui.table_animals_list.itemSelectionChanged.connect(self.selected_animal_resight)
        self.ui.table_animals_list.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.ui.table_animals_list.setSortingEnabled(True)

        self.ui.table_daily.itemSelectionChanged.connect(self.selected_daily)

        self.ui.table_daily.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.table_daily.customContextMenuRequested.connect(self.context_menu_daily)
        self.ui.table_daily.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.ui.table_daily.setSortingEnabled(True)

        self.ui.cmb_search_name.activated[str].connect(self.selected_search_name)

        self.ui.btn_previous.clicked.connect(self.previous_image)
        self.ui.btn_next.clicked.connect(self.next_image)
        self.ui.checkBox_filter_only_best_photo.stateChanged.connect(self.load_location)

        self.ui.animal_photos_daily.itemSelectionChanged.connect(self.selected_image_daily)
        self.ui.animal_photos_daily.itemClicked.connect(self.selected_image_daily)
        self.ui.animal_photos_daily.doubleClicked.connect(self.edit_photo)

        self.ui.dock_photos.visibilityChanged.connect(self.dock_photos_visibilityChanged)

        self.ui.comboBox_type_photo.activated[str].connect(self.change_type_photo)
        self.ui.comment_resight.textChanged.connect(self.comment_resight_edit)
        self.ui.comboBox_animal_type.activated[str].connect(self.change_animal_status_photo)

        self.ui.btn_edit.clicked.connect(self.edit_photo)
        self.ui.btn_delete.clicked.connect(self.delete_animal_location)
        self.ui.cmb_additional_info.setVisible(False)
        self.ui.btn_add_animal_info.setVisible(False)
        self.table_info.setVisible(False)

        self.ui.btn_add_animal_info.clicked.connect(self.add_animal_info)

        self.ui.brand_quality_resight.textEdited.connect(self.quality_text_edit)
        self.ui.cmb_status_resight.activated[str].connect(self.changed_status_resight)
        self.ui.cmb_gender_resight.activated[str].connect(self.changed_sex_resight)
        self.ui.chb_id_status.stateChanged.connect(self.changed_id_status_resight)

        self.ui.btn_add_animal.clicked.connect(self.add_new_animal)
        self.ui.btn_change_name_on_photo.clicked.connect(self.change_animal_name_photo)

    def load_sex_status(self):
        """

        Загружает варианты пола и статусы животных в выпадающие списки.
        """
        self.ui.cmb_gender_resight.clear()
        self.ui.cmb_status_resight.clear()

        sex_r = []
        for i, item in enumerate(m_params.support_animal_statuses):
            self.ui.cmb_status_resight.addItem(item.status)
            self.ui.cmb_status_resight.setItemData(i, item.description, Qt.ToolTipRole)

            sex_r.append(item.sex_r)

        sex_r = list(set(sex_r))
        sex_r.sort()

        self.ui.cmb_gender_resight.addItems(sex_r)
        self.ui.cmb_gender_resight.setCurrentIndex(-1)
        self.ui.cmb_status_resight.setCurrentIndex(-1)

    def load_animals_resight(self):
        """
        Формируем таблицу RESIGHT
        """
        self.ui.table_animals_list.setRowCount(0)
        self.ui.cmb_search_name.clear()
        self.ui.cmb_change_name_on_photo.clear()
        self.animal_names.clear()

        resight = self.main_session.query(Resight).filter_by(r_year=m_params.year,
                                                             site=m_params.site,
                                                             species=m_params.species).all()

        self.ui.table_animals_list.setRowCount(len(resight))

        for row, item in enumerate(resight):
            supportAnimal = m_params.support_animal_names.itemFromName(item.animal_name)
            self.animal_names.append(item)
            self.ui.cmb_search_name.addItem(item.animal_name, item)
            self.ui.cmb_change_name_on_photo.addItem(item.animal_name)
            t_year = 'NA'
            count_seen = len(item.daily_table)

            if supportAnimal:
                if supportAnimal.t_date:
                    t_year = str(supportAnimal.t_date)[0:4]

            if item.id_status:
                id_status = "Yes"
            else:
                id_status = "No"

            item_name = QtWidgets.QTableWidgetItem(str(item.animal_name))
            item_name.setData(Qt.UserRole, item)
            item_gender = QtWidgets.QTableWidgetItem(str(item.sex_r))
            item_status = QtWidgets.QTableWidgetItem(str(item.status))
            item_year = QtWidgets.QTableWidgetItem(str(t_year))
            item_brand_quality = QtWidgets.QTableWidgetItem(str(item.brand_quality))
            item_seen = QtWidgets.QTableWidgetItem(str(count_seen))
            item_id_status = QtWidgets.QTableWidgetItem(id_status)

            self.ui.table_animals_list.setItem(row, 0, item_name)
            self.ui.table_animals_list.setItem(row, 1, item_gender)
            self.ui.table_animals_list.setItem(row, 2, item_status)
            self.ui.table_animals_list.setItem(row, 3, item_year)
            self.ui.table_animals_list.setItem(row, 4, item_brand_quality)
            self.ui.table_animals_list.setItem(row, 5, item_seen)
            self.ui.table_animals_list.setItem(row, 6, item_id_status)

        self.ui.cmb_search_name.setCurrentIndex(-1)
        self.ui.cmb_change_name_on_photo.setCurrentIndex(-1)
        self.ui.table_animals_list.setCurrentCell(-1, -1)

    def load_animal_daily(self, data_resight):
        """
            Заполнение таблицы Daily
        """

        daily = self.main_session.query(Daily).filter_by(r_year=data_resight.r_year,
                                                         site=data_resight.site,
                                                         animal_name=data_resight.animal_name,
                                                         species=data_resight.species).all()

        self.ui.table_daily.setRowCount(len(daily))

        self.ui.table_daily.setColumnWidth(0, 40)
        self.ui.table_daily.setColumnWidth(1, 30)
        self.ui.table_daily.setColumnWidth(2, 100)
        self.ui.table_daily.setColumnWidth(3, 100)
        self.ui.table_daily.setColumnWidth(4, 100)
        self.ui.table_daily.setColumnWidth(5, 100)
        self.ui.table_daily.setColumnWidth(6, 200)
        self.ui.table_daily.setColumnWidth(7, 100)
        self.ui.table_daily.setColumnWidth(8, 200)

        for row, item in enumerate(daily):
            temp_loc_site = m_params.support_local_sites.itemFromId(item.local_site)

            item_year = QtWidgets.QTableWidgetItem(str(item.r_year))
            item_year.setData(Qt.UserRole, item)
            item_site = QtWidgets.QTableWidgetItem(str(item.site))
            item_date = QtWidgets.QTableWidgetItem(str(item.r_date))
            item_observer = QtWidgets.QTableWidgetItem(str(item.observer))
            item_datecreated = QtWidgets.QTableWidgetItem(str(item.datecreated))

            item_names = CustomQComboBox()
            item_names.activated[str].connect(self.changed_animal_name_daily)
            item_names.addItems(item_name.animal_name for item_name in self.animal_names)
            item_names.setCurrentText(str(item.animal_name))

            item_status = CustomQComboBox()
            item_status.activated[str].connect(self.changed_status_daily)

            for i in range(self.ui.cmb_status_resight.count()):
                item_status.addItem(self.ui.cmb_status_resight.itemText(i))
                item_status.setItemData(i, self.ui.cmb_status_resight.itemData(i, Qt.ToolTipRole), Qt.ToolTipRole)
            item_status.setCurrentText(str(item.status))

            item_local_sites = CustomQComboBox()
            item_local_sites.activated[str].connect(self.changed_local_site_daily)
            [item_local_sites.addItem(lc.local_site_name, lc) for lc in m_params.support_local_sites]
            item_local_sites.setCurrentText(str(temp_loc_site.local_site_name))

            item_comment = QtWidgets.QLineEdit()
            item_comment.setText(str(item.comments))
            item_comment.textEdited.connect(self.comment_daily_edit)

            self.ui.table_daily.setItem(row, 0, item_year)
            self.ui.table_daily.setItem(row, 1, item_site)
            self.ui.table_daily.setCellWidget(row, 2, item_names)
            self.ui.table_daily.setItem(row, 3, item_date)
            self.ui.table_daily.setCellWidget(row, 4, item_status)
            self.ui.table_daily.setCellWidget(row, 5, item_local_sites)
            self.ui.table_daily.setCellWidget(row, 6, item_comment)
            self.ui.table_daily.setItem(row, 7, item_observer)
            self.ui.table_daily.setItem(row, 8, item_datecreated)

        self.ui.table_daily.blockSignals(True)
        self.ui.table_daily.setCurrentCell(-1, -1)
        self.ui.table_daily.blockSignals(False)

    def load_additional_info(self):
        """
        Загружает дополнительную информацию для текущей выбранной строки в таблице списка животных.

        Этот метод загружает дополнительную информацию для выбранной строки в таблице списка животных.
        Сначала он проверяет, выбрана ли действительная строка, и если не выбрана,
        он возвращает без выполнения любых дополнительных действий.
        Затем он извлекает данные, связанные с выбранной строкой из таблицы.
        Если данных не найдено, он возвращает без выполнения каких-либо дополнительных действий.
        Затем он делает запрос к основной сессии, чтобы извлечь все экземпляры класса Resight,
        которые соответствуют году, лежбищу и виду животного выбранных данных data_resight.
        Метод затем очищает ComboBox cmb_additional_info и заполняет его элементами,
        полученными из метода m_params.support_animal_info.itemsFromSex(), передавая значение sex_r из data_resight в
        качестве параметра.
        Если в списке items_info есть элементы, ComboBox cmb_additional_info и связанные виджеты становятся видимыми,
         а таблица table_info очищается, изменяет размер и устанавливает соответствующие названия столбцов и
         ширину столбцов. Затем таблица table_info заполняется строками, равными длине data_resight.animal_info,
         и каждая ячейка в таблице заполняется соответствующим виджетом в зависимости от data_type элемента.
         Widget_data создается и устанавливается с соответствующими параметрами и соединениями сигналов.
         Наконец, в таблице table_info первый столбец заполняется виджетом QLineEdit info_type,
         а второй столбец - соответствующим widget_data.
        """
        row = self.ui.table_animals_list.currentRow()
        if row < 0:
            return

        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)

        if not data_resight:
            return

        resight = self.main_session.query(Resight).filter_by(r_year=data_resight.r_year,
                                                             site=data_resight.site,
                                                             species=data_resight.species).all()

        self.ui.cmb_additional_info.clear()
        items_info = m_params.support_animal_info.itemsFromSex(data_resight.sex_r)

        self.ui.cmb_additional_info.addItems(list(map(lambda x: x.info_id, items_info)))

        if items_info:
            self.ui.cmb_additional_info.setVisible(True)
            self.ui.btn_add_animal_info.setVisible(True)
            self.table_info.setVisible(True)
            self.ui.cmb_additional_info.setCurrentIndex(-1)
        else:
            self.ui.cmb_additional_info.setVisible(False)
            self.ui.btn_add_animal_info.setVisible(False)
            self.table_info.setVisible(False)

        self.table_info.clear()
        self.table_info.setColumnCount(2)
        self.table_info.setHorizontalHeaderLabels(('Type', 'Data'))
        self.table_info.setColumnWidth(0, 150)
        self.table_info.horizontalHeader().setStretchLastSection(True)
        self.table_info.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table_info.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        self.table_info.setRowCount(len(data_resight.animal_info))

        for row, item in enumerate(data_resight.animal_info):
            info_type = QtWidgets.QLineEdit(item.info_type)

            info_type.setMaximumWidth(200)
            info_type.setReadOnly(True)

            item_animal_info = m_params.support_animal_info.itemFromId(item.info_type)

            data_type = item_animal_info.info_data_type

            widget_data = None

            if "Text" == data_type:
                widget_data = CustomQComboBox()
                names = []
                if item.info_type == "PupName":
                    pass
                elif item.info_type == "MomName":
                    names = list(map(lambda x: x.animal_name, list(filter(lambda x: x.sex_r == "F", resight))))

                count_item_cmb = 0
                for item_name in names:
                    widget_data.addItem(item_name)
                    widget_data.setItemData(count_item_cmb, "{0}".format(item_name), Qt.ToolTipRole)
                    count_item_cmb += 1
                if item.info_value:
                    index = widget_data.findText(item.info_value)
                    widget_data.setCurrentIndex(index)
                else:
                    widget_data.setCurrentIndex(-1)
                widget_data.currentIndexChanged[int].connect(self.additional_data_name_changed)

            elif "Date" == data_type:
                widget_data = QtWidgets.QDateEdit()
                widget_data.setDisplayFormat("yyyy-MM-dd")
                if item.info_value:
                    date = str(item.info_value).replace('-', '')
                    i = datetime.now().replace(int(str(date)[0:4]),
                                               int(str(date)[5:6]),
                                               int(str(date)[7:8]))
                    widget_data.setDate(i)
                widget_data.dateChanged.connect(self.animal_info_data_time_changed)

            elif "Time" == data_type:
                widget_data = QtWidgets.QTimeEdit()
                widget_data.setDisplayFormat("HH:mm:ss")
                if item.info_value:
                    widget_data.setMaximumTime(QTime(23, 59, 59))
                    widget_data.setMinimumTime(QTime(00, 00, 00))
                    widget_data.setCurrentSection(QtWidgets.QDateTimeEdit.HourSection)
                    widget_data.setTimeSpec(Qt.OffsetFromUTC)
                    time_parts = str(item.info_value).split(':')
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    seconds = 0
                    if len(time_parts) > 2:
                        seconds = int(time_parts[2])

                    widget_data.setTime(QTime(hours, minutes, seconds))

                widget_data.timeChanged.connect(self.animal_info_data_time_changed)

            elif "Logical" == data_type:
                widget_data = QtWidgets.QCheckBox()
                widget_data.setText(item.info_value)

                if str(item.info_value).lower() == "Yes".lower():
                    widget_data.setChecked(True)
                else:
                    widget_data.setChecked(False)
                widget_data.stateChanged.connect(self.additional_data_cBox_changed)

            self.table_info.setCellWidget(row, 0, info_type)
            if widget_data:
                self.table_info.setCellWidget(row, 1, widget_data)

    def load_location(self):
        """
        Загрузка location и если есть prediction
        """
        self.scene_clear()
        self.ui.animal_photos_daily.setCurrentRow(-1)
        self.ui.animal_photos_daily.clear()
        self.animal_photos.clear()

        self.ui.comboBox_type_photo.setCurrentIndex(-1)
        self.ui.comboBox_animal_type.setCurrentIndex(-1)
        animal_photos = []
        row = self.ui.table_daily.currentRow()
        if row < 0:
            return

        data_daily = self.ui.table_daily.item(row, 0).data(Qt.UserRole)

        if data_daily:

            self.locations_animal = self.main_session.query(Location).filter_by(r_year=data_daily.r_year,
                                                                                site=data_daily.site,
                                                                                r_date=data_daily.r_date,
                                                                                animal_name=data_daily.animal_name,
                                                                                species=data_daily.species).all()
        else:
            self.locations_animal = self.main_session.query(Location).filter_by(r_year=data_daily.r_year,
                                                                                site=data_daily.site,
                                                                                animal_name=data_daily.animal_name,
                                                                                species=data_daily.species).all()

        if self.ui.checkBox_filter_only_best_photo.isChecked():
            animal_photos = list(
                filter(lambda x: str(x.type_photo).lower() == "BestPhoto".lower(), self.locations_animal))
        else:
            animal_photos = self.locations_animal

        self.ui.total_best_photo.setText(
            "Total Best: {0}".format(
                len(list(filter(lambda x: str(x.type_photo).lower() == "BestPhoto".lower(), self.locations_animal)))))

        self.selected_image = 0
        self.ui.label_image_count.setText("{0}/{1}".format(0, 0))
        self.ui.dock_photos.setWindowTitle("Location Photos: {0}".format(len(animal_photos)))

        if animal_photos:
            animal_photos = sorted(animal_photos, key=lambda x: x.file_name)

        for photo_loc in animal_photos:
            self.animal_photos.append(str(photo_loc.file_name))

            i = QListWidgetItem('%s' % str(photo_loc.file_name))

            type_count = "Location"
            if photo_loc.is_prediction_point:
                i.setForeground(QColor('#FF0000'))
                type_count = "Prediction"

            if str(photo_loc.type_photo) == "BestPhoto":
                type_photo = 'BestPhoto'
            else:
                type_photo = 'NoBest'

            i.setToolTip("{0}; {1}; {2}".format(str(photo_loc.animal_type), type_photo, type_count))

            i.setData(Qt.UserRole, photo_loc)

            self.ui.animal_photos_daily.addItem(i)

    def load_image(self, index):
        """
        Загружает и отображает изображение регистрации на основе данного индекса.

        """
        if index < 0:
            return

        path = ""

        for p in self.drivers:
            path_dir = os.path.dirname(p[0] + "/")
            path_photo = os.path.join(path_dir, str(self.animal_photos[index]).split('_')[0],
                                      self.animal_photos[index])
            if os.path.isfile(path_photo):
                path = path_photo
                break

        rect = self.search_coords_point(self.animal_photos[index])

        self.ui.label_image_count.setText("{0}/{1}".format(self.selected_image + 1, len(self.animal_photos)))

        if os.path.isfile(path):
            self.view.setPhoto(path)
            self.view.fitInView(rect=rect)
            self.view.setToolTip(str(path))

    def previous_image(self):
        """
        Переходит к предыдущему изображению в списке фотографий животных.
        """
        if len(self.animal_photos) == 0:
            return
        if self.selected_image > 0:
            self.selected_image -= 1
        elif self.selected_image == 0:
            self.selected_image = len(self.animal_photos) - 1

        if self.selected_image <= len(self.ui.animal_photos_daily) - 1 and len(self.ui.animal_photos_daily) > 0:
            self.ui.animal_photos_daily.setCurrentRow(self.selected_image)
            self.ui.animal_photos_daily.item(self.selected_image).setSelected(True)

    def next_image(self):
        """
        Переходит к следующему изображению в списке фотографий животных.
        """
        if len(self.animal_photos) == 0:
            return
        if self.selected_image < len(self.animal_photos) - 1:
            self.selected_image += 1
        elif self.selected_image == len(self.animal_photos) - 1:
            self.selected_image = 0

        if self.selected_image <= len(self.ui.animal_photos_daily) - 1 and len(self.ui.animal_photos_daily) > 0:
            self.ui.animal_photos_daily.setCurrentRow(self.selected_image)
            self.ui.animal_photos_daily.item(self.selected_image).setSelected(True)

    """"""

    # Выбрали животного в списке resight
    def selected_animal_resight(self):
        """
        Выбранная метка животного из таблицы регистрации за год.
        Обновляет пользовательский интерфейс на основе выбранного животного в списке животных.
        """
        self.ui.table_daily.setRowCount(0)
        self.ui.animal_photos_daily.setCurrentRow(-1)
        self.ui.animal_photos_daily.clear()
        self.scene_clear()
        self.animal_photos.clear()
        row = self.ui.table_animals_list.currentRow()
        self.ui.dock_photos.setWindowTitle("Location Photos: {0}".format(0))
        self.ui.total_best_photo.setText("Total Best: {0}".format(0))
        if row < 0:
            return

        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)

        self.ui.comment_resight.setPlainText(data_resight.comments)

        index = self.ui.cmb_search_name.findData(data_resight, Qt.UserRole)
        self.ui.cmb_search_name.setCurrentIndex(index)

        self.ui.cmb_status_resight.setCurrentText(data_resight.status)
        self.ui.cmb_gender_resight.setCurrentText(data_resight.sex_r)

        self.ui.brand_quality_resight.setText(data_resight.brand_quality)

        if self.ui.table_animals_list.item(row, 6).text().lower() == "Yes".lower():
            self.ui.chb_id_status.setChecked(True)
        else:
            self.ui.chb_id_status.setChecked(False)

        self.load_animal_daily(data_resight)
        self.load_additional_info()

        if str(data_resight.animal_name).lower() == 'unk' or str(data_resight.animal_name).lower() == 'u':
            self.ui.cmb_status_resight.setEnabled(False)
            self.ui.cmb_gender_resight.setEnabled(False)
            self.ui.brand_quality_resight.setEnabled(False)
            self.ui.comboBox_animal_type.setEnabled(False)
            self.ui.comboBox_type_photo.setEnabled(False)
        else:
            self.ui.cmb_status_resight.setEnabled(True)
            self.ui.cmb_gender_resight.setEnabled(True)
            self.ui.brand_quality_resight.setEnabled(True)
            self.ui.comboBox_animal_type.setEnabled(True)
            self.ui.comboBox_type_photo.setEnabled(True)

    """"""

    def add_new_animal(self):
        """
        Добавить регистрацию без фотографии.
        Инициализирует объект AnimalRegistration и подключает сигнал результата к методу handle_input_add_animal.
        """
        self.animal_registration = AnimalRegistration()
        self.animal_registration.result[ModelRegistrationAnimal].connect(self.handle_input_add_animal)

    def handle_input_add_animal(self, reg: ModelRegistrationAnimal):
        self.refresh()

    def additional_data_name_changed(self, name_index):
        """
        Изменяет имя метки для таблицы AnimalInfo для выбранного животного за день в таблице daily.
        """
        row = self.table_info.currentRow()

        row_resight = self.ui.table_animals_list.currentRow()
        if row_resight < 0 or row < 0:
            return
        data_resight = self.ui.table_animals_list.item(row_resight, 0).data(Qt.UserRole)

        info_data = self.table_info.cellWidget(row, 1).itemText(name_index)
        info_type = self.table_info.cellWidget(row, 0).text()
        animal_info = self.main_session.query(AnimalInfo).filter_by(r_year=data_resight.r_year,
                                                                    site=data_resight.site,
                                                                    species=data_resight.species,
                                                                    animal_name=data_resight.animal_name,
                                                                    info_type=info_type, ).first()
        animal_info.info_value = info_data
        animal_info.dateupdated = "{0} {1}".format(str(datetime.now()).split('.')[0], self.observer)
        self.main_session.commit()

    def additional_data_cBox_changed(self):
        """
        Этот метод вызывается при изменении значения флажка дополнительных данных.
        Он выполняет различные операции в зависимости от текущего состояния флажка и выбранной строки в
        таблице списка животных.

        """
        if self.ui.table_animals_list.currentRow() < 0:
            return

        row_info = self.table_info.currentRow()
        row_resight = self.ui.table_animals_list.currentRow()

        if row_info < 0 or row_resight < 0:
            return

        data_resight = self.ui.table_animals_list.item(row_resight, 0).data(Qt.UserRole)

        info_data = self.table_info.cellWidget(row_info, 1).isChecked()
        info_type = self.table_info.cellWidget(row_info, 0).text()
        if info_data:
            self.table_info.cellWidget(row_info, 1).setText("Yes")
        else:
            self.table_info.cellWidget(row_info, 1).setText("No")

        animal_info = self.main_session.query(AnimalInfo).filter_by(r_year=data_resight.r_year,
                                                                    site=data_resight.site,
                                                                    animal_name=data_resight.animal_name,
                                                                    info_type=info_type,
                                                                    species=data_resight.species,
                                                                    ).first()
        if animal_info:
            animal_info.info_value = self.table_info.cellWidget(row_info, 1).text()
            animal_info.dateupdated = makeDatecreated()

        if info_type == "IsFocalFemale" and info_data:
            insert_info = AnimalInfo(r_year=data_resight.r_year,
                                     site=data_resight.site,
                                     animal_name=data_resight.animal_name,
                                     info_type=info_type,
                                     info_value="Yes",
                                     species=data_resight.species,
                                     observer=m_params.creator,
                                     datecreated=makeDatecreated())
            self.main_session.add(insert_info)
        self.main_session.commit()

    def animal_info_data_time_changed(self):
        """

        Этот метод, animal_info_data_time_changed, используется для обновления значения информации и
        даты для экземпляра таблицы AnimalInfo в базе данных

        """
        if self.ui.table_animals_list.currentRow() < 0:
            return
        row_info = self.table_info.currentRow()
        row_resight = self.ui.table_animals_list.currentRow()

        if row_info < 0 or row_resight < 0:
            return

        data_resight = self.ui.table_animals_list.item(row_resight, 0).data(Qt.UserRole)

        date = self.table_info.cellWidget(row_info, 1).text()
        date = str(date).replace('-', '')
        info_type = self.table_info.cellWidget(row_info, 0).text()
        animal_info = self.main_session.query(AnimalInfo).filter_by(r_year=data_resight.r_year,
                                                                    site=data_resight.site,
                                                                    species=data_resight.species,
                                                                    animal_name=data_resight.animal_name,
                                                                    info_type=info_type).first()
        if animal_info:
            animal_info.info_value = date
            animal_info.dateupdated = makeDatecreated()
            self.main_session.commit()

    def add_animal_info(self):
        """
        Добавить дополнительную информацию о животном.
        """
        row = self.ui.table_animals_list.currentRow()
        if row < 0:
            return

        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)

        date_daily = datetime.now().replace(m_params.year,
                                            datetime.now().month,
                                            datetime.now().day).strftime("%Y%m%d")

        row_daily = self.ui.table_daily.currentRow()
        if row_daily >= 0:
            data_daily = self.ui.table_daily.item(row_daily, 0).data(Qt.UserRole)
            date_daily = data_daily.r_date

        info_type = self.ui.cmb_additional_info.currentText()
        support_info_type = m_params.support_animal_info.itemFromId(info_type)
        if not support_info_type:
            return
        data_type = support_info_type.info_data_type

        info_value = None
        animal_info = self.main_session.query(AnimalInfo).filter_by(r_year=data_resight.r_year,
                                                                    site=data_resight.site,
                                                                    species=data_resight.species,
                                                                    animal_name=data_resight.animal_name,
                                                                    info_type=info_type).first()
        if animal_info:
            self.ui.cmb_additional_info.setCurrentIndex(-1)
            QMessageBox.information(self, "Info", 'Record already exists!', QMessageBox.Ok)
            return
        else:
            if "Text".lower() == str(data_type).lower():
                pass

            elif "Time".lower() == str(data_type).lower():
                info_value = "00:00:00"

            elif "Date".lower() == str(data_type).lower():
                info_value = str(date_daily)

            elif "Logical".lower() == str(data_type).lower():
                info_value = "Yes"

            insert_info = AnimalInfo(r_year=data_resight.r_year,
                                     site=data_resight.site,
                                     animal_name=data_resight.animal_name,
                                     info_type=info_type,
                                     info_value=info_value,
                                     species=data_resight.species,
                                     observer=m_params.creator,
                                     datecreated=makeDatecreated())

            self.main_session.add(insert_info)
            self.main_session.commit()
            self.load_additional_info()

    def change_animal_info(self, item):
        """
        Изменить информацию о животном.
        Параметры: - item: Элемент, который нужно изменить на информацию о животном.
        Может быть одним из следующих значений:
        - "NP": NursingPup (Кормление щенка)
        - "NJ": NursingJuvenile (Кормление молодого)
        - "NJNP": NursingJuvenile and NursingPup (Кормление молодого и щенка)
        - "wj": PresenceJuvenile (Присутствие молодого)
        - "s": MomSuckling (Мама кормит)
        Примечание: Этот метод только изменяет информацию о текущем выбранном животном в таблице.
        Если животное не выбрано, метод вернется без внесения каких-либо изменений.
        """
        row = self.ui.table_animals_list.currentRow()
        if row < 0:
            return

        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)

        row_animal_info = []
        if str(item).lower() == "NP".lower() or str(item).lower() == "NJNP".lower():
            info_type = "NursingPup"
            data = "Yes"
            row_animal_info.append((data_resight.r_year,
                                    data_resight.site,
                                    data_resight.animal_name,
                                    info_type,
                                    data,
                                    makeDatecreated(),
                                    m_params.creator))

        if str(item).lower() == "NJ".lower() or str(item).lower() == "NJNP".lower():
            info_type = "NursingJuvenile"
            data = "Yes"
            row_animal_info.append((data_resight.r_year,
                                    data_resight.site,
                                    data_resight.animal_name,
                                    info_type,
                                    data,
                                    makeDatecreated(),
                                    m_params.creator))

        if str(item).lower() == "wj":
            info_type = "PresenceJuvenile"
            data = "Yes"
            row_animal_info.append((data_resight.r_year,
                                    data_resight.site,
                                    data_resight.animal_name,
                                    info_type,
                                    data,
                                    makeDatecreated(),
                                    m_params.creator))

        if str(item).lower() == "s":
            info_type = "MomSuckling"
            data = "Yes"
            row_animal_info.append((data_resight.r_year,
                                    data_resight.site,
                                    data_resight.animal_name,
                                    info_type,
                                    data,
                                    makeDatecreated(),
                                    m_params.creator))

        if row_animal_info:
            for row_inf in row_animal_info:
                animal_info = self.main_session.query(AnimalInfo).filter_by(r_year=data_resight.r_year,
                                                                            site=data_resight.site,
                                                                            animal_name=data_resight.animal_name,
                                                                            info_type=row_inf[3],
                                                                            species=data_resight.species,
                                                                            ).first()
                if animal_info:
                    animal_info.info_value = "Yes"
                    animal_info.dateupdated = makeDatecreated()

                else:
                    insert_info = AnimalInfo(r_year=data_resight.r_year,
                                             site=data_resight.site,
                                             animal_name=data_resight.animal_name,
                                             info_type=row_inf[3],
                                             info_value="Yes",
                                             species=data_resight.species,
                                             observer=m_params.creator,
                                             datecreated=makeDatecreated())
                    self.main_session.add(insert_info)
            self.main_session.commit()
            self.load_additional_info()

    def edit_photo(self):
        """

        Редактировать выбранное фото.
        Этот метод используется для редактирования выбранного фото в пользовательском интерфейсе модуля регистраций
        на фотографии.
        P.S. В дальнейшем будет выбор модуля взависимосте, где проведена регистрация: модуль регистрации на фото,
        модуль предсказаний расположения животных с метками (в разработке)

        """
        if not self.ui.animal_photos_daily.selectedItems():
            return

        file_name = self.animal_photos[self.selected_image]
        data = self.ui.animal_photos_daily.selectedItems()[0].data(Qt.UserRole)
        f_name_like = str(file_name).split('.')

        if data.is_prediction_point:
            pass
        else:
            self.open_location.emit({'data': data})

    def refresh(self):
        """
        Обновление всех данных
        """
        self.ui.dock_photos.setWindowTitle(f"Location Photos: {0}")
        row = self.ui.table_animals_list.currentRow()
        animal_name = None
        if row > -1:
            data = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)
            animal_name = data.animal_name
        self.drivers = select_project_folders(m_params)
        self.ui.table_daily.blockSignals(True)
        self.ui.table_daily.setRowCount(0)
        self.ui.table_daily.blockSignals(False)
        self.load_animals_resight()

        if animal_name:
            index = self.ui.cmb_search_name.findText(animal_name)
            self.ui.table_animals_list.selectRow(index)

    """context_menu"""

    def context_menu_resight_list(self, point):
        menu = QtWidgets.QMenu()
        edit_question = QtWidgets.QAction('Delete Animal ', menu)
        edit_question.triggered.connect(self.delete_animal_for_year)
        menu.addAction(edit_question)

        change_name = QtWidgets.QAction('Change Animal Name ', menu)
        change_name.triggered.connect(self.change_name_resight)
        menu.addAction(change_name)

        menu.exec(self.ui.table_animals_list.verticalHeader().mapToGlobal(point))

    def context_menu_daily(self, point):
        menu = QtWidgets.QMenu()

        delete_animal = QtWidgets.QAction('Delete Day ', menu)
        delete_animal.triggered.connect(self.delete_animal_for_day)

        menu.addAction(delete_animal)

        menu.exec(self.ui.table_daily.mapToGlobal(point))

    def context_menu_additional_info(self, point):
        menu = QtWidgets.QMenu()
        delete_info = QtWidgets.QAction('Delete Info', menu)
        delete_info.triggered.connect(self.delete_animal_info)

        menu.addAction(delete_info)
        menu.exec(self.table_info.mapToGlobal(point))

    """edit"""

    # Удаляем запись животного за год
    def delete_animal_for_year(self):
        """
        Удаляет все записи о животном за год из базы данных.

        Этот метод проверяет, выбрана ли строка в таблице.
        Если это так, то он предлагает пользователю подтвердить удаление всех записей выбранного животного из базы данных.
        Если пользователь подтверждает, метод производит удаление записей, удаляет строку из таблицы,
        обновляет выпадающий список имени поиска, очищает выбор и дополнительную информацию,
        а также очищает информацию о таблице.

        """
        if self.ui.table_animals_list.currentRow() < 0:
            return
        row = self.ui.table_animals_list.currentRow()
        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)

        res_1 = QMessageBox.question(self, "Question Resight!",
                                     "Delete all records of an animal {0} from the database for a year?  "
                                     .format(data_resight.animal_name),
                                     QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if res_1 == QMessageBox.Yes:
            res_2 = QMessageBox.question(self, "Question!",
                                         "Are you sure?  ",
                                         QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
            if res_2 == QMessageBox.Yes:
                self.main_session.delete(data_resight)
                self.main_session.commit()

                self.ui.table_animals_list.removeRow(row)
                self.ui.cmb_search_name.removeItem(row)

                self.ui.table_animals_list.selectionModel().clearSelection()
                self.ui.cmb_search_name.setCurrentIndex(-1)
                self.ui.cmb_additional_info.clear()
                self.table_info.clear()

    def change_name_resight(self):
        """
        Изменение имени животного в таблице регистраций за год.
        Этот метод изменяет имя выбранного животного в таблице регистраций за год, заменяя виджет ячейки на
        специальный комбо-бокс.
        Комбо-бокс позволяет пользователю выбрать новое имя из предустановленного списка имен животных.
        Как только выбрано новое имя, метод вызывает метод "changed_name_resight" для обновления изменений в
        таблице пользовательского интерфейса.

       """
        if self.ui.table_animals_list.selectedItems():
            row = self.ui.table_animals_list.currentRow()
            st_text = self.ui.table_animals_list.item(row, 0).text()

            names = CustomQComboBox()
            names.activated[str].connect(self.changed_name_resight)

            for item in self.animal_names:
                names.addItem(item.animal_name)

            names.setCurrentText(st_text)
            self.ui.table_animals_list.setCellWidget(row, 0, names)

    def changed_name_resight(self, new_name):
        """
        Изменит имя животного в таблице resight на новое имя и все связанные записи.
        """
        if self.ui.table_animals_list.currentRow() < 0:
            return
        row = self.ui.table_animals_list.currentRow()
        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)
        if not data_resight:
            return

        old_name = data_resight.animal_name

        res_1 = QMessageBox.question(self, "Question!",
                                     "Changing the name {0} to a {1}?   "
                                     .format(old_name, new_name),
                                     QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if res_1 == QMessageBox.Yes:
            res_2 = QMessageBox.question(self, "Question!",
                                         "Are you sure?  "
                                         .format(self.ui.cmb_search_name.currentText()),
                                         QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

            if res_2 == QMessageBox.Yes:
                for data_daily in data_resight.daily_table:
                    # проверяем есть ли дневная запись для нового имени за день, если нет - создаем
                    is_have_daily = self.main_session.query(Daily).filter_by(r_year=data_daily.r_year,
                                                                             site=data_daily.site,
                                                                             species=data_daily.species,
                                                                             r_date=data_daily.r_date,
                                                                             animal_name=new_name).first()

                    if not is_have_daily:
                        insert_daily = Daily(r_year=data_daily.r_year,
                                             site=data_daily.site,
                                             species=data_daily.species,
                                             r_date=data_daily.r_date,
                                             animal_name=new_name,
                                             status=data_daily.status,
                                             local_site=data_daily.local_site,
                                             comments=data_daily.comments,
                                             observer=m_params.creator,
                                             datecreated=makeDatecreated())

                        self.main_session.add(insert_daily)
                        self.main_session.commit()

                    # обновляем старое имя на новое в location
                    old_location = self.main_session.query(Location).filter_by(r_year=data_daily.r_year,
                                                                               site=data_daily.site,
                                                                               r_date=data_daily.r_date,
                                                                               species=data_daily.species,
                                                                               animal_name=old_name).all()
                    new_location = self.main_session.query(Location).filter_by(r_year=data_daily.r_year,
                                                                               site=data_daily.site,
                                                                               r_date=data_daily.r_date,
                                                                               species=data_daily.species,
                                                                               animal_name=new_name).all()
                    for item_old in old_location:
                        if not list(filter(lambda x: x.file_name == item_old.file_name, new_location)):
                            item_old.animal_name = new_name
                            item_old.dateupdated = makeDatecreated()
                    self.main_session.commit()

                    # Обновляем имя в Animal Info
                    animal_info_new = self.main_session.query(AnimalInfo).filter_by(r_year=data_daily.r_year,
                                                                                    site=data_daily.site,
                                                                                    species=data_daily.species,
                                                                                    animal_name=new_name).all()
                    animal_info_old = self.main_session.query(AnimalInfo).filter_by(r_year=data_daily.r_year,
                                                                                    site=data_daily.site,
                                                                                    species=data_daily.species,
                                                                                    animal_name=new_name).all()
                    for info_name_old in animal_info_old:
                        if not list(filter(lambda x: x.info_type == info_name_old.info_type, animal_info_new)):
                            info_name_old.animal_name = new_name
                            info_name_old.dateupdated = makeDatecreated()
                    self.main_session.commit()

                    old_daily = self.main_session.query(Daily).filter_by(r_year=data_daily.r_year,
                                                                         site=data_daily.site,
                                                                         species=data_daily.species,
                                                                         r_date=data_daily.r_date,
                                                                         animal_name=old_name).first()
                    if old_daily:
                        self.main_session.delete(old_daily)
                        self.main_session.commit()

                    name_all_daily = self.main_session.query(Daily).filter_by(r_year=data_daily.r_year,
                                                                              site=data_daily.site,
                                                                              species=data_daily.species,
                                                                              animal_name=old_name).all()
                    if not name_all_daily:
                        resight = self.main_session.query(Resight).filter_by(r_year=data_daily.r_year,
                                                                             site=data_daily.site,
                                                                             species=data_daily.species,
                                                                             animal_name=old_name).first()
                        self.main_session.delete(resight)
                        self.main_session.commit()

                self.ui.table_animals_list.removeCellWidget(row, 0)
                self.refresh()

    def delete_animal_info(self):
        """
        Удаляет дополнительную информацию о животном из базы данных на основе выбранной строки в таблице animal info.
        """
        if self.table_info.currentRow() < 0 or self.ui.table_animals_list.currentRow() < 0:
            return

        row = self.ui.table_animals_list.currentRow()
        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)

        row = self.table_info.currentRow()
        info_type = self.table_info.cellWidget(row, 0).text()
        animal_info = self.main_session.query(AnimalInfo).filter_by(r_year=data_resight.r_year,
                                                                    site=data_resight.site,
                                                                    species=data_resight.species,
                                                                    animal_name=data_resight.animal_name,
                                                                    info_type=info_type).first()
        if animal_info:
            self.main_session.delete(animal_info)
            self.main_session.commit()

        self.load_additional_info()

    def clear_selection_daily(self):
        row = self.ui.table_daily.currentRow()
        if row < 0:
            return
        self.ui.table_daily.blockSignals(True)
        self.ui.table_daily.removeCellWidget(row, 5)
        self.ui.table_daily.removeCellWidget(row, 4)
        self.ui.table_daily.removeCellWidget(row, 2)
        self.ui.table_daily.clearSelection()
        self.ui.animal_photos_daily.clear()
        self.ui.table_daily.blockSignals(False)

    # Удаляем запись животного за день
    def delete_animal_for_day(self):
        """
        Этот метод удаляет все записи о животном за определенный день из базы данных.
        Перед продолжением он запрашивает подтверждение у пользователя.
        Если пользователь подтверждает, он удаляет записи и соответствующим образом обновляет пользовательский интерфейс.
        """
        row = self.ui.table_daily.currentRow()
        if row < 0:
            return

        data_daily = self.ui.table_daily.item(row, 0).data(Qt.UserRole)

        res_1 = QMessageBox.question(self, "Question Daily!",
                                     "Delete all records of an animal {0} from the database for a day {1}?   "
                                     .format(data_daily.animal_name, data_daily.r_date),
                                     QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if res_1 == QMessageBox.Yes:
            res_2 = QMessageBox.question(self, "Question!",
                                         "Are you sure?  "
                                         .format(self.ui.cmb_search_name.currentText()),
                                         QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
            if res_2 == QMessageBox.Yes:

                if data_daily:

                    self.main_session.delete(data_daily)
                    self.main_session.commit()
                    self.ui.table_daily.removeRow(row)

                    if not self.main_session.query(Daily).filter_by(r_year=data_daily.r_year,
                                                                    site=data_daily.site,
                                                                    species=data_daily.species,
                                                                    animal_name=data_daily.animal_name).all():
                        row = self.ui.table_animals_list.currentRow()
                        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)

                        self.main_session.delete(data_resight)
                        self.main_session.commit()

                        self.ui.table_animals_list.removeRow(row)
                        self.ui.cmb_search_name.removeItem(row)

                        self.ui.table_animals_list.selectionModel().clearSelection()
                        self.ui.cmb_search_name.setCurrentIndex(-1)

    # кнопка delete в animal info
    def delete_animal_location(self):
        """
        Удаляет запись регистрации животного на фотографии из базы данных.
        """
        row_daily = self.ui.table_daily.currentRow()
        if not self.ui.animal_photos_daily.selectedItems() or row_daily < 0:
            return

        index_image = self.selected_image

        data_daily = self.ui.table_daily.item(row_daily, 0).data(Qt.UserRole)

        data_location = self.ui.animal_photos_daily.currentItem().data(Qt.UserRole)

        res_1 = QMessageBox.question(self, "Question!",
                                     f"Delete location records of an animal {data_daily.animal_name} from the database?",
                                     QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if res_1 == QMessageBox.Yes:
            res_2 = QMessageBox.question(self, "Question!",
                                         "Are you sure?  "
                                         .format(self.ui.cmb_search_name.currentText()),
                                         QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
            if res_2 == QMessageBox.Yes:
                if data_location:
                    if data_location.is_prediction_point:
                        pass

                    else:
                        self.main_session.delete(data_location)
                    self.main_session.commit()

                self.load_location()

                self.ui.animal_photos_daily.setCurrentRow(index_image)

    # Выбрали статус животного для замены в списке resight
    def changed_status_resight(self, item):
        """
        Изменяет статус животного в таблице за год.
        Отправляет пользователю диалоговое окно с вопросом для подтверждения изменения.
        """
        row = self.ui.table_animals_list.currentRow()
        if row < 0:
            return
        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)
        res = QMessageBox.question(self, "Question Resight!",
                                   "Change Animal Status: {0} to {1}?  ".format(data_resight.status,
                                                                                item),
                                   QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if res == QMessageBox.Yes:
            data_resight.status = item
            data_resight.dateupdated = makeDatecreated()
            self.change_animal_info(item)

            self.main_session.commit()
            self.ui.table_animals_list.item(row, 2).setText(item)
        else:
            self.ui.table_animals_list.item(row, 2).setText(item)
            self.ui.cmb_status_resight.setCurrentText(item)

    # Выбрали sex животного для замены в списке resight
    def changed_sex_resight(self, item):
        """
        Этот метод отвечает за изменение пола животного в таблице за год. Он предлагает пользователю диалог подтверждения,
        и если пользователь подтверждает, он обновляет значение пола выбранного животного и сохраняет изменения в базу данных.
        """
        row = self.ui.table_animals_list.currentRow()
        if row < 0:
            return

        data_resight = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)
        res = QMessageBox.question(self, "Question Resight!",
                                   "Change Animal Sex: {0} to {1}?  ".format(data_resight.sex_r,
                                                                             item),
                                   QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if res == QMessageBox.Yes:
            data_resight.sex_r = item
            data_resight.dateupdated = makeDatecreated()
            self.main_session.commit()
            self.ui.table_animals_list.item(row, 1).setText(item)
        else:
            self.ui.table_animals_list.item(row, 1).setText(item)
            self.ui.cmb_gender_resight.setCurrentText(item)

    def changed_id_status_resight(self):
        """
        Этот метод изменяет статус идентификации животного в таблице за год, обновляя соответствующую ячейку в
        таблице пользовательского интерфейса.
        """
        row = self.ui.table_animals_list.currentRow()
        if row < 0:
            return

        id_status = False
        text = "No"
        if self.ui.chb_id_status.isChecked():
            id_status = True
            text = "Yes"

        data = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)
        data.id_status = id_status
        data.dateupdated = makeDatecreated()
        self.main_session.commit()

        self.ui.table_animals_list.item(row, 6).setText(text)

    # Замена brand quality
    def quality_text_edit(self):
        """
        Редактирует текст о качестве метки выбранного животного в таблице.
        """
        row = self.ui.table_animals_list.currentRow()
        if row < 0:
            return

        self.ui.brand_quality_resight.setText(
            self.brand_quality_edit(self.ui.brand_quality_resight.text()))
        data = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)

        data.brand_quality = self.ui.brand_quality_resight.text()
        data.dateupdated = makeDatecreated()
        self.main_session.commit()
        self.ui.table_animals_list.item(row, 4).setText(self.ui.brand_quality_resight.text())

    def brand_length(self):
        """
        Вычисляет длину имени метки.
        """
        text = self.ui.cmb_search_name.currentText()
        brand_len = len(text) - text.count('r') - text.count('a')
        return brand_len-1

    def brand_quality_edit(self, brand_text):
        """
        Редактирует показатель качества метки на основе конкретных критериев качества.

        """
        brand_chars_in_text = [char for char in brand_text if char in BRAND_CHARS]

        if not brand_chars_in_text:
            return ""

        return brand_text[:self.brand_length()] if len(brand_chars_in_text) <= self.brand_length() else brand_text[:-1]

    def comment_daily_edit(self):
        """
        Обновит комментарий для ежедневной записи в таблице.
        """
        row = self.ui.table_daily.currentRow()
        if row < 0:
            return

        comment = self.ui.table_daily.cellWidget(row, 6).text()
        data = self.ui.table_daily.item(row, 0).data(Qt.UserRole)
        if data:
            data.comments = comment
            data.dateupdated = makeDatecreated()
            self.main_session.commit()

    def comment_resight_edit(self):
        """
        Обновит комментарий для годовой записи в таблице.
        """
        row = self.ui.table_animals_list.currentRow()
        if row > -1:

            comment = self.ui.comment_resight.toPlainText()
            data = self.ui.table_animals_list.item(row, 0).data(Qt.UserRole)
            if data:
                data.comments = comment
                data.dateupdated = makeDatecreated()
                self.main_session.commit()

    # Выбрали имя животного для замены в списке daily
    def changed_animal_name_daily(self, new_name):
        """
        Изменит имя животного в ежедневной записи.
        Параметры: - new_name - Новое имя, которое будет присвоено животному.
        Этот метод изменяет имя животного в ежедневной записи.
        Сначала он предлагает пользователю подтвердить изменение имени.
        Если пользователь подтверждает, он проверяет, есть ли уже ежедневная запись для нового имени в тот же день.
        Если нет, создается новая ежедневная запись с новым именем.
        Затем метод обновляет старое имя на новое в таблице местоположений.
        Также обновляется имя животного в таблице Информация о животных.
        Если в ежедневных записях больше нет других записей со старым именем, годовая запись для животного удаляется.
        В конце метод обновляет интерфейс пользователя, чтобы отразить изменения.
        """
        row = self.ui.table_daily.currentRow()
        if row < 0:
            return

        data_daily = self.ui.table_daily.item(row, 0).data(Qt.UserRole)
        old_name = data_daily.animal_name

        res_1 = QMessageBox.question(self, "Question!",
                                     "Changing the name {0} to a {1}?   "
                                     .format(old_name, new_name),
                                     QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if res_1 == QMessageBox.Yes:
            res_2 = QMessageBox.question(self, "Question!",
                                         "Are you sure?  "
                                         .format(self.ui.cmb_search_name.currentText()),
                                         QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

            if res_2 == QMessageBox.Yes:
                # проверяем есть ли дневная запись для нового имени за день, если нет - создаем
                _daily = self.main_session.query(Daily).filter_by(r_year=data_daily.r_year,
                                                                  site=data_daily.site,
                                                                  species=data_daily.species,
                                                                  r_date=data_daily.r_date,
                                                                  animal_name=new_name).first()

                if not _daily:
                    insert_daily = Daily(r_year=data_daily.r_year,
                                         site=data_daily.site,
                                         species=data_daily.species,
                                         r_date=data_daily.r_date,
                                         animal_name=new_name,
                                         status=data_daily.status,
                                         local_site=data_daily.local_site,
                                         comments=data_daily.comments,
                                         observer=m_params.creator,
                                         datecreated=makeDatecreated())

                    self.main_session.add(insert_daily)
                    self.main_session.commit()

                # обновляем старое имя на новое в location
                old_location = self.main_session.query(Location).filter_by(r_year=data_daily.r_year,
                                                                           site=data_daily.site,
                                                                           r_date=data_daily.r_date,
                                                                           species=data_daily.species,
                                                                           animal_name=old_name).all()
                new_location = self.main_session.query(Location).filter_by(r_year=data_daily.r_year,
                                                                           site=data_daily.site,
                                                                           r_date=data_daily.r_date,
                                                                           species=data_daily.species,
                                                                           animal_name=new_name).all()
                for item_old in old_location:
                    if not list(filter(lambda x: x.file_name == item_old.file_name, new_location)):
                        item_old.animal_name = new_name
                        item_old.dateupdated = makeDatecreated()
                self.main_session.commit()

                # Обновляем имя в Animal Info
                animal_info_new = self.main_session.query(AnimalInfo).filter_by(r_year=data_daily.r_year,
                                                                                site=data_daily.site,
                                                                                species=data_daily.species,
                                                                                animal_name=new_name).all()
                animal_info_old = self.main_session.query(AnimalInfo).filter_by(r_year=data_daily.r_year,
                                                                                site=data_daily.site,
                                                                                species=data_daily.species,
                                                                                animal_name=new_name).all()
                for info_name_old in animal_info_old:
                    if not list(filter(lambda x: x.info_type == info_name_old.info_type, animal_info_new)):
                        info_name_old.animal_name = new_name
                        info_name_old.dateupdated = makeDatecreated()
                self.main_session.commit()

                # удаляем старую дневную регистрацию
                old_daily = self.main_session.query(Daily).filter_by(r_year=data_daily.r_year,
                                                                     site=data_daily.site,
                                                                     species=data_daily.species,
                                                                     r_date=data_daily.r_date,
                                                                     animal_name=old_name).first()
                if old_daily:
                    self.main_session.delete(old_daily)
                    self.main_session.commit()

                # проверяем если нет дневных регистраций животного, то удаляем годовую регистрацию
                name_all_daily = self.main_session.query(Daily).filter_by(r_year=data_daily.r_year,
                                                                          site=data_daily.site,
                                                                          species=data_daily.species,
                                                                          animal_name=old_name).all()
                if not name_all_daily:
                    resight = self.main_session.query(Resight).filter_by(r_year=data_daily.r_year,
                                                                         site=data_daily.site,
                                                                         species=data_daily.species,
                                                                         animal_name=old_name).first()
                    self.main_session.delete(resight)
                    self.main_session.commit()

                self.refresh()

    # Выбрали локальный участок для замены в списке daily
    def changed_local_site_daily(self, item):
        """
        Используется для изменения локального участка на определенный день в
        таблице дневной регистрации.

        """
        row = self.ui.table_daily.currentRow()
        if row < 0:
            return

        row = self.ui.table_daily.currentRow()
        data_daily = self.ui.table_daily.item(row, 0).data(Qt.UserRole)

        if not data_daily:
            return

        temp_loc_site = m_params.support_local_sites.itemFromNameOrId(item)
        daily_loc_site = m_params.support_local_sites.itemFromNameOrId(data_daily.local_site)

        if daily_loc_site:
            daily_loc_site_name = daily_loc_site.local_site_name
        else:
            daily_loc_site_name = data_daily.local_site

        if temp_loc_site:
            loc_site_name = temp_loc_site.local_site_name
            loc_site_id = temp_loc_site.local_site_id
        else:
            loc_site_id = 'U'
            loc_site_name = 'Unknown'

        res = QMessageBox.question(
            self,
            "Question Daily!",
            f"Change local site for day {data_daily.r_date}: {daily_loc_site_name} to {loc_site_name}?",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

        if res == QMessageBox.Yes:
            data_daily.local_site = loc_site_id
            self.main_session.commit()

        else:
            self.ui.table_daily.cellWidget(row, 5).setCurrentText(daily_loc_site_name)

    # Выбрали статус животного для замены в списке daily
    def changed_status_daily(self, item):
        """
        Этот метод используется для изменения статуса животного на определенный день.
        """
        priority_status_daily = 0
        priority_status_resight = 0

        if self.ui.table_daily.currentRow() > -1:
            row_daily = self.ui.table_daily.currentRow()
            row_resight = self.ui.table_animals_list.currentRow()
            data_daily = self.ui.table_daily.item(row_daily, 0).data(Qt.UserRole)
            data_resight = self.ui.cmb_search_name.currentData(Qt.UserRole)

            if not data_daily or not data_resight:
                return

            res = QMessageBox.question(
                self, "Question Daily!",
                f"Change Animal Status for day {data_daily.r_date}: {data_daily.status} to {item}?",
                QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

            if res == QMessageBox.Yes:
                data_daily.status = item
                self.change_animal_info(item)

                status_daily = m_params.support_animal_statuses.itemFromName(item)
                if status_daily:
                    priority_status_daily = status_daily.priority

                status_resight = m_params.support_animal_statuses.itemFromName(data_resight.status)
                if status_resight:
                    priority_status_resight = status_resight.priority

                # если дневной статус больше годового, то меняем годовой
                if priority_status_daily > priority_status_resight:
                    data_resight.status = item
                    self.ui.cmb_status_resight.setCurrentText(item)
                    self.ui.table_animals_list.item(row_resight, 2).setText(item)

                self.main_session.commit()

            else:

                self.ui.table_daily.cellWidget(row_daily, 4).setCurrentText(data_daily.status)

    # Выбрали в table daily
    def selected_daily(self):
        """
        Выбирает конкретную ежедневную запись и загружает соответствующие фотографии животного.
        """
        row = self.ui.table_daily.currentRow()
        if row < 0:
            return

        self.load_location()

        if self.ui.animal_photos_daily.count():
            self.selected_image = 0
            self.ui.animal_photos_daily.setCurrentRow(self.selected_image)

    # Выбрали животное в списке поиска
    def selected_search_name(self, item):
        """
        Осуществляет поиск метки животного в таблице table_animals_list.
        """
        if self.ui.table_animals_list.rowCount() > 0:
            for row in range(self.ui.table_animals_list.rowCount()):
                if self.ui.table_animals_list.item(row, 0).text() == item:
                    self.ui.table_animals_list.selectRow(row)

    def scene_clear(self):
        self.view.setPixmap(QPixmap())
        self.view.setToolTip('')
        self.view.clearAllRects()

    def selected_image_daily(self):
        """

            Этот метод используется для обработки выбора ежедневного фото животного.
            Он очищает сцену, обновляет элементы пользовательского интерфейса и загружает выбранное изображение.

        """
        self.scene_clear()
        selected_items = self.ui.animal_photos_daily.selectedItems()
        self.ui.groupBox_statuses.setTitle("")
        self.ui.comboBox_type_photo.setCurrentIndex(-1)
        self.ui.comboBox_animal_type.setCurrentIndex(-1)
        self.view.setToolTip('')

        if selected_items:
            i = self.ui.animal_photos_daily.indexFromItem(selected_items[0])
            self.ui.animal_photos_daily.setCurrentIndex(i)
            data_location = self.ui.animal_photos_daily.currentItem().data(Qt.UserRole)

            self.selected_image = i.row()
            self.load_image(self.selected_image)

            if str(data_location.type_photo) == "BestPhoto":
                type_photo = 'BestPhoto'
            else:
                type_photo = 'NoBest'

            type_count = "Location"
            if data_location.is_prediction_point:
                type_count = "Prediction"

            self.ui.groupBox_statuses.setTitle(type_count)

            self.ui.comboBox_type_photo.setCurrentText(type_photo)
            self.ui.comboBox_animal_type.setCurrentText(str(data_location.animal_type))

    def change_type_photo(self, item):
        """
        Изменяет тип качества выбранного фото на предоставленное значение элемента.
        """
        if not self.ui.animal_photos_daily.selectedItems():
            self.ui.comboBox_type_photo.setCurrentIndex(-1)
            return

        index = self.selected_image

        if item == 'BestPhoto':
            type_photo = item
        else:
            type_photo = ""

        location = list(
            filter(lambda x: x.file_name == self.animal_photos[self.selected_image], self.locations_animal))

        if location:
            location = location[0]
            if location.is_prediction_point:
                pass
            else:
                location.type_photo = type_photo
                location.dateupdated = makeDatecreated()
            self.main_session.commit()

        self.load_location()
        if self.ui.animal_photos_daily.count() > 0:
            self.ui.animal_photos_daily.setCurrentRow(index)

    def change_animal_status_photo(self, item):
        """
        Измените статус животного регистрации на фото.
        """
        if not self.ui.animal_photos_daily.selectedItems():
            self.ui.comboBox_animal_type.setCurrentIndex(-1)
            return

        priority_status_location = 0
        priority_status_daily = 0
        priority_status_resight = 0

        if item == 'D':
            priority_status_location = 10

        index_image = self.selected_image
        current_image = self.animal_photos[self.selected_image]

        row_daily = self.ui.table_daily.currentRow()
        row_resight = self.ui.table_animals_list.currentRow()

        if row_daily < 0 or row_resight < 0:
            return

        data_resight = self.ui.cmb_search_name.currentData(Qt.UserRole)
        data_daily = self.ui.table_daily.item(row_daily, 0).data(Qt.UserRole)

        locations = list(
            filter(lambda x: x.file_name == current_image and x.animal_name == data_resight.animal_name,
                   self.locations_animal))
        if locations:
            location = locations[0]
            if location.is_prediction_point:
                pass
            else:
                location.animal_type = item
            self.main_session.commit()

        support_status_location = m_params.support_animal_statuses.itemFromName(item)
        if support_status_location:
            priority_status_location = support_status_location.priority

        support_status_daily = m_params.support_animal_statuses.itemFromName(data_daily.status)
        if support_status_daily:
            priority_status_daily = support_status_daily.priority

        support_status_resight = m_params.support_animal_statuses.itemFromName(data_resight.status)
        if support_status_resight:
            priority_status_resight = support_status_resight.priority

        if priority_status_location > priority_status_daily:
            data_daily.status = item

            self.ui.table_daily.item(row_daily, 4).setText(item)

            if priority_status_location > priority_status_resight:
                data_resight.status = item
                self.ui.cmb_status_resight.setCurrentText(item)
                self.ui.table_animals_list.item(row_resight, 2).setText(item)

            self.main_session.commit()

        self.change_animal_info(item)
        self.load_location()
        self.ui.animal_photos_daily.setCurrentRow(index_image)

    def change_animal_name_photo(self):
        """
        Изменяет имя животного регистрации на фото.
        """
        if not self.ui.animal_photos_daily.selectedItems():
            self.ui.cmb_change_name_on_photo.setCurrentIndex(-1)
            return
        index_new_name = self.ui.cmb_change_name_on_photo.currentIndex()

        row_resight = self.ui.table_animals_list.currentRow()
        row_daily = self.ui.table_daily.currentRow()

        if row_resight < 0 or index_new_name < 0 or row_daily < 0:
            return

        data_resight = self.ui.table_animals_list.item(row_resight, 0).data(Qt.UserRole)
        data_daily = self.ui.table_daily.item(row_daily, 0).data(Qt.UserRole)

        new_name = self.ui.cmb_change_name_on_photo.itemText(index_new_name)

        file_name = None

        res_1 = QMessageBox.question(self, "Question!",
                                     "Changing the name {0} to a {1}?   "
                                     .format(data_resight.animal_name, new_name),
                                     QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if res_1 == QMessageBox.Yes:
            res_2 = QMessageBox.question(self, "Question!",
                                         "Are you sure?  "
                                         .format(self.ui.cmb_search_name.currentText()),
                                         QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
            if res_2 == QMessageBox.Yes:

                data_location = self.ui.animal_photos_daily.currentItem().data(Qt.UserRole)

                if not data_location:
                    return

                # проверяем есть ли дневная запись для нового имени за день, если нет - создаем
                is_have_daily = self.main_session.query(Daily).filter_by(r_year=data_daily.r_year,
                                                                         site=data_daily.site,
                                                                         species=data_daily.species,
                                                                         r_date=data_daily.r_date,
                                                                         animal_name=new_name).first()

                if not is_have_daily:
                    insert_daily = Daily(r_year=data_daily.r_year,
                                         site=data_daily.site,
                                         species=data_daily.species,
                                         r_date=data_daily.r_date,
                                         animal_name=new_name,
                                         status=data_daily.status,
                                         local_site=data_daily.local_site,
                                         comments=data_daily.comments,
                                         observer=m_params.creator,
                                         datecreated=makeDatecreated())

                    self.main_session.add(insert_daily)
                    self.main_session.commit()

                # обновляем старое имя на новое в location
                new_location = self.main_session.query(Location).filter_by(r_year=data_resight.r_year,
                                                                           site=data_resight.site,
                                                                           r_date=data_daily.r_date,
                                                                           species=data_resight.species,
                                                                           animal_name=new_name,
                                                                           file_name=file_name).first()
                if not new_location and data_location:
                    data_location.animal_name = new_name
                    data_location.dateupdated = makeDatecreated()
                    self.main_session.commit()

                # проверяем есть ли еще записи старого имени за этот день в location,
                # если нет, то удаляем дневную запись для старого имени
                location_old_name_check = self.main_session.query(Location).filter_by(
                    r_year=data_resight.r_year,
                    site=data_resight.site,
                    species=data_resight.species,
                    r_date=data_daily.r_date,
                    animal_name=data_resight.animal_name).all()

                if not location_old_name_check:
                    daily_delete = self.main_session.query(Daily).filter_by(r_year=data_resight.r_year,
                                                                            site=data_resight.site,
                                                                            species=data_resight.species,
                                                                            r_date=data_daily.r_date,
                                                                            animal_name=data_resight.animal_name
                                                                            ).first()
                    if daily_delete:
                        self.main_session.delete(daily_delete)
                        self.main_session.commit()

                self.refresh()

    def search_coords_point(self, file_name):
        """
        Ищет координаты регистрации животного на фото.
        """
        loc = list(filter(lambda x: x.file_name == file_name, self.locations_animal))[0]

        res = QtCore.QRectF(loc.iLeft - 100, loc.iTop - 100, 200, 200)
        return res

    def open_report(self):
        """
        Откроет окно отчета регистраций животных.
        """
        self.animal_id_report = AnimalIdReportWindow()
        self.animal_id_report.show()

    def dock_photos_visibilityChanged(self):
        self.ui.table_daily.setFocus(True)
