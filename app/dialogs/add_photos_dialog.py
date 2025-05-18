import os

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItem, QColor, QKeySequence, QPixmap
from PyQt5.QtWidgets import QListWidgetItem, QAbstractItemView, QShortcut, QMessageBox

from app import m_params
from app.custom_widgets.image_viewer import PreviewImageViewer
from app.custom_widgets.list_widget_drag_and_drop import DragDropListWidget
from app.models.main_db import CountEffortTypes
from app.controllers.items_file import ItemFile
from app.services.helpers import select_project_folders, search_path_photo
from app.view.ui_dialog_add_count_photos import Ui_add_photos_count_dialog


class AddPhotosDialog(QtWidgets.QDialog):
    """
    Класс AddPhotosDialog
    Предназначенный для обработки операций, связанных с добавлением фотографий в режиме учета,
    при добавлении и редактировании фай-лов учета.
    Этот класс представляет собой диалоговое окно для добавления фотографий. Он наследуется от QDialog.
    Параметры: effortType - Объект типа CountEffortTypes, представляющий тип усилия.
    Методы:
    - __init__: Инициализирует класс AddPhotosDialog. Настройка пользовательского интерфейса, максимизация диалога,
    установка флагов окна для кнопок минимизации и максимизации. Инициализация переменных класса,
    соединение сигналов со слотами, настройка клавиатурных ярлыков.
    - move_item_complete: вызывается при перемещении элемента внутри списка добавленных фотографий.
    Сортирует элементы в списке добавленных фотографий, обновляет цвет элементов и обновляет название группы полей для ввода.
    - context_menu_photos: Слот-метод, вызываемый для отображения контекстного меню списка исходных фотографий.
    Создает меню с действием копирования и соединяет его с методом copy_selected_items.
    - context_menu_added_photos: Слот-метод, вызываемый для отображения контекстного меню для добавленного списка фотографий.
    Создает меню с действиями вставки, удаления и очистки и связывает их с соответствующими методами.
    - remove_all_added_photos: Метод для удаления всех фотографий из списка добавленных фотографий.
    - remove_added_photos: Метод для удаления выбранных элементов из списка добавленных фотографий.
    Если все элементы выбраны, он очищает список. В противном случае он удаляет каждый выбранный элемент.
    - copy_selected_items: Метод копирования выбранных элементов из списка исходных фотографий.
    Он добавляет выбранные элементы в список буфера обмена.
    - paste_items: Метод вставки элементов из буфера обмена в список добавленных фотографий. Проверяет,
    установлен ли день, и находит элементы в списке добавленных фотографий с идентичными именами файлов.
    Если элемент еще не присутствует, он добавляет его в список добавленных фотографий.
    Он обновляет список добавленных фотографий и очищает буфер обмена.
    - scene_clear: Метод очистки сцены предварительного просмотра изображения.
    - refresh_color_item: Метод обновления цвета элементов в списке исходных фотографий.
    Находит элементы в списке добавленных фотографий с соответствующими именами файлов и устанавливает их цвет в красный.
    - select_folder_count: Метод обработки выбора папки для определенного дня. Получает день и путь к каталогу
    из выбранного элемента и устанавливает текущий индекс на выбранный индекс.
    Он вызывает метод selected_folder_day с выбранным индексом.
    - selected_folder_day: Метод обработки выбора папки для определенного дня. Очищает сцену предварительного просмотра
    изображения и список исходных фотографий. Получает выбранный день и путь к родительскому каталогу
    из выбранного индекса. Устанавливает выбранный каталог и проверяет, существует ли выбранный день в
    качестве подкаталога. Если да, то собирает файлы или папки внутри выбранного каталога дня и добавляет их в
    список исходных фотографий.

    """
    def __init__(self, effortType: CountEffortTypes):
        super().__init__()

        self.ui = Ui_add_photos_count_dialog()
        self.ui.setupUi(self)

        self.showMaximized()

        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        self.effortType = effortType
        self.countType = m_params.support_count_type_id.itemFromId(self.effortType.count_type)

        self.clipboard = []
        self.ui.groupBox.setTitle('')
        self.ui.treeView_directories.clicked.connect(self.selected_folder_day)

        self.sourcePhotos = DragDropListWidget(self.effortType.r_date)
        self.ui.splitter.addWidget(self.sourcePhotos)
        self.sourcePhotos.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.addedPhotos = DragDropListWidget(self.effortType.r_date)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.addedPhotos.sizePolicy().hasHeightForWidth())
        self.addedPhotos.setSizePolicy(sizePolicy)
        self.addedPhotos.setMinimumSize(QSize(200, 0))
        self.addedPhotos.setMaximumSize(QSize(16777215, 16777215))
        self.ui.verticalLayout_2.addWidget(self.addedPhotos)

        self.sourcePhotos.itemSelectionChanged.connect(self.select_photo)
        self.sourcePhotos.clicked.connect(self.select_photo)
        self.addedPhotos.itemSelectionChanged.connect(self.select_added_photo)

        self.addedPhotos.setContextMenuPolicy(Qt.CustomContextMenu)
        self.addedPhotos.customContextMenuRequested.connect(self.context_menu_added_photos)

        self.sourcePhotos.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sourcePhotos.customContextMenuRequested.connect(self.context_menu_photos)

        self.sourcePhotos.setDragDropMode(QAbstractItemView.DragOnly)
        self.addedPhotos.setDragDropMode(QAbstractItemView.DropOnly)

        self.sourcePhotos.move_item_complete.connect(self.move_item_complete)

        # Создаем обработчики событий клавиатуры для копирования и вставки
        self.copy_shortcut = QShortcut(QKeySequence.Copy, self.sourcePhotos)
        self.paste_shortcut = QShortcut(QKeySequence.Paste, self.addedPhotos)
        self.del_shortcut = QShortcut(QKeySequence.Delete, self.addedPhotos)
        # Назначаем обработчики событий
        self.copy_shortcut.activated.connect(self.copy_selected_items)
        self.paste_shortcut.activated.connect(self.paste_items)
        self.del_shortcut.activated.connect(self.remove_added_photos)

        self.view = PreviewImageViewer()
        self.ui.imageLayout.addWidget(self.view, 0, 0, 1, 1)

        self.selected_directory = ""

        for item in self.effortType.count_files:
            path = search_path_photo(item.file_name)

            q_item = QListWidgetItem(item.file_name)
            q_item.setData(Qt.UserRole, ItemFile(fileName=item.file_name, path=str(path).replace('\\', '/')))
            self.addedPhotos.addItem(q_item)
        self.ui.groupBox_2.setTitle(f'Files: {self.addedPhotos.count()}')

        self.load_directories()

    @QtCore.pyqtSlot()
    def move_item_complete(self):
        self.addedPhotos.sortItems()
        self.refresh_color_item()
        self.ui.groupBox_2.setTitle(f'Files: {self.addedPhotos.count()}')

    def context_menu_photos(self, point):
        menu = QtWidgets.QMenu()

        copy = QtWidgets.QAction('Copy ', menu)
        copy.triggered.connect(self.copy_selected_items)
        menu.addAction(copy)

        menu.exec(self.sourcePhotos.mapToGlobal(point))

    def context_menu_added_photos(self, point):
        menu = QtWidgets.QMenu()

        past = QtWidgets.QAction('Paste ', menu)
        past.triggered.connect(self.paste_items)
        menu.addAction(past)

        delete = QtWidgets.QAction('Delete ', menu)
        delete.triggered.connect(self.remove_added_photos)
        menu.addAction(delete)

        clear = QtWidgets.QAction('Clear', menu)
        clear.triggered.connect(self.remove_all_added_photos)
        menu.addAction(clear)

        menu.exec(self.addedPhotos.mapToGlobal(point))

    def remove_all_added_photos(self):
        self.addedPhotos.clear()
        self.move_item_complete()

    def remove_added_photos(self):
        if self.addedPhotos.count() == len(self.addedPhotos.selectedItems()):
            self.addedPhotos.clear()

        for item in self.addedPhotos.selectedItems():
            row = self.addedPhotos.row(item)
            self.addedPhotos.takeItem(row)
        self.move_item_complete()

    # Функция для копирования выбранных элементов
    def copy_selected_items(self):
        for item in self.sourcePhotos.selectedItems():
            self.clipboard.append(item.data(Qt.UserRole))

    # Функция для вставки элементов из буфера обмена
    def paste_items(self):
        day = None
        self.addedPhotos.clearSelection()
        if self.addedPhotos.count():
            item_added = self.addedPhotos.item(0)
            day = item_added.text()[0:8]

        for copy_item in self.clipboard:
            items = self.addedPhotos.findItems(copy_item.fileName, Qt.MatchExactly)
            if not self.effortType.r_date or self.effortType.r_date == 0 or copy_item.fileName[0:8] == str(
                    self.effortType.r_date):
                if not day:
                    day = copy_item.fileName[0:8]
                if not list(filter(lambda x: x.text() == copy_item.fileName, items)):
                    if day and day == copy_item.fileName[0:8]:
                        lw_item = QListWidgetItem(copy_item.fileName)
                        lw_item.setData(Qt.UserRole, copy_item)
                        self.addedPhotos.addItem(lw_item)
        if self.clipboard:
            self.move_item_complete()
            self.clipboard.clear()

    def scene_clear(self):
        self.view.setPixmap(QtGui.QPixmap())

    def refresh_color_item(self):
        for row in range(self.sourcePhotos.count()):
            item = self.sourcePhotos.item(row)
            find_items = self.addedPhotos.findItems(item.text(), Qt.MatchFixedString | Qt.MatchRecursive)
            if find_items:
                item.setForeground(QColor('#FF0000'))
            else:
                item.setForeground(QColor('#000000'))

    # выбрали папку учета за день
    def select_folder_count(self, f_item):
        day = f_item.text()[0:8]
        data = f_item.data(Qt.UserRole)
        data = '/'.join(data.path.split('/')[0:3])

        index = self.ui.treeView_directories.currentIndex()
        current_day = m_params.model_directories.data(index)
        if current_day == day:
            return

        items = m_params.model_directories.findItems(data, Qt.MatchFixedString | Qt.MatchRecursive)
        for item in items:
            for r in range(item.rowCount()):

                if day.__contains__(item.child(r, 0).text()[0:8]):
                    index = item.child(r, 0).index()
                    self.ui.treeView_directories.setCurrentIndex(index)
                    self.selected_folder_day(index)
                    break

    def selected_folder_day(self, index):
        try:
            self.scene_clear()
            self.sourcePhotos.clear()

            day = m_params.model_directories.data(index)
            parent = m_params.model_directories.parent(index)
            d = m_params.model_directories.data(parent)
            self.selected_directory = d

            if os.path.isdir(d + "/" + day):
                for dirs, folders, files in os.walk(str(os.path.join(d, day))):

                    files.sort()
                    sources = files

                    if str(self.countType.folder).lower() == 'opp':
                        sources = folders

                    for item in sources:

                        item_file = ItemFile()
                        item_file.fileName = item
                        item_file.path = f'{d}/{day}/{item}'

                        lw_item = QListWidgetItem('%s' % item)
                        lw_item.setData(Qt.UserRole, item_file)

                        if self.addedPhotos.findItems(str(item), Qt.MatchFixedString | Qt.MatchRecursive):
                            lw_item.setForeground(QColor('#FF0000'))

                        self.sourcePhotos.addItem(lw_item)

                    break
        except Exception as ex:
            QMessageBox.warning(self, 'Exception', ex.args[0])

    # заполнить дерево папками
    def load_directories(self):

        self.sourcePhotos.clear()
        m_params.model_directories.clear()
        drivers = select_project_folders(m_params)

        for p in drivers:
            path = os.path.dirname(p[0] + "/")
            item = QStandardItem(path)
            if str(self.countType.folder).lower() in str(p[0]).lower():
                m_params.model_directories.appendRow(item)

                for dirs, folders, files in os.walk(os.path.join(path)):
                    folders.sort()
                    for f in folders:
                        i = QStandardItem(f)

                        item.appendRow(i)
                    break
        if len(drivers) > 0:
            m_params.model_directories.setHeaderData(0, Qt.Horizontal, " ")
            self.ui.treeView_directories.setModel(m_params.model_directories)

    def select_photo(self):
        # self.scene_clear()
        if self.sourcePhotos.currentRow() < 0:
            return
        self.selected_photo(self.sourcePhotos.currentItem())

    def selected_photo(self, name):
        if str(self.countType.folder).lower() == 'opp':
            pass
        else:
            self.load_image(name)

    def select_added_photo(self):
        if self.addedPhotos.currentRow() > -1:
            self.selected_added_photo(self.addedPhotos.currentItem())

    def selected_added_photo(self, f_item):

        self.select_folder_count(f_item)

        items = self.sourcePhotos.findItems(f_item.text(), Qt.MatchFixedString | Qt.MatchRecursive)

        if items:
            self.sourcePhotos.setCurrentItem(items[0])

    def load_image(self, item):
        self.ui.groupBox.setTitle('')
        data = item.data(Qt.UserRole)
        if data.path:
            self.ui.groupBox.setTitle(data.path)
            pix_map = QPixmap(data.path)
            self.view.setPixmap(pix_map)
