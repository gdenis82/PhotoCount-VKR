from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QModelIndex


class PandasTableModel(QtGui.QStandardItemModel):
    """

    PandasTableModel является подклассом QtGui.QStandardItemModel и предоставляет модель для отображения данных
    pandas DataFrame в представлении Qt.
    """
    def __init__(self, data, parent=None):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.__readonly_cols = []
        self._data = data

        for row in data.values.tolist():
            data_row = [QtGui.QStandardItem("{}".format(x)) for x in row]
            self.appendRow(data_row)
        return

    def rowCount(self, parent=None):
        return len(self._data.values)

    def columnCount(self, parent=None):
        return self._data.columns.size

    def headerData(self, x, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[x]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return self._data.index[x] + 1
        return None

    def flags(self, index: QModelIndex):
        if index.column() in self.__readonly_cols:
            return Qt.ItemIsEnabled
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def setReadOnly(self, columns: [int]):
        for i in columns:
            if i <= (self.columnCount() - 1) and i not in self.__readonly_cols:
                self.__readonly_cols.append(i)

    def resetReadOnly(self):
        self.__readonly_cols = []
