from PyQt5.QtCore import QSettings


class Settings:
    """
    Класс для доступа к настройкам приложения.
    Этот класс предоставляет одиночный экземпляр, который позволяет получать доступ к настройкам приложения через QSettings.
    """
    _instance = None

    def __init__(self):
        if Settings._instance is None:
            Settings._instance = QSettings("config.ini", QSettings.IniFormat)
        else:
            raise Exception("Settings is a singleton!")

    @staticmethod
    def instance():
        if Settings._instance is None:
            Settings()
        return Settings._instance
