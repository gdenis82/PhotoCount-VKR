import pickle

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication, QListWidget, QListWidgetItem
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QDragMoveEvent, QDrag
from PyQt5.QtCore import QMimeData, Qt, QPoint


class DragDropListWidget(QListWidget):
    """
    Класс для пользовательского QListWidget, который поддерживает функциональность перетаскивания.
    Сигналы:
    - move_item_complete: выпускается, когда элемент успешно перемещается в другой список
    Атрибуты:
    - date: дата, связанная со списком
    Методы:
    - mousePressEvent(event: QMouseEvent) -> None: Обрабатывает событие нажатия мыши.
    - mouseMoveEvent(event: QMouseEvent) -> None: Обрабатывает событие движения мыши.
    - start_drag()-> None: Запускает операцию перетаскивания.
    - dragEnterEvent(event: QDragEnterEvent) -> None: Обрабатывает событие входа перетаскивания.
    - dragMoveEvent(event: QDragMoveEvent) -> None: Обрабатывает событие перемещения перетаскивания.
    - dropEvent(event: QDropEvent) -> None: Обрабатывает событие выпадения.
    """
    move_item_complete = QtCore.pyqtSignal()

    def __init__(self, date):
        super().__init__()
        self.date = date
        self.dragPos = QPoint()
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDefaultDropAction(Qt.MoveAction)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.dragPos = event.pos()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.LeftButton:
            drag_distance = (event.pos() - self.dragPos).manhattanLength()
            if drag_distance >= QApplication.startDragDistance():
                self.start_drag()

        super().mouseMoveEvent(event)

    def start_drag(self):
        items = [item.data(Qt.UserRole) for item in self.selectedItems()]
        mime_data = QMimeData()
        data = pickle.dumps(items)
        mime_data.setData("ItemFile", data)

        # for item in items:
        #     mime_data = QMimeData()
        #     data = pickle.dumps(item.data(Qt.UserRole))
        #     mime_data.setData("ItemFile", data)

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)
        self.move_item_complete.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat("ItemFile"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat("ItemFile"):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:

        if event.mimeData().hasFormat("ItemFile"):
            mime_data = event.mimeData()
            items_data = pickle.loads(mime_data.data("ItemFile"))

            for item_data in items_data:
                items = self.findItems(item_data.fileName, Qt.MatchExactly | Qt.MatchRecursive)

                if self.count():
                    first_item = self.item(0)
                    day = first_item.text()[0:8]
                    if day != item_data.fileName[0:8]:
                        return

                if not self.date or self.date == 0 or item_data.fileName[0:8] == str(self.date):
                    if not items:
                        lw_item = QListWidgetItem(item_data.fileName, self)
                        lw_item.setData(Qt.UserRole, item_data)
                        lw_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)

                        event.acceptProposedAction()
