import os
import sys
from typing import Optional

import pandas as pd

from pathlib import Path
from datetime import datetime
from sqlalchemy import text

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QTranslator, QLocale
from PyQt5.QtCore import QFileInfo, Qt, QSortFilterProxyModel
from PyQt5.QtGui import QStandardItem, QPixmap, QColor, QPalette
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QListWidgetItem, QDialog, QTableWidgetItem, QHeaderView, \
    QAbstractItemView, QCompleter

from app import PRODUCT_NAME, COMPANY_NAME, m_params
from app.controllers.support_lists import SpeciesList
from app.controllers.tables import PandasTableModel
from app.custom_widgets.image_viewer import PreviewImageViewer
from app.controllers.items_file import ItemFile, ItemFileCount
from app.models.model_registration_animal import ModelRegistrationAnimal
from app.services.helpers import check_pattern_suffixes, select_project_folders, \
    search_path_photo
from app.services.main_style import style_sheet, set_font
from app.controllers.parameters import session_factory_main, support_session
from app.view.ui_window_main import Ui_MainWindow
from app.windows.about import AboutWindow
from app.windows.animal_Id_report import AnimalIdReportWindow
from app.windows.animal_id import AnimalIDWindow
from app.windows.animal_registration import AnimalRegistration
from app.windows.count_report import CountReportWindow
from app.windows.location import LocationWindow
from app.dialogs.create_count_dialog import CreateCountDialog
from app.dialogs.visual_count_dialog import VisualCountDialog
from app.windows.count import CountWindow
from app.models.main_db import CountList, CountFiles, PointsCount, CountEffortSites, GroupsCount, Location, Daily, \
    Resight, PatternCount, CountEffortCategories
from app.models.support_db import Sites, Species


class MainWindow(QtWidgets.QMainWindow):
    """
    Главное окно программы
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.animal_id: Optional[AnimalIDWindow] = None
        self.count_report: Optional[CountReportWindow] = None
        self.animal_id_report: Optional[AnimalIdReportWindow] = None
        self.translator = QTranslator()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.view = PreviewImageViewer()
        self.initUi()

        self.animal_registration: Optional[AnimalRegistration] = None
        # получаем сессию бд сбора данных
        self.main_session = session_factory_main.get_session()

        self.fill_data_parameters()
        self.set_params()

    def initUi(self):
        """

        Инициализирует пользовательский интерфейс приложения.

        """
        self.setWindowTitle(PRODUCT_NAME)
        self.showMaximized()
        self.ui.btn_new_count.setVisible(False)
        self.ui.btn_edit_count_info.setVisible(False)
        self.ui.btn_delete_count.setVisible(False)

        for i in range(self.ui.tab_main_widget.count()):
            self.ui.tab_main_widget.setTabVisible(i, False)

        self.ui.imageLayout.addWidget(self.view, 0, 0, 1, 1)

        self.ui.actionConnectDb.triggered.connect(self.open_file_db)
        self.ui.actionDark.triggered.connect(lambda: style_sheet('Dark'))
        self.ui.actionLight.triggered.connect(lambda: style_sheet('Light'))
        self.ui.actionCount.triggered.connect(self.selected_count_mode)
        self.ui.actionLocation.triggered.connect(self.selected_location_mode)
        self.ui.actionCreate_Data_Base.triggered.connect(self.create_data_base)
        self.ui.actionFont.triggered.connect(set_font)
        self.ui.actionAnimal_Catalog.triggered.connect(self.open_animal_catalog)
        self.ui.actionAnimal_ID.triggered.connect(self.open_animal_id)

        self.ui.actionCount_Report.triggered.connect(self.open_count_report)
        self.ui.actionAnimalID_Report.triggered.connect(self.open_animal_id_report)

        self.ui.actionAbout.triggered.connect(self.open_about)
        self.ui.actionRussian.triggered.connect(self.translate_ru)
        self.ui.actionEnglish.triggered.connect(self.translate_en)

        self.ui.btn_new_count.clicked.connect(self.create_count)
        self.ui.btn_effort_edit.setVisible(False)
        self.ui.btn_edit_count_info.clicked.connect(self.edit_count_info)
        self.ui.btn_edit_visual_count.clicked.connect(self.edit_visual_count)
        self.ui.btn_delete_count.clicked.connect(self.delete_count)
        self.ui.btn_get_data_total.clicked.connect(self.get_data_total)
        self.ui.btn_total_count_to_csv.clicked.connect(self.total_count_to_csv)

        self.ui.cmb_year.activated.connect(self.selected_year)
        self.ui.cmb_year.editTextChanged.connect(self.check_edit_text_year)
        self.ui.cmb_site_id.activated.connect(self.selected_site_id)
        self.ui.cmb_site.activated.connect(self.selected_site_name)
        self.ui.cmb_site.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.ui.cmb_species.activated.connect(self.selected_species)
        self.ui.cmb_observer.activated.connect(self.selected_observer)

        self.ui.treeView_directories.clicked.connect(self.selected_folder_location)
        self.ui.treeView_directories.activated.connect(self.selected_folder_location)

        self.ui.lw_done_photos.doubleClicked.connect(self.open_window_current_mode)
        self.ui.lw_done_photos.itemClicked.connect(self.select_done_photo)

        self.ui.cmb_year.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.ui.cmb_site.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.ui.cmb_species.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.ui.cmb_observer.completer().setCompletionMode(QCompleter.PopupCompletion)

        self.ui.dates_list.itemClicked.connect(self.selected_date)

        self.ui.listWidget_photos.doubleClicked.connect(self.open_window_current_mode)
        self.ui.listWidget_photos.itemClicked.connect(self.selected_photo)
        self.ui.listWidget_photos.itemActivated.connect(self.selected_photo)
        self.ui.listWidget_photos.itemSelectionChanged.connect(self.select_photo)

        self.ui.table_info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.table_visual_count.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.table_effort.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.table_daily_report.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.ui.table_info.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.table_visual_count.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.table_effort.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.table_daily_report.setSelectionBehavior(QAbstractItemView.SelectRows)

    def get_param_from_file_db(self, file_name):
        """
        Получить параметры из имени файла и обновить пользовательский интерфейс на основе извлеченных значений.

        :param file_name: Имя файла, из которого необходимо извлечь параметры.
        :type file_name: Str

        :return: None
        """
        split_f_name = str(file_name).replace(Path(file_name).suffix, '').split('_')

        support_species = SpeciesList(support_session.query(Species).all())

        for item_v in split_f_name:
            i_year = self.ui.cmb_year.findText(item_v)
            if i_year >= 0:
                self.ui.cmb_year.setCurrentIndex(i_year)
                m_params.year = self.ui.cmb_year.currentText()

            i_site = self.ui.cmb_site_id.findText(item_v)
            if i_site >= 0:
                self.ui.cmb_site_id.setCurrentIndex(i_site)
                self.ui.cmb_site.setCurrentIndex(i_site)
                m_params.site = self.ui.cmb_site_id.currentText()

            support_observer = m_params.support_observers.itemFromId(item_v)
            if support_observer:
                index_observer = self.ui.cmb_observer.findData(support_observer.observer, Qt.UserRole)
                if index_observer >= 0:
                    self.ui.cmb_observer.setCurrentIndex(index_observer)
                    self.ui.txt_box_observer_id.setText(support_observer.observer)
                    m_params.creator = support_observer.observer

            sup_species = support_species.itemFromNameOrId(item_v)
            if sup_species:
                index_species = self.ui.cmb_species.findData(sup_species.species, Qt.UserRole)
                if index_species >= 0:
                    self.ui.cmb_species.setCurrentIndex(index_species)
                    m_params.species = sup_species.species

    def create_data_base(self):
        """
        Создать базу данных.

        Этот метод позволяет пользователю создать новый файл базы данных SQLite и инициализировать сессию с ним.

        Returns:
            None
        """
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseCustomDirectoryIcons

        path, _ = QFileDialog.getSaveFileName(self, "Create Data Base", "", "Sqlite (*.db)", options=options)

        if path is not None:
            m_params.main_db_path = path

            # создаем файл базы и получаем сессию
            session_factory_main.create_db(f'sqlite:///{path}')
            self.main_session = session_factory_main.get_session()

            # Извлекаем параметры из имени файла
            self.get_param_from_file_db(Path(path).name)

            # меняем заголовок программы
            self.setWindowTitle(f"{PRODUCT_NAME}  Source DB: {path}")

            self.after_changing_params()

        else:
            return

    def open_file_db(self):
        """
        Открывает диалоговое окно выбора файла базы данных SQLite и подключается к базе данных.

        Returns:
            bool: Возвращает True, если подключение к базе данных прошло успешно, и требуемая таблица существует.
            В противном случае возвращает False.
        """
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseCustomDirectoryIcons
        if sys.platform == "linux" or sys.platform == "linux2":
            options |= QFileDialog.DontUseNativeDialog
        path, _ = QFileDialog.getOpenFileName(self, "Connect Data Base", "", "Sqlite (*.db | *.sqlite)",
                                              options=options)

        if path:
            session_factory_main.connect_db(f'sqlite:///{path}')
            self.main_session = session_factory_main.get_session()

            statement = text("SELECT name FROM sqlite_master WHERE type='table' ")
            tab_list = self.main_session.execute(statement).fetchall()
            if not ('survey_effort',) in tab_list:
                QMessageBox.information(self, "Information!", "The database does not match the structure!")
                return
            m_params.main_db_path = path

            self.get_param_from_file_db(Path(path).name)

            self.setWindowTitle(f"{PRODUCT_NAME}  Source DB: {path}")

            self.after_changing_params()
            return True
        return False

    def fill_data_parameters(self):
        """
        Заполнение параметров данных.

        Этот метод используется для заполнения параметров данных в форме пользовательского интерфейса.
        Он наполняет комбобоксы данными, полученными из системной базы данных.

        Returns:
        - None
        """

        if not support_session:
            return

        # получаем текущую дату и заполняем combobox year начиная с 2000 года
        date = datetime.now()
        for item in range(2000, date.year + 1):
            self.ui.cmb_year.addItem(str(item))
        self.ui.cmb_year.setCurrentIndex(-1)

        # получаем из системной базы участки лежбищ и заполняем combobox sites
        sites = support_session.query(Sites).all()
        for i, item in enumerate(sites):
            self.ui.cmb_site_id.addItem(str(item.site), str(item.site_name))
            self.ui.cmb_site_id.setItemData(i, str(item.site_name), Qt.ToolTipRole)

            self.ui.cmb_site.addItem(str(item.site_name), str(item.site))
            self.ui.cmb_site.setItemData(i, str(item.site), Qt.ToolTipRole)
        self.ui.cmb_site_id.setCurrentIndex(-1)
        self.ui.cmb_site.setCurrentIndex(-1)

        # получаем из системной базы типы животных и заполняем combobox species
        species = support_session.query(Species).all()
        for i, item in enumerate(species):
            self.ui.cmb_species.addItem(item.species_name, item.species)
            self.ui.cmb_species.setItemData(i, str(item.species), Qt.ToolTipRole)
        self.ui.cmb_species.setCurrentIndex(-1)

        # заполняем combobox observers
        for item in m_params.support_observers:
            self.ui.cmb_observer.addItem(item.observer_name, item.observer)
        self.ui.cmb_observer.setCurrentIndex(-1)

    def set_params(self):
        """
        Устанавливает параметры для текущего экземпляра программного обеспечения.

        Этот метод принимает параметры из объекта `m_params` и устанавливает соответствующие значения в
        элементах пользовательского интерфейса программного обеспечения.
        """

        if m_params.main_db_path:
            self.setWindowTitle(f"{PRODUCT_NAME}  Source DB: {m_params.main_db_path}")

        if m_params.year:
            self.ui.cmb_year.setCurrentText(str(m_params.year))

        if m_params.site:
            item_site = self.ui.cmb_site_id.findText(str(m_params.site))
            if item_site:
                self.ui.cmb_site_id.setCurrentIndex(item_site)
                self.ui.cmb_site.setCurrentIndex(item_site)

        if m_params.creator:
            index = self.ui.cmb_observer.findData(m_params.creator, Qt.UserRole)
            if index >= 0:
                self.ui.cmb_observer.setCurrentIndex(index)
            self.ui.txt_box_observer_id.setText(m_params.creator)

        if m_params.species:
            index = self.ui.cmb_species.findData(m_params.species, Qt.UserRole)
            if index >= 0:
                self.ui.cmb_species.setCurrentIndex(index)

    def check_edit_text_year(self, year):
        """
        Проверьте, является ли введенный год допустимым и существует ли он в комбобоксе.

        Parameters:
        - year: Вводимый год для проверки.


        Raises:
        - ValueError: Если введенный год не является числом или если год не найден в комбо-боксе.

        """
        if not year:
            return

        try:
            if not year.isdigit():
                raise ValueError('Input year can only be a number')

            elif len(year) > 4 or len(year) == 4 and self.ui.cmb_year.findText(year) < 0:
                raise ValueError('Year not found')

        except Exception as ex:
            QMessageBox.warning(self, 'Error', ex.args[0])
            if m_params.year:
                index = self.ui.cmb_year.findText(m_params.year)
                self.ui.cmb_year.setCurrentIndex(index)

    def create_count(self):
        """
        Метод создания нового учета.

        Этот метод проверяет, подключена ли основная сессия к файлу даты. Если подключение не установлено,
        он задает пользователю вопрос в диалоговом окне о необходимости подключить файл даты. Если пользователь выбирает
        подключить файл даты, он вызывает метод `open_file_db` для установления подключения. Если подключение успешно
        установлено, и основная сессия теперь подключена, он загружает список дат
        и выбирает дату, указанную пользователем в диалоге подсчета.
        """
        if not self.main_session:
            ret = QMessageBox.question(self, 'Question',
                                       "The date file is not connected! Connect a date file?",
                                       QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

            if ret == QMessageBox.Yes:
                is_connect = self.open_file_db()
                if not is_connect or not self.main_session:
                    QMessageBox.information(self, "Information!", "The date file is not connected!")
                    return
            else:
                return

        new_count = CreateCountDialog()

        if new_count.exec() == QDialog.Accepted:
            self.load_dates_list()
            self.select_date(new_count.countData)

    def delete_count(self):
        """
        Удаляет выбранные строки из таблицы и обновляет базу данных.
        """
        if not self.ui.dates_list.selectedItems():
            return
        ret = QMessageBox.question(self, 'Question',
                                   "Some rows have been deleted from the table, delete them from the database?",
                                   QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

        if ret == QMessageBox.Yes:
            ret_2 = QMessageBox.question(self, 'Question',
                                         "Are you sure? This will affect the associated data!",
                                         QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
            if ret_2 == QMessageBox.Yes:
                count_item = self.ui.dates_list.item(self.ui.dates_list.currentRow()).data(Qt.UserRole)

                self.main_session.delete(count_item)
                self.main_session.commit()

                self.after_changing_params()

    def edit_count_info(self):
        """
        Редактирование информации об учете для выбранной даты в списке дат.

        Этот метод открывает диалог редактирования учета для выбранной даты и позволяет пользователю изменить
        данные учета. Если диалог принят (нажата кнопка OK), список дат перезагружается,
        и выбранная дата выбирается снова.

        """
        if not self.ui.dates_list.selectedItems():
            return
        count_item = self.ui.dates_list.item(self.ui.dates_list.currentRow()).data(Qt.UserRole)
        count_dialog = CreateCountDialog(count_item)

        if count_dialog.exec() == QDialog.Accepted:
            self.load_dates_list()
            self.select_date(count_dialog.countData)

    def selected_year(self):
        """
        Получает выбранный год из комбо-бокса и вызывает метод after_changing_params.

        """

        m_params.year = self.ui.cmb_year.currentText()
        self.after_changing_params()

    def selected_site_id(self, index):
        """
        Устанавливает выбранный ID лежбища на основе данного индекса.

        :param index: Индекс лежбища в комбо-боксе.
        :type index: Int

        """

        self.ui.cmb_site.setCurrentIndex(index)
        m_params.site = self.ui.cmb_site_id.currentText()
        self.after_changing_params()

    def selected_site_name(self, index):
        """
        Устанавливает выбранное имя сайта на основе данного индекса.

        Parameters:
            index (int): Индекс выбранного сайта в выпадающем меню.

        Note:
            - Этот метод обновляет текущий индекс комбо-бокса лежбища до данного индекса.
            - Он устанавливает значение `m_params.site` в выбранное имя сайта.
            - Затем он вызывает метод `after_changing_params`.
        """

        self.ui.cmb_site_id.setCurrentIndex(index)
        m_params.site = self.ui.cmb_site_id.currentText()
        self.after_changing_params()

    def selected_species(self, index):
        """
        Выбирает вид на основе данного индекса.

        Parameters:
            - index (int): Индекс вида в ComboBox.

        Note:
            Этот метод обновляет значение переменной `m_params.species` и вызывает метод `after_changing_params`.
        """

        data = self.ui.cmb_species.itemData(index, Qt.UserRole)
        m_params.species = data
        self.after_changing_params()

    def selected_observer(self, index):
        """
        Обновит наблюдателя на основе выбранного индекса.

        Parameters:
        - index (int): Индекс выбранного наблюдателя.
        """

        data = self.ui.cmb_observer.itemData(index, Qt.UserRole)
        m_params.creator = data
        self.ui.txt_box_observer_id.setText(data)
        self.after_changing_params()

    def selected_date(self):
        """

        Метод используется для обработки выбора даты в пользовательском интерфейсе.
        Он выполняет различные действия в зависимости от текущего режима,
        установленного в переменной `m_params.current_mode

        """
        try:
            self.clear_current_info()
            if not self.ui.dates_list.selectedItems():
                return

            if m_params.current_mode == 'Location':
                # извлекаем текущую дату
                date = self.ui.dates_list.item(self.ui.dates_list.currentRow()).data(Qt.UserRole)
                # получаем список имен файлов с регистрацией
                m_params.done_files = self.load_done_location_files(date)
                # выбираем директорию с папкой текущей даты
                self.select_folder_day_location(date)

            elif m_params.current_mode == 'Count':
                count_item = self.ui.dates_list.item(self.ui.dates_list.currentRow()).data(Qt.UserRole)
                m_params.current_data = count_item
                m_params.done_files = self.load_done_count_files(count_item)

                self.load_daily_report()
                self.load_count_info(count_item)
                self.load_count_files(count_item)

                self.createTableEffort()
                self.load_effort(count_item)
                self.load_table_visual()

        except Exception as ex:
            QMessageBox.warning(self, 'Error', ex.args[0])

    def selected_folder_location(self, index):
        """

        Обновляет пользовательский интерфейс для отображения выбранной папки и ее содержимого
        Parameters:
        - index: индекс выбранной папки в модели.


        """
        try:
            self.scene_clear()
            m_params.photos_for_day.clear()
            self.ui.listWidget_photos.clear()
            self.ui.lw_done_photos.clear()
            self.ui.dates_list.setCurrentRow(-1)
            self.clear_table_report_daily()

            parent = m_params.model_directories.parent(index)
            data = m_params.model_directories.data(parent)

            if not data:
                return

            day = m_params.model_directories.data(index)

            if self.ui.dates_list.count() and m_params.current_mode == 'Location':
                items_count = self.ui.dates_list.findItems(day, Qt.MatchFixedString | Qt.MatchRecursive)
                if items_count:
                    self.ui.dates_list.setCurrentItem(items_count[0])
                    date = self.ui.dates_list.item(self.ui.dates_list.currentRow()).data(Qt.UserRole)
                    m_params.done_files = self.load_done_location_files(date)

                    # таблица дневного отчета
                    self.load_daily_report()

            m_params.current_data = day

            path = os.path.join(data, day)
            if os.path.isdir(path):
                for dirs, folder, files in os.walk(str(path)):

                    files.sort()

                    for f_item in files:
                        if check_pattern_suffixes(f_item):
                            lw_item_data = ItemFile(fileName=str(f_item), path=str(os.path.join(str(path), f_item)))
                            lw_item = QListWidgetItem('%s' % f_item)
                            lw_item.setData(Qt.UserRole, lw_item_data)

                            if str(f_item) in m_params.done_files:
                                lw_item.setForeground(QColor('#FF0000'))

                            self.ui.listWidget_photos.addItem(lw_item)
                            m_params.photos_for_day.append(lw_item_data)

        except Exception as ex:
            QMessageBox.warning(self, 'Error', ex.args[0])

    def selected_photo(self, itemFile):
        """
            Загружает и выбирает фотографию из данного элемента файла.

            Parameters:
            - itemFile: элемент файла, содержащий данные о фотографии.

            Description:
            Этот метод получает элемент файла и извлекает связанные с ним данные. Если данных нет,
            метод немедленно возвращает управление, не выполняя дальнейших действий.
            Если данные доступны, метод загружает изображение с помощью пути, сохраненного в данных.
            Затем он проходит по списку сделанных фотографий, отображенных в пользовательском интерфейсе
            ищет соответствующий элемент. Если соответствующий элемент найден, метод устанавливает его в качестве
            текущего выбранного элемента в пользовательском интерфейсе и завершает цикл.
            Обратите внимание, что если у нескольких элементов одинаковое имя файла, в пользовательском интерфейсе
            будет выбран только первый из них.
            """
        data = itemFile.data(Qt.UserRole)
        if not data:
            return

        self.load_image(data.path)
        for i in range(self.ui.lw_done_photos.count()):
            item = self.ui.lw_done_photos.item(i)
            if item.text() == data.fileName:
                self.ui.lw_done_photos.setCurrentRow(i)
                break

    def after_changing_params(self):
        """
        Выбирает режим на основании данных в m_params.current_mode
        """

        if m_params.current_mode == 'Count':
            self.selected_count_mode()
        elif m_params.current_mode == 'Location':
            self.selected_location_mode()

    def selected_count_mode(self):
        """
        Устанавливает текущий режим на "Count" и соответствующим образом обновляет пользовательский интерфейс.

        Note:
        - Этот метод закрывает все другие окна в различных режимах.
        - Устанавливает текущий режим в "Count".
        - Скрывает директории дерева просмотра и виджет списка локальных участков.
        - Делает доступными кнопки для создания нового учета, удаления учета и редактирования информации об учете."""
        self.closeAllWindowsOtherMode()
        m_params.current_mode = "Count"
        self.ui.treeView_directories.setVisible(False)
        self.ui.btn_new_count.setVisible(True)
        self.ui.btn_delete_count.setVisible(True)
        self.ui.btn_edit_count_info.setVisible(True)

        for i in range(self.ui.tab_main_widget.count()):
            self.ui.tab_main_widget.setTabVisible(i, True)

        self.load_dates_list()

    def selected_location_mode(self):
        """
        Устанавливает текущий режим в "Location" и производит необходимые корректировки пользовательского интерфейса.

        Этот метод закрывает все другие окна в разных режимах, устанавливает текущий режим
        на "Location", загружает список дат и делает видимыми/невидимыми определенные элементы
        пользовательского интерфейса.
        Он также корректирует видимость вкладок в основном виджете.

        """
        self.closeAllWindowsOtherMode()
        m_params.current_mode = "Location"
        self.load_dates_list()
        self.ui.treeView_directories.setVisible(True)
        self.ui.btn_new_count.setVisible(False)
        self.ui.btn_delete_count.setVisible(False)
        self.ui.btn_edit_count_info.setVisible(False)
        for i in range(self.ui.tab_main_widget.count()):
            if i == 0:
                self.ui.tab_main_widget.setTabVisible(i, True)
            else:
                self.ui.tab_main_widget.setTabVisible(i, False)

    def select_date(self, item_count):
        """
        Выбирает дату из dates_list на основе предоставленного item_count.

        Parameters:
        - item_count: Параметр item_count, содержащий информацию о дате и времени начала.
        """
        if self.ui.dates_list.count():
            items = self.ui.dates_list.findItems('{0} {1}'.format(item_count.r_date, item_count.time_start),
                                                 Qt.MatchFixedString | Qt.MatchRecursive)
            if items:
                self.ui.dates_list.setCurrentItem(items[0])
                self.ui.dates_list.setCurrentRow(self.ui.dates_list.currentRow())
                self.selected_date()

    def select_folder_day_location(self, day):
        """
        Выбирает директорию папки для указанного дня.

        :param day: День, для которого следует выбрать директорию папки.
        :type day: Str
        """

        items = m_params.model_directories.findItems(day, Qt.MatchFixedString | Qt.MatchRecursive)
        if items:
            index = m_params.model_directories.indexFromItem(items[0])
            self.ui.treeView_directories.setCurrentIndex(index)

    def select_folder_location(self, file_name):
        """
        Выбирает директорию папки для данного имени файла.

        Args:
            file_name (str): имя файла

        Returns:
            None
        """
        day = file_name[0:8]
        dir_items = m_params.model_directories.findItems(day, Qt.MatchFixedString | Qt.MatchRecursive)
        m_params.done_files = self.load_done_location_files(day)
        self.load_daily_report()
        self.scene_clear()

        _flag = False
        _temp_index = None

        for dir_item in dir_items:
            index = m_params.model_directories.indexFromItem(dir_item)
            self.ui.listWidget_photos.clear()
            m_params.photos_for_day.clear()

            if self.ui.dates_list.count() and m_params.current_mode == 'Location':
                items_count = self.ui.dates_list.findItems(day, Qt.MatchFixedString | Qt.MatchRecursive)
                if items_count:
                    self.ui.dates_list.setCurrentItem(items_count[0])

                    parent = m_params.model_directories.parent(index)
                    d = m_params.model_directories.data(parent)

                    path = os.path.join(d, day)
                    if os.path.isdir(path):
                        for dirs, folder, files in os.walk(path):
                            files.sort()

                            for f_item in files:
                                if check_pattern_suffixes(f_item):
                                    lw_item_data = ItemFile(fileName=str(f_item), path=str(os.path.join(path, f_item)))
                                    lw_item = QListWidgetItem('%s' % f_item)
                                    lw_item.setData(Qt.UserRole, lw_item_data)
                                    if file_name == str(f_item):
                                        _temp_index = index
                                        _flag = True
                                    if str(f_item) in m_params.done_files:
                                        lw_item.setForeground(QColor('#FF0000'))

                                    self.ui.listWidget_photos.addItem(lw_item)
                                    m_params.photos_for_day.append(lw_item_data)

                            if _flag:
                                self.ui.treeView_directories.setCurrentIndex(_temp_index)
                                item = self.ui.listWidget_photos.findItems(file_name,
                                                                           Qt.MatchFixedString | Qt.MatchRecursive)
                                if item:
                                    self.ui.listWidget_photos.setCurrentItem(item[0])
                                return
                            break

    def select_photo(self):
        """
        Выбирает фотографию из списка фотографий.
        """
        if self.ui.listWidget_photos.currentRow() >= 0 and m_params.photos_for_day:
            self.selected_photo(self.ui.listWidget_photos.currentItem())

    def select_done_photo(self):
        """
        Выбирает выполненное фото из списка выполненных фотографий.
        """
        if self.ui.lw_done_photos.currentRow() >= 0:
            if m_params.current_mode == 'Count':
                for i in range(self.ui.listWidget_photos.count()):
                    item = self.ui.listWidget_photos.item(i)
                    if item.text().split(' ')[1] == self.ui.lw_done_photos.currentItem().text():
                        self.ui.listWidget_photos.setCurrentRow(i)

            elif m_params.current_mode == 'Location':
                file_name = self.ui.lw_done_photos.currentItem().text()

                if self.ui.listWidget_photos.selectedItems():
                    if self.ui.listWidget_photos.currentItem().text() == file_name:
                        return

                self.select_folder_location(file_name)
                self.load_resight_info()

    def scene_clear(self):
        """
        Очистка QGraphicsPixmap от изображения
        """
        self.view.setPixmap(QPixmap())

    def clear_current_info(self):
        """
        Очищает поля отображения текущей информации по учету или регистрации
        """
        m_params.done_files.clear()
        m_params.photos_for_day.clear()

        self.scene_clear()

        self.ui.listWidget_photos.clear()
        self.ui.lw_done_photos.clear()
        self.ui.table_daily_report.clear()
        self.ui.table_daily_report.setColumnCount(0)
        self.ui.table_daily_report.setRowCount(0)

        if m_params.current_mode == 'Count':
            self.clear_table_info()
            self.clear_table_effort()
            self.clear_table_report_daily()
            self.clear_table_visual()
            self.clear_table_daily_summary()

    def clear_table_daily_summary(self):
        """
        Очистка таблицы отображения суммарной информации учета
        """
        self.ui.table_summary_daily.setModel(QSortFilterProxyModel())

    def clear_table_effort(self):
        """
        Очистка таблицы отображения усилий учета
        """
        indices = self.ui.table_effort.rowCount()
        for index in reversed(range(indices)):
            self.ui.table_effort.model().removeRow(index)

    def clear_table_visual(self):
        """
        Очистка таблицы визуального учета
        """
        indices = self.ui.table_visual_count.rowCount()
        for index in reversed(range(indices)):
            self.ui.table_visual_count.model().removeRow(index)

    def clear_table_report_daily(self):
        """
        Очистка таблицы отображения детальной инф по фото учету
        """
        self.ui.table_daily_report.clear()
        indices = self.ui.table_daily_report.rowCount()
        for index in reversed(range(indices)):
            self.ui.table_daily_report.model().removeRow(index)

    def clear_table_info(self):
        """
        Очистка отображения таблицы текущей информации режима учета или регистраций
        """
        self.ui.table_info.clear()
        indices = self.ui.table_info.rowCount()
        for index in reversed(range(indices)):
            self.ui.table_info.model().removeRow(index)

    def load_dates_list(self):
        """

        Загрузить список дат на основе текущего режима.


        """

        self.ui.dates_list.clear()
        self.clear_current_info()

        statement = text("SELECT name FROM sqlite_master WHERE type='table' ")
        tab_list = self.main_session.execute(statement).fetchall()

        if not self.main_session or not tab_list:
            QMessageBox.information(self, 'Information', 'Please? connect data base file! ')
            return

        if m_params.current_mode == 'Count':

            self.load_directories()

            count_list = self.main_session.query(CountList).filter_by(r_year=m_params.year,
                                                                      site=m_params.site,
                                                                      species=m_params.species).all()
            count_list.sort(key=lambda x: x.r_date)

            for item in count_list:
                item_count = QListWidgetItem('{0} {1}'.format(item.r_date, item.time_start))
                item_count.setData(Qt.UserRole, item)
                self.ui.dates_list.addItem(item_count)

        if m_params.current_mode == 'Location':

            daily = self.main_session.query(Daily).filter_by(r_year=m_params.year,
                                                             site=m_params.site,
                                                             species=m_params.species).all()
            dates = list(map(lambda x: x.r_date, daily))
            dates = list(set(dates))
            dates.sort()
            for date in dates:
                item_count = QListWidgetItem(str(date))
                item_count.setData(Qt.UserRole, str(date))
                self.ui.dates_list.addItem(item_count)

            self.load_directories()
            self.load_resight_info()

    def load_resight_info(self):
        """
        Подгружает список зарегистрированных животных за текущий год
        """
        resight = self.main_session.query(Resight).filter_by(r_year=m_params.year, site=m_params.site,
                                                             species=m_params.species).all()

        self.ui.table_info.clear()
        self.ui.table_info.setColumnCount(2)
        self.ui.table_info.setHorizontalHeaderLabels(('NAME', 'STATUS'))
        if not resight:
            return
        self.ui.table_info.setRowCount(len(resight))
        self.ui.table_info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.table_info.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        row = 0
        for value in resight:
            name_item = QTableWidgetItem(value.animal_name)
            data_item = QTableWidgetItem(value.status)

            self.ui.table_info.setItem(row, 0, name_item)
            self.ui.table_info.setItem(row, 1, data_item)
            row += 1

    def load_directories(self):
        """
        Заполняет дерево директорий
        """
        m_params.model_directories.clear()
        drivers = select_project_folders(m_params)
        dates = list(map(lambda x: self.ui.dates_list.item(x).text(), range(self.ui.dates_list.count())))

        for p in drivers:

            path = os.path.dirname(p[0] + "/")
            item = QStandardItem(path)
            m_params.model_directories.appendRow(item)

            for dirs, folders, files in os.walk(os.path.join(path)):
                folders.sort()
                for folder in folders:
                    sub_item = QStandardItem(folder)

                    if folder in dates:
                        sub_item.setForeground(QColor('#FF0000'))

                    item.appendRow(sub_item)
                break
        if len(drivers) > 0:
            m_params.model_directories.setHeaderData(0, Qt.Horizontal, " ")
            self.ui.treeView_directories.setModel(m_params.model_directories)
            self.ui.treeView_directories.selectionModel().currentChanged.connect(self.selected_folder_location)

    def load_count_files(self, count_item):
        """
        Загружает файлы учета на основе параметров.

        Parameters:
        - count_item (CountItem): Объект элемента учета.

        """
        self.ui.listWidget_photos.clear()

        if not count_item:
            return

        data_count_files = self.main_session.query(CountFiles).filter_by(r_year=count_item.r_year,
                                                                         site=count_item.site,
                                                                         r_date=count_item.r_date,
                                                                         time_start=count_item.time_start,
                                                                         creator=count_item.creator,
                                                                         species=count_item.species).all()
        temp_done_files = m_params.done_files.copy()
        for item in data_count_files:
            if check_pattern_suffixes(item.file_name):

                lw_item = QListWidgetItem(f'{item.count_type} {item.file_name}')

                path = search_path_photo(item.file_name)
                if path:
                    countType = m_params.support_count_type_id.itemFromId(item.count_type)
                    lw_item_data = ItemFileCount(path=path.replace('\\', '/'),
                                                 fileName=item.file_name,
                                                 countType=countType,
                                                 data=item)
                    m_params.photos_for_day.append(lw_item_data)
                    lw_item.setData(Qt.UserRole, lw_item_data)

                if item.file_name in temp_done_files:

                    if item.points_count and item.points_count[0].animal_category == 'NoAnimal':
                        lw_item.setForeground(QColor('#031FCB'))
                    elif item.points_count and item.points_count[0].animal_category == 'NoMarked':
                        lw_item.setForeground(QColor('#108405'))
                    else:
                        lw_item.setForeground(QColor('#FF0000'))

                    temp_done_files.remove(item.file_name)
                self.ui.listWidget_photos.addItem(lw_item)

    def load_image(self, path):
        """

            Загружает изображение из указанного пути и отображает его на экране.

            :param path: Путь к файлу изображения для загрузки.
            :type path: Str
        """
        self.scene_clear()
        pix_map = QPixmap(path)
        self.view.setPixmap(pix_map)

    def load_done_count_files(self, item_count):
        """

        Загрузка выполненных файлов подсчета

        Очищает список выполненных фотографий в пользовательском интерфейсе.
        Извлекает данные из базы данных на основе указанных параметров учета.
        Заполняет список выполненных файлов уникальными именами файлов, отсортированными по времени.

        :param item_count: Параметры учета.
        :return: Список выполненных файлов.

        """
        m_params.done_files.clear()
        self.ui.lw_done_photos.clear()

        data = []
        done_files = []

        if not item_count:
            return done_files

        if m_params.current_mode == "Count":
            data = self.main_session.query(PointsCount).filter_by(r_year=item_count.r_year,
                                                                  site=item_count.site,
                                                                  r_date=str(item_count.r_date),
                                                                  time_start=str(item_count.time_start),
                                                                  creator=item_count.creator,
                                                                  species=item_count.species).all()

            data_pattern = self.main_session.query(PatternCount).filter_by(r_year=item_count.r_year,
                                                                           site=item_count.site,
                                                                           r_date=str(item_count.r_date),
                                                                           time_start=str(item_count.time_start),
                                                                           creator=item_count.creator,
                                                                           species=item_count.species).all()
            data = data + data_pattern
        if data:
            done_files = list(map(lambda x: x.file_name, data))

            done_files = list(set(done_files))
            done_files.sort(key=lambda x: int(str(x).split('_')[1]))
            for item in done_files:
                done_item = QListWidgetItem(f'{item}')

                self.ui.lw_done_photos.addItem(done_item)

        return done_files

    def load_done_location_files(self, date):
        """
        Подгружает имена файлов с регистрацией животных

        Parameters:
        - date (str): Дата, для которой нужно загрузить файлы.

        Returns:
        - done_files (list[str]): Список выполненных файлов.
        """
        m_params.done_files.clear()
        self.ui.lw_done_photos.clear()

        done_files: list[str] = []

        data = self.main_session.query(Location).filter_by(r_year=m_params.year,
                                                           site=m_params.site,
                                                           r_date=date,
                                                           species=m_params.species).all()

        if data:
            # из data берем имена файлов
            done_files = list(map(lambda x: x.file_name, data))
            # убираем дубликаты
            done_files = list(set(done_files))
            # сортируем по времени из имени файла
            done_files.sort(key=lambda x: int(str(x).split('_')[1]))
            # заполняем список
            for item in done_files:
                done_item = QListWidgetItem(f'{item}')
                self.ui.lw_done_photos.addItem(done_item)

        return done_files

    def load_daily_report(self):
        """
        Формирует таблицу дневного отчета исходя из выбранного режима
        """

        current_date_row = self.ui.dates_list.currentRow()
        current_data_item = self.ui.dates_list.item(current_date_row).data(Qt.UserRole)
        self.ui.table_daily_report.clear()
        row = 0
        report = []
        if not current_data_item:
            return
        if m_params.current_mode.lower() == "location":
            self.ui.table_daily_report.setColumnCount(2)
            self.ui.table_daily_report.setHorizontalHeaderLabels(('NAME', 'STATUS'))

            data_daily = self.main_session.query(Daily).filter_by(r_year=m_params.year,
                                                                  site=m_params.site,
                                                                  species=m_params.species,
                                                                  r_date=current_data_item).all()
            for item_data in data_daily:
                report.append({'name': item_data.animal_name, 'data': item_data.status})

        elif m_params.current_mode.lower() == "count":
            self.ui.table_daily_report.setColumnCount(2)
            self.ui.table_daily_report.setHorizontalHeaderLabels(('CATEGORY', 'COUNT'))

            data_count = self.main_session.query(PointsCount).filter_by(r_year=current_data_item.r_year,
                                                                        r_date=current_data_item.r_date,
                                                                        site=current_data_item.site,
                                                                        species=current_data_item.species,
                                                                        time_start=current_data_item.time_start,
                                                                        creator=current_data_item.creator).all()
            for item_cat in m_params.support_categories_points:
                count = len(list(filter(lambda x: x.animal_category == item_cat.animal_category, data_count)))
                report.append({'name': item_cat.animal_category, 'data': count})

        self.ui.table_daily_report.setRowCount(len(report))
        self.ui.table_daily_report.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for i in report:
            name_item = QTableWidgetItem(str(i['name']))
            data_item = QTableWidgetItem(str(i['data']))
            self.ui.table_daily_report.setItem(row, 0, name_item)
            self.ui.table_daily_report.setItem(row, 1, data_item)
            row += 1

    def load_count_info(self, item_count):
        """

        Загрузить информацию о фотоучете таблицу.

        Parameters:
        - item_count: Параметры выбранного учета

        """
        self.ui.table_info.clearContents()
        self.ui.table_info.setColumnCount(2)
        self.ui.table_info.setHorizontalHeaderLabels(('LABEL', 'INFO'))
        if not item_count:
            return
        self.ui.table_info.setRowCount(len(item_count.as_dict().items()))
        self.ui.table_info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.table_info.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        row = 0
        for key, value in item_count.as_dict().items():
            name_item = QTableWidgetItem(key)
            data_item = QTableWidgetItem(str(value))

            self.ui.table_info.setItem(row, 0, name_item)
            self.ui.table_info.setItem(row, 1, data_item)
            row += 1

    def load_effort(self, count_item):
        """
        Загрузить данные об усилиях в таблицу.

        Parameters:
        - count_item: Параметры учета

        """
        if not count_item:
            return
        efforts = self.main_session.query(CountEffortSites).filter_by(r_year=count_item.r_year,
                                                                      site=count_item.site,
                                                                      r_date=count_item.r_date,
                                                                      time_start=count_item.time_start,
                                                                      species=count_item.species,
                                                                      creator=count_item.creator).all()

        for effort in efforts:
            row = self.ui.table_effort.rowCount()
            self.add_row_table_effort()

            self.ui.table_effort.item(row, 0).setText(str(effort.r_date))
            self.ui.table_effort.item(row, 0).setData(Qt.UserRole, effort)

            self.ui.table_effort.item(row, 1).setText(effort.time_start)
            count_type = list(filter(lambda x: x.type_id == effort.count_type, m_params.support_count_type_id))[
                0].description
            self.ui.table_effort.item(row, 2).setText(count_type)
            local_site = m_params.support_local_sites.itemFromId(effort.local_site)
            self.ui.table_effort.item(row, 3).setText(local_site.local_site_name)
            creator = list(filter(lambda x: x.observer == effort.creator, m_params.support_observers))[0].observer_name
            self.ui.table_effort.item(row, 4).setText(creator)
            observer = list(filter(lambda x: x.observer == effort.observer, m_params.support_observers))[
                0].observer_name
            self.ui.table_effort.item(row, 5).setText(observer)
            self.ui.table_effort.item(row, 6).setText(effort.comments)
            self.ui.table_effort.item(row, 7).setText(effort.visibility)
            self.ui.table_effort.item(row, 8).setText(effort.distance)
            self.ui.table_effort.item(row, 9).setText(effort.rain)
            self.ui.table_effort.item(row, 10).setText(effort.splash)
            self.ui.table_effort.item(row, 11).setText(effort.quality)
            self.ui.table_effort.item(row, 12).setText('Yes' if effort.count_performed else 'No')
            self.ui.table_effort.item(row, 13).setText(str(effort.coverage))
            self.ui.table_effort.item(row, 14).setText(effort.datecreated)
            self.ui.table_effort.item(row, 15).setText(effort.dateupdated)

    def createTableEffort(self):
        """
        Настройка представления таблицы для отображения данных об усилиях.


        """
        headers = ('Date', 'Time Start', 'Count Type', 'Local Site', 'Creator', 'Observer', 'Comments', 'Visibility',
                   'Distance', 'Rain', 'Splash', 'Quality', 'Count Performed', 'Coverage', 'Date Created',
                   'Date Update')
        self.ui.table_effort.setColumnCount(len(headers))
        self.ui.table_effort.setHorizontalHeaderLabels(headers)
        self.ui.table_effort.setColumnWidth(0, 100)
        self.ui.table_effort.setColumnWidth(1, 100)
        self.ui.table_effort.setColumnWidth(2, 150)
        self.ui.table_effort.setColumnWidth(3, 180)
        self.ui.table_effort.setColumnWidth(4, 100)
        self.ui.table_effort.setColumnWidth(5, 200)
        self.ui.table_effort.setColumnWidth(6, 120)
        self.ui.table_effort.setColumnWidth(7, 120)
        self.ui.table_effort.setColumnWidth(8, 120)
        self.ui.table_effort.setColumnWidth(9, 120)
        self.ui.table_effort.setColumnWidth(10, 120)
        self.ui.table_effort.setColumnWidth(11, 120)
        self.ui.table_effort.setColumnWidth(12, 120)
        self.ui.table_effort.setColumnWidth(13, 200)
        self.ui.table_effort.setColumnWidth(14, 200)
        self.ui.table_effort.setColumnWidth(15, 200)

    def add_row_table_effort(self):
        """
        Добавляет строку в виджет table_effort.

        Этот метод вставляет новую строку в конец виджета table_effort и заполняет каждую ячейку в новой строке пустым
        элементом QTableWidgetItem.
        """
        row = self.ui.table_effort.rowCount()
        self.ui.table_effort.insertRow(row)

        self.ui.table_effort.setItem(row, 0, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 1, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 2, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 3, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 4, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 5, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 6, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 7, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 8, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 9, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 10, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 11, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 12, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 13, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 14, QtWidgets.QTableWidgetItem())
        self.ui.table_effort.setItem(row, 15, QtWidgets.QTableWidgetItem())

    @staticmethod
    def open_about():
        """
        Открывает окно О программе.
        """
        about = AboutWindow()
        if about.exec():
            pass

    def open_window_current_mode(self):
        """
        Открывает окно в зависимости от текущего режима.
        """
        try:
            if m_params.current_mode == "Location":
                self.open_location()

            elif m_params.current_mode == "Count":
                if self.ui.dates_list.selectedItems():
                    self.open_count()
        except Exception as ex:
            print(ex)

    def open_count(self):
        """
        Метод используется для открытия окна фотоучета для выбранного фото в списке фотографий.
        """
        currentDataPhoto = self.ui.listWidget_photos.currentItem().data(Qt.UserRole)
        count_window = CountWindow(self, currentDataPhoto)
        count_window.update_done_photo_count.connect(self.update_done_photo_count)
        m_params.windows_list.append(count_window)

    def open_location(self):
        """
        Открывает окно регистрации меток по фото для текущего выбранного фото.

        """
        currentDataPhoto = self.ui.listWidget_photos.currentItem().data(Qt.UserRole)
        location_window = LocationWindow(self, currentDataPhoto)
        location_window.update_done_location[str].connect(self.update_done_location)
        m_params.windows_list.append(location_window)

    def open_animal_id(self):
        """
        Открывает окно идентификатора животного.

        Этот метод инициализирует новый экземпляр класса AnimalIDWindow
        и подключает сигнал open_location к слоту open_location_from_animal_id.
        """
        self.animal_id = AnimalIDWindow()
        self.animal_id.open_location[dict].connect(self.open_location_from_animal_id)

    # report count
    def open_count_report(self):
        """
        Открывает окно отчета о подсчете.
        """
        self.count_report = CountReportWindow()

    def open_animal_id_report(self):
        """
        Открывает окно отчета об идентификаторе животного.
        """
        self.animal_id_report = AnimalIdReportWindow()
        self.animal_id_report.show()

    def open_animal_catalog(self):
        """
        Открывает каталог животных.

        Поведение метода зависит от текущего режима.
        Если текущий режим - 'Count', он устанавливает атрибут 'onlyRead' объекта 'animal_registration' как True.
        Если текущий режим - 'Location', он подключает сигнал 'result' объекта 'animal_registration' к методу
        'handle_input_registration'.
        """
        self.animal_registration = AnimalRegistration()
        if m_params.current_mode == 'Count':
            self.animal_registration.onlyRead = True
        elif m_params.current_mode == 'Location':
            self.animal_registration.result[ModelRegistrationAnimal].connect(self.handle_input_registration)

    def handle_input_registration(self, reg: ModelRegistrationAnimal):
        """
        Обновит текущие данные с указанной датой регистрации и обновит список выполненных фотографий.

        :param reg: Объект ModelRegistrationAnimal, представляющий сведения о регистрации.
        """
        m_params.current_data = str(reg.date)
        self.update_done_location()

    # @QtCore.pyqtSlot(dict)
    def open_location_from_animal_id(self, param):
        """
        Откроет окно регистраций по фото, связанное с ID животного.

        :param param: Словарь, содержащий ID животного и данные регистрации на фото.
        :type param: Dict
        """
        data = param['data']
        self.selected_location_mode()
        items = self.ui.dates_list.findItems(str(data.r_date), Qt.MatchFixedString | Qt.MatchRecursive)
        if not items:
            return

        items[0].setSelected(True)
        self.ui.dates_list.setCurrentItem(items[0])
        self.ui.dates_list.setCurrentRow(self.ui.dates_list.currentRow())
        self.selected_date()

        items_done_photo = self.ui.lw_done_photos.findItems(str(data.file_name),
                                                            Qt.MatchFixedString | Qt.MatchRecursive)
        if items_done_photo:
            self.ui.lw_done_photos.setCurrentItem(items_done_photo[0])
            self.select_done_photo()
            self.open_location()

    def update_done_location(self, file_name=None):
        """
        Обновляет таблицы регистраций, добавляет файл в список фотографий с точками

        :param file_name: (Optional) имя файла.
        :type file_name: Str
        """
        if m_params.current_mode != 'Location':
            return
        items_dates = self.ui.dates_list.findItems(m_params.current_data, Qt.MatchFixedString | Qt.MatchRecursive)
        if m_params.current_data not in [item.text() for item in items_dates]:
            lw_date = QListWidgetItem(str(m_params.current_data))
            lw_date.setData(Qt.UserRole, m_params.current_data)
            self.ui.dates_list.addItem(lw_date)
            self.ui.dates_list.setCurrentItem(lw_date)
            self.ui.dates_list.setCurrentRow(self.ui.dates_list.currentRow())

        if file_name:
            index = self.ui.treeView_directories.currentIndex()
            items_done = self.ui.lw_done_photos.findItems(file_name, Qt.MatchFixedString | Qt.MatchRecursive)

            if file_name in m_params.done_files:
                if not items_done:
                    done_item = QListWidgetItem(f'{file_name}')
                    self.ui.lw_done_photos.addItem(done_item)

                m_params.model_directories.itemFromIndex(index).setForeground(QColor('#FF0000'))
                self.ui.listWidget_photos.currentItem().setForeground(QColor('#FF0000'))
            else:
                palette = QPalette()
                m_params.model_directories.itemFromIndex(index).setForeground(palette.text().color())
                self.ui.listWidget_photos.currentItem().setForeground(palette.text().color())

                for item_done in items_done:
                    row_item = self.ui.lw_done_photos.row(item_done)
                    self.ui.lw_done_photos.takeItem(row_item)

        self.load_resight_info()
        self.load_daily_report()

    def update_done_photo_count(self, itemData: ItemFileCount, categories, currentOperator):
        """

        Обновляет список выполненных фотографий и применяет визуальное оформление к соответствующим элементам в
        пользовательском интерфейсе.

        Параметры:
        - itemData: Экземпляр класса ItemFileCount, представляющий данные файла.
        - categories: Словарь, содержащий имена категорий в качестве ключей и подсчеты в качестве значений.
        - currentOperator: Функция, которая принимает два целочисленных аргумента и возвращает целочисленный результат
        (сложение или вычитание).

        """
        file_name = itemData.fileName
        items_done = self.ui.lw_done_photos.findItems(file_name, Qt.MatchFixedString | Qt.MatchRecursive)
        items_photo = self.ui.listWidget_photos.findItems(f"{itemData.fileData.count_type} {file_name}",
                                                          Qt.MatchFixedString | Qt.MatchRecursive)
        item_photo = None
        if items_photo:
            item_photo = items_photo[0]

        if file_name in m_params.done_files:
            if not items_done:
                done_item = QListWidgetItem(f'{file_name}')
                self.ui.lw_done_photos.addItem(done_item)
                self.ui.lw_done_photos.sortItems()

            if item_photo:
                data = item_photo.data(Qt.UserRole).fileData
                if data.points_count and data.points_count[0].animal_category == 'NoAnimal':
                    item_photo.setForeground(QColor('#031FCB'))
                elif data.points_count and data.points_count[0].animal_category == 'NoMarked':
                    item_photo.setForeground(QColor('#108405'))
                else:
                    item_photo.setForeground(QColor('#FF0000'))
        else:
            palette = QPalette()
            if item_photo:
                item_photo.setForeground(palette.text().color())

            for item_done in items_done:
                row_item = self.ui.lw_done_photos.row(item_done)
                self.ui.lw_done_photos.takeItem(row_item)
                self.ui.lw_done_photos.sortItems()

        for i in range(self.ui.table_daily_report.rowCount()):
            daily_item = self.ui.table_daily_report.item(i, 0)
            daily_item = daily_item.text()
            if daily_item in categories:
                count = categories[daily_item]
                result = currentOperator(int(self.ui.table_daily_report.item(i, 1).text()), count)
                self.ui.table_daily_report.item(i, 1).setText(str(result))

    def load_table_visual(self):
        """

        Загрузит таблицу визуального учета в пользовательском интерфейсе на
        основе выбранного элемента даты в dates_list.

        """
        try:
            self.ui.table_visual_count.clear()
            count_item = self.ui.dates_list.item(self.ui.dates_list.currentRow()).data(Qt.UserRole)
            if not count_item:
                return

            effortCategories = self.main_session.query(CountEffortCategories).filter_by(
                species=m_params.species,
                r_year=m_params.year,
                site=m_params.site,
                r_date=m_params.current_data.r_date,
                time_start=m_params.current_data.time_start,
                creator=m_params.current_data.creator,
                count_type='Visual', ).all()

            effort_categories_points = list(map(lambda x: x.animal_category, effortCategories))
            countAnimalsCategories = list(
                filter(lambda x: x.animal_category in effort_categories_points, m_params.support_categories_points))

            countAnimalsCategories.sort(key=lambda x: x.order)

            header = ['Date', 'Time Start', 'Observer', 'Local Site', 'Start', 'Finish']
            header += [item.animal_category for item in m_params.support_categories_points] + ['Total']

            self.ui.table_visual_count.setColumnCount(len(header))
            self.ui.table_visual_count.setHorizontalHeaderLabels(header)

            visuals = self.main_session.query(GroupsCount).filter_by(r_year=count_item.r_year,
                                                                     site=count_item.site,
                                                                     r_date=count_item.r_date,
                                                                     time_start=count_item.time_start,
                                                                     species=count_item.species,
                                                                     creator=count_item.creator,
                                                                     count_type='Visual').all()
            if not visuals:
                return

            row = 0
            df_visual = pd.DataFrame([item.as_dict() for item in visuals])
            local_sites = list(set(df_visual['local_site'].tolist()))
            self.ui.table_visual_count.setRowCount(len(local_sites))

            for loc_site in local_sites:
                total = 0
                df_data = df_visual[df_visual['local_site'] == loc_site]

                r_date = QtWidgets.QTableWidgetItem(str(df_data.iloc[0].r_date))
                self.ui.table_visual_count.setItem(row, 0, r_date)
                r_date.setData(Qt.UserRole, df_data)

                self.ui.table_visual_count.setItem(row, 1, QtWidgets.QTableWidgetItem(df_data.iloc[0].time_start))
                observer = m_params.support_observers.itemFromId(df_data.iloc[0].observer)
                self.ui.table_visual_count.setItem(row, 2, QtWidgets.QTableWidgetItem(observer.observer_name))

                local_site = m_params.support_local_sites.itemFromId(df_data.iloc[0].local_site)
                self.ui.table_visual_count.setItem(row, 3, QtWidgets.QTableWidgetItem(local_site.local_site_name))

                self.ui.table_visual_count.setItem(row, 4, QtWidgets.QTableWidgetItem(df_data.iloc[0].time_s))
                self.ui.table_visual_count.setItem(row, 5, QtWidgets.QTableWidgetItem(df_data.iloc[0].time_f))

                i = 6
                for a_item in m_params.support_categories_points:
                    category = pd.DataFrame()
                    count = 0
                    if a_item in countAnimalsCategories:
                        category = df_data[df_data['animal_category'] == a_item.animal_category]
                    else:
                        count = 'NA'

                    if not category.empty:
                        count = category['count'].iloc[0]
                    self.ui.table_visual_count.setItem(row, i, QtWidgets.QTableWidgetItem(str(count)))

                    if a_item.count_category and count != 'NA':
                        total += int(count)
                    i += 1
                self.ui.table_visual_count.setItem(row, i, QtWidgets.QTableWidgetItem(str(total)))
                row += 1
        except Exception as ex:
            QMessageBox.warning(self, 'Error', ex.args[0])

    def edit_visual_count(self):
        """
        Вызовет окно модуля добавления/редактирования визуального учёта для выбранной даты в списке дат.
        """
        if self.ui.dates_list.currentRow() < 0:
            return

        if 'Visual' not in [eff_type.count_type for eff_type in m_params.current_data.effort_types]:
            ret = QMessageBox.question(self, 'Question',
                                       f'Not Effort for Visual Count! Fill out Effort?',
                                       QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
            if ret == QMessageBox.Yes:
                self.edit_count_info()
            else:
                return

        visual_dialog = VisualCountDialog()

        if visual_dialog.exec():
            self.load_table_visual()

    def get_data_total(self):
        """
        Получить общие данные учета для выбранной даты.
        """
        if self.ui.dates_list.currentRow() < 0:
            return
        count_item = self.ui.dates_list.item(self.ui.dates_list.currentRow()).data(Qt.UserRole)

        self.clear_table_daily_summary()
        daily_total_count = DailyTotalCount(count_item)
        res_total = daily_total_count.get_data()
        tablemodel = PandasTableModel(pd.DataFrame(res_total))
        tablemodel.setReadOnly(range(tablemodel.columnCount()))
        proxyModel = QSortFilterProxyModel()
        proxyModel.setSourceModel(tablemodel)
        self.ui.table_summary_daily.setSortingEnabled(True)
        self.ui.table_summary_daily.setModel(proxyModel)

    def total_count_to_csv(self):
        """
        Экспортирует данные об общем дневном учете в файл CSV.

        """
        if self.ui.dates_list.currentRow() < 0:
            return
        count_item = self.ui.dates_list.item(self.ui.dates_list.currentRow()).data(Qt.UserRole)

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseCustomDirectoryIcons
        if sys.platform == "linux" or sys.platform == "linux2":
            options |= QFileDialog.DontUseNativeDialog
        title = 'Count Daily Total {0} '.format(self.ui.cmb_species.currentText())
        file, _ = QFileDialog.getSaveFileName(self, "Save Excel",
                                              title + str(count_item.r_date),
                                              "Excel (*.xlsx)", options=options)

        if file:
            daily_total_count = DailyTotalCount(count_item)
            res_total = daily_total_count.get_data()
            file_path = QFileInfo(file).filePath()
            res_total.to_excel(file_path, index=False)
            QMessageBox.information(self, 'Information', 'Complete! ', QMessageBox.Ok, QMessageBox.Ok)

    def translate_ru(self):
        """
        Перевести приложение на русский язык.
        """
        QLocale.setDefault(QLocale(QLocale.Russian))
        if self.translator.load(":/translates/ru.qm"):
            QtCore.QCoreApplication.installTranslator(self.translator)
            self.ui.retranslateUi(self)
        else:
            print("Ошибка загрузки файла перевода:")

    def translate_en(self):
        """
        Удаляет переводчика и устанавливает язык по умолчанию.
        """
        QtCore.QCoreApplication.removeTranslator(self.translator)
        QLocale.setDefault(QLocale.system())
        self.ui.retranslateUi(self)

    @staticmethod
    def closeAllWindowsOtherMode():
        """
        Закроет все окна из списка m_params.windows_list.
        """
        for w in m_params.windows_list:
            w.close()


class DailyTotalCount(object):
    """

    Представляет собой объект суммарного ежедневного подсчета.

    """
    def __init__(self, count_item):
        super().__init__()

        self.main_session = session_factory_main.get_session()

        self.count_item = count_item

    def get_data(self):
        """
        Возвращает фрейм данных, содержащий данные, вычисленные на основе различных подсчетов.
        """
        points_count = self.main_session.query(PointsCount).filter_by(r_year=self.count_item.r_year,
                                                                      r_date=self.count_item.r_date,
                                                                      site=self.count_item.site,
                                                                      species=self.count_item.species,
                                                                      time_start=self.count_item.time_start,
                                                                      creator=self.count_item.creator).all()
        points_count = list(map(lambda x: x.as_dict(), points_count))
        df_points = pd.DataFrame(points_count)

        groups_count = self.main_session.query(GroupsCount).filter_by(r_year=self.count_item.r_year,
                                                                      r_date=self.count_item.r_date,
                                                                      site=self.count_item.site,
                                                                      species=self.count_item.species,
                                                                      time_start=self.count_item.time_start,
                                                                      creator=self.count_item.creator).all()
        groups_count = list(map(lambda x: x.as_dict(), groups_count))
        groups_count = pd.DataFrame(groups_count)

        data = []
        for eff_type in self.count_item.effort_types:
            eff_type_sites = eff_type.effort_sites
            eff_type_sites.sort(key=lambda x: x.local_site)
            for eff_site in eff_type_sites:
                if eff_type.count_type == eff_site.count_type:
                    for cat in m_params.support_categories_points:

                        temp = {'r_year': self.count_item.r_year,
                                'site': self.count_item.site,
                                'r_date': self.count_item.r_date,
                                'time_start': self.count_item.time_start,
                                'count_type': eff_type.count_type,
                                'creator': self.count_item.creator,
                                'species': self.count_item.species,
                                'local_site': eff_site.local_site,
                                'animal_category': cat.animal_category,
                                'count': 'NA'
                                }
                        if cat.animal_category in self.get_effort_animal_categories(eff_type):
                            temp['count'] = 0
                        if not df_points.empty:
                            local_sites_points = list(set(df_points['local_site']))
                            local_sites_points.sort()

                            if eff_site.local_site in local_sites_points:
                                count_point = df_points[(df_points['animal_category'] == cat.animal_category) &
                                                        (df_points['local_site'] == eff_site.local_site) &
                                                        (df_points['count_type'] == eff_type.count_type)]

                                if not count_point.empty:
                                    temp['count'] = len(count_point)
                        if not groups_count.empty:
                            local_sites_groups = list(set(groups_count['local_site']))
                            local_sites_groups.sort()
                            if eff_site.local_site in local_sites_groups:
                                temp_count = groups_count[(groups_count['animal_category'] == cat.animal_category) &
                                                          (groups_count['local_site'] == eff_site.local_site) &
                                                          (groups_count['count_type'] == eff_type.count_type)]

                                if not temp_count.empty:
                                    count = temp_count.groupby(['animal_category', 'local_site']).sum()
                                    temp['count'] = count['count'][0]

                        data.append(temp)

        df = pd.DataFrame(data)
        res = []
        local_sites = list(set(df['local_site']))
        local_sites.sort()

        creator = self.count_item.creator
        support_creator = m_params.support_observers.itemFromId(self.count_item.creator)
        if support_creator:
            creator = support_creator.observer_name

        for local_site_id in local_sites:
            local_site_name = local_site_id

            support_local_site = m_params.support_local_sites.itemFromNameOrId(local_site_id)
            if support_local_site:
                local_site_name = support_local_site.local_site_name

            temp = {'r_year': self.count_item.r_year,
                    'site': self.count_item.site,
                    'r_date': self.count_item.r_date,
                    'time_start': self.count_item.time_start,
                    'creator': creator,
                    'species': self.count_item.species,
                    'local_site_id': local_site_id,
                    'local_site_name': local_site_name,
                    'cameras': 'NA',
                    'count_types': '',
                    'comments': self.count_item.comments,
                    }
            total = 'NA'
            lc_count_types = list(set(df[(df['local_site'] == local_site_id)]['count_type'].tolist()))
            if 'Map' in lc_count_types:
                points_count_local_site = self.main_session.query(PointsCount).filter_by(
                    r_year=self.count_item.r_year,
                    r_date=self.count_item.r_date,
                    site=self.count_item.site,
                    species=self.count_item.species,
                    time_start=self.count_item.time_start,
                    creator=self.count_item.creator,
                    local_site=local_site_id,
                    count_type='Map').all()
                cameras_lc = list(
                    set(str(file.file_name).split('_')[-1].split('.')[0] for file in points_count_local_site))
                cameras_lc.sort()
                temp['cameras'] = f"{len(cameras_lc)}: {cameras_lc}"

            temp['count_types'] = f"{len(lc_count_types)}: {lc_count_types}"
            temp_count = df[(df['local_site'] == local_site_id) & (df['count'] != 'NA')]
            if not temp_count.empty:
                total = 0
            for cat in m_params.support_categories_points:

                temp_count = df[(df['animal_category'] == cat.animal_category) &
                                (df['local_site'] == local_site_id) & (df['count'] != 'NA')]
                if not temp_count.empty:
                    count = temp_count.groupby(['animal_category', 'local_site'])['count'].sum()[0]
                    if cat.count_category:
                        total += count
                else:
                    count = 'NA'
                temp[cat.animal_category] = count

            temp['Total'] = total
            res.append(temp)
        df_res = pd.DataFrame(res)
        return df_res

    def get_effort_animal_categories(self, eff_type):
        """
        Функция извлекает категории животных, связанные с заданным типом усилий.
        """
        effort_categories_points = self.main_session.query(CountEffortCategories).filter_by(
            species=eff_type.species,
            r_year=eff_type.r_year,
            site=eff_type.site,
            r_date=eff_type.r_date,
            time_start=eff_type.time_start,
            creator=eff_type.creator,
            count_type=eff_type.count_type, ).all()
        effort_categories_points = list(map(lambda x: x.animal_category, effort_categories_points))
        return effort_categories_points


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(COMPANY_NAME)
    app.setApplicationName(PRODUCT_NAME)
    if support_session:
        main_window = MainWindow()
        main_window.show()
        sys.exit(app.exec())
    else:
        QMessageBox.warning(None, "Warning", "No connecting support base!")
