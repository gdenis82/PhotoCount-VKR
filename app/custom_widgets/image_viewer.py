from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QPoint
from PyQt5.QtGui import QBrush, QFont, QPixmap, QColor, QPen
from PyQt5.QtWidgets import QGraphicsView, QGraphicsPixmapItem, QGraphicsScene, QFrame, QGraphicsRectItem

from app.controllers.items_point import PointItem
from app.controllers.support_lists import PointsList
from app.services.helpers import open_image_to_pixmap

ZOOM_IN_FACTOR = 1.25
ZOOM_OUT_FACTOR = 0.8


class ImageViewer(QGraphicsView):
    """
    Класс ImageViewer
    Класс, представляющий виджет просмотра изображений, который наследуется от класса QGraphicsView.
    Класс ImageViewer используется для отображения и манипулирования изображениями.
    Сигналы:
    - zoomDisplay: Сигнал, который посылается при изменении уровня масштабирования обзора. Он передает текущий уровень
    масштабирования в виде целого числа.
    - newPoint: Сигнал, который посылается при создании новой точки на видах. Он передает позицию
    новой точки в виде QPoint.
    - selectedPoints: Сигнал, который посылается при выборе одной или нескольких точек на видах. Он передает список
    выбранных точек в виде списка объектов PointItem.
    - deletePointsInParent: Сигнал, который посылается при активации операции удаления точек.
    - movePoint: Сигнал, который посылается при перемещении точки по видам. Он передает перемещенную точку
    как объект PointItem.

    Методы:
    - __init__(self): Конструктор класса, инициализирует основные параметры и переменные, создает объекты
    QGraphicsPixmapItem, QGraphicsScene и настраивает интерфейс.

    - initUI(self): Настройка интерфейса виджета, устанавливает определенные свойства для QGraphicsView.

    - setSizePoint(self, size): Устанавливает размер точек.

    - textPointsVisible(self, value: bool): Устанавливает видимость текста точек.

    - changeColorPoint(self, text, color): Изменяет цвет точек по тексту.

    - visiblePoint(self, text, value): Устанавливает видимость точек по тексту.

    - recalculateSceneRect(self): Пересчитывает размер сцены.

    - fitInView: Подгоняет изображение.

    - setPhoto(self, file_path, factor=None): Загружает фото из файла и подгоняет его.

    - clearAllRects(self): Удаляет все прямоугольники из сцены.

    - drawRect(self, rect: QRectF): Рисует прямоугольник на сцене.

    - scene_clear(self): Очищает сцену от точек и устанавливает режим NoDrag.

    - addPoint: Добавляет точку на сцену.

    - removedPointFromContextMenu: Обрабатывает удаление точек из контекстного меню.

    - selectPoints(self, rows): Выделяет точки с определенными данными.

    - removePoints(self, points): Удаляет список точек со сцены.

    - removePoint(self, point): Удаляет одну точку со сцены.

    - setPixmap(self, pixmap, factor=None): Устанавливает изображение на сцену и подгоняет под вид.

    - get_zoom(self): Получает текущий уровень масштабирования.

    - wheelEvent(self, event): Обрабатывает событие вращения колеса мыши для масштабирования.

    - mousePressEvent(self, event): Обрабатывает событие нажатия кнопки мыши.

    - mouseMoveEvent(self, event): Обрабатывает событие перемещения мыши.

    - mouseReleaseEvent(self, event): Обрабатывает событие отпускания кнопки мыши.

    - view_magnifier(self, pos): Отображает увеличенное изображение в магнифаере.

    - font: Свойство для получения/установки шрифта.

    - sizePoint: Свойство для получения/установки размера точек.

    - visibleTextPoint: Свойство для получения/установки видимости текста точек.
    """
    zoomDisplay = pyqtSignal(int)
    newPoint = pyqtSignal(QPoint)
    selectedPoints = pyqtSignal(list)
    deletePointsInParent = pyqtSignal()
    movePoint = pyqtSignal(PointItem)

    def __init__(self):
        super().__init__()
        self.initUI()

        self.photo = QGraphicsPixmapItem()

        self.scene = QGraphicsScene(self)
        self.scene.addItem(self.photo)
        self.setScene(self.scene)

        self.magnifier = Magnifier()

        self.zoom = 0

        # шрифт
        self._size_point: int = 10
        self._font: QFont = QFont("Arial", self.sizePoint, QFont.Normal)
        self._visibleTextPoint: bool = True

        # контейнер для хранения точек
        self.points: PointsList[PointItem] = PointsList()

        self.active_point = None

        # состояния
        self.isPanning = False
        self.isMagnifier = False
        self.isMousePressed = False
        self.isModeCreatePoints = True
        self.dragPos = QPoint()

    def initUI(self):

        # настройка интерфейса
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.setFrameShape(QFrame.NoFrame)

    def setSizePoint(self, size):
        self.sizePoint = size
        self.scene.update()

    def textPointsVisible(self, value: bool):
        self.visibleTextPoint = value
        self.scene.update()

    def changeColorPoint(self, text, color):
        for item in self.points:
            if item.text == text:
                item.color = color
        self.scene.update()

    def visiblePoint(self, text, value):
        for item in self.points:
            if item.text == text:
                item.setVisible(value)
        self.scene.update()

    def recalculateSceneRect(self):
        rect = QRectF(self.photo.pixmap().rect())
        self.setSceneRect(rect)

    def fitInView(self, rect=None, factor=None, flags=Qt.IgnoreAspectRatio):
        """
        Подгонка под view
        """
        if not rect:
            # получаем rectangle сцены
            rect = QRectF(self.photo.pixmap().rect())

        if not rect.isNull():
            self.setSceneRect(rect)
            if not factor:
                # вычисляем масштабирование
                unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())

                view_rect = self.viewport().rect()
                scene_rect = self.transform().mapRect(rect)
                factor = min(view_rect.width() / scene_rect.width(),
                             view_rect.height() / scene_rect.height())

            self.zoom = int(factor * 10)
            self.scale(factor, factor)

    def setPhoto(self, file_path, factor=None):
        self.scene_clear()

        # загружаем фото из файла
        pixmap = open_image_to_pixmap(file_path)

        # добавляем в сцену
        self.photo.setPixmap(pixmap)

        # обновляем вид
        self.fitInView(factor=factor)

    def clearAllRects(self):
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem):
                self.scene.removeItem(item)
        self.update()

    def drawRect(self, rect: QRectF):
        rectItem = QGraphicsRectItem(rect.x(), rect.y(), rect.width(), rect.height())
        pen = QPen(Qt.red)
        pen.setWidth(2)
        rectItem.setPen(pen)
        self.scene.addItem(rectItem)

    def scene_clear(self):
        self.removePoints(self.points.copy())
        self.setDragMode(QGraphicsView.NoDrag)
        self.photo.setPixmap(QPixmap())

    def addPoint(self, pos, text, data=None, tooltip=None, color=QColor('#FF0000')):

        point = PointItem(parent=self, text=text, color=color, size=self.sizePoint)
        point.setPos(pos)
        point.setToolTip(tooltip)
        point.textVisible = self.visibleTextPoint

        if data:
            point.setData(Qt.UserRole, data)

        self.scene.addItem(point)
        self.points.append(point)

    def removedPointFromContextMenu(self, point):
        self.selectedPoints.emit([point])
        self.deletePointsInParent.emit()

    def selectPoints(self, rows):
        self.scene.clearSelection()
        for data in rows:
            for point in self.points:
                if data == point.data(Qt.UserRole):
                    point.setSelected(True)

    def removePoints(self, points):
        for point in points:
            self.removePoint(point)

    def removePoint(self, point):
        if point in self.points:
            self.points.remove(point)
            self.scene.removeItem(point)

    def setPixmap(self, pixmap, factor=None):
        self.scene_clear()
        self.photo.setPixmap(pixmap)

        # обновляем вид
        self.fitInView(factor=factor)

    def get_zoom(self):
        rect = QRectF(self.photo.pixmap().rect())
        zoom = self.transform().mapRect(rect)
        if rect.isNull():
            res = 0
        else:
            res = int((zoom.width() / rect.width()) * 100)
        return res

    # обработка скролла мыши
    def wheelEvent(self, event):
        # угол прокрутки колёсика мыши
        angle = event.angleDelta().y()

        # увеличение масштаба
        if angle > 0:
            zoom_factor = ZOOM_IN_FACTOR
            self.zoom += 1

        # уменьшение
        else:
            zoom_factor = ZOOM_OUT_FACTOR
            self.zoom -= 1

        if self.zoom > 0:

            # масштабируем текущий вид
            self.scale(zoom_factor, zoom_factor)
        elif self.zoom <= 0:
            self.fitInView()
        else:
            self.zoom = 0

        self.zoomDisplay.emit(self.get_zoom())

    def mouseDoubleClickEvent(self, event):
        pass

    def mousePressEvent(self, event):
        self.dragPos = event.pos()

        if event.button() == Qt.RightButton:

            self.isMousePressed = True
            self.setCursor(Qt.ClosedHandCursor)
            if self.isPanning:
                self.dragPos = event.pos()
                event.accept()

        if event.button() == Qt.LeftButton:
            pos = event.pos()
            self.setCursor(Qt.ArrowCursor)
            point = self.mapToScene(pos).toPoint()
            if point.x() < 0 or point.y() < 0:
                return

            if self.isModeCreatePoints:
                self.selectedPoints.emit([])
                self.newPoint.emit(point)

            else:
                point = self.itemAt(pos)
                if isinstance(point, PointItem):
                    self.selectedPoints.emit([point])
                    self.active_point = point

        if event.button() == 4:
            if self.isMagnifier:
                self.isMagnifier = False
                self.magnifier.close()
                return

            self.isMagnifier = True
            self.isMousePressed = True
            self.isPanning = False
            self.view_magnifier(event.pos())

    def mouseMoveEvent(self, event):
        if self.active_point:
            if event.buttons() == Qt.LeftButton:
                diff = self.mapToScene(event.pos()).toPoint() - self.mapToScene(self.dragPos).toPoint()
                self.dragPos = event.pos()
                self.active_point.setPos(self.active_point.pos() + diff)
                event.accept()

        if self.isMagnifier:
            self.view_magnifier(event.pos())
        elif self.isMousePressed and self.isPanning and not self.isMagnifier:
            diff = event.pos() - self.dragPos
            self.dragPos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        elif self.isMousePressed:
            self.isPanning = True
        else:
            super(ImageViewer, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.active_point:
            data = self.active_point.data(Qt.UserRole)
            y = self.active_point.pos().y()
            x = self.active_point.pos().x()
            if (data.iTop, data.iLeft) != (
                    y, x) and self.photo.pixmap().height() >= y >= 0 and self.photo.pixmap().width() >= x >= 0:
                self.movePoint.emit(self.active_point)
            else:
                self.active_point.setPos(QPoint(data.iLeft, data.iTop))
            self.active_point = None
        if event.button() == 4:
            self.isMagnifier = False
            self.isMousePressed = False
            self.magnifier.photo.setPixmap(QPixmap())
            self.magnifier.close()
        if event.button() == Qt.RightButton:
            self.isPanning = False
            self.isMousePressed = False
            self.setCursor(Qt.ArrowCursor)
        super(ImageViewer, self).mouseReleaseEvent(event)

    def view_magnifier(self, pos):
        if not self.magnifier:
            return
        pos_map = self.mapToScene(pos).toPoint()
        self.magnifier.photo.setPixmap(self.photo.pixmap())
        self.magnifier.setSceneRect(pos_map.x() - 200, pos_map.y() - 200, self.magnifier.geometry().width(),
                                    self.magnifier.geometry().height())

        self.magnifier.centerOn(pos_map)

        if self.cursor().pos().y() + 400 > self.screen().geometry().height() and \
                self.cursor().pos().x() + 400 > self.screen().geometry().width():
            self.magnifier.setGeometry(self.cursor().pos().x() - 405, self.cursor().pos().y() - 405, 400, 400)

        elif self.cursor().pos().x() + 400 > self.screen().geometry().width():
            self.magnifier.setGeometry(self.cursor().pos().x() - 405, self.cursor().pos().y() + 5, 400, 400)

        elif self.cursor().pos().y() + 400 > self.screen().geometry().height():
            self.magnifier.setGeometry(self.cursor().pos().x() + 5, self.cursor().pos().y() - 405, 400, 400)

        else:
            self.magnifier.setGeometry(self.cursor().pos().x() + 5, self.cursor().pos().y() + 5, 400, 400)

        self.magnifier.show()

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        if self._font != value:
            self._font = value
            for item in self.points:
                item.setPointFont(value)

    @property
    def sizePoint(self):
        return self._size_point

    @sizePoint.setter
    def sizePoint(self, value):
        if self._size_point != value:
            self._size_point = value
            for item in self.points:
                item.setPointSize(value)

    @property
    def visibleTextPoint(self):
        return self._visibleTextPoint

    @visibleTextPoint.setter
    def visibleTextPoint(self, value):
        if self._visibleTextPoint != value:
            self._visibleTextPoint = value
            for item in self.points:
                item.textVisible = value


class PreviewImageViewer(ImageViewer):
    """

    Класс: PreviewImageViewer
    Этот класс является подклассом ImageViewer и предоставляет дополнительную функциональность, специфичную для
    предварительного просмотра изображений.
    Методы:
    - addPoint(pos, text, data=None, tooltip=None, color=None): Этот метод отображает изображение в указанной позиции.
    Принимает следующие параметры:
        - pos (tuple): Позиция точки на изображении.
        - text (str): Текст, который будет отображаться рядом с точкой.
        - data (любое): Дополнительные данные, связанные с точкой (необязательно).
        - tooltip (str): Дополнительный текст всплывающей подсказки, который будет отображаться при наведении на
        точку (необязательно). - color (str): Дополнительный цвет для точки (необязательно).
    - get_zoom(): Этот метод возвращает текущий уровень увеличения в просмотрщике изображений.

    """
    def __init__(self):
        super().__init__()

    def addPoint(self, pos, text, data=None, tooltip=None, color=None):
        pass

    def get_zoom(self):
        pass


class Magnifier(QGraphicsView):
    """
    Класс Magnifier является подклассом QGraphicsView и используется для отображения увеличенного изображения.
    Он предоставляет окно с функциональностью увеличения и скрывает полосы прокрутки.
    """
    def __init__(self):
        super(Magnifier, self).__init__()
        self.verticalScrollBar().setVisible(False)
        self.horizontalScrollBar().setVisible(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWindowFlag(Qt.FramelessWindowHint)

        self.scale(3, 3)
        self.scene = QGraphicsScene()
        self.photo = QGraphicsPixmapItem()
        self.scene.addItem(self.photo)
        self.setScene(self.scene)