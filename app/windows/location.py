import subprocess
from typing import Optional

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import QListWidgetItem, QTableWidgetItem, QShortcut

from app import m_params
from app.custom_widgets.image_viewer import ImageViewer
from app.controllers.items_file import ItemFile
from app.models.model_registration_animal import ModelRegistrationAnimal

from app.controllers.parameters import session_factory_main, user_settings
from app.view.ui_window_location import Ui_LocationWindow

from app.windows.animal_registration import AnimalRegistration
from app.models.main_db import Location, SurveyEffort, Resight, Daily

HEADER_LABELS_POINTS = ('NAME', 'STATUS', 'LOCAL SITE')
HEADER_LABELS_SEEN = ('NO SEEN', 'SEEN')


class LocationWindow(QtWidgets.QMainWindow):
    """
    Модуль регистрации животных на фотографии
    """
    update_done_location = pyqtSignal(str)
    insert_local_sites = pyqtSignal(tuple)

    def __init__(self, parent, currentDataPhoto: ItemFile):
        super(LocationWindow, self).__init__(parent=parent)

        self.keyPressEvent = self.onCtrlPress
        self.keyReleaseEvent = self.onCtrlRelease

        self.main_session = session_factory_main.get_session()

        self.location_points: list[Location] = []
        self.new_coords: QtCore.QPoint() = QtCore.QPoint()

        self.animal_registration: Optional[AnimalRegistration] = None
        self.ui = Ui_LocationWindow()
        self.view = ImageViewer()

        self.initUI()

        self.load_images_list()

        if user_settings.contains("SizePoint") and user_settings.value("SizePoint"):
            self.ui.spinBox_sizePoint.setValue(int(user_settings.value("SizePoint")))

        if currentDataPhoto:
            self.search_item_photo_and_select(currentDataPhoto.fileName)
            self.ui.groupBox_image.setTitle(currentDataPhoto.fileName)

    def initUI(self):
        """
        Инициализирует пользовательский интерфейс.
        """
        self.ui.setupUi(self)
        self.installEventFilter(self)
        self.showMaximized()
        self.setWindowTitle("Location Window")

        self.ui.imageLayout.addWidget(self.view, 0, 0, 1, 1)
        self.view.zoomDisplay.connect(self.zoom_display)
        self.view.selectedPoints.connect(self.selectPointsInTable)
        self.view.newPoint.connect(self.new_point)
        self.view.deletePointsInParent.connect(self.deleteSelectedPointsInTable)
        self.view.movePoint.connect(self.movePoint)

        self.ui.spinBox_sizePoint.valueChanged.connect(self.changeSizePoints)
        self.ui.tableWidget_Points.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.ui.tableWidget_Points.itemSelectionChanged.connect(self.selectPointsInImageView)

        self.ui.tableWidget_SeenNoSeen.setColumnCount(len(HEADER_LABELS_SEEN))
        self.ui.tableWidget_SeenNoSeen.setHorizontalHeaderLabels(HEADER_LABELS_SEEN)

        self.ui.tableWidget_Points.setColumnCount(len(HEADER_LABELS_POINTS))
        self.ui.tableWidget_Points.setHorizontalHeaderLabels(HEADER_LABELS_POINTS)
        self.ui.tableWidget_Points.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidget_Points.customContextMenuRequested.connect(self.context_menu_table_points)

        self.ui.listWidget_Images.itemClicked.connect(self.open_image)
        self.ui.listWidget_Images.itemActivated.connect(self.open_image)
        self.ui.listWidget_Images.itemChanged.connect(self.open_image)
        self.ui.listWidget_Images.itemSelectionChanged.connect(self.selected_image)

        self.ui.toolBar.visibilityChanged.connect(self.tool_bar_visibility)

        self.ui.actionSeenNoSeenPanel.triggered.connect(self.dockWidget_SeenTable_visible)
        self.ui.dockWidget_SeenTable.visibilityChanged.connect(self.check_dockWidget_SeenTable)

        self.ui.actionImages_List.triggered.connect(self.dockWidget_ImagesList_visible)
        self.ui.dockWidget_ImagesList.visibilityChanged.connect(self.check_dockWidget_ImagesList)

        self.ui.actionPointsPanel.triggered.connect(self.dockWidget_PointsTable_visible)
        self.ui.dockWidget_PointsTable.visibilityChanged.connect(self.check_dockWidget_PointsTable)

        self.ui.actionCreatPoint.triggered.connect(self.setModeCreatePoint)
        self.ui.actionSelectPoint.triggered.connect(self.setModeSelectPoint)

        self.ui.actionZoomIn.triggered.connect(self.zoom_in)
        self.ui.actionZoomOut.triggered.connect(self.zoom_out)
        self.ui.actionZoom_2x.triggered.connect(self.zoom_2x)
        self.ui.actionZoom_Reset.triggered.connect(self.zoom_reset)

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

        self.shortcut_down = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_down.activated.connect(self.next_photo)

        self.shortcut_up = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_up.activated.connect(self.previous_photo)

        self.ui.actionPointsPanel.setChecked(False)
        self.ui.actionSeenNoSeenPanel.setChecked(False)
        self.ui.actionImages_List.setChecked(False)
        self.ui.dockWidget_ImagesList.setVisible(False)
        self.ui.dockWidget_SeenTable.setVisible(False)
        self.ui.dockWidget_PointsTable.setVisible(False)

    def context_menu_table_points(self, point):
        """
        Показать контекстное меню для точек таблицы.

        """
        menu = QtWidgets.QMenu()

        delete_point = QtWidgets.QAction('Delete', menu)
        delete_point.triggered.connect(self.deleteSelectedPointsInTable)
        menu.addAction(delete_point)

        menu.exec(self.ui.tableWidget_Points.verticalHeader().mapToGlobal(point))

    def next_photo(self):
        """
        Переходит к следующему фото в списке.

        Этот метод устанавливают фокус на виджет списка, содержащий фотографии,
        и проверяет, является ли текущее фото первым. Если текущее фото не является
        первым, метод переходит к предыдущему фото, устанавливая текущую строку равной
        текущей строке виджета списка минус 1.

        Если ни одно фото не выбрано, метод устанавливает текущую строку на первое фото.

        В конце концов метод вызывает функцию `open_image` с текущим элементом
        виджета списка и устанавливает фокус на главное окно.
        """
        self.ui.listWidget_Images.setFocus()
        if self.ui.listWidget_Images.currentRow() == 0:
            return
        elif len(self.ui.listWidget_Images.selectedItems()) == 0:
            self.ui.listWidget_Images.setCurrentRow(0)
        else:
            self.ui.listWidget_Images.setCurrentRow(self.ui.listWidget_Images.currentRow() - 1)

        self.open_image(self.ui.listWidget_Images.currentItem())
        self.setFocus()

    def previous_photo(self):
        """
        Переходит к предыдущему фото

        Установить фокус на виджет списка изображений. Если в списке нет изображений,
        или если текущая строка является последней, метод вернется, не выполняя никаких дополнительных действий.
        Если в списке выбраны элементы, он установит текущую строку на следующую.
        В противном случае он установит текущую строку на первую строку.
        """
        self.ui.listWidget_Images.setFocus()
        if len(self.ui.listWidget_Images) <= self.ui.listWidget_Images.currentRow() + 1:
            return
        elif len(self.ui.listWidget_Images.selectedItems()) == 0:
            self.ui.listWidget_Images.setCurrentRow(0)
        else:
            self.ui.listWidget_Images.setCurrentRow(self.ui.listWidget_Images.currentRow() + 1)

        self.open_image(self.ui.listWidget_Images.currentItem())
        self.setFocus()

    def search_item_photo_and_select(self, file_name):
        """
        Ищет фотографию элемента и выбирает ее.

        """
        items = self.ui.listWidget_Images.findItems(file_name, Qt.MatchFixedString)
        if items:
            index = self.ui.listWidget_Images.row(items[0])
            self.ui.listWidget_Images.setCurrentRow(index)
            self.open_image(self.ui.listWidget_Images.currentItem())

    def new_point(self, coords):
        """
        Используется для создания новой точки. В качестве параметра принимает координаты точки.
        """
        if not self.view.isModeCreatePoints:
            return
        self.new_coords = coords
        survey_effort = self.main_session.query(SurveyEffort).filter_by(
            r_year=m_params.year,
            site=m_params.site,
            species=m_params.species,
        ).first()
        if not survey_effort:
            survey_effort = SurveyEffort(r_year=m_params.year,
                                         site=m_params.site,
                                         species=m_params.species,
                                         )
            self.main_session.add(survey_effort)
            self.main_session.commit()

        self.animal_registration = AnimalRegistration()

        self.animal_registration.iLeft = self.new_coords.x()
        self.animal_registration.iTop = self.new_coords.y()
        self.animal_registration.file_name = self.ui.listWidget_Images.currentItem().data(Qt.UserRole).fileName

        self.animal_registration.result[ModelRegistrationAnimal].connect(self.handle_input_registration)

    def load_images_list(self):
        """
        Очищает виджет списка и заполняет его изображениями из m_params.photos_for_day.
        Устанавливает красный цвет шрифта для элементов, которые находятся в m_params.done_files.
        Устанавливает заголовок окна док-виджета на "Изображения: {0}", где {0} - это количество изображений
        в виджете списка.
        """
        self.ui.listWidget_Images.clear()

        for item in m_params.photos_for_day:
            lw_item = QListWidgetItem('%s' % item.fileName)
            lw_item.setData(Qt.UserRole, item)
            if item.fileName in m_params.done_files:
                lw_item.setForeground(QColor('#FF0000'))

            self.ui.listWidget_Images.addItem(lw_item)

        self.ui.dockWidget_ImagesList.setWindowTitle("Images: {0}".format(len(self.ui.listWidget_Images)))

    def selected_image(self):
        """
        Открывает выбранное изображение в виджете списка.

        """
        if self.ui.listWidget_Images.currentRow() > 0:
            self.open_image(self.ui.listWidget_Images.currentItem())

    def open_image(self, item):
        """
        Открывает изображение и заполняет пользовательский интерфейс изображением и соответствующими данными.

        Метод очищает точки расположения, извлекает данные изображения из выбранного элемента,
        устанавливает фотографию в представлении с использованием пути к изображению, извлекает точки расположения,
        связанные с изображением, отображает уровень увеличения на дисплее,
        обновляет строку состояния информацией об изображении, заполняет таблицы соответствующими данными и
        добавляет точки к представлению, соответствующие точкам местоположения, с всплывающими подсказками,
        отображающими информацию об животном.
        """
        self.location_points.clear()

        data = item.data(Qt.UserRole)
        self.view.setPhoto(data.path, 1)
        self.location_points = self.get_location(data.fileName)

        self.ui.lcd_zoom.display(str(self.view.get_zoom()))

        self.ui.statusBar.showMessage(f"Images: {len(self.ui.listWidget_Images)}  |  " +
                                      f"Selected {self.ui.listWidget_Images.currentRow() + 1}  |  " +
                                      f"Image Path: {data.path}")
        self.fill_tables()

        for loc in self.location_points:
            tooltip = f"{loc.animal_type} {loc.local_site}"
            self.view.addPoint(pos=QtCore.QPoint(loc.iLeft, loc.iTop), text=loc.animal_name, data=loc, tooltip=tooltip)

    def get_location(self, fileName):
        """
        Получает информацию о регистрациях на фотографии
        """
        points = self.main_session.query(Location).filter_by(r_year=m_params.year,
                                                             site=m_params.site,
                                                             r_date=m_params.current_data,
                                                             file_name=fileName,
                                                             species=m_params.species).all()

        return points

    def selectPointsInImageView(self):
        """
        Выбирает точки в представлении изображения на основе выбранных строк в виджете таблицы
        """
        data_rows = []

        selected = self.ui.tableWidget_Points.selectionModel().selectedRows()
        rows = [ix.row() for ix in selected]
        for row in rows:
            data_loc = self.ui.tableWidget_Points.item(row, 0).data(Qt.UserRole)
            data_rows.append(data_loc)

        self.view.selectPoints(data_rows)

    def selectPointsInTable(self, points):
        """
        Выбирает строки в tableWidget_Points, которые соответствуют заданным точкам
        """
        if not points:
            self.ui.tableWidget_Points.clearSelection()
        for point in points:
            data = point.data(Qt.UserRole)
            for i in range(self.ui.tableWidget_Points.rowCount()):
                if data == self.ui.tableWidget_Points.item(i, 0).data(Qt.UserRole):
                    self.ui.tableWidget_Points.selectRow(i)

    def deleteSelectedPointsInTable(self):
        """

        Удаляет выбранные точки в таблице.

        """
        data_rows = []

        selected = self.ui.tableWidget_Points.selectionModel().selectedRows()
        rows = [ix.row() for ix in selected]
        for row in rows:
            data_loc = self.ui.tableWidget_Points.item(row, 0).data(Qt.UserRole)
            data_rows.append(data_loc)

        points = list(filter(lambda x: x.data(Qt.UserRole) in data_rows, self.view.points))
        self.view.removePoints(points)
        self.delete_location(data_rows)
        self.fill_tables()
        file_name = self.ui.listWidget_Images.currentItem().text()

        if not self.location_points:
            m_params.done_files.remove(file_name)

        self.update_done_location.emit(file_name)

    def movePoint(self, point):
        """
        Обновляет местоположение данной точки.

        """
        loc = point.data(Qt.UserRole)
        loc.iTop = int(point.pos().y())
        loc.iLeft = int(point.pos().x())
        self.main_session.commit()

    # Удаляем запись в Location
    def delete_location(self, locations):
        """
        Удаляет регистрацию на фото и связанные с ней записи из базы данных.
        """
        for loc in locations:

            self.main_session.delete(loc)
            self.main_session.commit()

            all_locations = self.main_session.query(Location).filter_by(r_year=loc.r_year,
                                                                        site=loc.site,
                                                                        r_date=loc.r_date,
                                                                        animal_name=loc.animal_name).all()

            if not all_locations:
                daily = self.main_session.query(Daily).filter_by(r_year=loc.r_year,
                                                                 site=loc.site,
                                                                 r_date=loc.r_date,
                                                                 animal_name=loc.animal_name).first()
                if daily:
                    self.main_session.delete(daily)
                    self.main_session.commit()

            daily = self.main_session.query(Daily).filter_by(r_year=loc.r_year,
                                                             site=loc.site,
                                                             animal_name=loc.animal_name).all()
            if not daily:
                resight = self.main_session.query(Resight).filter_by(r_year=loc.r_year,
                                                                     site=loc.site,
                                                                     animal_name=loc.animal_name).first()
                if resight:
                    self.main_session.delete(resight)
                    self.main_session.commit()

            self.location_points.remove(loc)

    def fill_table_points(self):
        """
        Заполнить таблицу животных зарегистрированных на фото
        """
        self.ui.tableWidget_Points.clear()
        self.ui.tableWidget_Points.setHorizontalHeaderLabels(HEADER_LABELS_POINTS)
        self.ui.tableWidget_Points.setRowCount(len(self.location_points))

        row = 0
        for loc in self.location_points:
            cell_name = QTableWidgetItem(f"{loc.animal_name}")
            cell_name.setData(Qt.UserRole, loc)
            cell_status = QTableWidgetItem(f"{loc.animal_type}")
            cell_local_site = QTableWidgetItem(f"{loc.local_site}")

            self.ui.tableWidget_Points.setItem(row, 0, cell_name)
            self.ui.tableWidget_Points.setItem(row, 1, cell_status)
            self.ui.tableWidget_Points.setItem(row, 2, cell_local_site)
            row += 1

    def fill_table_seen(self):
        """
        Заполнить таблицу животных зарегистрированных в текущий день
        """
        self.ui.tableWidget_SeenNoSeen.clear()
        self.ui.tableWidget_SeenNoSeen.setHorizontalHeaderLabels(HEADER_LABELS_SEEN)

        resight = self.main_session.query(Resight).filter_by(r_year=m_params.year,
                                                             site=m_params.site,
                                                             species=m_params.species, ).all()
        self.ui.tableWidget_SeenNoSeen.setRowCount(len(resight))
        row = 0
        seen = 0
        no_seen = 0
        for res in resight:
            cell = QTableWidgetItem(f"{res.animal_name} {res.status}")
            daily = self.main_session.query(Daily).filter_by(r_year=m_params.year,
                                                             site=m_params.site,
                                                             r_date=m_params.current_data,
                                                             animal_name=res.animal_name,
                                                             species=m_params.species, ).first()
            if daily:
                cell_daily = QTableWidgetItem(f"{res.animal_name} {daily.status}")
                self.ui.tableWidget_SeenNoSeen.setItem(row, 1, cell_daily)
                seen += 1
            else:
                self.ui.tableWidget_SeenNoSeen.setItem(row, 0, cell)
                no_seen += 1
            row += 1

    def fill_tables(self):
        """
        Заполнить таблицы
        """
        self.fill_table_points()
        if self.ui.dockWidget_SeenTable.isVisible():
            self.fill_table_seen()

    def handle_input_registration(self, reg: ModelRegistrationAnimal):
        """ Обработка результата ввода данных в форме регистрации"""

        self.location_points.append(reg.location)

        tooltip = f"{reg.animal_status} {reg.local_site}"

        self.view.addPoint(pos=self.new_coords, text=reg.animal_name, tooltip=tooltip, data=reg.location)

        if reg.file_name not in m_params.done_files:
            m_params.done_files.append(reg.file_name)

        self.update_done_location.emit(reg.file_name)
        self.fill_tables()
        self.ui.listWidget_Images.currentItem().setForeground(QColor('#FF0000'))

    """Показать / скрыть панель"""

    # Показать / скрыть панель tab_seen
    def dockWidget_SeenTable_visible(self):
        """
        Устанавливает видимость док-виджета для таблицы "seen" на основе состояния действия.
        """
        self.ui.dockWidget_SeenTable.setVisible(self.ui.actionSeenNoSeenPanel.isChecked())

        if self.ui.actionSeenNoSeenPanel.isChecked():
            self.fill_table_seen()

    def check_dockWidget_SeenTable(self):
        """
        Проверяет, видим ли док-виджет "SeenTable", и обновляет состояние действия "SeenNoSeenPanel"
        """
        self.ui.actionSeenNoSeenPanel.setChecked(self.ui.dockWidget_SeenTable.isVisible())

    # Показать / скрыть панель Images List
    def dockWidget_ImagesList_visible(self):
        """
        Устанавливает видимость док-виджета для списка изображений.
        """
        self.ui.dockWidget_ImagesList.setVisible(self.ui.actionImages_List.isChecked())

    def check_dockWidget_ImagesList(self):
        """
        Устанавливает состояние проверки действия "Список изображений"
        на основе видимости док-виджета "Список изображений".
        """
        self.ui.actionImages_List.setChecked(self.ui.dockWidget_ImagesList.isVisible())

    # Показать / скрыть панель PointsTable
    def dockWidget_PointsTable_visible(self):
        """
        Устанавливает видимость док-виджета для таблицы точек на основе состояния действия actionPointsPanel.
        """
        self.ui.dockWidget_PointsTable.setVisible(self.ui.actionPointsPanel.isChecked())

    def check_dockWidget_PointsTable(self):
        """
        Этот метод используется для проверки видимости док-виджета с именем "dockWidget_PointsTable"
        и установки состояния действия "actionPointsPanel" соответственно.
        """
        self.ui.actionPointsPanel.setChecked(self.ui.dockWidget_PointsTable.isVisible())

    """zoom"""

    def zoom_display(self, zoom):
        """
        Устанавливает значение увеличения изображения на lcd дисплее.
        """
        self.ui.lcd_zoom.display(str(zoom))

    def zoom_out(self):
        """
        Уменьшает коэффициент масштабирования изображения и обновляет уровень увеличения,
        отображаемый на пользовательском интерфейсе.
        """
        factor = 0.8
        self.view.scale(factor, factor)
        self.view.zoom -= 1
        self.zoom_display(self.view.get_zoom())

    def zoom_in(self):
        """
        Увеличивает коэффициент масштабирования изображения и обновляет уровень увеличения,
        отображаемый на пользовательском интерфейсе.
        """
        factor = 1.2
        self.view.scale(factor, factor)
        self.view.zoom += 1
        self.zoom_display(self.view.get_zoom())

    def zoom_reset(self):
        """
        Сбрасывает уровень увеличения изображения.
        """
        self.view.fitInView()
        self.view.zoom = 0
        self.zoom_display(self.view.get_zoom())

    def zoom_2x(self):
        """
        Увеличивает изображение в два раза.
        """
        factor = 2
        self.view.scale(factor, factor)
        self.view.zoom = 20
        self.zoom_display(self.view.get_zoom())

    def changeSizePoints(self):
        """Задает размер точки и сохраняет в настройки пользователя"""
        self.view.setSizePoint(self.ui.spinBox_sizePoint.value())
        user_settings.setValue("SizePoint", self.ui.spinBox_sizePoint.value())

    def tool_bar_visibility(self):
        # блокировка скрытия toolbar
        self.ui.toolBar.setVisible(True)

    def closeEvent(self, *args, **kwargs):
        m_params.windows_list.remove(self)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.zoom_reset()
        elif e.key() == Qt.Key_F1:
            subprocess.check_call("hh.exe help.chm::/location.htm")

    def onCtrlPress(self, event):
        """
        Устанавливает действие выбора точки и меняет режим на выбор точки при нажатии клавиши Ctrl.
        """
        if event.key() == Qt.Key_Control:
            self.ui.actionSelectPoint.setChecked(True)
            self.setModeSelectPoint()

    def onCtrlRelease(self, event):
        """
        Обрабатывает отпускание клавиши Ctrl.
        Если отпущенная клавиша является клавишей Control, он устанавливает режим создания точки.
        """
        if event.key() == Qt.Key_Control:
            self.ui.actionCreatPoint.setChecked(True)
            self.setModeCreatePoint()

    def setModeCreatePoint(self):
        """
        Устанавливает режим для создания точки.
        Этот метод устанавливает режим представления для создания точек.
        Он также очищает выбор точек в виджете таблицы и отключает режим выбора точки".
        """
        self.view.isModeCreatePoints = True
        self.ui.actionSelectPoint.setChecked(False)
        self.ui.tableWidget_Points.clearSelection()

    def setModeSelectPoint(self):
        """
        Устанавливает режим для выбора точек.
        Этот метод отключает режим выбора точек.
        """
        self.view.isModeCreatePoints = False
        self.ui.actionCreatPoint.setChecked(False)
