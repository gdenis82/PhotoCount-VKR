from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QStandardItem, QFontMetrics, QPalette
from PyQt5.QtWidgets import qApp, QStyledItemDelegate, QComboBox


class CheckableComboBox(QComboBox):
    """
    Класс CheckableComboBox является подклассом QComboBox, который позволяет пользователю выбрать несколько элементов из
    выпадающего списка. Выбранные элементы отображаются в виде текста, разделенного запятыми, в комбобоксе.

    Этот класс переопределяет некоторые методы из QComboBox, чтобы добавить пользовательское поведение:
    - метод __init__() инициализирует CheckableComboBox и настраивает начальное состояние комбобокса.
    Он добавляет элемент "All" в выпадающий список и делает комбобокс редактируемым, но только для чтения.
    Также он устанавливает пользовательскому делегату действия с элементами в списке и соединяет сигнал dataChanged
    модели с методом updateText. - метод clear_items() очищает все элементы в комбобоксе и обновляет отображаемый текст.
     - метод resizeEvent() вызывается при изменении размера комбобокса. Он пересчитывает текст для отображения с
     учетом многоточия.
     - метод eventFilter() фильтрует события для поля редактирования и области просмотра выпадающего списка.
     Он обрабатывает события отпускания кнопки мыши для поля редактирования, для показа/скрытия всплывающего окна,
     и отпускания кнопки мыши для области просмотра, чтобы переключить состояние выбора элементов в списке.
     - метод showPopup() показывает всплывающее окно и устанавливает флаг для закрытия всплывающего окна
     при щелчке по полю редактирования. - метод hidePopup() скрывает всплывающее окно, запускает таймер,
     чтобы предотвратить немедленное повторное открытие всплывающего окна при нажатии на поле редактирования,
     и обновляет отображаемый текст. - метод timerEvent() вызывается, когда срок действия таймера для скрытия
     всплывающего окна истекает. Он останавливает таймер и сбрасывает флаг, чтобы закрыть всплывающее окно при щелчке по
      полю редактирования. - метод updateText() обновляет текст отображения комбобокса на основе выбранных элементов.
      - метод addItem() добавляет элемент в выпадающий список с указанным текстом и данными.
      Если данные не предоставлены, используется текст. - метод addItems() добавляет несколько элементов в выпадающий
      список с указанными текстами и необязательным даталистом.
      - метод currentData() возвращает список данных выбранных элементов.
      - метод itemChecked() возвращает True, если элемент с указанным индексом проверен, иначе False.
      - метод itemSetChecked() устанавливает состояние проверки для элемента с заданным индексом как выбрано.
      - метод itemUnChecked() устанавливает состояние проверки для элемента с заданным индексом как не выбрано.
      - метод itemCheckedCount() возвращает количество выбранных элементов в выпадающем списке.
      - метод itemsIsChecked() возвращает список выбранных элементов в выпадающем списке.
      - метод itemsCheckedIndexes() возвращает список индексов выбранных элементов в выпадающем списке.
      - метод all_selected() обрабатывает выбор элемента "All" и соответственно обновляет отображаемый текст,
      значение комбобокса и подсказку.
    """

    class Delegate(QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(20)
            return size

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.addItem("All")
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        palette = qApp.palette()
        palette.setBrush(QPalette.Base, palette.button())
        self.lineEdit().setPalette(palette)

        self.setItemDelegate(CheckableComboBox.Delegate())
        self.model().dataChanged.connect(self.updateText)
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False
        self.view().viewport().installEventFilter(self)

    def clear_items(self):
        self.clear()
        self.updateText()

    def resizeEvent(self, event):
        self.updateText()
        super().resizeEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.lineEdit():
            if event.type() == QEvent.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if obj == self.view().viewport():
            if event.type() == QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().item(index.row())

                if item.checkState() == Qt.Checked:
                    if item.text() == 'All':
                        for i in range(self.count()):
                            self.itemUnChecked(i)
                    else:
                        item.setCheckState(Qt.Unchecked)
                        if len(self.currentData()) != self.model().rowCount():
                            self.model().item(self.findText('All')).setCheckState(Qt.Unchecked)
                else:

                    if item.text() == 'All':
                        for i in range(self.count()):
                            self.itemSetChecked(i)
                    else:
                        item.setCheckState(Qt.Checked)
                        if len(self.currentData()) == self.model().rowCount() - 1:
                            if self.model().item(self.findText('All')).checkState() == Qt.Unchecked:
                                self.model().item(self.findText('All')).setCheckState(Qt.Checked)
                return True
        return False

    def showPopup(self):
        super().showPopup()
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        self.startTimer(100)
        self.updateText()

    def timerEvent(self, event):
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self):
        texts = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.Checked:
                texts.append(self.model().item(i).text())

        text = ", ".join(texts)

        metrics = QFontMetrics(self.lineEdit().font())
        elidedText = metrics.elidedText(text, Qt.ElideRight, self.lineEdit().width())
        self.lineEdit().setText(elidedText)

    def addItem(self, text, data=None):
        item = QStandardItem()
        item.setText(text)
        if data is None:
            item.setData(text, Qt.UserRole)
        else:
            item.setData(data, Qt.UserRole)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData(Qt.Unchecked, Qt.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts, datalist=None):
        for i, text in enumerate(texts):
            try:
                data = datalist[i]
            except (TypeError, IndexError):
                data = None
            self.addItem(text, data)

    def currentData(self, role=Qt.UserRole):
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.Checked:
                res.append(self.model().item(i).data())
        return res

    def itemChecked(self, index):
        item = self.model().item(index, 0)
        if not item:
            return
        return item.checkState() == Qt.Checked

    def itemSetChecked(self, index):
        item = self.model().item(index, 0)
        if not item:
            return
        return item.setCheckState(Qt.Checked)

    def itemUnChecked(self, index):
        item = self.model().item(index, 0)
        if not item:
            return
        return item.setCheckState(Qt.Unchecked)

    def itemCheckedCount(self):
        count = []
        for index in range(self.model().rowCount()):
            item = self.model().item(index, 0)
            if item.checkState() == Qt.Checked:
                count.append(item)
        return count

    def itemsIsChecked(self):
        items = []
        for index in range(self.model().rowCount()):
            item = self.model().item(index, 0)
            if item.checkState() == Qt.Checked:
                items.append(item)
        return items

    def itemsCheckedIndexes(self):
        indexes = []
        for index in range(self.model().rowCount()):
            item = self.model().item(index, 0)
            if item.checkState() == Qt.Checked:
                indexes.append(index)
        return indexes

    def all_selected(self, value):

        for index in range(self.count()):
            if value == self.itemText(index):
                if self.itemChecked(index):
                    self.itemUnChecked(index)
                    for i in range(self.count()):
                        if self.itemText(i) == "All":
                            self.itemUnChecked(i)
                else:
                    self.itemSetChecked(index)
                    c = 0
                    for i in range(self.count()):
                        if self.itemChecked(i):
                            c += 1
                    if c == self.count() - 1 and c > 1:
                        for i in range(self.count()):
                            if self.itemText(i) == "All":
                                self.itemSetChecked(i)
                if value == "All":
                    if self.itemChecked(index):
                        for i in range(self.count()):
                            self.itemSetChecked(i)
                    else:
                        for i in range(self.count()):
                            self.itemUnChecked(i)
                break
        string = ''
        many_items = self.itemsCheckedIndexes()
        for i in self.itemCheckedCount():
            string = string + '{0}, '.format(i.text())
        if many_items and 'All' in string.split(','):
            string = 'All'
            self.setCurrentText(string)
        elif len(many_items) > 1:
            self.setCurrentText("Many")
        else:
            index_item = self.itemsCheckedIndexes()
            if index_item:
                self.setCurrentIndex(index_item[0])
        self.setToolTip(string)
        if not string:
            self.setCurrentIndex(-1)
