from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QPen, QFont
from PyQt5.QtWidgets import QGraphicsItem, QStyle, QMenu


class PointItem(QGraphicsItem):
    """

    Класс, представляющий элемент точки в графической сцене. Этот класс наследует от QGraphicsItem.

    """
    def __init__(self, parent, text, color, size):
        super().__init__()

        self.text = text
        self.color = color
        self.parent = parent

        # размеры точки и текста
        self.size = size
        self.font = QFont("Arial", self.size, QFont.Normal)
        self.textVisible = True

        self.cords_factor = self.size * 0.5

        self.setToolTip(text)

        self.initUI()

    def initUI(self):
        """
        """
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)

    def contextMenuEvent(self, event):
        menu = QMenu()
        remove_action = menu.addAction("Remove Point", self.removePoint)
        selected_action = menu.exec_(event.screenPos())

        if selected_action == remove_action:
            pass

        event.accept()

    def removePoint(self):
        """
        Удалить точку используя контекстное меню.

        """
        self.parent.removedPointFromContextMenu(self)

    def setPointSize(self, size):
        """
        Установит размер точки шрифта и обновит связанные атрибуты.
        """
        self.size = size
        self.font = QFont("Arial", self.size, QFont.Normal)
        self.cords_factor = self.size * 0.5

    def setPointFont(self, font):
        """
        Устанавливает шрифт для точки.
        """
        self.font = font

    def boundingRect(self):
        """
        Вычисляет и возвращает ограничивающий прямоугольник текста.
        """
        lengthText = 1
        height_factor = self.size * 0.3

        if self.textVisible:
            lengthText = len(self.text) + 1
            height_factor = self.size

        width = lengthText * self.size
        height = height_factor + self.size * 0.8
        return QRectF(-self.cords_factor, -self.cords_factor, width, height)

    def paint(self, painter, option, widget=None):
        """
        Рисует точку с заданными параметрами.
        """
        # рисуем точку
        painter.setBrush(QBrush(self.color))
        painter.drawEllipse(-self.cords_factor, -self.cords_factor, self.size, self.size)

        if self.textVisible:
            # рисуем текст
            painter.setPen(QPen(self.color, 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setFont(self.font)
            painter.drawText(self.cords_factor, self.size, self.text)

        # рисуем выделение точки
        if option.state & QStyle.State_Selected:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(Qt.white, 2, Qt.DashLine))
            painter.drawRect(self.boundingRect())

