import os
import sys
from datetime import datetime

import cv2
from pathlib import Path

from PyQt5 import QtGui
from PyQt5.QtCore import QDir, Qt
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QFileSystemModel

from app import COUNT_FOLDERS, LOCATION_FOLDERS, PATTERN_SUFFIX, m_params


def select_project_folders(param):
    """
    Выбор директории расположения фотографий по параметрам
    """

    model = QFileSystemModel()
    model.setFilter(QDir.AllDirs | QDir.NoDot | QDir.AllEntries)
    drivers = []
    for drive in model.rootDirectory().drives():
        drivers.append(drive.path())

    item_list = []

    for d in drivers:

        for t_folder in COUNT_FOLDERS if param.current_mode == 'Count' else LOCATION_FOLDERS:
            _dir = None
            if sys.platform == "linux" or sys.platform == "linux2":
                _dir = os.path.join(d, f"{param.species.upper()}_DB/{param.year,}_{param.site}_{t_folder}")

            elif sys.platform == "win32":
                _dir = f"{d}{param.species.upper()}_DB/{param.year}_{param.site}_{t_folder}"

            if os.path.exists(_dir):
                item_list.append((_dir, _dir.split('/')))

    return item_list


def check_pattern_suffixes(item):
    """
    Проверяет расширение файлов на наличие в списке паттерна
    """
    suf = Path(item).suffix.lower()
    if suf in PATTERN_SUFFIX:
        return True
    return False


def open_image_to_pixmap(path):
    """
    Открывает изображение и помещает его в QPixmap
    """
    if not check_pattern_suffixes(path):
        return QtGui.QPixmap()

    image = cv2.imread(path)  # загружает изображение из файла path с помощью OpenCV
    size = image.shape  # получаем размер изображения
    step = image.size / size[0]  # вычисляем шаг строки в байтах (смещение между строками в памяти)
    qformat = QImage.Format_Indexed8  # для grayscale изображений

    # Определяем формат QImage на основе числа каналов
    if len(size) == 3:
        if size[2] == 4:
            qformat = QImage.Format_RGBA8888  # для изображений RGBA
        else:
            qformat = QImage.Format_RGB888  # для изображений RGB

    # Создаем QImage, передавая ему данные из OpenCV изображения и преобразуем из BGR порядка в RGB.
    img = QImage(image, size[1], size[0], step, qformat).rgbSwapped()
    return QtGui.QPixmap.fromImage(img)


def makeDatecreated():
    """
    Создает отформатированную строку с текущей датой и временем, а также именем создателя.
    Возвращает: Строку, представляющую отформатированную дату и имя создателя.

    """
    return f"{str(datetime.now()).split('.')[0]} {m_params.creator}"


def search_path_photo(name_photo):
    """
    Ищет путь к фотографии на основе ее имени

    Parameters:
    - name_photo (str): Имя фотографии

    Returns:
    - str: Путь к фотографии, если она найдена, или None, если фотография не найдена.
    """
    date = name_photo[0:8]
    items = m_params.model_directories.findItems(date, Qt.MatchFixedString | Qt.MatchRecursive)
    if items:
        for item in items:
            parent = m_params.model_directories.parent(item.index())
            path = os.path.join(parent.data(), date, name_photo)
            folder = str(parent.data()).split('_')[-1]

            if os.path.exists(path):
                return path
    return None
