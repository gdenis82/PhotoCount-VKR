from pathlib import Path

from app.models.main_db import CountFiles
from app.models.support_db import CountTypes


class ItemFile:
    """
    Этот класс представляет файл директории.

    """
    def __init__(self, path: str = "", fileName: str = ""):
        self.path = path
        self.fileName = fileName

    def asPath(self):
        return Path(self.path)


class ItemFileCount(ItemFile):
    """
    Класс ItemFileCount является подклассом класса ItemFile.
    Он представляет элемент файлов учета с дополнительными свойствами для типа учета и данных файла.

    """
    def __init__(self, path: str = "", fileName: str = "", countType: CountTypes = CountTypes,
                 data: CountFiles = CountFiles):
        super().__init__(path, fileName)
        self.path = path
        self.fileName = fileName
        self.countType = countType
        self.fileData = data

    def asPath(self):
        return Path(self.path)
