import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal as Signal
from PyQt5.QtGui import QKeySequence, QPixmap
from PyQt5.QtWidgets import QShortcut, QDialog, QMessageBox, QFileDialog

from app import m_params, PATTERN_SUFFIX
from app.dialogs.confirmation_location_dialog import ConfirmationLocationDialog
from app.custom_widgets.image_viewer import PreviewImageViewer
from app.models.main_db import Resight, Daily, Location, AnimalInfo
from app.models.model_registration_animal import ModelRegistrationAnimal
from app.services.helpers import makeDatecreated
from app.controllers.parameters import session_factory_main
from app.view.ui_window_animal_registration import Ui_RegistrationWindow


class AnimalRegistration(QtWidgets.QMainWindow):
    """
    Модуль идентификации меток животных
    """
    result = Signal(ModelRegistrationAnimal)

    def __init__(self):
        super().__init__()
        self.onlyRead = False
        self.iLeft = -1
        self.iTop = -1
        self.file_name = None
        self.main_session = session_factory_main.get_session()

        self.ui = Ui_RegistrationWindow()
        self.ui.setupUi(self)
        self.show()

        self.view = PreviewImageViewer()
        self.ui.imageLayout.addWidget(self.view, 0, 0, 1, 1)

        self.currentAnimalName = None
        self.isSmallSize: bool = True

        self.currentImageIndex: int = 0
        self.filteredBrand: list[str] = []
        self.pathsImages: list[str] = []
        self.animalNames: list[str] = []

        self.locationDialog: Optional[ConfirmationLocationDialog] = None

        self.setMinimumWidth(200)
        self.setMaximumWidth(200)
        self.ui.groupBox_right.setVisible(False)
        self.ui.btn_Save.setEnabled(False)

        self.ui.dateEdit.dateChanged.connect(self.date_changed)

        self.ui.cmb_AnimalName.activated[str].connect(self.selected_animal_name)
        self.ui.cmb_AnimalName.editTextChanged.connect(self.edit_animal_name)
        self.ui.list_AnimalNames.itemClicked.connect(self.selected_list_name)
        self.ui.list_AnimalNames.itemActivated.connect(self.selected_list_name)
        self.ui.btn_Ok.clicked.connect(self.clicked_ok)
        self.ui.btn_select_dir.clicked.connect(self.select_archive)

        self.ui.cmb_StatusPhoto.activated[str].connect(self.selected_status_photo)
        self.ui.line_BrandQuality.textEdited[str].connect(self.edit_brand_quality)
        self.ui.btn_Save.clicked.connect(self.clicked_save)

        self.shortcut_ctrl_enter = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self.shortcut_ctrl_enter.activated.connect(self.clicked_save)
        self.shortcut_ctrl_return = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_ctrl_return.activated.connect(self.clicked_save)

        self.shortcut_alt_enter = QShortcut(QKeySequence("Alt+Enter"), self)
        self.shortcut_alt_enter.activated.connect(self.substitution_status)
        self.shortcut_alt_return = QShortcut(QKeySequence("Alt+Return"), self)
        self.shortcut_alt_return.activated.connect(self.substitution_status)

        self.shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        self.shortcut_esc.activated.connect(self.close)

        self.ui.cmb_StatusPhoto.editTextChanged[str].connect(self.edit_status_photo)
        self.ui.cmb_LocalSite.editTextChanged[str].connect(self.edit_local_site)
        self.ui.btn_Unknown.clicked.connect(self.clicked_unknown)
        self.ui.btn_previous.clicked.connect(self.previous_image)
        self.ui.btn_next.clicked.connect(self.next_image)

        self.ui.btn_search_brand.clicked.connect(self.search_brand)
        self.ui.btn_reset_search.clicked.connect(self.fill_pos_search)
        self.ui.list_result_search_brand.itemClicked.connect(self.selected_search_name)

        self.fill_animals_names()
        self.fill_local_sites(m_params.support_local_sites)
        self.fill_date_edit()
        self.fill_sex_and_status()
        self.set_current_animal_name()

        self.ui.label_path_archive.setText(f"Archive: {m_params.archive_animals_path}")

    def fill_date_edit(self):
        """
        Установить дату
        """
        self.ui.dateEdit.setDisplayFormat("yyyy-MM-dd")
        d_time = datetime.now()
        if m_params.current_data:
            if m_params.current_mode == 'Location':
                date = str(m_params.current_data)
            elif m_params.current_mode == 'Count':
                date = str(m_params.current_data.r_date)
            d_time = datetime.now().replace(int(date[0:4]), int(date[4:6]), int(date[6:8]))
            self.ui.dateEdit.setEnabled(False)
        else:

            d_time = datetime.now().replace(m_params.year, d_time.month, d_time.day)
            self.ui.dateEdit.setEnabled(True)

        self.ui.dateEdit.setDate(d_time)

    def fill_animals_names(self):
        """
        Заполняет список животных
        """

        for item in m_params.support_animal_names:
            if m_params.year >= int(str(item.t_date)[0:4]):
                if item.t_date:
                    r_year = str(item.t_date)[0:4]
                    age = m_params.year - int(r_year)
                else:
                    r_year = 'NA'
                    age = 'NA'
                r_sex = item.t_sex
                if r_year == 'NA' or m_params.year >= int(r_year):
                    self.animalNames.append(f"{item.animal_name} {r_sex} {r_year} {age}")
                    self.ui.cmb_AnimalName.addItem(str(item.animal_name))

        if self.ui.list_AnimalNames.count():
            self.ui.list_AnimalNames.clear()
        if not self.isSmallSize:
            self.ui.list_AnimalNames.addItems(self.animalNames)

    def fill_pos_search(self):
        """
        Заполняем списки pos для поиска животного
        """
        self.ui.list_result_search_brand.clear()
        self.filteredBrand.clear()
        self.ui.label_total_search_brand.setText(f"Total result: {len(self.filteredBrand)}")

        p = ["*", "#"]
        self.ui.cmb_pos1.clear()
        self.ui.cmb_pos2.clear()
        self.ui.cmb_pos3.clear()
        self.ui.cmb_pos4.clear()
        self.ui.cmb_pos5.clear()

        pos1 = list(map(lambda x: x.pos1, m_params.support_animal_names))
        pos1 = list(set(pos1))
        pos1.sort()
        pos2 = list(map(lambda x: x.pos2, m_params.support_animal_names))
        pos2 = list(set(pos2))
        pos2.sort()
        pos3 = list(map(lambda x: x.pos3, m_params.support_animal_names))
        pos3 = list(set(pos3))
        pos3.sort()
        pos4 = list(map(lambda x: x.pos4, m_params.support_animal_names))
        pos4 = list(set(pos4))
        pos4.sort()
        pos5 = list(map(lambda x: x.pos5, m_params.support_animal_names))
        pos5 = list(set(pos5))
        pos5.sort()

        for item in p:
            pos1.insert(1, item)
            pos2.insert(1, item)
            pos3.insert(1, item)
            pos4.insert(1, item)
            pos5.insert(1, item)

        self.ui.cmb_pos1.addItems(pos1)
        self.ui.cmb_pos2.addItems(pos2)
        self.ui.cmb_pos3.addItems(pos3)
        self.ui.cmb_pos4.addItems(pos4)
        self.ui.cmb_pos5.addItems(pos5)

    def fill_local_sites(self, local_sites):
        """
        Заполнить список локальных участков
        """
        count = 0
        for item in local_sites:
            self.ui.cmb_LocalSite.addItem(item.local_site_name)
            self.ui.cmb_LocalSite.setItemData(count, item.local_site_id, Qt.ToolTipRole)
            count += 1
        self.ui.cmb_LocalSite.setCurrentIndex(-1)

    def fill_sex_and_status(self):
        """
        Заполнить списки пола и статуса животных
        """
        sex_r = []
        count = 0
        for item in m_params.support_animal_statuses:
            self.ui.cmb_StatusPhoto.addItem(f"{item.status}")
            self.ui.cmb_StatusPhoto.setItemData(count, item.description, Qt.ToolTipRole)
            sex_r.append(item.sex_r)
            count += 1

        s = set(sex_r)
        sex_r.clear()

        for i in s:
            sex_r.append(i)
        sex_r.sort()

        self.ui.cmb_Gender.addItems(sex_r)
        self.ui.cmb_Gender.setCurrentIndex(-1)
        self.ui.cmb_StatusPhoto.setCurrentIndex(-1)

    def date_changed(self):
        """
        Событие при изменении даты
        """
        if self.ui.cmb_AnimalName.currentText():
            self.ui.line_BrandQuality.setText("")
            self.ui.text_StatusResight.setText("")
            self.ui.cmb_Gender.setCurrentIndex(-1)
            self.ui.text_StatusDaily.setText("")
            self.ui.cmb_LocalSite.setCurrentIndex(-1)

            self.get_animal_resight(self.ui.cmb_AnimalName.currentText())
            self.get_animal_daily(self.ui.cmb_AnimalName.currentText())

    def edit_brand_quality(self, text):
        """

        Изменить качество бренда на основе введенного текста.
        Проверяет вводимые символы, допустимы только ['+', '-', '$', '0']

        """
        brand = []
        brand_length = self.brand_length()
        for ch in text:
            if ch in ['+', '-', '$', '0']:
                brand.append(ch)
                if len(brand) >= brand_length:
                    self.ui.line_BrandQuality.setText(text[0:brand_length])
                    self.ui.cmb_StatusPhoto.setEnabled(True)
                else:
                    self.ui.btn_Save.setEnabled(False)
                    self.ui.cmb_StatusPhoto.setEnabled(False)
            else:
                self.ui.line_BrandQuality.setText(text[0:-1])

    def edit_animal_name(self, text):
        """
        Событие при изменении имени животного
        """
        self.scene_clear()
        self.pathsImages.clear()
        self.ui.statusbar.showMessage("")
        self.ui.label_coun_img.setText("")
        self.ui.label_verified.setText("")
        self.ui.text_StatusDaily.setText("")
        self.ui.text_StatusResight.setText("")
        self.ui.line_BrandQuality.setText("")
        self.ui.btn_Ok.setEnabled(False)
        self.ui.btn_Save.setEnabled(False)
        self.ui.cmb_StatusPhoto.setCurrentIndex(-1)
        self.ui.cmb_Gender.setCurrentIndex(-1)
        self.ui.cmb_LocalSite.setCurrentIndex(-1)
        self.ui.text_Comment.setPlainText("")
        self.ui.text_Comment.setEnabled(True)
        self.ui.line_BrandQuality.setEnabled(False)
        self.ui.cmb_StatusPhoto.setEnabled(False)
        self.ui.list_AnimalNames.setCurrentRow(-1)
        self.ui.cmb_AnimalName.setFocus()

    def edit_status_photo(self, text):
        """
        Ввод статуса животного. Проверка введенного статуса с доступными в списке статусов.
        """
        if text != "":
            for item in m_params.support_animal_statuses:
                if str(text).lower() == str(item.status).lower():
                    self.ui.cmb_Gender.setEnabled(True)
                    self.ui.cmb_StatusPhoto.setCurrentIndex(self.ui.cmb_StatusPhoto.findText(item.status))
                    self.ui.cmb_Gender.setCurrentText(item.sex_r)
                    self.ui.cmb_LocalSite.setEnabled(True)
                    return
                else:
                    self.ui.cmb_Gender.setCurrentIndex(-1)

        self.ui.cmb_Gender.setCurrentIndex(-1)
        self.ui.cmb_Gender.setEnabled(False)
        self.ui.cmb_LocalSite.setEnabled(False)

    def edit_local_site(self, text):
        """
        Ввод локального участка. Проверка введенного участка с доступными в списке.
        """
        for item in m_params.support_local_sites:
            if text == item.local_site_name:
                self.ui.text_Comment.setEnabled(True)
                self.ui.btn_Save.setEnabled(True)
                return
        self.ui.text_Comment.setEnabled(True)
        self.ui.btn_Save.setEnabled(False)

    def brand_length(self):
        """
        Проверяет длину имени метки.
        Удаляет все символы, которые являются 'r' или 'а', из текущего текста в cmb_AnimalName,
        а затем возвращает длину оставшегося текста.
        """
        text = self.ui.cmb_AnimalName.currentText()
        brand_len = 0
        for ch in text:
            if ch not in ['r', 'a']:
                brand_len += 1
        return brand_len - 1

    def check_name(self, name):
        """
        Проверяет, соответствует ли предоставленное имя метки любому из имен животных, хранящихся в списке.
        """
        self.currentAnimalName = ''

        for item in self.animalNames:
            if str(item).split(' ')[0].lower() == name.lower():
                self.currentAnimalName = str(item).split(' ')[0]
                return True

        self.ui.btn_Ok.setEnabled(False)
        return False

    def set_current_animal_name(self):
        """
        Выбрать имя животного в списке
        """
        if self.currentAnimalName:
            if self.check_name(self.currentAnimalName):
                self.ui.cmb_AnimalName.setCurrentText(self.currentAnimalName)
                self.ui.line_BrandQuality.setEnabled(True)
            else:
                self.ui.cmb_AnimalName.setCurrentIndex(-1)

            self.ui.cmb_AnimalName.setFocus()
            self.get_animal_resight(self.currentAnimalName)
            self.get_animal_daily(self.currentAnimalName)
        else:
            self.ui.cmb_AnimalName.setCurrentIndex(-1)
            self.ui.cmb_AnimalName.setFocus()

    def get_animal_resight(self, name):
        """
        Получить resight регистрацию животного
        """
        try:
            resight = self.main_session.query(Resight).filter_by(r_year=m_params.year,
                                                                 site=m_params.site, animal_name=name).first()
            if resight:
                self.ui.line_BrandQuality.setText(resight.brand_quality)
                self.ui.text_StatusResight.setText(resight.status)
                self.ui.cmb_Gender.setCurrentText(resight.sex_r)
                self.ui.cmb_StatusPhoto.setEnabled(True)
                self.ui.cmb_StatusPhoto.setFocus()
            else:
                self.ui.line_BrandQuality.setText("")
                self.ui.text_StatusResight.setText("")
                self.ui.cmb_Gender.setCurrentIndex(-1)
        except Exception as ex:
            print(ex)

    def get_animal_daily(self, name):
        """
        Получить регистрацию daily
        """
        try:
            daily = self.main_session.query(Daily).filter_by(r_year=m_params.year,
                                                             site=m_params.site,
                                                             r_date=self.ui.dateEdit.text().replace('-', ''),
                                                             animal_name=name).first()

            if daily:
                self.ui.text_StatusDaily.setText(daily.status)
                self.ui.cmb_LocalSite.setCurrentIndex(
                    self.ui.cmb_LocalSite.findData(str(daily.local_site), Qt.ToolTipRole, Qt.MatchFixedString))
                self.ui.text_Comment.setText(daily.comments)
            else:
                self.ui.text_StatusDaily.setText("")
                self.ui.cmb_LocalSite.setCurrentIndex(-1)
                self.ui.text_Comment.setText("")
        except Exception as ex:
            print(ex)

    def keyPressEvent(self, e):
        """

        Этот метод вызывается при нажатии клавиши в приложении.
        Он проверяет, какая клавиша была нажата, и выполняет различные действия в зависимости от клавиши.
        Если нажата клавиша Enter или Return, он проверяет, имеют ли кнопки с фокусом btn_Save или btn_Ok,
        и вызывает соответствующие методы clicked_save() или clicked_ok().
        Если приложение находится в режиме малого размера, он меняет размер и видимость определенных элементов
        в пользовательском интерфейсе.
        Если приложение не находится в режиме малого размера, он устанавливает фокус на btn_Ok.
        Он также обновляет список имен животных и обрабатывает выбор имени животного.
        """
        if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
            if self.ui.btn_Save.hasFocus():
                self.clicked_save()
                return
            elif self.ui.btn_Ok.hasFocus():
                self.clicked_ok()
                return
            elif self.isSmallSize:
                self.isSmallSize = False
                self.setMinimumWidth(800)
                self.setMaximumWidth(1500000)
                self.ui.groupBox_right.setVisible(True)
                self.ui.btn_Ok.setEnabled(True)

                self.fill_pos_search()
                self.get_images(self.ui.cmb_AnimalName.currentText())
            else:
                self.ui.btn_Ok.setFocus()
                return
            if len(self.ui.list_AnimalNames) <= 0:
                self.ui.list_AnimalNames.addItems(self.animalNames)
            if self.check_name(self.ui.cmb_AnimalName.currentText()):
                self.ui.list_AnimalNames.setCurrentRow(self.ui.cmb_AnimalName.currentIndex())
                self.ui.line_BrandQuality.setEnabled(True)
                self.ui.btn_Ok.setFocus()
            else:
                self.ui.line_BrandQuality.setEnabled(False)
                self.ui.list_AnimalNames.setCurrentRow(-1)

    def search_brand(self):
        """
        Поиск животного по известным знакам
        """
        self.ui.list_result_search_brand.clear()
        self.filteredBrand = []

        filtered_pos1_animals = self.filter_animals_based_on_ui('pos1', m_params.support_animal_names)
        filtered_pos2_animals = self.filter_animals_based_on_ui('pos2', filtered_pos1_animals)
        filtered_pos3_animals = self.filter_animals_based_on_ui('pos3', filtered_pos2_animals)
        filtered_pos4_animals = self.filter_animals_based_on_ui('pos4', filtered_pos3_animals)
        filtered_pos5_animals = self.filter_animals_based_on_ui('pos5', filtered_pos4_animals)

        for animal in filtered_pos5_animals:
            age, registration_year = self.calculate_animal_age_and_registration_year(animal)
            if age == 'NA' or age >= 0:
                self.filteredBrand.append(f"{animal.animal_name} {animal.t_sex} {registration_year} {age}")
        self.ui.list_result_search_brand.addItems(self.filteredBrand)
        self.ui.label_total_search_brand.setText(f"Total result: {len(self.filteredBrand)}")

    def filter_animals_based_on_ui(self, pos, animals):
        """

        Фильтровать животных на основе выбранного варианта из ниспадающего списка пользовательского интерфейса
        поиска меток.
        """
        ui_combo = getattr(self.ui, f'cmb_{pos}')
        ui_combo_text = ui_combo.currentText()

        if ui_combo_text == "#":
            return list(filter(lambda x: str(getattr(x, pos)).isdigit() and getattr(x, pos), animals))
        elif ui_combo_text == "*":
            return list(filter(lambda x: not str(getattr(x, pos)).isdigit() and getattr(x, pos), animals))
        elif ui_combo_text != "#" and ui_combo_text != "*" and ui_combo.currentIndex():
            return list(filter(lambda x: str(getattr(x, pos)) == ui_combo_text and getattr(x, pos), animals))
        elif not ui_combo.currentIndex():
            return animals

    def calculate_animal_age_and_registration_year(self, animal):
        """
        Вычисляет возраст и год регистрации животного.
        """
        age = 'NA'
        registration_year = 'NA'
        if animal.t_date:
            registration_year = str(animal.t_date)[0:4]
            age = int(m_params.year) - int(registration_year)
        return age, registration_year

    def selected_search_name(self, item):
        """
        Находит соответствующее имя в списке имен животных и выбирает его.
        """
        name = self.ui.list_AnimalNames.findItems(item.text(), Qt.MatchExactly)
        if name:
            index = self.ui.list_AnimalNames.indexFromItem(name[0]).row()
            self.ui.list_AnimalNames.setCurrentRow(index)
            self.selected_list_name(name[0])

    def substitution_status(self):
        if self.ui.cmb_StatusPhoto.currentText() == "":
            self.ui.cmb_StatusPhoto.setCurrentText(self.ui.text_StatusDaily.text())
            self.selected_status_photo(self.ui.text_StatusDaily.text())
            self.ui.cmb_StatusPhoto.setEnabled(True)
        else:
            return

    def selected_status_photo(self, text):
        """
        Этот метод используется для установки текущего пола и фокусировки комбо-бокса локального участка и
        кнопки сохранения в пользовательском интерфейсе если введенный статус есть в списке статусов.
        """
        for item in m_params.support_animal_statuses:
            if item.status == text:
                self.ui.cmb_Gender.setCurrentText(item.sex_r)
                self.ui.cmb_LocalSite.setFocus()
                self.ui.btn_Save.setFocus()
                break

    def selected_animal_name(self, name=None):
        """
        Устанавливает выбранное имя животного в пользовательском интерфейсе и выполняет проверку метки.
        """
        if self.check_name(self.ui.cmb_AnimalName.currentText()):
            self.ui.list_AnimalNames.setCurrentRow(self.ui.cmb_AnimalName.currentIndex())
            self.ui.line_BrandQuality.setEnabled(True)
            self.get_animal_resight(self.ui.cmb_AnimalName.currentText())
            self.get_animal_daily(self.ui.cmb_AnimalName.currentText())

            if not self.isSmallSize:
                self.get_images(self.ui.cmb_AnimalName.currentText())
        else:
            self.ui.line_BrandQuality.setEnabled(False)

    def selected_list_name(self, name):
        """
        Устанавливает выбранный элемент в комбинированном поле для имен животных и обновляет изображения,
        повторные данные и ежедневные данные, относящиеся к выбранному животному.
        """
        name = str(name.text()).split(' ')[0]
        self.ui.cmb_AnimalName.setCurrentText(name)
        self.get_images(name)
        self.get_animal_resight(name)
        self.get_animal_daily(name)
        self.ui.btn_Ok.setEnabled(True)

    def select_archive(self):
        """
        Выбирает архивный каталог с помощью диалогового окна выбора файла.
        """
        dialog = QFileDialog(self, 'Select Archive')
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        if dialog.exec_() == QDialog.Accepted:
            self.scene_clear()
            m_params.archive_animals_path = dialog.selectedFiles()[0]
            self.ui.label_path_archive.setText(f"Archive: {m_params.archive_animals_path}")
            if self.ui.cmb_AnimalName.currentText():
                self.get_images(self.ui.cmb_AnimalName.currentText())

    @staticmethod
    def rename_folder_archive():
        """
        Переименует папки в архивном каталоге за год B_2017.
        P.S. Исправляет ошибку при формировании архива.
        """
        archive_path = m_params.archive_animals_path
        directory = os.path.join(archive_path, "B_2017")
        if os.path.exists(directory):
            for dirs, folder, files in os.walk(directory):
                for f in folder:
                    if str(f)[-1] != 'L':
                        os.rename(os.path.join(archive_path, "B_2017", f),
                                  os.path.join(archive_path, "B_2017", f + "L"))
                break

    def get_images(self, animal_name):
        """

        Этот метод извлекает пути к изображениям на основе данного animal_name из архива фотографий меток

        """
        try:
            self.view.setToolTip('')
            self.ui.label_name_file.setText('')

            self.rename_folder_archive()
            if '>' in animal_name:
                animal_name = animal_name.replace('>', '^')
            self.ui.label_verified.setText("")
            self.ui.label_coun_img.setText("")
            self.pathsImages.clear()
            directory = "{0}".format(m_params.archive_animals_path)

            if os.path.exists(directory):
                for (root, dirs, files) in os.walk(directory, topdown=True):
                    for item in dirs:
                        for (_, s_dirs, _) in os.walk(os.path.join(root, item), topdown=True):
                            res_search = list(filter(lambda x: str(x) == animal_name, s_dirs))

                            for res in res_search:
                                [self.pathsImages.append(os.path.join(root, item, res, f)) for f in
                                 Path(os.path.join(root, item, res)).glob('*') if
                                 f.suffix.lower() in PATTERN_SUFFIX]
                            break
                    break

            self.currentImageIndex = 0
            self.scene_clear()
            if len(self.pathsImages) > 0:
                self.load_image(self.pathsImages[self.currentImageIndex])

        except Exception as ex:
            print(ex)

    def scene_clear(self):
        """
        Очищает QGraphicsPixmap от изображения.
        """
        self.view.scene_clear()
        self.view.setPixmap(QPixmap())

    def load_image(self, path_image):
        """
        Загрузить изображение метки по указанному пути и отобразить его в пользовательском интерфейсе.
        """
        self.scene_clear()

        if not path_image:
            return
        self.ui.label_name_file.setText(Path(path_image).name)
        self.view.setToolTip(path_image)

        self.ui.label_verified.setText("")
        if str(path_image).find('not_verified') > -1:
            self.ui.label_verified.setText("not verified")
        else:
            self.ui.label_verified.setText("verified")

        pixMap = QtGui.QPixmap(path_image)
        self.view.setPixmap(pixMap)

        self.ui.label_coun_img.setText(f"{len(self.pathsImages)} / {self.currentImageIndex + 1}")

    def previous_image(self):
        """
        Перейти к предыдущему изображению.
        """
        if not self.pathsImages:
            return
        if self.currentImageIndex > 0:
            self.currentImageIndex -= 1
            self.load_image(self.pathsImages[self.currentImageIndex])
        elif self.currentImageIndex == 0:
            self.currentImageIndex = len(self.pathsImages) - 1
            self.load_image(self.pathsImages[self.currentImageIndex])

    def next_image(self):
        """

        Перейти к следующему изображению.

        """
        if not self.pathsImages:
            return
        if self.currentImageIndex < len(self.pathsImages) - 1:
            self.currentImageIndex += 1
            self.load_image(self.pathsImages[self.currentImageIndex])
        elif self.currentImageIndex == len(self.pathsImages) - 1:
            self.currentImageIndex = 0
            self.load_image(self.pathsImages[0])

    def check_fill_fields(self):
        """
        Проверяет, заполнены ли все необходимые поля.
        """
        if len(self.ui.line_BrandQuality.text()) != self.brand_length():
            self.ui.line_BrandQuality.setFocus()
            return False
        elif self.ui.dateEdit.date().year() != m_params.year:
            self.ui.dateEdit.setEnabled(True)
            self.ui.dateEdit.setFocus()
            return False
        elif self.ui.cmb_StatusPhoto.currentText() == "":
            self.ui.cmb_StatusPhoto.setEnabled(True)
            self.ui.cmb_StatusPhoto.setFocus()
            return False
        elif self.ui.cmb_StatusPhoto.currentIndex() > -1:
            self.selected_status_photo(self.ui.cmb_StatusPhoto.currentText())
            if self.ui.cmb_LocalSite.currentText() == "":
                self.ui.cmb_LocalSite.setFocus()
                return False
        elif self.ui.cmb_Gender.currentText() == "":
            self.ui.cmb_Gender.setEnabled(True)
            self.ui.cmb_Gender.setFocus()
            return False
        elif self.ui.cmb_LocalSite.currentText() == "":
            self.ui.cmb_LocalSite.setFocus()
            return False

        self.ui.btn_Save.setEnabled(True)
        self.ui.btn_Save.setFocus()

        return True

    def clicked_unknown(self):
        """
        Нажата регистрация неизвестного животного.

        Создает новый экземпляр ModelRegistrationAnimal и устанавливает его свойства на основе параметров в m_params
        и пользовательского ввода из пользовательского интерфейса.
        """
        registration = ModelRegistrationAnimal()
        registration.species = m_params.species
        registration.year = m_params.year
        registration.site = m_params.site
        registration.date = int(self.ui.dateEdit.text().replace('-', ''))
        registration.animal_name = 'UNK'
        registration.brand_quality = 'UNK'
        registration.local_site = 'U'
        registration.animal_status = 'U'
        registration.sex = 'U'
        registration.type_photo = ''
        registration.status_confirmation = 'U'
        registration.comment = self.ui.text_Comment.toPlainText()

        self.handle_input_registration(registration)

    def clicked_ok(self):
        """
        Метод для обработки события нажатия кнопки "ОК".

        Этот метод вызывается при нажатии кнопки "OK". Он скрывает правую группу, устанавливает минимальную и
        максимальную ширину объекта равной 200, устанавливает флаг "isSmallSize" в значение True, а затем вызывает
        метод "check_fill_fields".
        """
        self.ui.groupBox_right.setVisible(False)
        self.setMinimumWidth(200)
        self.setMaximumWidth(200)
        self.isSmallSize = True
        self.check_fill_fields()

    def clicked_save(self):
        """
        Метод для обработки события нажатия кнопки сохранения.

        Используется для обработки события нажатия кнопки сохранения.
        В общих чертах, этот метод выполняет следующие действия:
        Проверяет, заполнены ли все необходимые поля, используя метод check_fill_fields().
        Если поля не заполнены или включен режим "только для чтения", метод возвращает управление.
        Проверяет, совпадает ли год, указанный на пользовательском интерфейсе, с годом в m_params.
        Если они не совпадают, выводится предупреждающее сообщение.
        Получает пол животного из таблицы пересмотра и ежедневной таблицы, и проверяет, соответствуют ли они полу,
        указанному на пользовательском интерфейсе. Если они не совпадают, выводится сообщение.
        Вызывает диалоговое окно ConfirmationLocationDialog для получения подтверждения от пользователя.
        Создает экземпляр ModelRegistrationAnimal, устанавливает его свойства на основе параметров в m_params и
        пользовательского ввода, и затем передает его в метод handle_input_registration() для
        обработки ввода регистрации.
        Важно отметить, что любые изменения данных в этом методе несут временный характер и
        сохраняются только в текущем сеансе.
        """
        if not self.check_fill_fields() or self.onlyRead:
            if self.onlyRead:
                QMessageBox.information(self, 'Message', f"Only read mode!")
            return

        sex_res = None
        sex_daily = None

        if m_params.year != self.ui.dateEdit.date().year():
            QMessageBox.warning(self, 'Message', "Please checked filled the year!",
                                QMessageBox.Ok, QMessageBox.Ok)
            return

        if self.ui.text_StatusResight.text():
            sex_res = m_params.support_animal_statuses.itemFromName(self.ui.text_StatusResight.text()).sex_r
        if self.ui.text_StatusDaily.text():
            sex_daily = m_params.support_animal_statuses.itemFromName(self.ui.text_StatusDaily.text()).sex_r

        if sex_res and sex_res != self.ui.cmb_Gender.currentText():
            QMessageBox.information(self, 'Message',
                                    f"Please checked filled the gender! Gender in table resight '{sex_res}'.")

            return
        else:
            if sex_daily and sex_daily != self.ui.cmb_Gender.currentText():
                QMessageBox.information(self, 'Message',
                                        f"Please checked filled the gender! Gender in table daily '{sex_daily}'.")
                return

            count_best_photos = self.main_session.query(Location).filter_by(r_year=m_params.year,
                                                                            site=m_params.site,
                                                                            animal_name=self.ui.cmb_AnimalName.currentText()
                                                                            ).all()

            self.locationDialog = ConfirmationLocationDialog(len(count_best_photos))
            self.locationDialog.show()

            if self.locationDialog.exec() == QDialog.Accepted:
                registration = ModelRegistrationAnimal()
                registration.species = m_params.species
                registration.year = m_params.year
                registration.site = m_params.site
                registration.date = int(self.ui.dateEdit.text().replace('-', ''))
                registration.animal_name = self.ui.cmb_AnimalName.currentText()
                registration.brand_quality = self.ui.line_BrandQuality.text()
                registration.local_site = self.ui.cmb_LocalSite.itemData(self.ui.cmb_LocalSite.currentIndex(),
                                                                         Qt.ToolTipRole)
                registration.animal_status = self.ui.cmb_StatusPhoto.currentText()
                registration.sex = self.ui.cmb_Gender.currentText()
                registration.type_photo = "BestPhoto" if self.locationDialog.isBestPhoto else ''
                registration.status_confirmation = self.locationDialog.status
                registration.comment = self.ui.text_Comment.toPlainText()

                self.handle_input_registration(registration)

    """ Обработка результата ввода данных в форме регистрации"""
    def handle_input_registration(self, reg: ModelRegistrationAnimal):
        """

        Этот метод отвечает за обработку регистрации ввода данных о животном.
        Он выполняет операции на основе предоставленных данных о регистрации.

        Метод выполняет следующие шаги:

        Устанавливает атрибуты observer, iLeft, iTop и file_name объекта reg на основе соответствующих атрибутов
        вызывающего экземпляра.
        Если атрибут file_name вызывающего экземпляра не пуст, извлекает time_start из file_name и
        устанавливает его в объекте reg.
        Инициализирует переменные priority_status_photo, priority_status_resight и priority_status_daily как целые числа
         со значением по умолчанию 0.
        Проверяет, зарегистрировано ли заданное животное для указанной фотографии.
        Если да, отображает информационное сообщение и завершает выполнение.
        Запрашивает таблицы Resight и Daily базы данных для указанного года, места, имени животного и вида.
        Если найдена запись resight, и animal_name не равно "UNK", обновляет атрибут brand_quality записи resight на
        основе предоставленных данных о регистрации.
        Устанавливает переменную priority_status_photo на основе приоритетного значения animal_status
        в m_params support_animal_statuses.
        Устанавливает переменную priority_status_resight на основе приоритетного значения атрибута status записи resight.
        Если animal_status равно 'D' или 'DL', устанавливает priority_status_photo в 10.
        Если priority_status_photo больше priority_status_resight, обновляет атрибуты status, sex_r и
        dateupdated записи resight в базе данных.
        Если найдена запись daily, устанавливает переменную priority_status_daily на основе приоритетного значения
        атрибута status записи daily.
        Если priority_status_photo больше priority_status_daily, обновляет атрибуты status, local_site,
        comments и dateupdated записи daily в базе данных.
        Если запись daily не найдена, создает новую строку в таблице Daily с предоставленными данными о регистрации.
        Если запись resight не найдена, создает новую строку в таблице Resight с предоставленными данными о регистрации.
        Если запись daily не найдена, создает новую строку в таблице Daily с предоставленными данными о регистрации.
        Если атрибут file_name вызывающего экземпляра не пуст, создает новую строку в таблице Location с
        предоставленными данными о регистрации.
        Если animal_name не равно "UNK", обновляет записи animal_info в таблице AnimalInfo на основе animal_status и sex.
        Генерирует сигнал result с объектом reg и закрывает текущий экземпляр.

        Примечание:
        Этот метод предполагает наличие следующих переменных и классов: m_params, QMessageBox, Location, Resight, Daily, AnimalInfo, makeDatecreated.
        Этот метод предполагает наличие следующих методов в вызывающем экземпляре: new_row_daily, new_row_resight, new_row_location, new_animal_info.
        Этот метод предполагает наличие следующих атрибутов в вызывающем экземпляре: iLeft, iTop, file_name.
        """
        reg.observer = m_params.creator
        reg.iLeft = self.iLeft
        reg.iTop = self.iTop
        reg.file_name = self.file_name
        if self.file_name:
            reg.time_start = str(reg.file_name).split('_')[1]

        priority_status_photo: int = 0
        priority_status_resight: int = 0
        priority_status_daily: int = 0

        if reg.animal_name != "UNK" and reg.file_name:
            location_points = self.main_session.query(Location).filter_by(r_year=reg.year, site=reg.site,
                                                                          animal_name=reg.animal_name,
                                                                          species=reg.species,
                                                                          file_name=reg.file_name,
                                                                          ).first()
            if location_points:
                QMessageBox.information(self, "Info!", f"This animal {reg.animal_name} is registered in this is photo!")
                return

        resight = self.main_session.query(Resight).filter_by(r_year=reg.year, site=reg.site,
                                                             animal_name=reg.animal_name,
                                                             species=reg.species, ).first()
        daily = self.main_session.query(Daily).filter_by(r_year=reg.year, site=reg.site, r_date=reg.date,
                                                         animal_name=reg.animal_name,
                                                         species=reg.species, ).first()

        if resight and reg.animal_name != "UNK":
            resight.brand_quality = reg.brand_quality

            support_status_photo = m_params.support_animal_statuses.itemFromName(reg.animal_status)
            if support_status_photo:
                priority_status_photo = support_status_photo.priority

            support_status_resight = m_params.support_animal_statuses.itemFromName(resight.status)
            if support_status_resight:
                priority_status_resight = support_status_resight.priority

            if reg.animal_status == 'D' or reg.animal_status == 'DL':
                priority_status_photo = 10

            if priority_status_photo > priority_status_resight:
                resight.status = reg.animal_status
                resight.sex_r = reg.sex
                resight.dateupdated = makeDatecreated()
                self.main_session.commit()

            if daily:
                support_status_daily = m_params.support_animal_statuses.itemFromName(daily.status)
                if support_status_daily:
                    priority_status_daily = support_status_daily.priority

                if priority_status_photo > priority_status_daily:
                    daily.status = reg.animal_status

                daily.local_site = reg.local_site
                daily.comments = reg.comment
                daily.dateupdated = makeDatecreated()

                self.main_session.commit()

            else:
                self.new_row_daily(reg)
        elif not resight:
            self.new_row_resight(reg)
            self.new_row_daily(reg)
        elif not daily:
            self.new_row_daily(reg)

        if reg.file_name:
            # Запись в Location
            location = self.new_row_location(reg)
            reg.location = location

        if reg.animal_name != "UNK":
            animal_st = reg.animal_status
            if animal_st == "NP" or animal_st == "NJNP" or animal_st == "NJ" and reg.sex == "F":
                animal_info_np = self.main_session.query(AnimalInfo).filter_by(r_year=reg.year, site=reg.site,
                                                                               animal_name=reg.animal_name,
                                                                               info_type='NursingPup',
                                                                               species=reg.species,
                                                                               ).first()

                animal_info_nj = self.main_session.query(AnimalInfo).filter_by(r_year=reg.year, site=reg.site,
                                                                               animal_name=reg.animal_name,
                                                                               info_type='NursingJuvenile',
                                                                               species=reg.species,
                                                                               ).first()

                if animal_st == "NP" or animal_st == "NJNP":
                    if animal_info_np:
                        animal_info_np.info_value = "Yes"
                        animal_info_np.dateupdated = makeDatecreated()
                    else:
                        self.new_animal_info(reg, 'NursingPup', "Yes")

                if animal_st == "NJ" or animal_st == "NJNP":
                    if animal_info_nj:
                        animal_info_nj.info_value = "Yes"
                        animal_info_nj.dateupdated = makeDatecreated()
                    else:
                        self.new_animal_info(reg, 'NursingJuvenile', "Yes")
            self.main_session.commit()

        self.result.emit(reg)
        self.close()

    def new_row_daily(self, reg: ModelRegistrationAnimal):
        """
        Создает новую строку в ежедневной таблице с предоставленной информацией о регистрации.
        """
        daily = Daily(species=reg.species,
                      r_year=reg.year,
                      site=reg.site,
                      animal_name=reg.animal_name,
                      r_date=reg.date,
                      status=reg.animal_status,
                      local_site=reg.local_site,
                      comments=reg.comment,
                      observer=reg.observer,
                      datecreated=makeDatecreated())
        self.main_session.add(daily)
        self.main_session.commit()

    def new_row_resight(self, reg: ModelRegistrationAnimal):
        """

        Этот метод добавляет новую строку в таблицу Resight в базе данных на
        основе предоставленного объекта ModelRegistrationAnimal.

        """
        resight = Resight(species=reg.species,
                          r_year=reg.year,
                          site=reg.site,
                          animal_name=reg.animal_name,
                          brand_quality=reg.brand_quality,
                          sex_r=reg.sex,
                          status=reg.animal_status,
                          comments=reg.comment,
                          datecreated=makeDatecreated())

        self.main_session.add(resight)
        self.main_session.commit()

    def new_row_location(self, reg: ModelRegistrationAnimal):
        """
        Вставляет новую строку в таблицу 'Location' с предоставленными регистрационными данными.
        """
        location = Location(
            species=reg.species,
            r_year=reg.year,
            site=reg.site,
            animal_name=reg.animal_name,
            r_date=reg.date,
            time_start=reg.time_start,
            local_site=reg.local_site,
            animal_type=reg.animal_status,
            iLeft=reg.iLeft,
            iTop=reg.iTop,
            observer=reg.observer,
            file_name=reg.file_name,
            type_photo=reg.type_photo,
            is_prediction_point=reg.is_prediction_point,
            datecreated=makeDatecreated(),
        )
        self.main_session.add(location)
        self.main_session.commit()

        return location

    def new_animal_info(self, reg: ModelRegistrationAnimal, a_type, data):
        """
        Добавляет новую информацию о животном в базу данных.
        """
        animal_info = AnimalInfo(
            species=reg.species,
            r_year=reg.year,
            site=reg.site,
            animal_name=reg.animal_name,
            info_type=a_type,
            info_value=data,
            observer=reg.observer,
            datecreated=makeDatecreated(),
        )
        self.main_session.add(animal_info)
        self.main_session.commit()
