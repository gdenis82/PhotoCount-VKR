import pandas as pd
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QIntValidator
from PyQt5.QtWidgets import QShortcut, QMessageBox, QAbstractItemView, QLineEdit

from app import m_params
from app.custom_widgets.support_cmb import SupportQComboBox
from app.models.main_db import CountEffortSites, GroupsCount, CountEffortCategories, CountFiles
from app.services.helpers import makeDatecreated
from app.controllers.parameters import session_factory_main
from app.view.ui_dialog_visual_count import Ui_VisualCountDialog


class VisualCountDialog(QtWidgets.QDialog):
    """
    Класс, представляющий диалоговое окно визуального подсчета.
    Этот класс предоставляет функциональность для редактирования и отображения данных визуального подсчета.
    Атрибуты:
    - HEADER_LABELS (list): Список заголовков для виджета таблицы.
    - main_session (Session): Объект сессии SQLAlchemy, представляющий основную сессию базы данных.
    - ui (Ui_VisualCountDialog): Экземпляр пользовательского интерфейса, сгенерированного Qt Designer.
    - delete_shortcut (QShortcut): Горячая клавиша для удаления строк в виджете таблицы.
    - new_row_shortcut (QShortcut): Горячая клавиша для добавления новых строк в виджет таблицы.
    - isClose (bool): Флаг, указывающий, должен ли диалог быть закрыт.
    - visualEfforts (list): Список сайтов для визуального подсчета усилий.
    - countAnimalsCategories (list): Список поддерживаемых категорий животных для подсчета.
    Методы:
    - initUi(): Инициализирует пользовательский интерфейс.
    - onReject(): Слот для обработки отклонения диалога.
    - closeEvent(event): Обработчик событий для события закрытия диалога.
    - checkUpdate(): Проверяет обновления в виджете таблицы и обновляет основную сессию соответственно.
    - accept(): Переопределяет функцию/метод accept() класса QDialog.
    - check(): Проверяет, заполнены ли все обязательные поля в виджете таблицы.
    - load_count(): Загружает данные визуального подсчета из основной сессии и заполняет виджет таблицы.
    """
    def __init__(self):

        super(VisualCountDialog, self).__init__()
        self.HEADER_LABELS = ['Date', 'Time Start', 'Observer', 'Local Site', 'Start', 'Finish']
        self.main_session = session_factory_main.get_session()

        self.ui = Ui_VisualCountDialog()
        self.ui.setupUi(self)

        self.delete_shortcut = QShortcut(QKeySequence.Delete, self.ui.tableWidget)
        self.new_row_shortcut = QShortcut(QKeySequence.New, self.ui.tableWidget)

        self._isClose = False
        self.visualEfforts = self.main_session.query(CountEffortSites).filter_by(
            r_year=m_params.year,
            site=m_params.site,
            r_date=m_params.current_data.r_date,
            time_start=m_params.current_data.time_start,
            species=m_params.species,
            count_type='Visual',
            creator=m_params.current_data.creator).all()

        effortCategories = self.main_session.query(CountEffortCategories).filter_by(
            species=m_params.species,
            r_year=m_params.year,
            site=m_params.site,
            r_date=m_params.current_data.r_date,
            time_start=m_params.current_data.time_start,
            creator=m_params.current_data.creator,
            count_type='Visual', ).all()
        effort_categories_points = list(map(lambda x: x.animal_category, effortCategories))
        self.countAnimalsCategories = list(
            filter(lambda x: x.animal_category in effort_categories_points, m_params.support_categories_points))

        self.countAnimalsCategories.sort(key=lambda x: x.order)

        self.initUi()

        self.load_count()

    def initUi(self):

        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidget.setSortingEnabled(True)
        self.ui.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.HEADER_LABELS += [item.animal_category for item in self.countAnimalsCategories] + ['Total']
        self.ui.tableWidget.setColumnCount(len(self.HEADER_LABELS))
        self.ui.tableWidget.setHorizontalHeaderLabels(self.HEADER_LABELS)

        self.ui.btn_add.clicked.connect(self.add_row)
        self.ui.btn_delete.clicked.connect(self.delete_row)

        self.delete_shortcut.activated.connect(self.delete_row)
        self.new_row_shortcut.activated.connect(self.add_row)

        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        self.ui.buttonBox.rejected.disconnect()
        self.ui.buttonBox.rejected.connect(self.onReject)

        self.showMaximized()
        self.setModal(True)

    def onReject(self):
        self.close()

    def closeEvent(self, event):
        self.checkUpdate()
        if self._isClose:
            try:
                self.main_session.commit()
            except Exception as ex:
                self.main_session.rollback()
                QMessageBox.warning(self, 'Error', ex.args[0])
                event.ignore()
            else:
                super().accept()
        else:
            if self.main_session.new or self.main_session.deleted or self.main_session.dirty:
                ret = QMessageBox.question(self, 'Question',
                                           "Close visual count editing? Are you sure?",
                                           QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
                if ret == QMessageBox.Yes:
                    self.main_session.rollback()
                    super().reject()
                else:
                    event.ignore()
            else:
                self.main_session.rollback()
                super().reject()

    def checkUpdate(self):
        result = self.getResultFromTable()
        for row in result:
            for animal_category in row['animal_category'].items():
                visual = self.main_session.query(GroupsCount).filter_by(r_year=m_params.year,
                                                                        site=m_params.site,
                                                                        r_date=m_params.current_data.r_date,
                                                                        time_start=m_params.current_data.time_start,
                                                                        species=m_params.species,
                                                                        creator=m_params.creator,
                                                                        local_site=row['local_site'],
                                                                        animal_category=animal_category[0]).first()
                if visual:
                    visual.observer = row['observer']
                    visual.time_s = row['start']
                    visual.time_f = row['finish']
                    visual.count = int(animal_category[1])
                    visual.dateupdated = makeDatecreated()

                else:
                    countFile = self.main_session.query(CountFiles).filter_by(
                        r_year=m_params.year,
                        site=m_params.site,
                        r_date=m_params.current_data.r_date,
                        time_start=m_params.current_data.time_start,
                        species=m_params.species,
                        creator=m_params.current_data.creator,
                        file_name='no_file',
                        count_type='Visual', ).first()
                    if not countFile:
                        self.main_session.add(CountFiles(r_year=m_params.year,
                                                         site=m_params.site,
                                                         species=m_params.species,
                                                         creator=m_params.current_data.creator,
                                                         r_date=m_params.current_data.r_date,
                                                         time_start=m_params.current_data.time_start,
                                                         observer=m_params.creator,
                                                         file_name='no_file',
                                                         count_type='Visual',
                                                         datecreated=makeDatecreated()))

                    visual = GroupsCount(r_year=m_params.year,
                                         site=m_params.site,
                                         r_date=m_params.current_data.r_date,
                                         time_start=m_params.current_data.time_start,
                                         observer=row['observer'],
                                         creator=m_params.creator,
                                         local_site=row['local_site'],
                                         time_s=row['start'],
                                         time_f=row['finish'],
                                         animal_category=animal_category[0],
                                         file_name='no_file',
                                         count=int(animal_category[1]),
                                         species=m_params.species,
                                         count_type='Visual',
                                         datecreated=makeDatecreated())

                    self.main_session.add(visual)

    def accept(self):
        if self.check():
            self._isClose = True
            self.close()
        else:
            QMessageBox.information(self, 'Information', "Visual Count not filled!")

    def check(self):
        for row in range(self.ui.tableWidget.rowCount()):

            if not self.ui.tableWidget.cellWidget(row, 2).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 2).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 3).currentData(Qt.UserRole):
                self.ui.tableWidget.cellWidget(row, 3).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 4).text():
                self.ui.tableWidget.cellWidget(row, 4).setFocus()
                return False
            if not self.ui.tableWidget.cellWidget(row, 5).text():
                self.ui.tableWidget.cellWidget(row, 5).setFocus()
                return False
        return True

    def load_count(self):
        try:
            visualCounts = self.main_session.query(GroupsCount).filter_by(r_year=m_params.year,
                                                                          site=m_params.site,
                                                                          r_date=m_params.current_data.r_date,
                                                                          time_start=m_params.current_data.time_start,
                                                                          species=m_params.species,
                                                                          creator=m_params.current_data.creator,
                                                                          count_type='Visual').all()

            df_visual = pd.DataFrame([item.as_dict() for item in visualCounts])
            if df_visual.empty:
                return

            local_sites = list(set(df_visual['local_site'].tolist()))

            row = 0
            for loc_site in local_sites:
                self.add_row()

                df_data = df_visual[df_visual['local_site'] == loc_site]
                self.ui.tableWidget.item(row, 0).setData(Qt.UserRole, df_data)
                self.ui.tableWidget.cellWidget(row, 2).select_data(df_data.iloc[0].observer)
                self.ui.tableWidget.cellWidget(row, 3).select_data(df_data.iloc[0].local_site)
                self.ui.tableWidget.cellWidget(row, 3).setEnabled(False)
                self.ui.tableWidget.cellWidget(row, 4).setText(df_data.iloc[0].time_s)
                self.ui.tableWidget.cellWidget(row, 5).setText(df_data.iloc[0].time_f)

                total = 0
                i = 6
                for a_item in self.countAnimalsCategories:
                    category = df_data[df_data['animal_category'] == a_item.animal_category]
                    count = 'NA'
                    if not category.empty:
                        count = category['count'].iloc[0]
                    self.ui.tableWidget.cellWidget(row, i).setText(str(count))
                    if a_item.count_category and count != 'NA':
                        total += count
                    i += 1

                self.ui.tableWidget.item(row, i).setText(str(total))

                row += 1
        except Exception as ex:
            QMessageBox.warning(self, 'Error', ex.args[0])

    def add_row(self):
        onlyInt = QIntValidator()
        df_effort = pd.DataFrame([item.as_dict() for item in self.visualEfforts])

        row = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.insertRow(row)

        item_date = QtWidgets.QTableWidgetItem(str(m_params.current_data.r_date))
        item_date.setFlags(Qt.ItemIsEnabled)
        item_date.setData(Qt.UserRole, pd.DataFrame())

        item_time = QtWidgets.QTableWidgetItem(m_params.current_data.time_start)
        item_time.setFlags(Qt.ItemIsEnabled)

        local_sites_effort = df_effort['local_site'].tolist()

        item_local_site = SupportQComboBox()
        for item in m_params.support_local_sites:
            if item.local_site_id in local_sites_effort:
                item_local_site.addItem(item.local_site_name, userData=item.local_site_id)
        item_local_site.setCurrentIndex(-1)
        item_local_site.activated.connect(self.check_selected_local_sites)

        item_observer = SupportQComboBox()
        for item in m_params.support_observers:
            item_observer.addItem(item.observer_name, userData=item.observer)
        item_observer.setCurrentIndex(item_observer.findData(m_params.creator, Qt.UserRole))

        item_start = QLineEdit()
        item_start.setValidator(onlyInt)
        item_start.setInputMask('00:00:00')
        item_finish = QLineEdit()
        item_finish.setValidator(onlyInt)
        item_finish.setInputMask('00:00:00')

        self.ui.tableWidget.setItem(row, 0, item_date)
        self.ui.tableWidget.setItem(row, 1, item_time)
        self.ui.tableWidget.setCellWidget(row, 2, item_observer)
        self.ui.tableWidget.setCellWidget(row, 3, item_local_site)
        self.ui.tableWidget.setCellWidget(row, 4, item_start)
        self.ui.tableWidget.setCellWidget(row, 5, item_finish)

        i = 6
        for _ in self.countAnimalsCategories:
            item_animal_type = QtWidgets.QLineEdit()
            item_animal_type.setValidator(onlyInt)
            item_animal_type.textChanged.connect(self.updateTotal)

            self.ui.tableWidget.setCellWidget(row, i, item_animal_type)
            i += 1

        item_total = QtWidgets.QTableWidgetItem()
        item_total.setFlags(Qt.ItemIsEnabled)
        self.ui.tableWidget.setItem(row, i, item_total)

        self.ui.tableWidget.resizeColumnsToContents()

    def check_selected_local_sites(self):
        loc_sites = []
        for row in range(self.ui.tableWidget.rowCount()):
            if row != self.ui.tableWidget.currentRow():
                loc_sites.append(self.ui.tableWidget.cellWidget(row, 3).currentData(Qt.UserRole))
        current_row = self.ui.tableWidget.cellWidget(self.ui.tableWidget.currentRow(), 3)
        if current_row.currentData(Qt.UserRole) in loc_sites:
            current_row.setCurrentIndex(-1)

    def delete_row(self):
        indices = self.ui.tableWidget.selectionModel().selectedRows()
        deleteVisuals = []
        for index in reversed(indices):
            df_data = self.ui.tableWidget.item(index.row(), 0).data(Qt.UserRole)
            if not df_data.empty:
                row = df_data.iloc[0].to_dict()

                visuals = self.main_session.query(GroupsCount).filter_by(r_year=int(row['r_year']),
                                                                         site=int(row['site']),
                                                                         r_date=int(row['r_date']),
                                                                         time_start=row['time_start'],
                                                                         species=row['species'],
                                                                         creator=row['creator'],
                                                                         observer=row['observer'],
                                                                         time_s=row['time_s'],
                                                                         time_f=row['time_f'],
                                                                         local_site=row['local_site'],
                                                                         count_type='Visual'
                                                                         ).all()

                deleteVisuals.append((index.row(), visuals))

            else:
                self.ui.tableWidget.model().removeRow(index.row())
        if deleteVisuals:
            ret = QMessageBox.question(self, 'Question',
                                       "Some rows have been deleted from the table, delete them from the database?",
                                       QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

            if ret == QMessageBox.Yes:
                ret_2 = QMessageBox.question(self, 'Question',
                                             "Are you sure? This will affect the associated data!",
                                             QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
                if ret_2 == QMessageBox.Yes:
                    for index, items in deleteVisuals:
                        self.ui.tableWidget.model().removeRow(index)
                        for item in items:
                            self.main_session.delete(item)

    def getResultFromTable(self):
        result = []

        for row in range(self.ui.tableWidget.rowCount()):
            visual = {}

            visual['observer'] = self.ui.tableWidget.cellWidget(row, 2).currentData(Qt.UserRole)
            visual['local_site'] = self.ui.tableWidget.cellWidget(row, 3).currentData(Qt.UserRole)

            visual['start'] = str(self.ui.tableWidget.cellWidget(row, 4).text()).replace(':', '')
            visual['finish'] = str(self.ui.tableWidget.cellWidget(row, 5).text()).replace(':', '')

            col = 6
            total = 0
            visual['animal_category'] = {}
            for i, value in enumerate(self.countAnimalsCategories):
                count = 0
                if self.ui.tableWidget.cellWidget(row, col + i).text().isdigit():
                    count = int(self.ui.tableWidget.cellWidget(row, col + i).text())
                visual['animal_category'][value.animal_category] = count
                if value.count_category and count:
                    total += count

            visual['total'] = total

            result.append(visual)

        return result

    def updateTotal(self):
        row = self.ui.tableWidget.currentRow()
        if row < 0:
            return

        col = 6
        total = 0

        for i, value in enumerate(self.countAnimalsCategories):
            count = 0
            item = self.ui.tableWidget.cellWidget(row, col + i)
            if item.text().isdigit():
                count = int(item.text())

            if value.count_category and count:
                total += count

        self.ui.tableWidget.item(row, len(self.HEADER_LABELS) - 1).setText(str(total))
