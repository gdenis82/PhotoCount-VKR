from PyQt5 import QtWidgets


def getOpenFilesAndDirs(parent=None, caption='', directory='', filter='', initialFilter='', options=None):
    """
    Этот метод открывает диалоговое окно выбора файлов для выбора нескольких файлов и каталогов.
    Параметры:
    - parent: (не обязательно) Родительский виджет для окна выбора файлов.
    - caption: (не обязательно) Заголовок окна выбора файла.
    - directory: (не обязательно) Стандартный каталог для открытия в диалоге файлов.
    - filter: (не обязательно) Фильтр файлов для ограничения типов файлов, отображаемых в диалоге файлов.
    - initialFilter: (не обязательно) Начальный фильтр файлов для выбора в диалоге файлов.
    - options: (не обязательно) Дополнительные параметры для диалога файлов.
    Возвращается:
    - Список выбранных путей файлов и каталогов.

    Пример использования:
    parent = QtWidgets.QWidget()
    caption = "Open Files and Directories"
    directory = "/path/to/dir"
    filter = "Images (*.png *.jpg);;Text Files (*.txt)"
    initialFilter = "Images (*.png *.jpg)"
    options = QtWidgets.QFileDialog.Option()
    selected_files = getOpenFilesAndDirs(parent, caption, directory, filter, initialFilter, options)
    print(selected_files)

    """
    def updateText():
        # обновить содержимое виджета редактирования строки выбранными файлами
        selected = []
        for index in view.selectionModel().selectedRows():
            selected.append('"{}"'.format(index.data()))
        lineEdit.setText(' '.join(selected))

    dialog = QtWidgets.QFileDialog(parent, windowTitle=caption)
    dialog.setFileMode(dialog.ExistingFiles)
    if options:
        dialog.setOptions(options)
    dialog.setOption(dialog.DontUseNativeDialog, True)  # !!!
    if directory:
        dialog.setDirectory(directory)
    if filter:
        dialog.setNameFilter(filter)
        if initialFilter:
            dialog.selectNameFilter(initialFilter)

    dialog.accept = lambda: QtWidgets.QDialog.accept(dialog)

    stackedWidget = dialog.findChild(QtWidgets.QStackedWidget)
    view = stackedWidget.findChild(QtWidgets.QListView)
    view.selectionModel().selectionChanged.connect(updateText)

    lineEdit = dialog.findChild(QtWidgets.QLineEdit)
    # очищаем содержимое строки редактирования всякий раз, когда изменяется текущий каталог
    dialog.directoryEntered.connect(lambda: lineEdit.setText(''))

    dialog.exec_()
    return dialog.selectedFiles()