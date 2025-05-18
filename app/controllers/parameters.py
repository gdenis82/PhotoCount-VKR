import os

from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QApplication

from app.controllers.items_file import ItemFile
from app.controllers.support_lists import LocalSitesList, CountTypesList, ObserversList, AnimalCategoriesList, \
    AnimalStatusList, AnimalNamesList, AnimalInfoList
from app.services.db_manager import SessionFactorySupport, SessionFactoryMain
from app.services.user_settings import Settings
from app.models.support_db import AnimalCategories, LocalSites, Observers, CountTypes, AnimalStatus, AnimalNames, \
    EffortTypes, AnimalInfo
from app.services.main_style import style_sheet

user_settings = Settings.instance()
session_factory_main = SessionFactoryMain()
session_factory_support = SessionFactorySupport()
support_session = session_factory_support.get_session()


class MainParams:
    """

    Этот класс хранит и управляет основными параметрами приложения.

    """

    def __init__(self):

        self._main_db_path: str = ''

        self._year: int = 0
        self._site: int = 0
        self._creator: str = ''
        self._species: str = ''
        self._current_mode: str = ''

        self._archive_animals_path: str = ''

        self.current_data = None

        self.model_directories = QStandardItemModel()

        self.done_files: list[str] = []
        self.photos_for_day: list[object] = []
        self.windows_list: list[object] = []

        self._support_categories_points: AnimalCategoriesList[AnimalCategories] = AnimalCategoriesList()
        self._support_local_sites: LocalSitesList[LocalSites] = LocalSitesList()
        self._support_animal_statuses: AnimalStatusList[AnimalStatus] = AnimalStatusList()
        self._support_animal_names: AnimalNamesList[AnimalNames] = AnimalNamesList(support_session.query(AnimalNames).all())
        self._support_animal_info: AnimalInfoList[AnimalInfo] = AnimalInfoList(support_session.query(AnimalInfo).all())
        self.support_observers: ObserversList[Observers] = ObserversList(support_session.query(Observers).all())
        self.support_count_type_id: CountTypesList[CountTypes] = CountTypesList(support_session.query(CountTypes).all())
        self.support_effort_type_id: list[EffortTypes] = support_session.query(EffortTypes).all()

        self.get_user_user_settings()

    def get_user_user_settings(self):
        """
        Получит пользовательские настройки для приложения.

        Метод проверяет, содержат ли пользовательские настройки определенные ключи, и присваивает соответствующие
        значения переменным экземпляра класса.
        - Устанавливает основной путь к базе данных, если ключ "FileDB" существует в пользовательских настройках.
        - Устанавливает год, сайт, создателя и вид, если существуют соответствующие ключи.
        - Применяет указанный лист стилей и шрифт, если существуют ключи "StyleSheet" и "Font".
        - Устанавливает путь к архиву животных, если существует ключ "ArchivePath".
        """
        if not user_settings:
            return

        if user_settings.contains("FileDB") and user_settings.value('FileDB'):
            file_db = user_settings.value('FileDB')
            if os.path.isfile(file_db):
                self.main_db_path = file_db

        if user_settings.contains("Year") and user_settings.value('Year'):
            self.year = user_settings.value('Year')
        if user_settings.contains("Site") and user_settings.value('Site'):
            self.site = user_settings.value('Site')
        if user_settings.contains("Observer") and user_settings.value('Observer'):
            self.creator = user_settings.value('Observer')
        if user_settings.contains("Species") and user_settings.value('Species'):
            self.species = user_settings.value('Species')

        if user_settings.contains("StyleSheet") and user_settings.value('StyleSheet'):
            style_sheet(str(user_settings.value('StyleSheet')))
        if user_settings.contains("Font") and user_settings.value('Font'):
            QApplication.setFont(user_settings.value('Font'))

        if user_settings.contains('ArchivePath') and user_settings.value('ArchivePath'):
            self.archive_animals_path = user_settings.value('ArchivePath')

    def reset_params(self):
        """
        Сбрасывает параметры текущего экземпляра.
        Этот метод сбрасывает следующие параметры текущего экземпляра:
        - current_data.
        - model_directories.
        - done_files.
        - photos_for_day.

        """
        self.current_data = None
        self.model_directories.clear()
        self.done_files.clear()
        self.photos_for_day.clear()

    # prop for path db
    @property
    def main_db_path(self):
        return self._main_db_path

    @main_db_path.setter
    def main_db_path(self, value):
        if self._main_db_path != value:
            self._main_db_path = value
            url = f'sqlite:///{value}'
            session_factory_main.connect_db(url)
            user_settings.setValue("FileDB", value)

    # prop year
    @property
    def year(self):
        return self._year

    @year.setter
    def year(self, value):
        if self._year != value:
            self._year = int(value)
            self.reset_params()
            user_settings.setValue("Year", value)

    # prop site
    @property
    def site(self):
        return self._site

    @site.setter
    def site(self, value):
        if self._site != value:
            self._site = int(value)
            self._support_local_sites = LocalSitesList(support_session.query(LocalSites).filter_by(site=value).all())
            user_settings.setValue("Site", value)
            self.reset_params()

    # prop observer
    @property
    def creator(self):
        return self._creator

    @creator.setter
    def creator(self, value):
        if self._creator != value:
            self._creator = value
            user_settings.setValue("Observer", value)

    # prop species
    @property
    def species(self):
        return self._species

    @species.setter
    def species(self, value):
        if self._species != value:
            self._species = value
            user_settings.setValue("Species", value)

            self.support_categories_points = support_session.query(AnimalCategories).filter_by(species=value).all()
            self.support_animal_statuses = AnimalStatusList(support_session.query(AnimalStatus).filter_by(species=value).all())
            self.support_animal_info = AnimalInfoList(support_session.query(AnimalInfo).filter_by(species=value).all())
            self.reset_params()

    # prop current_mode
    @property
    def current_mode(self):
        return self._current_mode

    @current_mode.setter
    def current_mode(self, value):
        if self._current_mode != value:
            self._current_mode = value
            self.reset_params()

    # prop для списка локальных участков лежбища
    @property
    def support_local_sites(self):
        return self._support_local_sites

    @support_local_sites.setter
    def support_local_sites(self, value):
        value.sort(key=lambda x: x.local_site_id)
        self._support_local_sites = value

    # prop для списка категорий точек учета
    @property
    def support_categories_points(self):
        return self._support_categories_points

    @support_categories_points.setter
    def support_categories_points(self, value):
        value.sort(key=lambda x: x.order)
        self._support_categories_points = value

    # prop для списка категорий статуса животных
    @property
    def support_animal_statuses(self):
        return self._support_animal_statuses

    @support_animal_statuses.setter
    def support_animal_statuses(self, value):
        value.sort(key=lambda x: x.sex_r and x.priority)
        value.reverse()
        self._support_animal_statuses = value

    @property
    def support_animal_info(self):
        return self._support_animal_info

    @support_animal_info.setter
    def support_animal_info(self, value):
        value.sort(key=lambda x: x.display_order)
        self._support_animal_info = value

    # prop для списка имен животных
    @property
    def support_animal_names(self):
        return self._support_animal_names

    @support_animal_names.setter
    def support_animal_names(self, value):
        self._support_animal_names = value

    # prop для адреса к архивным фотографиям
    @property
    def archive_animals_path(self):
        return self._archive_animals_path

    @archive_animals_path.setter
    def archive_animals_path(self, value):
        if self._archive_animals_path != value:
            self._archive_animals_path = value
            user_settings.setValue("ArchivePath", value)




