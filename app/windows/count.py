import operator
import pickle
import subprocess
from typing import Optional

import pandas as pd

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QPointF
from PyQt5.QtGui import QColor, QKeySequence, QBrush, QConicalGradient
from PyQt5.QtWidgets import QListWidgetItem, QShortcut, QTableWidgetItem, QButtonGroup, QDialog, QToolButton, \
    QMessageBox, QHeaderView, QAbstractItemView, QApplication

from app import m_params
from app.custom_widgets.image_viewer import ImageViewer
from app.dialogs.custom_dialog import DialogSelectCountCategory, DialogSelectLocalSite
from app.models.main_db import PointsCount, CountEffortSites, PatternCount, CountEffortCategories, CountFiles
from app.controllers.items_file import ItemFileCount
from app.controllers.support_lists import AnimalCategoriesList
from app.models.support_db import AnimalCategories, LocalSites
from app.services.helpers import makeDatecreated
from app.controllers.parameters import session_factory_main, user_settings
from app.view.ui_window_count import Ui_MainWindow

HEADER_LABELS = ['Category', 'Local Site']


class CountWindow(QtWidgets.QMainWindow):
    """
    Модуль учета животных на фотографии
    """
    update_done_photo_count = pyqtSignal(ItemFileCount, dict, object)

    def __init__(self, parent, currentDataPhoto: Optional[ItemFileCount]):
        super(CountWindow, self).__init__(parent=parent)

        self.installEventFilter(self)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.showMaximized()

        self.main_session = session_factory_main.get_session()
        self.currentCategory = None
        self.count_points = []
        self.currentImageRow = -1

        effort_categories_points = self.main_session.query(CountEffortCategories).filter_by(
            species=m_params.species,
            r_year=m_params.year,
            site=m_params.site,
            r_date=m_params.current_data.r_date,
            time_start=m_params.current_data.time_start,
            creator=m_params.current_data.creator,
            count_type=currentDataPhoto.countType.type_id, ).all()
        effort_categories_points = list(map(lambda x: x.animal_category, effort_categories_points))

        self.effortCategoriesPoints = AnimalCategoriesList(
            filter(lambda x: x.animal_category in effort_categories_points, m_params.support_categories_points))
        self.effortCategoriesPoints.sort(key=lambda x: x.order)

        self.efforts = self.main_session.query(CountEffortSites).filter_by(
            r_year=m_params.year,
            site=m_params.site,
            r_date=m_params.current_data.r_date,
            time_start=m_params.current_data.time_start,
            species=m_params.species,
            count_type=currentDataPhoto.countType.type_id,
            creator=m_params.current_data.creator).all()

        self.view = ImageViewer()
        self.button_group = QButtonGroup()
        self.cbox_group = QButtonGroup()
        self.btn_category_shortcuts = []
        self.initUi()

        if user_settings.value(f"CategoriesPoints_{m_params.species}"):
            data = bytes(user_settings.value(f"CategoriesPoints_{m_params.species}"))
            self.effortCategoriesPoints = pickle.loads(data)

        if user_settings.contains("SizePoint") and user_settings.value("SizePoint"):
            self.ui.spinBox_sizePoint.setValue(int(user_settings.value("SizePoint")))

        self.load_categories_buttons()

        self.load_images_list()

        if currentDataPhoto:
            self.search_item_photo_and_select(currentDataPhoto.fileName)

    def initUi(self):
        """
        Инициализирует пользовательский интерфейс приложения.
        Этот метод настраивает виджеты и подключает их к соответствующим сигналам и слотам.

        """
        for i, item in enumerate(m_params.support_local_sites):
            self.ui.cmb_local_site.addItem(item.local_site_name)
            self.ui.cmb_local_site.setItemData(i, item.local_site_id, Qt.ToolTipRole)
            self.ui.cmb_local_site.setItemData(i, item, Qt.UserRole)
        self.ui.cmb_local_site.setCurrentIndex(-1)

        self.button_group.setExclusive(True)
        self.button_group.buttonClicked[QtWidgets.QAbstractButton].connect(self.change_category)
        self.cbox_group.setExclusive(False)
        self.cbox_group.buttonClicked[QtWidgets.QAbstractButton].connect(self.btn_category_checkbox_stateChanged)

        self.ui.imageLayout.addWidget(self.view, 0, 0, 1, 1)
        self.view.newPoint.connect(self.new_point)
        self.view.movePoint.connect(self.movePoint)
        self.view.zoomDisplay.connect(self.zoom_display)
        self.view.selectedPoints.connect(self.selectPointsInTable)
        self.view.deletePointsInParent.connect(self.deleteSelectedPointsInTable)

        self.ui.spinBox_sizePoint.valueChanged.connect(self.changeSizePoints)
        self.ui.checkBox_view_text_points.setChecked(True)
        self.ui.checkBox_view_text_points.stateChanged.connect(self.text_points_change)

        self.ui.listWidget_Images.itemActivated.connect(self.select_image)
        self.ui.listWidget_Images.itemSelectionChanged.connect(self.select_image)

        self.ui.tableWidget_Points.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.ui.tableWidget_Points.itemSelectionChanged.connect(self.selectPointsInImageView)
        self.ui.tableWidget_Points.setColumnCount(len(HEADER_LABELS))
        self.ui.tableWidget_Points.setHorizontalHeaderLabels(HEADER_LABELS)
        self.ui.tableWidget_Points.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.tableWidget_Points.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidget_Points.customContextMenuRequested.connect(self.context_menu_table_points)

        self.ui.btn_no_animal.clicked.connect(self.no_animal)

        self.ui.actionCreatPoint.triggered.connect(self.setModeCreatePoint)
        self.ui.actionSelectPoint.triggered.connect(self.setModeSelectPoint)

        self.ui.actionZoomIn.triggered.connect(self.zoom_in)
        self.ui.actionZoomOut.triggered.connect(self.zoom_out)
        self.ui.actionZoom_2x.triggered.connect(self.zoom_2x)
        self.ui.actionZoom_Reset.triggered.connect(self.zoom_reset)

        self.ui.actionImages_List.triggered.connect(self.dockWidget_ImagesList_visible)
        self.ui.dockWidget_ImagesList.setVisible(False)
        self.ui.dockWidget_ImagesList.visibilityChanged.connect(self.check_dockWidget_ImagesList)

        self.ui.scrollArea_tools.setVisible(False)
        self.ui.scrollArea_categories.setVisible(False)
        self.ui.actionTop_Area.triggered.connect(self.top_Area_isvisible)
        self.ui.actionBottom_Area.triggered.connect(self.bottom_Area_isvisible)
        self.ui.actionPointsPanel.triggered.connect(self.dockWidget_PointsTable_visible)

        self.ui.dockWidget_PointsTable.setVisible(False)
        self.ui.dockWidget_PointsTable.visibilityChanged.connect(self.check_dockWidget_PointsTable)

        self.ui.actionview_others_animals.setChecked(True)
        self.ui.actionview_others_animals.triggered.connect(self.view_other_animals)

        self.shortcut_zoom_in1 = QShortcut(QKeySequence("Ctrl+="), self)
        self.shortcut_zoom_in1.activated.connect(self.zoom_in)
        self.shortcut_zoom_in2 = QShortcut(QKeySequence("Ctrl++"), self)
        self.shortcut_zoom_in2.activated.connect(self.zoom_in)

        self.shortcut_zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        self.shortcut_zoom_out.activated.connect(self.zoom_out)

        self.shortcut_zoom_2x1 = QShortcut(QKeySequence("Alt++"), self)
        self.shortcut_zoom_2x1.activated.connect(self.zoom_2x)
        self.shortcut_zoom_2x2 = QShortcut(QKeySequence("Alt+="), self)
        self.shortcut_zoom_2x2.activated.connect(self.zoom_2x)

        self.shortcut_delete_point = QShortcut(QKeySequence("Del"), self)
        self.shortcut_delete_point.activated.connect(self.deleteSelectedPointsInTable)

        self.shortcut_next = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_next.activated.connect(self.next_photo)

        self.shortcut_previous = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_previous.activated.connect(self.previous_photo)

        self.setWindowTitle("Count")

    def context_menu_table_points(self, point):
        menu = QtWidgets.QMenu()

        change_site = QtWidgets.QAction('Change local site', menu)
        change_site.triggered.connect(self.change_local_sites_for_point)
        menu.addAction(change_site)

        change_site = QtWidgets.QAction('Change category', menu)
        change_site.triggered.connect(self.change_category_for_point)
        menu.addAction(change_site)

        delete_point = QtWidgets.QAction('Delete', menu)
        delete_point.triggered.connect(self.deleteSelectedPointsInTable)
        menu.addAction(delete_point)

        menu.exec(self.ui.tableWidget_Points.verticalHeader().mapToGlobal(point))

    def next_photo(self):
        """
        Перемещает текущий выбор в виджете списка к следующему фото.
        """
        self.ui.listWidget_Images.setFocus()
        if self.ui.listWidget_Images.currentRow() == 0:
            return
        elif len(self.ui.listWidget_Images.selectedItems()) == 0:
            self.ui.listWidget_Images.setCurrentRow(0)
        else:
            self.ui.listWidget_Images.setCurrentRow(self.ui.listWidget_Images.currentRow() - 1)

        # self.open_image(self.ui.listWidget_Images.currentItem())
        self.setFocus()

    def previous_photo(self):
        """
        Переходит к предыдущей фотографии в списке.
        """
        self.ui.listWidget_Images.setFocus()
        if len(self.ui.listWidget_Images) <= self.ui.listWidget_Images.currentRow() + 1:
            return
        elif len(self.ui.listWidget_Images.selectedItems()) == 0:
            self.ui.listWidget_Images.setCurrentRow(0)
        else:
            self.ui.listWidget_Images.setCurrentRow(self.ui.listWidget_Images.currentRow() + 1)

        self.setFocus()

    def no_animal(self):
        """
        Проверяет, есть ли какие-либо точки в списке self.count_points.
        Если точки есть, он задает пользователю вопрос с помощью QMessageBox, чтобы подтвердить удаление точек и
        установку метки 'No Animals'. Если пользователь подтверждает, он выбирает все строки в QTableWidget и
        удаляет выбранные точки. Если пользователь отменяет, метод возвращает.
        После этого он создает новый экземпляр AnimalCategories с параметрами:
         - animal_category = 'NoAnimal' - species = m_params.species - color_representation_large = '#031FCB'
         - color_representation_small = '#031FCB' Затем он вызывает метод new_point с параметром QPoint и
         присваивает результат переменной 'res'. В конце концов, он устанавливает self.currentCategory в None и
         возвращает 'res'.

        """
        if any(int(x.r_year) != 0 for x in self.count_points):
            ret = QMessageBox.question(self, 'Question',
                                       "This photo has a points! Delete points and set label 'No Animals'?",
                                       QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

            if ret == QMessageBox.Yes:
                ret = QMessageBox.question(self, 'Question',
                                           "Are you sure?",
                                           QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

                if ret == QMessageBox.Yes:
                    self.ui.tableWidget_Points.setSelectionMode(QAbstractItemView.MultiSelection)
                    for row in range(self.ui.tableWidget_Points.rowCount()):
                        self.ui.tableWidget_Points.selectRow(row)
                    self.deleteSelectedPointsInTable()
                    self.ui.tableWidget_Points.setSelectionMode(QAbstractItemView.ExtendedSelection)
                else:
                    return
            else:
                return

        self.currentCategory = AnimalCategories(animal_category='NoAnimal',
                                                species=m_params.species,
                                                color_representation_large='#031FCB',
                                                color_representation_small='#031FCB',
                                                )
        res = self.new_point(QPoint(-1, -1))
        self.currentCategory = None

        return res

    def no_marked(self):
        """
        Этот метод проверяет, имеют ли какие-либо из точек в списке count_points не нулевое значение r_year.
        Если у какой-либо точки не нулевое значение r_year, отображается QMessageBox, спрашивающий пользователя,
        хочет ли он удалить точки и установить метку 'No Marked'.
        Если пользователь подтверждает, метод выбирает все строки в tableWidget_Points и удаляет выбранные точки.
        Если пользователь отменяет, метод возвращает без внесения каких-либо изменений.
        После проверки точек с ненулевыми значениями r_year, метод создает новый объект AnimalCategories с установленной
        категорией 'NoMarked' и свойствами species, color_representation_large, и color_representation_small
        установленными в соответствии с объектом m_params. Затем метод вызывает метод new_point с объектом QPoint,
        созданным с координатами (-1, -1) и, наконец, сбрасывает свойство currentCategory в None.

        """
        if any(int(x.r_year) != 0 for x in self.count_points):
            ret = QMessageBox.question(self, 'Question',
                                       "This photo has a points! Delete points and set label 'No Marked'?",
                                       QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

            if ret == QMessageBox.Yes:
                ret = QMessageBox.question(self, 'Question',
                                           "Are you sure?",
                                           QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)

                if ret == QMessageBox.Yes:
                    self.ui.tableWidget_Points.setSelectionMode(QAbstractItemView.MultiSelection)
                    for row in range(self.ui.tableWidget_Points.rowCount()):
                        self.ui.tableWidget_Points.selectRow(row)
                    self.deleteSelectedPointsInTable()
                    self.ui.tableWidget_Points.setSelectionMode(QAbstractItemView.ExtendedSelection)
                else:
                    return
            else:
                return

        self.currentCategory = AnimalCategories(animal_category='NoMarked',
                                                species=m_params.species,
                                                color_representation_large='#108405',
                                                color_representation_small='#108405',
                                                )
        res = self.new_point(QPoint(-1, -1))
        self.currentCategory = None
        return res

    def movePoint(self, point):
        """
        Переместит данную точку в новое местоположение.
        """
        loc = point.data(Qt.UserRole)
        loc.iTop = point.pos().y()
        loc.iLeft = point.pos().x()
        self.main_session.commit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.zoom_reset()
        elif e.key() == Qt.Key_F1:
            subprocess.check_call("hh.exe help.chm::/location.htm")

    def load_images_list(self):
        """
        Загрузка списка изображений

        Загружает список изображений в виджет списка пользовательского интерфейса.
        """
        self.ui.listWidget_Images.clear()

        for item in m_params.photos_for_day:
            i = QListWidgetItem('%s' % item.fileName)
            i.setData(Qt.UserRole, item)
            if item.fileName in m_params.done_files:

                isNoAnimals = False
                isNoMarked = False

                if item.fileData.points_count:
                    isNoAnimals = True if item.fileData.points_count[0].animal_category == 'NoAnimal' else False
                    isNoMarked = True if item.fileData.points_count[0].animal_category == 'NoMarked' else False

                if isNoAnimals:
                    i.setForeground(QColor('#031FCB'))
                elif isNoMarked:
                    i.setForeground(QColor('#108405'))
                else:
                    i.setForeground(QColor('#FF0000'))

            self.ui.listWidget_Images.addItem(i)
        self.ui.dockWidget_ImagesList.setWindowTitle(f"Images: {len(self.ui.listWidget_Images)}")

    def selected_image(self):
        """
        Выбирает изображение на основе текущей строки в виджете списка.
        """
        row = self.ui.listWidget_Images.currentRow()
        if row < 0:
            return

        self.currentImageRow = row
        self.open_image(self.ui.listWidget_Images.currentItem())

    def open_image(self, item):
        """
        Этот метод открывает изображение и загружает связанные данные.
        """
        self.count_points.clear()

        itemData = item.data(Qt.UserRole)
        self.view.setPhoto(itemData.path, 1)
        self.count_points = self.load_points(itemData.fileData) + self.load_pattern_points(itemData.fileData)

        self.ui.lcd_zoom.display(str(self.view.get_zoom()))

        self.ui.statusBar.showMessage(f"Images: {len(self.ui.listWidget_Images)}  |  " +
                                      f"Selected {self.ui.listWidget_Images.currentRow() + 1}  |  " +
                                      f"Image Path: {itemData.path}")
        if self.ui.actionview_others_animals.isChecked():
            self.count_points += self.get_view_other_animals(itemData.fileData)

            self.fill_table(self.count_points)

        for point in self.count_points:
            if point.iLeft >= 0 and point.iTop >= 0:
                tooltip = f"{point.animal_category} {point.local_site}"

                animalCategory = self.effortCategoriesPoints.itemFromName(point.animal_category)

                gradient = QConicalGradient()
                start_color = QColor(animalCategory.color_representation_small)
                end_color = QColor(animalCategory.color_representation_large)

                gradient.setColorAt(0.0, start_color)
                gradient.setColorAt(0.25, start_color.lighter())
                gradient.setColorAt(0.5, start_color.darker())
                gradient.setColorAt(0.75, end_color.darker())
                gradient.setColorAt(1.0, end_color)
                gradient.setSpread(QtGui.QGradient.RepeatSpread)

                brush = QBrush(gradient)

                self.view.addPoint(pos=QPoint(point.iLeft, point.iTop), text=animalCategory.animal_category,
                                   data=point, tooltip=tooltip, color=brush)

    def get_view_other_animals(self, data: CountFiles):
        """
        Возвращает список объектов PointsCount, которые не относятся к текущему виду.
        """
        res_points = []
        pointsCount = self.main_session.query(PointsCount).filter_by(r_year=data.r_year,
                                                                     site=data.site,
                                                                     r_date=data.r_date,
                                                                     time_start=data.time_start,
                                                                     file_name=data.file_name,
                                                                     count_type=data.count_type).filter(
            PointsCount.species != m_params.species).all()

        pointsPattern = self.main_session.query(PatternCount).filter_by(r_year=data.r_year,
                                                                        site=data.site,
                                                                        r_date=data.r_date,
                                                                        time_start=data.time_start,
                                                                        file_name=data.file_name,
                                                                        count_type=data.count_type).filter(
            PatternCount.species != m_params.species).all()

        for item in pointsPattern + pointsCount:
            _point = PointsCount(
                r_year=0,
                site=int(item.site),
                r_date=item.r_date,
                time_start=item.time_start,
                observer=item.observer,
                local_site=item.local_site,
                animal_category=item.animal_category,
                iLeft=item.iLeft,
                iTop=item.iTop,
                datecreated=item.datecreated,
                file_name=item.file_name,
                species=item.species,
                creator=item.creator,
                count_type=item.count_type)

            res_points.append(_point)

        return res_points

    def select_image(self):
        """
        Выбирает изображение из списка изображений.

        Метод проверяет, есть ли выбранное изображение в listWidget_Images.
        Если изображение выбрано и currentImageRow допустим, он дополнительно проверяет, нет ли точек или
        у любой точки нет ненулевого r_year. Если эти условия выполнены, он проверяет, является ли выбранное изображение
        таким же, как currentImageRow. Если это так, он блокирует сигналы для listWidget_Images,
        устанавливает текущую строку в currentImageRow, разблокирует сигналы и возвращает.
        Если выбранное изображение не то же самое, что и currentImageRow, он отображает QMessageBox, чтобы спросить,
        есть ли на фото животные. В QMessageBox есть три кнопки: Yes (No Animal), No (No Marked) и Cancel.
        Если пользователь выбирает Yes, он вызывает метод no_animal и проверяет результат.
        Если метод no_animal возвращает False, он устанавливает текущую строку на current ImageRow и возвращается.
        Если пользователь выбирает Cancel, он устанавливает текущую строку в currentImageRow и возвращается.
        Если пользователь выбирает No, он вызывает метод no_marked и проверяет результат.
        Если метод no_marked возвращает False, он устанавливает текущую строку в currentImageRow и возвращает.
        Наконец, если все условия выполнены, он вызывает метод selected_image.
        """
        if self.ui.listWidget_Images.selectedItems():
            if self.currentImageRow >= 0:
                if not self.count_points or not any(int(x.r_year) != 0 for x in self.count_points):
                    if self.ui.listWidget_Images.currentRow() == self.currentImageRow:
                        self.ui.listWidget_Images.blockSignals(True)
                        self.ui.listWidget_Images.setCurrentRow(self.currentImageRow)
                        self.ui.listWidget_Images.blockSignals(False)
                        return

                    msg = QMessageBox()
                    msg.setText("Are there no animals in this photo?")
                    msg.setStandardButtons(
                        QMessageBox.Yes |
                        QMessageBox.No |
                        QMessageBox.Cancel)
                    msg.button(QMessageBox.Yes).setText("No Animal")
                    msg.button(QMessageBox.No).setText("No Marked")
                    msg.button(QMessageBox.Cancel).setText("Cancel")
                    ret = msg.exec_()

                    if ret == QMessageBox.Yes:
                        res = self.no_animal()
                        if not res:
                            self.ui.listWidget_Images.setCurrentRow(self.currentImageRow)
                            return
                    elif ret == QMessageBox.Cancel:
                        self.ui.listWidget_Images.setCurrentRow(self.currentImageRow)
                        return
                    elif ret == QMessageBox.No:
                        res = self.no_marked()
                        if not res:
                            self.ui.listWidget_Images.setCurrentRow(self.currentImageRow)
                            return

            self.selected_image()

    def load_points(self, data: CountFiles):
        """

        Загрузить точки из базы данных.

        """
        points = self.main_session.query(PointsCount).filter_by(
            r_year=data.r_year,
            site=data.site,
            r_date=data.r_date,
            time_start=data.time_start,
            file_name=data.file_name,
            species=data.species,
            creator=data.creator,
            count_type=data.count_type).all()

        return points

    def load_pattern_points(self, data: CountFiles):
        """

        Загрузить точки из таблицы PatternCount базы данных.

        """
        points = self.main_session.query(PatternCount).filter_by(r_year=data.r_year,
                                                                 site=data.site,
                                                                 r_date=data.r_date,
                                                                 time_start=data.time_start,
                                                                 file_name=data.file_name,
                                                                 species=data.species,
                                                                 creator=data.creator,
                                                                 count_type=data.count_type).all()
        return points

    def changeSizePoints(self):
        """Задать размер точки"""
        self.view.setSizePoint(self.ui.spinBox_sizePoint.value())
        user_settings.setValue("SizePoint", self.ui.spinBox_sizePoint.value())

    def check_local_site(self, local_site: LocalSites, data: CountFiles):
        """

        Проверить, присутствует ли локальный сайт в данных об усилиях.

        """
        df_effort = pd.DataFrame([item.as_dict() for item in self.efforts])
        if df_effort.empty:
            return None
        local_sites_effort = df_effort['local_site'].tolist()
        if local_site.local_site_id in local_sites_effort:
            return local_site
        else:
            ret = QMessageBox.question(self, 'Question',
                                       f'The selected local site is not in Effort for {data.count_type}! Fill out '
                                       'Effort?', QMessageBox.Yes | QMessageBox.Cancel,
                                       QMessageBox.Cancel)
            if ret == QMessageBox.Yes:
                self.parent().edit_count_info()
                self.efforts = self.main_session.query(CountEffortSites).filter_by(r_year=m_params.year,
                                                                                   site=m_params.site,
                                                                                   r_date=m_params.current_data.r_date,
                                                                                   time_start=m_params.current_data.time_start,
                                                                                   species=m_params.species,
                                                                                   count_type=data.count_type,
                                                                                   creator=m_params.current_data.creator).all()

                return local_site
            else:
                return None

    def new_point(self, coords):
        """

        Этот метод используется для добавления новой точки. Он выполняет следующие шаги:
        1. Если нажата клавиша Alt, открывается диалог выбора категории животного.
        - Если выбрана и принята категория, обновляется атрибут currentCategory.
        - Соответствующая кнопка категории отмечается.
        2. Если currentCategory не установлен, метод возвращает False.
        3. Получаются данные элемента для текущего файла в listWidget_Images.
        4. Если в списке count_points есть только одна точка и она принадлежит категории 'nomarked' или 'noanimal',
        и вид совпадает с m_params.species, то точка удаляется из main_session и списка count_points очищается.
        5. Если в списке count_points нет точек или текущий локальный участок не выбран, открывается диалог выбора локального участка.
        - Если диалог отклонен, метод возвращает False.
        - В противном случае локальный участок находится в комбо-боксе cmb_local_site и устанавливается как текущий.
        6. Проверяется локальный участок.
        - Если локальный сайт не найден, метод возвращает False.
        7. Если точка с теми же координатами уже существует в списке count_points, метод возвращает False.
        8. Если категория животного currentCategory не 'inj', создается объект PointsCount.
        - В противном случае создается объект PatternCount.
        9. Объект точки добавляется в main_session и фиксируется.
        10. Если fileName из itemData отсутствует в списке m_params.done_files, он добавляется.
        11. Устанавливается цвет переднего плана элемента файла на основе currentCategory.
        12. Точка добавляется в список count_points.
        13. Излучается сигнал update_done_photo_count с itemData и словарем, содержащим категорию животного в качестве ключа и 1 в качестве значения.
        14. Если координаты точки больше или равны 0, создается всплывающая подсказка с категорией животного и локальным сайтом.
        - Вызывается метод addPoint представления с координатами точки, категорией животного в качестве текста, точкой в качестве данных, подсказкой и кистью в качестве цвета.
        15. tableWidget_Points обновляется информацией о новой точке.
        - Создается QTableWidgetItem для категории животного и локального сайта.
        16. Выбирается последняя строка tableWidget_Points.
        17. Метод возвращает True при успешном выполнении.

        """
        if QApplication.keyboardModifiers() & Qt.AltModifier:
            cat_dialog = DialogSelectCountCategory(m_params.species)
            cat_dialog.show()
            if cat_dialog.exec() == QDialog.Accepted:
                if cat_dialog.result:
                    self.currentCategory = cat_dialog.result

                    buttons = self.button_group.buttons()
                    btn_category = next(b for b in buttons if b.objectName() == cat_dialog.result.animal_category)
                    btn_category.setChecked(True)

        if not self.currentCategory:
            return

        file_item = self.ui.listWidget_Images.item(self.currentImageRow)
        itemData = file_item.data(Qt.UserRole)

        if len(self.count_points) == 1:
            point_to_delete = self.count_points[0]
            categories = ['nomarked', 'noanimal']
            if (str(point_to_delete.animal_category).lower() in categories
                    and point_to_delete.species == m_params.species):

                if self.main_session.is_modified(point_to_delete):
                    self.main_session.delete(point_to_delete)
                    self.main_session.commit()
                self.count_points.clear()

        if not self.count_points or self.ui.cmb_local_site.currentIndex() < 0:
            dialogSelectLocalSite = DialogSelectLocalSite()
            dialogSelectLocalSite.show()
            if dialogSelectLocalSite.exec() == QDialog.Rejected:
                return
            else:
                index = self.ui.cmb_local_site.findData(dialogSelectLocalSite.localSite, Qt.UserRole)
                if index >= 0:
                    self.ui.cmb_local_site.setCurrentIndex(index)
        local_site = self.check_local_site(self.ui.cmb_local_site.currentData(Qt.UserRole), itemData.fileData)

        if not local_site:
            return

        if any((item.iLeft, item.iTop) == (coords.x(), coords.y()) for item in self.count_points):
            return

        if self.currentCategory.animal_category.lower() != 'inj':
            point = PointsCount(
                r_year=m_params.current_data.r_year,
                site=m_params.current_data.site,
                r_date=m_params.current_data.r_date,
                time_start=m_params.current_data.time_start,
                observer=m_params.creator,
                local_site=local_site.local_site_id,
                animal_category=self.currentCategory.animal_category,
                iLeft=coords.x(),
                iTop=coords.y(),
                datecreated=makeDatecreated(),
                file_name=itemData.fileName,
                species=m_params.current_data.species,
                creator=m_params.current_data.creator,
                count_type=itemData.fileData.count_type)
        else:
            point = PatternCount(
                r_year=m_params.current_data.r_year,
                site=m_params.current_data.site,
                r_date=m_params.current_data.r_date,
                time_start=m_params.current_data.time_start,
                observer=m_params.creator,
                local_site=local_site.local_site_id,
                animal_category=self.currentCategory.animal_category,
                iLeft=coords.x(),
                iTop=coords.y(),
                datecreated=makeDatecreated(),
                file_name=itemData.fileName,
                species=m_params.current_data.species,
                creator=m_params.current_data.creator,
                count_type=itemData.fileData.count_type)

        self.main_session.add(point)
        self.main_session.commit()

        if itemData.fileName not in m_params.done_files:
            m_params.done_files.append(itemData.fileName)

        if self.currentCategory.animal_category.lower() in ['nomarked', 'noanimal']:
            file_item.setForeground(QColor(self.currentCategory.color_representation_large))
        else:
            file_item.setForeground(QColor('#FF0000'))

        self.count_points.append(point)
        self.update_done_photo_count.emit(itemData, {point.animal_category: 1}, operator.add)

        if point.iLeft >= 0 and point.iTop >= 0:
            tooltip = f"{point.animal_category} {point.local_site}"

            gradient = QConicalGradient()
            start_color = QColor(self.currentCategory.color_representation_small)
            end_color = QColor(self.currentCategory.color_representation_large)

            gradient.setColorAt(0.0, start_color)
            gradient.setColorAt(0.25, start_color.lighter())
            gradient.setColorAt(0.5, start_color.darker())
            gradient.setColorAt(0.75, end_color.darker())
            gradient.setColorAt(1.0, end_color)
            gradient.setSpread(QtGui.QGradient.RepeatSpread)

            brush = QBrush(gradient)
            self.view.addPoint(pos=QPointF(point.iLeft, point.iTop),
                               text=point.animal_category,
                               data=point, tooltip=tooltip, color=brush)

        self.ui.tableWidget_Points.setRowCount(len(self.count_points))
        cell_category = QTableWidgetItem("{0}".format(self.currentCategory.animal_category))
        cell_category.setData(Qt.UserRole, point)
        cell_loc_site = QTableWidgetItem("{0}".format(local_site.local_site_id))

        self.ui.tableWidget_Points.setItem(len(self.count_points) - 1, 0, cell_category)
        self.ui.tableWidget_Points.setItem(len(self.count_points) - 1, 1, cell_loc_site)
        self.ui.tableWidget_Points.selectRow(len(self.count_points) - 1)

        return True

    def text_points_change(self, value):
        """

        Переключает видимость текста точки

        """
        self.view.textPointsVisible(value)

    def selectPointsInTable(self, points):
        """
        Выбирает указанные точки в таблице.
        """
        if not points:
            self.ui.tableWidget_Points.clearSelection()
        for point in points:
            data = point.data(Qt.UserRole)
            for i in range(self.ui.tableWidget_Points.rowCount()):
                if data == self.ui.tableWidget_Points.item(i, 0).data(Qt.UserRole):
                    self.ui.tableWidget_Points.selectRow(i)

    def selectPointsInImageView(self):
        """

            Выбирает точки на изображении на основе выбранных строк в виджете таблицы.

        """
        data_rows = []

        selected = self.ui.tableWidget_Points.selectionModel().selectedRows()
        rows = [ix.row() for ix in selected]
        for row in rows:
            data_loc = self.ui.tableWidget_Points.item(row, 0).data(Qt.UserRole)
            data_rows.append(data_loc)

        self.view.selectPoints(data_rows)

    def deleteSelectedPointsInTable(self):
        """

        Удалить выбранные точки в таблице.

        Этот метод удаляет выбранные точки в таблице.
        Он извлекает выбранные строки из виджета таблицы, получает данные для каждой выбранной строки, проверяет,
        соответствует ли вид указанному параметру, добавляет данные в список, удаляет данные из сессии,
        удаляет точки из представления и фиксирует изменения в сессии.
        """
        data_rows = []

        selected = self.ui.tableWidget_Points.selectionModel().selectedRows()
        rows = [ix.row() for ix in selected]

        for row in rows:
            data = self.ui.tableWidget_Points.item(row, 0).data(Qt.UserRole)

            if data.species == m_params.species:
                data_rows.append(data)
                self.main_session.delete(data)
                self.count_points.remove(data)

        data_dict = {r: True for r in data_rows}
        removePoints = [x for x in self.view.points if x.data(Qt.UserRole) in data_dict]

        self.view.removePoints(removePoints)
        self.main_session.commit()

        item_photo = self.ui.listWidget_Images.item(self.currentImageRow)
        itemData = item_photo.data(Qt.UserRole)

        if not any(x for x in self.count_points if x.r_year > 0):
            item_photo.setForeground(QColor('#000000'))
            if itemData.fileName in m_params.done_files:
                m_params.done_files.remove(itemData.fileName)

        categories = {}
        for item in data_rows:
            if item.animal_category in categories:
                categories[item.animal_category] += 1
            else:
                categories[item.animal_category] = 1

        self.update_done_photo_count.emit(itemData, categories, operator.sub)

        self.fill_table(self.count_points)

    def fill_table(self, points):
        """

        Заполнить таблицу.

        Заполняет виджет таблицы данными из заданного списка точек.
        """
        self.ui.tableWidget_Points.clear()
        self.ui.tableWidget_Points.setRowCount(len(points))

        for row, point in enumerate(points):
            cell_category = QTableWidgetItem(f"{str(point.animal_category)}")
            cell_category.setData(Qt.UserRole, point)
            cell_loc_site = QTableWidgetItem(f"{str(point.local_site)}")

            if point.r_year == 0:
                cell_category.setBackground(QBrush(QColor(Qt.gray)))
                cell_loc_site.setBackground(QBrush(QColor(Qt.gray)))

            self.ui.tableWidget_Points.setItem(row, 0, cell_category)
            self.ui.tableWidget_Points.setItem(row, 1, cell_loc_site)

    def change_local_sites_for_point(self):
        """
        Изменить локальный участок для выбранной точки.
        """
        if not self.ui.tableWidget_Points.selectedItems():
            return
        data = self.ui.tableWidget_Points.selectedItems()[0].data(Qt.UserRole)
        if not data or data.species != m_params.species:
            QMessageBox.information(self, 'Information', 'The change is not possible! ')
            return

        dialog_selected_loc_site = DialogSelectLocalSite()
        dialog_selected_loc_site.show()
        if dialog_selected_loc_site.exec() == QDialog.Rejected:
            return
        else:

            local_site = self.check_local_site(dialog_selected_loc_site.localSite, data)
            if local_site:

                for index in self.ui.tableWidget_Points.selectedIndexes():
                    item = self.ui.tableWidget_Points.itemFromIndex(index)
                    row = self.ui.tableWidget_Points.row(item)
                    item_data = self.ui.tableWidget_Points.item(row, 0).data(Qt.UserRole)
                    if item_data:
                        item_point = self.view.points.itemFromData(item_data)
                        point_data = item_point.data(Qt.UserRole)

                        item_data.local_site = dialog_selected_loc_site.localSite.local_site_id
                        item_point.setToolTip(f'{point_data.animal_category} {item_data.local_site}')

                        self.ui.tableWidget_Points.item(row, 1).setText(
                            dialog_selected_loc_site.localSite.local_site_id)

                self.main_session.commit()

    def change_category_for_point(self):
        """

        Изменить категорию для выбранной точки в таблице.

        """
        if not self.ui.tableWidget_Points.selectedItems():
            return

        data = self.ui.tableWidget_Points.selectedItems()[0].data(Qt.UserRole)
        if not data or data.species != m_params.species:
            QMessageBox.information(self, 'Information', 'The change is not possible! ')
            return

        file_item = self.ui.listWidget_Images.item(self.currentImageRow)
        fileData = file_item.data(Qt.UserRole)

        cat_dialog = DialogSelectCountCategory(m_params.species)
        cat_dialog.show()
        if cat_dialog.exec() == QDialog.Accepted:
            if cat_dialog.result:
                for index in self.ui.tableWidget_Points.selectedIndexes():
                    item = self.ui.tableWidget_Points.itemFromIndex(index)
                    row = self.ui.tableWidget_Points.row(item)
                    item_data = self.ui.tableWidget_Points.item(row, 0).data(Qt.UserRole)
                    if item_data:
                        item_point = self.view.points.itemFromData(item_data)
                        point_data = item_point.data(Qt.UserRole)
                        self.update_done_photo_count.emit(fileData, {item_data.animal_category: 1}, operator.sub)
                        item_data.animal_category = cat_dialog.result.animal_category
                        self.update_done_photo_count.emit(fileData, {item_data.animal_category: 1}, operator.add)

                        self.ui.tableWidget_Points.item(row, 0).setText(cat_dialog.result.animal_category)

                        animalCategory = self.effortCategoriesPoints.itemFromName(item_data.animal_category)

                        gradient = QConicalGradient()
                        start_color = QColor(animalCategory.color_representation_small)
                        end_color = QColor(animalCategory.color_representation_large)

                        gradient.setColorAt(0.0, start_color)
                        gradient.setColorAt(0.25, start_color.lighter())
                        gradient.setColorAt(0.5, start_color.darker())
                        gradient.setColorAt(0.75, end_color.darker())
                        gradient.setColorAt(1.0, end_color)
                        gradient.setSpread(QtGui.QGradient.RepeatSpread)

                        brush = QBrush(gradient)

                        item_point.setToolTip(f'{item_data.animal_category} {point_data.local_site}')
                        item_point.color = brush
                        item_point.text = item_data.animal_category

                self.main_session.commit()

    def search_item_photo_and_select(self, file_name):
        """
        Ищет элемент с определенным именем файла в listWidget_Images и выбирает его.

        """
        items = self.ui.listWidget_Images.findItems(file_name, Qt.MatchFixedString | Qt.MatchRecursive)
        if items:
            item = items[0]
            row = self.ui.listWidget_Images.row(item)
            self.ui.listWidget_Images.setCurrentRow(row)

    def load_categories_buttons(self):
        """
        Загрузить кнопки категорий.

        Этот метод генерирует и загружает кнопки категорий на пользовательский интерфейс.
        Он создает QHBoxLayout для размещения кнопок и итерирует по списку effortCategoriesPoints для генерации
        кнопок для каждого элемента.
        """
        horizontalLayout = QtWidgets.QHBoxLayout()

        for i, item in enumerate(self.effortCategoriesPoints):

            verticalLayout = QtWidgets.QVBoxLayout()
            widget_btn = QtWidgets.QWidget()
            if i + 1 <= 9:
                hotkey = str(i + 1)
            else:
                if i + 1 <= 18:
                    hotkey = 'Ctrl+' + str((i + 1) - 9)
                else:
                    hotkey = 'Alt+' + str((i + 1) - 18)

            btn_category = CategoryButton(item.animal_category, item, hotkey)
            btn_category.setAutoExclusive(True)
            btn_category.setCheckable(True)
            btn_category.setFixedWidth(50)
            btn_category.setFixedHeight(50)

            btn_category.change_color_point.connect(self.change_color_points)

            shortcut_btn_category = QShortcut(QKeySequence(hotkey), self)
            shortcut_btn_category.activated.connect(btn_category.click)

            checkbox = CategoryCheckBox(item)

            self.btn_category_shortcuts.append(shortcut_btn_category)

            self.cbox_group.addButton(checkbox)
            self.button_group.addButton(btn_category)

            verticalLayout.addWidget(btn_category)
            verticalLayout.addWidget(checkbox)
            widget_btn.setLayout(verticalLayout)

            horizontalLayout.addWidget(widget_btn)

        horizontalLayout.setAlignment(Qt.AlignLeft)
        self.ui.scrollAreaWidgetContents.setLayout(horizontalLayout)

    def view_other_animals(self):
        """
        Отобразить животных другого вида, если есть учеты для них на данной фотографии.

        """
        if self.ui.listWidget_Images.selectedItems():
            self.selected_image()

    @QtCore.pyqtSlot(QtWidgets.QAbstractButton)
    def change_category(self, btn):
        """
        Обработчик сигнала.
        Изменить текущую категорию на категорию, назначенную кнопке.
        """
        self.currentCategory = btn.data

    @QtCore.pyqtSlot(QtWidgets.QAbstractButton)
    def btn_category_checkbox_stateChanged(self, item):
        """
        Обработать событие изменения состояния видимости категории.

        """
        value = True
        if item.checkState():
            value = False
        data = item.data
        self.view.visiblePoint(text=data.animal_category, value=value)

    def change_color_points(self, value):
        """
        Изменить цветовое представление точек, принадлежащих к определенному виду и категории животных.
        """
        new_categories = AnimalCategoriesList()
        for item in self.effortCategoriesPoints:
            if item.species == value.species and item.animal_category == value.animal_category:
                item.color_representation_large = value.color_representation_large
                item.color_representation_small = value.color_representation_small
                new_categories.append(item)
            else:
                new_categories.append(item)

        self.currentCategory = value
        self.effortCategoriesPoints = new_categories

        gradient = QConicalGradient()
        start_color = QColor(self.currentCategory.color_representation_small)
        end_color = QColor(self.currentCategory.color_representation_large)

        gradient.setColorAt(0.0, start_color)
        gradient.setColorAt(0.25, start_color.lighter())
        gradient.setColorAt(0.5, start_color.darker())
        gradient.setColorAt(0.75, end_color.darker())
        gradient.setColorAt(1.0, end_color)
        gradient.setSpread(QtGui.QGradient.RepeatSpread)

        brush = QBrush(gradient)

        self.view.changeColorPoint(text=value.animal_category, color=brush)
        data = pickle.dumps(new_categories)
        user_settings.setValue(f'CategoriesPoints_{m_params.species}', data)

    """Показать / скрыть панель"""

    def top_Area_isvisible(self):
        """
        Устанавливает видимость для верхней панели на основе состояния действия 'Top_Area'.
        """
        self.ui.scrollArea_tools.setVisible(self.ui.actionTop_Area.isChecked())

    def bottom_Area_isvisible(self):
        """
        Проверить видимость нижней панели с кнопками категорий в пользовательском интерфейсе.
        """
        self.ui.scrollArea_categories.setVisible(self.ui.actionBottom_Area.isChecked())

    # Показать / скрыть панель Images List
    def dockWidget_ImagesList_visible(self):
        """
            Переключить видимость виджета док-панели со списком фотографий.

            Этот метод проверяет, видим ли в данный момент виджет док-панель.
            Если он видимый, то видимость устанавливается в False, делая виджет док-панели скрытым.
            Если он не видим, то видимость устанавливается в True, делая виджет док-панели видимым.
            """
        if self.ui.dockWidget_ImagesList.isVisible():
            self.ui.dockWidget_ImagesList.setVisible(False)
        else:
            self.ui.dockWidget_ImagesList.setVisible(True)

    def check_dockWidget_ImagesList(self):
        """
        Проверяет, видим ли виджет док-панели списка фотографий или нет.

        Если виджет док-панели видим, то 'actionImages_List' отмечен. В противном случае, он снимается.
        """
        if self.ui.dockWidget_ImagesList.isVisible():
            self.ui.actionImages_List.setChecked(True)
        else:
            self.ui.actionImages_List.setChecked(False)

    # Показать / скрыть панель PointsTable
    def dockWidget_PointsTable_visible(self):
        """
        Переключить видимость док-панели виджета PointsTable.

       Этот метод используется для переключения видимости док-панели виджета PointsTable.
       Если виджет док-панели в данный момент видим, его устанавливают как невидимый, и наоборот.
        """
        if self.ui.dockWidget_PointsTable.isVisible():
            self.ui.dockWidget_PointsTable.setVisible(False)
        else:
            self.ui.dockWidget_PointsTable.setVisible(True)

    def check_dockWidget_PointsTable(self):
        """
        Проверяет, видим ли виджет док-панели таблицы точек или нет.

        Если виджет док-панели видим, то 'actionPointsPanel' отмечен. В противном случае, он снимается.
        """
        if self.ui.dockWidget_PointsTable.isVisible():
            self.ui.actionPointsPanel.setChecked(True)
        else:
            self.ui.actionPointsPanel.setChecked(False)

    """zoom"""

    def zoom_display(self, zoom):
        """
        Установить значение масштабирования на дисплее.

        """
        self.ui.lcd_zoom.display(str(zoom))

    def zoom_out(self):
        """
        Уменьшает масштаб изображения, уменьшая коэффициент масштабирования.
        """
        factor = 0.8
        self.view.scale(factor, factor)
        self.view.zoom -= 1
        self.zoom_display(self.view.get_zoom())

    def zoom_in(self):
        """
        Увеличивает масштаб изображения, увеличивая коэффициент масштабирования.
        """
        factor = 1.2
        self.view.scale(factor, factor)
        self.view.zoom += 1
        self.zoom_display(self.view.get_zoom())

    def zoom_reset(self):
        """
        Сбрасывает уровень масштабирования и обновляет дисплей.
        """
        self.view.fitInView()
        self.view.zoom = 0
        self.zoom_display(self.view.get_zoom())

    def zoom_2x(self):
        """
        Увеличивает масштаб представления на фактор 2 и обновляет дисплей масштабирования.
        """
        factor = 2
        self.view.scale(factor, factor)
        self.view.zoom = 20
        self.zoom_display(self.view.get_zoom())

    """set mode"""

    def setModeCreatePoint(self):
        """
        Устанавливает режим создания точек.

        Этот метод устанавливает режим создания точек на изображении.
        Он обновляет флаг 'isModeCreatePoints' в представлении изображения на True.
        Он также снимает галочку с чекбокса 'actionSelectPoint' в пользовательском интерфейсе.
        Очищает выбор в таблице 'tableWidget_Points'.
        """
        self.view.isModeCreatePoints = True
        self.ui.actionSelectPoint.setChecked(False)
        self.ui.tableWidget_Points.clearSelection()

    def setModeSelectPoint(self):
        """
            Устанавливает режим выбора точек.

            Этот метод устанавливает флаг `isModeCreatePoints` в объекте `view` в `False`, что указывает на то,
            что пользователь находится в режиме выбора. Он также снимает галочку с опции `actionCreatPoint` в
         пользовательском интерфейсе.
            """
        self.view.isModeCreatePoints = False
        self.ui.actionCreatPoint.setChecked(False)

    def closeEvent(self, event):
        """
        Закрывает событие и обрабатывает событие закрытия для окна.

        Этот метод проверяет, отмечены ли на фотографии какие-либо точки.
        Если их нет, то он отображает сообщение, чтобы подтвердить, что на фотографии нет животных.
        - Если пользователь нажимает 'Нет животных', он вызывает метод 'no_animal()' и
        проверяет его возвращаемое значение.
        Если возвращается False, событие игнорируется и метод возвращает.
        - Если пользователь нажимает 'Отмена', событие игнорируется и метод возвращает.
        - Если пользователь нажимает 'Нет отмеченных', он вызывает метод 'no_marked()' и
        проверяет его возвращаемое значение.
        Если возвращается False, событие игнорируется и метод возвращает.
        - Наконец, он удаляет окно из списка активных окон.
        """
        if not self.count_points or not any(int(x.r_year) != 0 for x in self.count_points):
            msg = QMessageBox()
            msg.setText("Are there no animals in this photo?")
            msg.setStandardButtons(
                QMessageBox.Yes |
                QMessageBox.No |
                QMessageBox.Cancel)
            msg.button(QMessageBox.Yes).setText("No Animal")
            msg.button(QMessageBox.No).setText("No Marked")
            msg.button(QMessageBox.Cancel).setText("Cancel")
            ret = msg.exec_()

            if ret == QMessageBox.Yes:
                res = self.no_animal()
                if not res:
                    event.ignore()
                    return
            elif ret == QMessageBox.Cancel:
                event.ignore()
                return
            elif ret == QMessageBox.No:
                res = self.no_marked()
                if not res:
                    event.ignore()
                    return

            m_params.windows_list.remove(self)


class CategoryButton(QToolButton):
    """
    Модель кнопки категории животного
    """
    change_color_point = QtCore.pyqtSignal(object)

    def __init__(self, text, data, hotkey, parent=None):
        QToolButton.__init__(self, parent)

        self.data = data
        self.setObjectName(text)
        bt_text = "{0}\n{1}".format(text, hotkey)
        self.setText(bt_text)
        style_text = 'QToolButton {color:' + data.color_representation_large + '; font: bold;}'
        self.setStyleSheet(style_text)
        self.setToolTip(hotkey)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

    def context_menu(self, point):
        menu = QtWidgets.QMenu()
        color = QtWidgets.QAction('Set color', menu)
        color.triggered.connect(self.change_color)
        menu.addAction(color)
        menu.exec(self.mapToGlobal(point))

    def change_color(self):
        """
        Изменить цвет текущей кнопки.

        Этот метод открывает диалог выбора цвета и позволяет пользователю выбрать два цвета.
        Первый выбранный цвет обновит большое представление цвета, второй цвет обновит малое представление цвета.
        """
        self.open_colors_dialog = ColorsDialog(self.data)
        self.open_colors_dialog.show()

        if self.open_colors_dialog.exec() == 0:
            if self.open_colors_dialog.DialogCode:
                color_1 = self.open_colors_dialog.line_edit_c1.text()
                color_2 = self.open_colors_dialog.line_edit_c2.text()
                if not color_1 or not color_2:
                    return

                self.data.color_representation_large = color_1
                self.data.color_representation_small = color_2
                style_text = 'QToolButton {color:' + color_1 + '; font: bold;}'
                self.setStyleSheet(style_text)
                self.change_color_point.emit(self.data)

    def reset_color(self):
        style_text = 'QToolButton {color:' + self.data.color_representation_large + '; font: bold;}'
        self.setStyleSheet(style_text)


class CategoryCheckBox(QtWidgets.QCheckBox):
    """
    Пользовательский виджет QCheckBox, который предоставляет дополнительную функциональность
    для отображения скрытия точки.
    """
    def __init__(self, data, parent=None):
        QtWidgets.QCheckBox.__init__(self, parent)
        self.data = data
        self.stateChanged.connect(self.state_changed)
        self.state_changed()

    def state_changed(self):
        if self.checkState():
            style_text = 'QCheckBox {text-decoration: line-through;}'
            self.setStyleSheet(style_text)

            self.setText('visible')
        else:
            style_text = 'QCheckBox {}'
            self.setStyleSheet(style_text)
            self.setText('visible')


class ColorsDialog(QtWidgets.QDialog):
    def __init__(self, data):
        super().__init__()
        self.setFixedWidth(300)
        self.setFixedHeight(120)

        self._flag = False

        self.v_layout = QtWidgets.QVBoxLayout()
        self.v_layout.setAlignment(QtCore.Qt.AlignTop)
        self.label = QtWidgets.QLabel("Select colors")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.v_layout.addWidget(self.label)

        self.h1_layout = QtWidgets.QHBoxLayout()
        self.h1_layout.setAlignment(QtCore.Qt.AlignRight)
        self.label_c1 = QtWidgets.QLabel("Select color 1:")
        self.line_edit_c1 = QtWidgets.QLineEdit()
        self.btn1_select = QtWidgets.QPushButton("Select")
        self.line_edit_c1.setEnabled(False)
        self.h1_layout.addWidget(self.label_c1)
        self.h1_layout.addWidget(self.line_edit_c1)
        self.h1_layout.addWidget(self.btn1_select)

        self.h2_layout = QtWidgets.QHBoxLayout()
        self.h2_layout.setAlignment(QtCore.Qt.AlignRight)
        self.label_c2 = QtWidgets.QLabel("Select color 2:")
        self.line_edit_c2 = QtWidgets.QLineEdit()
        self.line_edit_c2.setEnabled(False)
        self.btn2_select = QtWidgets.QPushButton("Select")
        self.h2_layout.addWidget(self.label_c2)
        self.h2_layout.addWidget(self.line_edit_c2)
        self.h2_layout.addWidget(self.btn2_select)

        self.h3_layout = QtWidgets.QHBoxLayout()
        self.h3_layout.setAlignment(QtCore.Qt.AlignRight)
        self.btn_selected_colors = QtWidgets.QPushButton("OK")
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.h3_layout.addWidget(self.btn_selected_colors)
        self.h3_layout.addWidget(self.btn_cancel)

        self.v_layout.addLayout(self.h1_layout)
        self.v_layout.addLayout(self.h2_layout)
        self.v_layout.addLayout(self.h3_layout)

        self.setLayout(self.v_layout)

        self.btn1_select.clicked.connect(self.b1_select)
        self.btn2_select.clicked.connect(self.b2_select)
        self.btn_selected_colors.clicked.connect(self.ok)
        self.btn_cancel.clicked.connect(self.close)

        self.line_edit_c1.setText(data.color_representation_large)
        self.line_edit_c2.setText(data.color_representation_small)
        self.line_edit_c1.setStyleSheet('QLineEdit {color:' + data.color_representation_large + '; font: bold;}')
        self.line_edit_c2.setStyleSheet('QLineEdit {color:' + data.color_representation_small + '; font: bold;}')

    def ok(self):
        self._flag = True
        self.close()

    def closeEvent(self, event):
        if self._flag:
            self.DialogCode(1)
        else:
            self.DialogCode(0)

    def b1_select(self):
        self.color_1 = QtWidgets.QColorDialog()
        self.color_1.show()
        self.color_1.colorSelected.connect(self.selected_c1)

    def selected_c1(self):
        self.line_edit_c1.setText(self.color_1.currentColor().name())
        self.line_edit_c1.setStyleSheet('QLineEdit {color:' + self.color_1.currentColor().name() + '; font: bold;}')

    def b2_select(self):
        self.color_2 = QtWidgets.QColorDialog()
        self.color_2.show()
        self.color_2.colorSelected.connect(self.selected_c2)

    def selected_c2(self):
        self.line_edit_c2.setText(self.color_2.currentColor().name())
        self.line_edit_c2.setStyleSheet('QLineEdit {color:' + self.color_2.currentColor().name() + '; font: bold;}')
