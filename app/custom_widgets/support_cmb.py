from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox, QCompleter


class CustomQComboBox(QComboBox):
    """
    Пользовательская реализация виджета QComboBox с дополнительной функциональностью.
    """
    def __init__(self, scrollWidget=None, *args, **kwargs):
        super(CustomQComboBox, self).__init__(*args, **kwargs)
        self.scrollWidget = scrollWidget
        self.setFocusPolicy(Qt.ClickFocus)

    def wheelEvent(self, *args, **kwargs):
        if self.hasFocus():
            return
        else:
            return


class SupportQComboBox(QComboBox):
    """
    Подкласс QComboBox, предоставляющий дополнительную функциональность для обработки задач,
    связанных с системными данными.
    """
    def __init__(self, scrollWidget=None, *args, **kwargs):
        super(SupportQComboBox, self).__init__(*args, **kwargs)
        self.scrollWidget = scrollWidget
        self.setFocusPolicy(Qt.ClickFocus)
        self.setEditable(True)
        self.completer().setCompletionMode(QCompleter.PopupCompletion)

    def select_data(self, value):
        for i in range(self.count()):
            data = self.itemData(i, Qt.UserRole)
            if value == data:
                self.setCurrentIndex(i)
                break

    def wheelEvent(self, *args, **kwargs):
        if self.hasFocus():
            return
        else:
            return
