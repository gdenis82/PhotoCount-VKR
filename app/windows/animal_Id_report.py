import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QSortFilterProxyModel, Qt, QFileInfo, QCoreApplication
from PyQt5.QtWidgets import QProgressBar, QTableView, QFileDialog, QListWidgetItem

from app import m_params
from app.custom_widgets.checkable_comboBox import CheckableComboBox
from app.controllers.tables import PandasTableModel
from app.dialogs.open_files_and_dirs_dialog import getOpenFilesAndDirs
from app.models.main_db import Resight, Daily, AnimalInfo
from app.controllers.support_lists import LocalSitesList, SitesList
from app.models.support_db import Sites, LocalSites
from app.services.db_manager import SessionFactoryMain
from app.controllers.parameters import session_factory_main, support_session, user_settings
from app.view.ui_window_animal_id_report import Ui_AnimalIdReportWindow


class AnimalIdReportWindow(QtWidgets.QMainWindow):
    """
    Модуль отчета регистраций животных
    """
    def __init__(self, parent=None):
        super(AnimalIdReportWindow, self).__init__(parent=parent)

        self.main_session = session_factory_main.get_session()

        self.ui = Ui_AnimalIdReportWindow()
        self.ui.setupUi(self)
        self.show()

        self.headers = []
        self.reports_tabs: list[pd.DataFrame] = []
        self.sheet_header = ['Resight', 'Daily', 'Summary', 'Summary for day']

        self.myLongTask: Optional[TaskThread] = None

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        self.ui.statusbar.addWidget(self.progress_bar)
        self.label_status = QtWidgets.QLabel()
        self.ui.statusbar.addWidget(self.label_status)

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
                self.load_years_sites()

    def load_years_sites(self):
        """
        Загружает годы и сайты из данного списка файлов базы данных.
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
            resight = db_session.query(Resight).all()
            years = years + list(map(lambda x: x.r_year, resight))
            years = list(set(years))
            years.sort()
            sites = sites + list(map(lambda x: x.site, resight))
            sites = list(set(sites))
            sites.sort()

            species = species + list(map(lambda x: x.species, resight))
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

        Удаляет выбранные элементы из списка базы данных и обновляет другие связанные
        элементы пользовательского интерфейса
        """
        if self.db_list.selectedItems():
            for item in self.db_list.selectedItems():
                self.db_list.takeItem(self.db_list.row(item))

        self.comboBox_years.clear_items()
        self.comboBox_sites.clear_items()

        # for db_index in range(self.db_list.count()):
        self.load_years_sites()  # self.db_list.item(db_index).data(Qt.UserRole)

    def clear_list_db(self):
        """
        Очищает список, выпадающие списки и виджет вкладок.
        Этот метод очищает список в базе данных, удаляет элементы в выпадающих списках для годов и лежбищ,
        а также очищает все вкладки в виджете вкладок.
        """
        self.db_list.clear()
        self.comboBox_years.clear_items()
        self.comboBox_sites.clear_items()
        self.ui.tabWidget.clear()

    def add_db_to_report(self):
        """
        Добавляет файлы базы данных в отчет.
        Этот метод открывает диалог выбора файла для выбора одного или нескольких файлов базы данных SQLite.
        Выбранные файлы затем добавляются в список баз данных в отчете.
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
                        for file in os.listdir(str(os.path.join(root, folder))):
                            path = str(os.path.join(root, folder, file))
                            if Path(path).is_file():
                                fileNames.append(path)
                    if not folders:
                        for file in os.listdir(str(os.path.join(root, item))):
                            path = str(os.path.join(root, item, file))
                            if Path(path).is_file():
                                fileNames.append(path)
                    break

        if fileNames:
            for file in fileNames:
                if not self.db_list.findItems(Path(file).name, Qt.MatchFixedString):
                    item = QListWidgetItem(Path(file).name)
                    item.setData(Qt.UserRole, file)
                    item.setToolTip(file)
                    self.db_list.addItem(item)
        self.load_years_sites()

    def closeEvent(self, *args, **kwargs):
        if self.myLongTask:
            if self.myLongTask.isRunning():
                self.myLongTask.quit()

    def get_report(self):
        """
        Сформировать отчет.

        Отключает кнопку экспорта и кнопку получения отчета.
        Он извлекает выбранные годы и сайты из выпадающих списков и сохраняет их в отдельных списках.
        Если не выбраны ни годы, ни сайты, он устанавливает видимость индикатора прогресса в False,
        включает кнопку получения отчета и выходит из метода.
        В противном случае, он извлекает элементы из списка баз данных и создает новый экземпляр
        класса TaskThread с выбранными годами, сайтами, элементами и видами.
        Он подключает сигнал результата экземпляра TaskThread к методу результата.
        Затем он запускает TaskThread, устанавливает видимость индикатора прогресса в True,
        устанавливает минимальные и максимальные значения индикатора прогресса на 0,
        и обновляет текст label_status на "Обработка отчета".
        """
        self.btn_export.setEnabled(False)
        self.btn_get_report.setEnabled(False)

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
        self.myLongTask.start()
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.label_status.setText("Report Processing")

    def export(self):
        """
        Экспортирует данные в файл Excel.
        """
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseCustomDirectoryIcons
        if sys.platform == "linux" or sys.platform == "linux2":
            options |= QFileDialog.DontUseNativeDialog
        file, _ = QFileDialog.getSaveFileName(self, "Save Excel",
                                              "AnimalsReport_{0}-{1}-{2}".format(datetime.now().year,
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

    def result(self, dataFrames: list):
        """
        Отображает набор данных отчета в формате таблицы и показывает их в виде вкладок в пользовательском интерфейсе.
        """
        self.ui.tabWidget.clear()

        self.reports_tabs = dataFrames

        for i, data in enumerate(dataFrames):
            tablemodel = PandasTableModel(data)
            tableview = QTableView()
            proxyModel = QSortFilterProxyModel()
            proxyModel.setSourceModel(tablemodel)

            tableview.setSortingEnabled(True)
            tableview.setModel(proxyModel)
            tableview.verticalHeader().setModel(tablemodel)

            self.ui.tabWidget.addTab(tableview, self.sheet_header[i])

        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_get_report.setEnabled(True)
        self.myLongTask.quit()
        self.label_status.setText("Report Processing Completed")


class DataProcessor:
    """

    Класс, отвечающий за обработку данных из данных регистраций за год resight.

    """
    def __init__(self, resight_df):
        self.resight_df = resight_df
        self.ages = []
        self.natal_rookeries = []
        self.rookery_site = []
        self.support_sites = SitesList(support_session.query(Sites).all())

    def process_animal_name(self, animal_name):
        animal_rows = self.resight_df[self.resight_df['animal_name'] == animal_name]

        for index, item_res in animal_rows.iterrows():
            support_animal_name = m_params.support_animal_names.itemFromName(item_res['animal_name'])

            if support_animal_name:
                self.get_age(item_res, support_animal_name)
                self.get_natal_rookery(support_animal_name)
                self.get_rookery_site(item_res)

    def get_age(self, item_res, support_animal_name):
        if support_animal_name.t_date:
            age = int(item_res['r_year']) - int(str(support_animal_name.t_date)[0:4])
            self.ages.append(age)
        else:
            self.ages.append(None)

    def get_natal_rookery(self, support_animal_name):
        t_site = support_animal_name.t_site

        if t_site:
            support_rookery = self.support_sites.itemFromId(id_site=int(t_site))
            if support_rookery:
                natal_rookery = support_rookery.site_name
                self.natal_rookeries.append(natal_rookery)
            else:
                self.natal_rookeries.append(None)
        else:
            self.natal_rookeries.append(None)

    def get_rookery_site(self, item_res):
        if item_res['site']:
            support_rookery = self.support_sites.itemFromId(id_site=int(item_res['site']))
            if support_rookery:
                self.rookery_site.append(support_rookery.site_name)

    def process_all_animal_names(self):
        for animal_name in self.resight_df['animal_name'].unique():
            self.process_animal_name(animal_name)

    def update_resight_df(self):
        self.resight_df['age'] = self.ages
        self.resight_df['natal_rookery'] = self.natal_rookeries
        self.resight_df['rookery_site'] = self.rookery_site


class TaskThread(QtCore.QThread):
    """

   Класс TaskThread является подклассом QtCore.QThread.
   Он отвечает за выполнение задачи формирования отчета в отдельном потоке и отправку сигнала с результатом.
    """
    result = QtCore.pyqtSignal(list)

    def __init__(self, years=None, sites=None, db_list=None, species=None):
        QtCore.QThread.__init__(self)

        if not years or not sites or not db_list or not species:
            return

        self.years = years
        self.sites = sites
        self.species = species
        self.db_list = db_list
        self.support_local_sites = LocalSitesList(support_session.query(LocalSites).all())

    def run(self):
        """
        Запускает метод для извлечения данных из нескольких файлов базы данных за указанные годы, лежбиже и виды животных.
        """
        all_dt = []

        all_resight = []
        all_daily = []
        all_animal_info = []

        for db_file in self.db_list:
            session_report = SessionFactoryMain(f'sqlite:///{db_file}')
            db_session = session_report.get_session()
            for year in self.years:
                for site in self.sites:
                    resight = db_session.query(Resight).filter_by(r_year=year, site=site, species=self.species).all()
                    r_daily = db_session.query(Daily).filter_by(r_year=year, site=site, species=self.species).all()
                    animal_info = db_session.query(AnimalInfo).filter_by(r_year=year, site=site,
                                                                         species=self.species).all()

                    all_resight = all_resight + [item.as_dict() for item in resight]
                    all_daily = all_daily + [item.as_dict() for item in r_daily]
                    all_animal_info = all_animal_info + [item.as_dict() for item in animal_info]

        temp_all_daily = []
        for item_daily in all_daily:
            support_site_name = self.support_local_sites.itemFromNameOrIdAndSite(nameOrId=item_daily['local_site'],
                                                                                 site=item_daily['site'])
            if support_site_name:
                loc_site_name = support_site_name.local_site_name
            else:
                loc_site_name = item_daily['local_site']

            item_daily['local_site_name'] = loc_site_name
            temp_all_daily.append(item_daily)

        daily_df = pd.DataFrame(temp_all_daily)
        resight_df = pd.DataFrame(all_resight)
        animal_info_df = pd.DataFrame(all_animal_info)

        # Группируем по animal_name, считаем количество встреч
        encounter_count_df = daily_df.groupby(['species', 'r_year', 'site',
                                               'animal_name']).size().reset_index(name='time_seen')

        # Слияние результата с таблицей resight
        resight_df = pd.merge(resight_df, encounter_count_df,
                              on=['species', 'r_year', 'site', 'animal_name'], how='left')

        # Группируем по animal_name и находим первую и последнюю дату r_date
        result_seen_df = daily_df.groupby(['species', 'r_year', 'site',
                                           'animal_name']).agg({'r_date': ['min', 'max']}).reset_index()
        result_seen_df.columns = ['species', 'r_year', 'site', 'animal_name', 'first_seen', 'last_seen']

        # Слияние результата с таблицей resight
        resight_df = pd.merge(resight_df, result_seen_df,
                              on=['species', 'r_year', 'site', 'animal_name'], how='left')

        # Фильтруем строки по условию status (без учета регистра)
        filtered_animal_with_pup_df = daily_df[daily_df['status'].str.lower().isin(['wp', 'np'])]

        # Группируем и выбираем первую дату встречи самки с щенком
        first_seen_with_pup_df = filtered_animal_with_pup_df.groupby(['species',
                                                                      'r_year',
                                                                      'site',
                                                                      'animal_name'])['r_date'].min().reset_index()
        first_seen_with_pup_df.columns = ['species', 'r_year', 'site', 'animal_name', 'first_seen_with_pup']

        # Слияние результата с таблицей resight
        resight_df = pd.merge(resight_df, first_seen_with_pup_df,
                              on=['species', 'r_year', 'site', 'animal_name'], how='left')

        # Фильтруем строки по условию info_type и info_value!='no' (без учета регистра)
        column_animal_info = ["BiopsyTaken", "DatePupBirth", "MomPresence",
                              "IsFocalFemale", "MomSuckling", "NursingJuvenile",
                              "NursingPup", "PresenceJuvenile", "PupName",
                              "PupSurvival"]
        filtered_animal_info = animal_info_df[(animal_info_df['info_type'].isin(column_animal_info)) &
                                              (~animal_info_df['info_value'].str.lower().eq('no'))]

        # Группируем и выбираем значения для каждой группы
        grouped_animal_info_df = filtered_animal_info.groupby(['species',
                                                               'r_year', 'site',
                                                               'animal_name',
                                                               'info_type'])['info_value'].first().reset_index()

        # Преобразуем значения столбца info_type в заголовки столбцов
        pivoted_animal_info_df = grouped_animal_info_df.pivot(index=['species',
                                                                     'r_year', 'site', 'animal_name'],
                                                              columns='info_type', values='info_value').reset_index()

        for col in column_animal_info:
            if col not in pivoted_animal_info_df.columns:
                pivoted_animal_info_df[col] = np.nan

        # Слияние результата с таблицей resight
        resight_df = pd.merge(resight_df, pivoted_animal_info_df,
                              on=['species', 'r_year', 'site', 'animal_name'], how='left')

        data_processor = DataProcessor(resight_df)
        data_processor.process_all_animal_names()
        data_processor.update_resight_df()

        # Создаем значения по датам как отдельные колонки для summary_day_df
        daily_pivot = daily_df.pivot(index=['animal_name'], columns='r_date', values='status')

        # Объединяем таблицы для summary_day_df
        combining_tables_df = resight_df.join(daily_pivot, on='animal_name')

        # Выбираем нужные колонки для summary_day_df
        dates_summary = list(set(daily_df['r_date'].tolist()))
        dates_summary.sort()
        summary_day_df = combining_tables_df[['species', 'animal_name', 'sex_r', 'status'] + dates_summary]

        # Меняем столбцы
        summary_day_df.columns = ['Species', 'Animal Name', 'Gender', 'Status'] + dates_summary

        resight_df.columns = ['Species', 'Year', 'Site', 'Animal Name', 'Brand Quality', 'Gender', 'Status',
                              'Comment', 'IdStatus', 'Datecreated', 'Dateupdated', 'Time Seen', 'First Seen',
                              'Last Seen', 'FirstSeenWithPup', 'NursingJuvenile', 'NursingPup', 'BiopsyTaken',
                              'DatePupBirth', 'MomPresence', 'IsFocalFemale', 'MomSuckling', 'PresenceJuvenile',
                              'PupName', 'PupSurvival', 'Age', 'Natal Rookery', 'Rookery Site']

        daily_df.columns = ['Species', 'Year', 'Site', 'Animal Name', 'Date', 'Status', 'Local Site Id', 'Comment',
                            'Observer', 'Date Created', 'Date Updated', 'Local Site Name']

        daily_df = daily_df[['Species', 'Year', 'Site', 'Animal Name', 'Date', 'Status', 'Local Site Id',
                             'Local Site Name', 'Comment', 'Observer', 'Date Created', 'Date Updated']]

        # Заполняем NaN
        resight_df = resight_df.fillna('')
        daily_df = daily_df.fillna('')
        summary_day_df = summary_day_df.fillna('')

        resight_df['FirstSeenWithPup'] = resight_df['FirstSeenWithPup'].apply(
            lambda x: int(x) if x and not pd.isna(x) else '')

        all_dt.append(resight_df[['Species', 'Year', 'Site', 'Animal Name', 'Brand Quality', 'Gender', 'Status',
                                  'Comment', 'IdStatus', 'Datecreated', 'Dateupdated']])
        all_dt.append(daily_df)
        all_dt.append(resight_df[['Species', 'Year', 'Site', 'Natal Rookery', 'Rookery Site', 'Animal Name', 'Age',
                                  'Brand Quality', 'Gender', 'Status', 'Comment', 'Time Seen', 'First Seen',
                                  'Last Seen', 'FirstSeenWithPup', 'NursingJuvenile', 'NursingPup', 'BiopsyTaken',
                                  'DatePupBirth', 'MomPresence', 'IsFocalFemale', 'MomSuckling', 'PresenceJuvenile',
                                  'PupName', 'PupSurvival', 'IdStatus', 'Datecreated', 'Dateupdated']])
        all_dt.append(summary_day_df)

        self.result.emit(all_dt)
