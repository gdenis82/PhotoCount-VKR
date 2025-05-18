from PyQt5.QtCore import Qt

from app.controllers.items_point import PointItem
from app.models.support_db import LocalSites, CountTypes, Observers, AnimalCategories, AnimalStatus, AnimalNames, \
    AnimalInfo, Sites, Species


class SitesList(list[Sites]):
    """

    Класс SitesList
    Подкласс списка, который представляет собой список объектов Sites.
    Методы:
    - itemFromId(self, id_site: int) -> Sites or None: Возвращает объект Sites с указанным id_site,
    если он существует в списке. Если id_site не найден, возвращает None.
    - itemFromName(self, name_site: str) -> Sites or None: Возвращает объект Sites с указанным name_site,
    если он существует в списке. Если name_site не найден, возвращает None.

    """

    def itemFromId(self, id_site: int):
        try:
            result = next(x for x in self if x.site == id_site)
        except StopIteration:
            result = None
        return result

    def itemFromName(self, name_site: str):
        try:
            result = next(x for x in self if x.site_name == name_site)
        except StopIteration:
            result = None
        return result


class LocalSitesList(list[LocalSites]):
    """
    Класс LocalSitesList является подклассом встроенного класса list и содержит коллекцию объектов LocalSites.
    Он предоставляет методы для извлечения объектов LocalSites на основе различных критериев.
    Методы:
    - `itemFromName(name: str) -> LocalSites или None`: Возвращает объект `LocalSites` с указанным `name`.
    Если соответствующий объект не найден, возвращает `None`.
    - `itemFromId(id_name: str) -> LocalSites или None`: Возвращает объект `LocalSites` с указанным `id_name`.
    Если соответствующий объект не найден, возвращает `None`.
    - `itemFromNameOrId(value: str) -> LocalSites или None`: Возвращает объект `LocalSites` с указанным `value`,
    который может быть либо `name`, либо `id_name`. Если соответствующий объект * не найден, возвращает `None`.
    - `itemFromNameOrIdAndSite(nameOrId: str, site: int) -> LocalSites или None`: Возвращает объект `LocalSites` с
    указанным `nameOrId` и `site`. Параметр `nameOrId` может быть либо * `name`, либо `id_name`.
    Если соответствующий объект не найден, возвращает `None`.
    """

    def itemFromName(self, name: str):
        try:
            result = next(x for x in self if x.local_site_name == name)
        except StopIteration:
            result = None
        return result

    def itemFromId(self, id_name: str):
        try:
            result = next(x for x in self if x.local_site_id == id_name)
        except StopIteration:
            result = None
        return result

    def itemFromNameOrId(self, value: str):
        try:
            result = next(x for x in self if x.local_site_id == value or x.local_site_name == value)
        except StopIteration:
            result = None
        return result

    def itemFromNameOrIdAndSite(self, nameOrId: str, site: int):
        try:
            result = next(
                x for x in self if (x.local_site_id == nameOrId or x.local_site_name == nameOrId) and x.site == site)
        except StopIteration:
            result = None

        return result


class CountTypesList(list[CountTypes]):
    """
    Класс CountTypesList
    Подкласс встроенного класса list, который представляет собой список объектов CountTypes.
    Методы:
    - itemFromName(name: str) -> CountTypes или None: Возвращает первый объект CountTypes в списке,
    описание которого соответствует данному имени. Если совпадение не найдено, возвращает None.
    - itemFromId(id_name: str) -> CountTypes или None: Возвращает первый объект CountTypes в списке,
    type_id которого соответствует данному id_name. Если совпадение не найдено, возвращает None.

    """

    def itemFromName(self, name: str):
        try:
            result = next(x for x in self if x.description == name)
        except StopIteration:
            result = None
        return result

    def itemFromId(self, id_name: str):
        try:
            result = next(x for x in self if x.type_id == id_name)
        except StopIteration:
            result = None
        return result


class ObserversList(list[Observers]):
    """
    Класс ObserversList является подклассом встроенного класса list в Python.
    Он представляет собой список объектов Observers, которые предполагается имеют свойства 'observer_name' и 'observer'.
    Методы:
    - itemFromName(name: str) -> Observers или None: Возвращает первый объект Observers в списке,
    свойство 'observer_name' которого соответствует указанному параметру name.
    Если соответствующий объект не найден, возвращает None.
    - itemFromId(id_name: str) -> Observers или None: Возвращает первый объект Observers в списке,
    свойство 'observer' которого соответствует указанному параметру id_name. Если соответствующий объект не найден,
    возвращает None.
    """

    def itemFromName(self, name: str):
        try:
            result = next(x for x in self if x.observer_name == name)
        except StopIteration:
            result = None
        return result

    def itemFromId(self, id_name: str):
        try:
            result = next(x for x in self if x.observer == id_name)
        except StopIteration:
            result = None
        return result


class AnimalCategoriesList(list[AnimalCategories]):
    """
    Класс, представляющий список объектов AnimalCategories.
    Методы: - itemFromName(name: str): Возвращает первый объект AnimalCategories в списке с указанным именем.
    Если объект не найден, возвращает None.
    """

    def itemFromName(self, name: str):
        try:
            result = next(x for x in self if x.animal_category == name)
        except StopIteration:
            result = None
        return result


class AnimalStatusList(list[AnimalStatus]):
    """
    Класс, представляющий список объектов AnimalStatus. Наследуется от встроенного класса list.
    Методы:
    - itemFromName(name: str) -> Опциональный[AnimalStatus]: Возвращает первый объект AnimalStatus в списке,
    у которого атрибут `status` совпадает с указанным `name`. Если нет объекта с совпадающим именем, возвращает `None`.
    """

    def itemFromName(self, name: str):
        try:
            result = next(x for x in self if x.status == name)
        except StopIteration:
            result = None
        return result


class AnimalNamesList(list[AnimalNames]):
    """
    Класс, представляющий список имен животных.
    Класс AnimalNamesList расширяет встроенный класс list для хранения объектов типа AnimalNames.
    Методы:
    - itemFromName(name: str) -> Опциональный[AnimalNames]: Возвращает первый экземпляр AnimalNames в списке,
    который соответствует данному имени. Если совпадение не найдено, возвращается None.
    """

    def itemFromName(self, name: str):
        try:
            result = next(x for x in self if x.animal_name == name)
        except StopIteration:
            result = None
        return result


class AnimalInfoList(list[AnimalInfo]):
    """
    Класс AnimalInfoList предоставляет реализацию списка, специально разработанную для хранения и
    манипулирования объектами AnimalInfo.
    Методы:
    - itemFromId(infoId: str) -> Опциональный[AnimalInfo]: Этот метод возвращает объект AnimalInfo из списка,
    который имеет соответствующий infoId. Если соответствующий объект не найден, он возвращает None.
    - itemsFromSex(sex_name: str) -> Список[AnimalInfo]: Этот метод возвращает список объектов AnimalInfo из списка,
    которые имеют указанный sex_name. Если соответствующие объекты не найдены, возвращается пустой список.
    """

    def itemFromId(self, infoId: str):
        try:
            result = next(x for x in self if str(x.info_id).lower() == infoId.lower())
        except StopIteration:
            result = None
        return result

    def itemsFromSex(self, sex_name: str):
        result = []
        try:
            result = list(filter(lambda x: str(x.applicable_sex).lower() == sex_name.lower(), self))
        except Exception:
            result = []
        finally:
            return result


class SpeciesList(list[Species]):
    """
    Класс для представления списка видов животных.
    Наследуется от встроенного класса list и указывает, что элементы в списке имеют тип Species.
    Методы:
     - itemFromNameOrId(nameOrId: str) -> Опциональный[Species] Извлекает первый вид в списке,
     который соответствует данному имени или идентификатору.

    """

    def itemFromNameOrId(self, nameOrId: str):

        try:
            result = next(
                x for x in self if (x.species.lower() == nameOrId.lower() or
                                    x.species_name.lower() == nameOrId.lower()))
        except StopIteration:
            result = None

        return result


class PointsList(list[PointItem]):
    """
    Класс, представляющий список объектов PointItem.
    Этот класс расширяет встроенный класс list, чтобы предоставить дополнительную функциональность
    для работы с объектами PointItem.
    Методы: - itemFromData(data: object) -> PointItem: Возвращает объект PointItem из списка,
    который имеет указанные данные.
    """

    def itemFromData(self, data: object) -> PointItem:
        try:
            result = next(x for x in self if x.data(Qt.UserRole) == data)
        except StopIteration:
            result = None
        return result
