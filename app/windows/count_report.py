import os
import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from datetime import datetime
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QSortFilterProxyModel, Qt, QFileInfo, QCoreApplication
from PyQt5.QtWidgets import QTableView, QProgressBar, QFileDialog, QListWidgetItem

from app import m_params
from app.controllers.support_lists import LocalSitesList
from app.custom_widgets.checkable_comboBox import CheckableComboBox
from app.dialogs.open_files_and_dirs_dialog import getOpenFilesAndDirs
from app.controllers.tables import PandasTableModel
from app.models.main_db import CountList, PointsCount, GroupsCount, CountEffortCategories, CountFiles
from app.models.support_db import Species, LocalSites
from app.services.db_manager import SessionFactoryMain
from app.controllers.parameters import session_factory_main, support_session, user_settings
from app.view.ui_window_count_report import Ui_CountReportWindow


class CountReportWindow(QtWidgets.QMainWindow):
    """
    Отчет по учетам
    """
    def __init__(self, parent=None):
        super(CountReportWindow, self).__init__(parent=parent)

        self.main_session = session_factory_main.get_session()

        self.ui = Ui_CountReportWindow()
        self.ui.setupUi(self)
        self.show()

        self.sheet_header = ['Count Summary', 'Local Sites Summary', 'Efforts', 'Local Sites Summary by Camera']
        self.myLongTask: Optional[TaskThread] = None
        self.reports_tabs = None

        self.btn_export = QtWidgets.QPushButton("Export to Excel")
        self.btn_get_report = QtWidgets.QPushButton("Get")
        self.btn_export.clicked.connect(self.export)
        self.btn_get_report.clicked.connect(self.get_report)
        self.btn_export.setEnabled(False)
        self.ui.horizontalLayout.addWidget(self.btn_export)

        self.comboBox_years = CheckableComboBox()
        self.comboBox_years.setMinimumWidth(85)
        self.comboBox_years.setEditable(True)
        self.comboBox_sites = CheckableComboBox()
        self.comboBox_sites.setMinimumWidth(85)
        self.comboBox_sites.setEditable(True)
        self.comboBox_species = QtWidgets.QComboBox()
        self.comboBox_species.setMinimumWidth(85)

        self.label_years = QtWidgets.QLabel("Years: ")
        self.ui.horizontalLayout.addWidget(self.label_years)
        self.ui.horizontalLayout.addWidget(self.comboBox_years)
        self.label_sites = QtWidgets.QLabel("Sites: ")
        self.ui.horizontalLayout.addWidget(self.label_sites)
        self.ui.horizontalLayout.addWidget(self.comboBox_sites)
        self.label_species = QtWidgets.QLabel("Species: ")
        self.ui.horizontalLayout.addWidget(self.label_species)
        self.ui.horizontalLayout.addWidget(self.comboBox_species)
        self.ui.horizontalLayout.addWidget(self.btn_get_report)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        self.ui.statusbar.addWidget(self.progress_bar)
        self.label_status = QtWidgets.QLabel()
        self.ui.statusbar.addWidget(self.label_status)

        self.list_options = QtWidgets.QButtonGroup()
        self.list_options.setExclusive(False)
        for item_option in self.sheet_header:
            check_bx = QtWidgets.QCheckBox()
            check_bx.setChecked(True)
            check_bx.setText(item_option)
            self.list_options.addButton(check_bx)
            self.ui.verticalLayout_options.addWidget(check_bx)

        # список дата-файлов
        self.db_list = QtWidgets.QListWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.db_list.setSizePolicy(sizePolicy)
        self.db_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.db_list.customContextMenuRequested.connect(self.context_menu_list_db)

        self.group_box_db_list = QtWidgets.QGroupBox('DB List')
        self.vl_db = QtWidgets.QVBoxLayout()
        self.hl_db = QtWidgets.QHBoxLayout()
        self.btn_add_db = QtWidgets.QPushButton('Add DB')
        self.btn_add_db.clicked.connect(self.add_db_to_report)
        self.btn_clear_list = QtWidgets.QPushButton('Clear list')
        self.btn_clear_list.clicked.connect(self.clear_list_db)
        self.hl_db.addWidget(self.btn_add_db)
        self.hl_db.addWidget(self.btn_clear_list)
        self.vl_db.addItem(self.hl_db)
        self.vl_db.addWidget(self.db_list)
        self.group_box_db_list.setLayout(self.vl_db)
        self.ui.verticalLayout_options.addWidget(self.group_box_db_list)

        if user_settings.value('FileDB'):
            if os.path.exists(user_settings.value('FileDB')):
                file = user_settings.value('FileDB')
                item = QListWidgetItem(Path(file).name)
                item.setData(Qt.UserRole, file)
                item.setToolTip(file)
                self.db_list.addItem(item)
                self.load_years_sites_species()

    def load_years_sites_species(self):
        """
        Загружает года, сайты и виды из баз данных
        """
        files_db = []
        for db_index in range(self.db_list.count()):
            files_db.append(self.db_list.item(db_index).data(Qt.UserRole))
        if not files_db:
            return

        years = []
        sites = []
        species = []
        for file_db in files_db:
            session_report = SessionFactoryMain(f'sqlite:///{file_db}')
            db_session = session_report.get_session()
            counts_list = pd.DataFrame([cl.as_dict() for cl in db_session.query(CountList).all()])

            years = years + counts_list['r_year'].tolist()
            years = list(set(years))
            years.sort()
            sites = sites + counts_list['site'].tolist()
            sites = list(set(sites))
            sites.sort()
            species = species + counts_list['species'].tolist()
            species = list(set(species))
            species.sort()

        for i, year in enumerate(years):
            if self.comboBox_years.findText(str(year), Qt.MatchFixedString) < 0:
                self.comboBox_years.addItem(str(year))
                if str(year) == str(m_params.year):
                    self.comboBox_years.itemSetChecked(i + 1)
                    self.comboBox_years.setCurrentIndex(i + 1)

        for i, site in enumerate(sites):
            if self.comboBox_sites.findText(str(site), Qt.MatchFixedString) < 0:
                self.comboBox_sites.addItem(str(site))
                if str(site) == str(m_params.site):
                    self.comboBox_sites.itemSetChecked(i + 1)
                    self.comboBox_sites.setCurrentIndex(i + 1)

        for i, spec in enumerate(species):
            if self.comboBox_species.findText(str(spec), Qt.MatchFixedString) < 0:
                self.comboBox_species.addItem(str(spec))
                if str(spec) == str(m_params.species):
                    self.comboBox_species.setCurrentIndex(i)

        self.comboBox_years.setCurrentIndex(-1)
        self.comboBox_sites.setCurrentIndex(-1)

    def context_menu_list_db(self, point):
        menu = QtWidgets.QMenu()

        delete = QtWidgets.QAction('Delete ', menu)
        delete.triggered.connect(self.remove_db)
        menu.addAction(delete)

        menu.exec(self.db_list.mapToGlobal(point))

    def remove_db(self):
        """
        Удаляет выбранные элементы из списка баз данных и очищает данные о годах и сайтах.
        """
        if self.db_list.selectedItems():
            for item in self.db_list.selectedItems():
                self.db_list.takeItem(self.db_list.row(item))

        self.comboBox_years.clear_items()
        self.comboBox_sites.clear_items()
        # for db_index in range(self.db_list.count()):
        self.load_years_sites_species()  # self.db_list.item(db_index).data(Qt.UserRole)

    def clear_list_db(self):
        """

        Очищает список баз данных, сбрасывает выбор года, сайта, вида и виджета вкладок

        """
        self.db_list.clear()
        self.comboBox_years.clear_items()
        self.comboBox_sites.clear_items()
        self.comboBox_species.clear()
        self.ui.tabWidget.clear()

    def add_db_to_report(self):
        """
        Добавляет выбранные файлы баз данных в отчет.
        """
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseCustomDirectoryIcons
        selected_files = getOpenFilesAndDirs(filter="Sqlite (*.db)", options=options, caption="Selected Data Base")

        if not selected_files:
            return

        fileNames = []
        for item in selected_files:
            if Path(item).is_file():
                fileNames.append(item)
            else:
                for (root, dirs, files) in os.walk(item, topdown=True):
                    folders = list(filter(lambda x: x.endswith("_Data"), dirs))
                    for folder in folders:
                        for file in os.listdir(os.path.join(root, folder)):
                            path = os.path.join(root, folder, file)
                            if Path(path).is_file():
                                fileNames.append(path)
                    if not folders:
                        for file in os.listdir(os.path.join(root, item)):
                            path = os.path.join(root, item, file)
                            if Path(path).is_file():
                                fileNames.append(path)
                    break

                # fileNames = fileNames + [os.path.join(dirpath, f) for (dirpath, dirnames, filenames) in os.walk(item) for f in filenames]

        if fileNames:
            for file in fileNames:
                if not self.db_list.findItems(Path(file).name, Qt.MatchFixedString):
                    item = QListWidgetItem(Path(file).name)
                    item.setData(Qt.UserRole, file)
                    item.setToolTip(file)
                    self.db_list.addItem(item)

        self.load_years_sites_species()

    def get_report(self):
        """
        Очищает виджет вкладок пользовательского интерфейса, отключает кнопку get_report и кнопку экспорта.
        Извлекает выбранные годы и места из выпадающих списков.
        Если года или сайты не выбраны, возвращается без дальнейшей обработки.
        Извлекает элементы из списка баз данных.
        Инициализирует TaskThread с выбранными годами, сайтами, элементами из списка баз данных и выбранными видами.
        Соединяет сигналы result и progress_result TaskThread c соответствующими слотами. Запускает TaskThread.
        Устанавливает видимость индикатора прогресса и задает его минимальные и максимальные * значения равными 0.
        Устанавливает текст label_status в "Report Processing".
        """
        self.ui.tabWidget.clear()
        self.btn_get_report.setEnabled(False)
        self.btn_export.setEnabled(False)

        years = []
        sites = []

        for index in range(self.comboBox_years.count()):
            if self.comboBox_years.itemChecked(index) and self.comboBox_years.itemText(index) != 'All':
                years.append(int(self.comboBox_years.itemText(index)))

        for index in range(self.comboBox_sites.count()):
            if self.comboBox_sites.itemChecked(index) and self.comboBox_sites.itemText(index) != 'All':
                sites.append(int(self.comboBox_sites.itemText(index)))

        if not years or not sites:
            self.progress_bar.setVisible(False)
            self.btn_get_report.setEnabled(True)
            return

        items_db = []
        for x in range(self.db_list.count()):
            items_db.append(self.db_list.item(x).data(Qt.UserRole))
        self.myLongTask = TaskThread(years, sites, items_db, self.comboBox_species.currentText())
        self.myLongTask.result[list].connect(self.result)
        self.myLongTask.progress_result[str].connect(self.progress_result)
        self.myLongTask.start()
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.label_status.setText("Report Processing")

    def progress_result(self, string):
        """
        Устанавливает индикатор прогресса и обновляет метку статуса.
        """
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(0)
        self.label_status.setText(string)

    def result(self, report):
        """
        Устанавливает результаты отчета для отображения в пользовательском интерфейсе.
        """
        self.reports_tabs = report

        for i in range(len(report)):
            tablemodel = PandasTableModel(report[i])
            tableview = QTableView()
            proxyModel = QSortFilterProxyModel()
            proxyModel.setSourceModel(tablemodel)
            tableview.setSortingEnabled(True)
            tableview.setModel(proxyModel)
            if self.list_options.buttons()[i].checkState() > 0:
                self.ui.tabWidget.addTab(tableview, self.sheet_header[i])

        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_get_report.setEnabled(True)
        self.myLongTask.quit()
        self.label_status.setText("Report Processing Completed")

    def export(self):
        """
        Экспортирует данные reports_tabs в файл Excel.
        """
        if not self.reports_tabs:
            return

        species_name = self.comboBox_species.currentText()
        support_species = support_session.query(Species).all()
        support_species = list(filter(lambda x: x.species == species_name, support_species))
        if support_species:
            species_name = support_species[0].species_name

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseCustomDirectoryIcons
        if sys.platform == "linux" or sys.platform == "linux2":
            options |= QFileDialog.DontUseNativeDialog
        title = f'Count Report {species_name}'
        file, _ = QFileDialog.getSaveFileName(self, "Save Excel",
                                              title + "_{0}-{1}-{2}".format(datetime.now().year,
                                                                            datetime.now().month,
                                                                            datetime.now().day),
                                              "Excel (*.xlsx)", options=options)

        if file:

            file_path = QFileInfo(file).filePath()

            self.progress_bar.setVisible(True)
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(len(self.sheet_header))
            self.label_status.setText("Export Processing")

            with pd.ExcelWriter(file_path) as writer:
                for i, df in enumerate(self.reports_tabs):
                    header = self.sheet_header[i]
                    df.to_excel(writer, sheet_name=header, index=False)
                    self.label_status.setText(f"Export {header} | {len(df)} rows")
                    QCoreApplication.processEvents()

            self.progress_bar.setVisible(False)
            self.label_status.setText("Export Completed")

    def closeEvent(self, *args, **kwargs):
        if self.myLongTask:
            if self.myLongTask.isRunning():
                self.myLongTask.quit()


class TaskThread(QtCore.QThread):
    """
    Класс, представляющий поток для формирования отчета в фоновом режиме.
    """
    result = QtCore.pyqtSignal(list)
    progress_result = QtCore.pyqtSignal(str)

    def __init__(self, years=None, sites=None, db_list=None, species=None):
        QtCore.QThread.__init__(self)

        if not years or not sites or not db_list or not species:
            return

        self.years = years
        self.sites = sites
        self.species = species
        self.db_list = db_list

    @staticmethod
    def get_effort_animal_categories(eff_type, db_session):
        """

        Этот метод извлекает категории животных, связанные с заданным типом усилий.

        """
        effort_categories_points = db_session.query(CountEffortCategories).filter_by(
            species=eff_type.species,
            r_year=eff_type.r_year,
            site=eff_type.site,
            r_date=eff_type.r_date,
            time_start=eff_type.time_start,
            creator=eff_type.creator,
            count_type=eff_type.count_type, ).all()
        effort_categories_points = list(map(lambda x: x.animal_category, effort_categories_points))
        return effort_categories_points

    def run(self):

        self.years.sort()
        self.sites.sort()

        locals_sites_summary = []
        count_summary = []
        efforts_report = []
        cameras_summary = []

        for db_file in self.db_list:
            session_report = SessionFactoryMain(f'sqlite:///{db_file}')
            db_session = session_report.get_session()
            for year in self.years:
                for site in self.sites:
                    sys_local_sites = LocalSitesList(support_session.query(LocalSites).filter_by(site=int(site)).all())
                    sys_local_sites.sort(key=lambda x: x.local_site_id)

                    counts_list = db_session.query(CountList).filter_by(r_year=year,
                                                                        species=self.species,
                                                                        site=site).all()

                    for count_item in counts_list:
                        self.progress_result.emit(f"Grouping data: Site: {site}, Date: {count_item.r_date}")
                        points_count = db_session.query(PointsCount).filter_by(
                            r_year=count_item.r_year,
                            r_date=count_item.r_date,
                            site=count_item.site,
                            species=count_item.species,
                            time_start=count_item.time_start,
                            creator=count_item.creator).all()
                        points_count = list(map(lambda x: x.as_dict(), points_count))
                        df_points_count = pd.DataFrame(points_count)

                        groups_count = db_session.query(GroupsCount).filter_by(
                            r_year=count_item.r_year,
                            r_date=count_item.r_date,
                            site=count_item.site,
                            species=count_item.species,
                            time_start=count_item.time_start,
                            creator=count_item.creator).all()
                        groups_count = list(map(lambda x: x.as_dict(), groups_count))
                        df_groups_count = pd.DataFrame(groups_count)

                        data = []
                        for eff_type in count_item.effort_types:
                            eff_type_sites = eff_type.effort_sites
                            eff_type_sites.sort(key=lambda x: x.local_site)
                            for eff_site in eff_type_sites:
                                if eff_type.count_type == eff_site.count_type:

                                    item_eff_report = eff_site.as_dict()

                                    efforts_report.append(item_eff_report)

                                    for cat in m_params.support_categories_points:

                                        _temp_data = {'r_year': count_item.r_year,
                                                      'site': count_item.site,
                                                      'r_date': count_item.r_date,
                                                      'time_start': count_item.time_start,
                                                      'count_type': eff_type.count_type,
                                                      'creator': count_item.creator,
                                                      'species': count_item.species,
                                                      'local_site': eff_site.local_site,
                                                      'animal_category': cat.animal_category,
                                                      'comments': eff_type.comments,
                                                      'count': 'NA'
                                                      }
                                        effort_animal_categories = self.get_effort_animal_categories(eff_type,
                                                                                                     db_session)
                                        if cat.animal_category in effort_animal_categories and eff_site.count_performed:
                                            _temp_data['count'] = 0

                                        if not df_points_count.empty:
                                            local_sites_points = list(set(df_points_count['local_site']))
                                            local_sites_points.sort()

                                            if eff_site.local_site in local_sites_points:
                                                count_point = df_points_count[
                                                    (df_points_count['animal_category'] == cat.animal_category) &
                                                    (df_points_count['local_site'] == eff_site.local_site) &
                                                    (df_points_count['count_type'] == eff_type.count_type)]

                                                if not count_point.empty:
                                                    _temp_data['count'] = len(count_point)
                                        if not df_groups_count.empty:
                                            local_sites_groups = list(set(df_groups_count['local_site']))
                                            local_sites_groups.sort()
                                            if eff_site.local_site in local_sites_groups:
                                                temp_count = df_groups_count[
                                                    (df_groups_count['animal_category'] == cat.animal_category) &
                                                    (df_groups_count['local_site'] == eff_site.local_site) &
                                                    (df_groups_count['count_type'] == eff_type.count_type)]

                                                if not temp_count.empty:
                                                    count = temp_count.groupby(['animal_category', 'local_site']).sum()
                                                    _temp_data['count'] = count['count'].iloc[0]

                                        data.append(_temp_data)

                        df = pd.DataFrame(data)

                        local_sites = list(set(df['local_site']))
                        local_sites.sort()

                        creator = count_item.creator
                        support_creator = m_params.support_observers.itemFromId(count_item.creator)
                        if support_creator:
                            creator = support_creator.observer_name

                        # count summary
                        count_types = list(set(df['count_type'].tolist()))
                        count = 'NA'
                        total = 'NA'
                        _count_summary = {'r_year': count_item.r_year, 'site': count_item.site,
                                          'r_date': count_item.r_date, 'time_start': count_item.time_start,
                                          'creator': creator, 'species': count_item.species, 'cameras': 'NA',
                                          'local_sites': f"{len(local_sites)}: {local_sites}",
                                          'count_types': f"{len(count_types)}: {count_types}",
                                          'comments': count_item.comments, }

                        if 'Map' in count_types:
                            photo_files_count = db_session.query(CountFiles).filter_by(
                                r_year=count_item.r_year,
                                r_date=count_item.r_date,
                                site=count_item.site,
                                species=count_item.species,
                                time_start=count_item.time_start,
                                creator=count_item.creator,
                                count_type='Map', ).all()
                            photo_files_point = db_session.query(PointsCount).filter_by(
                                r_year=count_item.r_year,
                                r_date=count_item.r_date,
                                site=count_item.site,
                                species=count_item.species,
                                time_start=count_item.time_start,
                                creator=count_item.creator,
                                count_type="Map").all()

                            photo_files = photo_files_count + photo_files_point

                            if photo_files:
                                pattern = r'_([A-Za-z\d-]+)(?:\.)'
                                cameras = list(
                                    set(re.search(pattern, file.file_name).group(1) for file in photo_files))
                                cameras.sort()
                                _count_summary['cameras'] = f"{len(cameras)}: {cameras}"

                                """cameras_summary"""
                                temp_df = pd.DataFrame([item.as_dict() for item in photo_files_point])

                                if not temp_df.empty:
                                    # Извлекаем имя камеры из столбца 'file_name'
                                    temp_df['camera_name'] = temp_df['file_name'].str.extract(r"_([A-Za-z\d-]+)(?:\.)")

                                    # Группировка данных
                                    grouped_data = temp_df.groupby(
                                        ['r_date', 'time_start', 'count_type', 'species', 'animal_category',
                                         'camera_name']).size().reset_index(
                                        name='count')

                                    # Создаем сводную таблицу
                                    pivot_table = pd.pivot_table(grouped_data, values='count',
                                                                 index=['camera_name',
                                                                        'r_date',
                                                                        'time_start',
                                                                        'count_type',
                                                                        'species'],
                                                                 columns=['animal_category'],
                                                                 aggfunc='sum', fill_value=0)

                                    # Сбрасываем индексы, чтобы сделать столбцы 'camera_name' обычными столбцами
                                    pivot_table.reset_index(inplace=True)

                                    for cam in cameras:
                                        cam_total = 0
                                        _cameras_summary = {'r_year': count_item.r_year,
                                                            'site': count_item.site,
                                                            'r_date': count_item.r_date,
                                                            'time_start': count_item.time_start,
                                                            'species': count_item.species,
                                                            'creator': count_item.creator,
                                                            'count_type': "Map",
                                                            'camera_name': cam, }

                                        for cat in m_params.support_categories_points:
                                            count = 0

                                            temp_cam_count = pivot_table[(pivot_table['camera_name'] == cam)]
                                            if not temp_cam_count.empty and cat.animal_category in temp_cam_count:
                                                count = temp_cam_count[cat.animal_category].sum()
                                            if cat.count_category:
                                                cam_total += count
                                            _cameras_summary[cat.animal_category] = count
                                        _cameras_summary['Total'] = cam_total
                                        cameras_summary.append(_cameras_summary)
                                    """"""

                        temp_count = df[(df['count'] != 'NA')]
                        if not temp_count.empty:
                            total = 0
                        for cat in m_params.support_categories_points:
                            temp_count = df[(df['animal_category'] == cat.animal_category) & (df['count'] != 'NA')]
                            if not temp_count.empty:
                                count = temp_count.groupby(['animal_category'])['count'].sum().iloc[0]
                                if cat.count_category:
                                    total += count
                            else:
                                count = 'NA'
                            _count_summary[cat.animal_category] = count

                        _count_summary['Total'] = total
                        count_summary.append(_count_summary)

                        # local sites summary
                        for item_site in local_sites:
                            local_site_name = item_site
                            support_local_site = sys_local_sites.itemFromId(item_site)
                            if support_local_site:
                                local_site_name = support_local_site.local_site_name

                            _eff_loc_site_comments = list(set(df[(df['local_site'] == item_site)]['comments'].tolist()))
                            _local_sites_summary = {
                                'r_year': count_item.r_year,
                                'site': count_item.site,
                                'r_date': count_item.r_date,
                                'time_start': count_item.time_start,
                                'creator': creator,
                                'species': count_item.species,
                                'local_site_id': item_site,
                                'local_site_name': local_site_name,
                                'cameras': 'NA',
                                'comments': list(filter(lambda x: x not in ["", ".", " "], _eff_loc_site_comments))
                            }
                            total = 'NA'
                            lc_count_types = list(set(df[(df['local_site'] == item_site)]['count_type'].tolist()))
                            if 'Map' in lc_count_types:
                                points_count_local_site = db_session.query(PointsCount).filter_by(
                                    r_year=count_item.r_year,
                                    r_date=count_item.r_date,
                                    site=count_item.site,
                                    species=count_item.species,
                                    time_start=count_item.time_start,
                                    creator=count_item.creator,
                                    local_site=item_site,
                                    count_type="Map").all()
                                cameras_lc = list(
                                    set(str(file.file_name).split('_')[-1].split('.')[0] for file in
                                        points_count_local_site))
                                cameras_lc.sort()
                                _local_sites_summary['cameras'] = f"{len(cameras_lc)}: {cameras_lc}"

                            _local_sites_summary['count_types'] = f"{len(lc_count_types)}: {lc_count_types}"
                            temp_count = df[(df['local_site'] == item_site) & (df['count'] != 'NA')]
                            if not temp_count.empty:
                                total = 0
                            for cat in m_params.support_categories_points:

                                temp_count = df[(df['animal_category'] == cat.animal_category) &
                                                (df['local_site'] == item_site) & (df['count'] != 'NA')]
                                if not temp_count.empty:
                                    count = temp_count.groupby(['animal_category', 'local_site'])['count'].sum().iloc[0]
                                    if cat.count_category:
                                        total += count
                                else:
                                    count = 'NA'
                                _local_sites_summary[cat.animal_category] = count

                            _local_sites_summary['Total'] = total
                            locals_sites_summary.append(_local_sites_summary)

        df_locals_sites_summary = pd.DataFrame(locals_sites_summary)
        df_count_summary = pd.DataFrame(count_summary)
        df_efforts_report = pd.DataFrame(efforts_report)
        df_cameras_summary = pd.DataFrame(cameras_summary)
        self.result.emit([df_count_summary, df_locals_sites_summary, df_efforts_report, df_cameras_summary])
