from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication, QFontDialog

from app.services.user_settings import Settings

user_settings = Settings.instance()


def style_sheet(value):
    """
    Устанавливает таблицу стилей приложения.

    :param value: Значение таблицы стилей для установки. Должно быть либо 'Dark' (темное), либо 'Light' (светлое).
    :type value: str
    """
    QApplication.setStyle("Fusion")
    if value == 'Dark':

        #
        # # Now use a palette to switch to dark colors:
        dark_palette = QPalette()

        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))  #
        dark_palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))  #
        dark_palette.setColor(QPalette.Highlight, QColor(126, 71, 130))
        dark_palette.setColor(QPalette.HighlightedText, Qt.white)
        dark_palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
        dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, Qt.darkGray)
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, Qt.darkGray)
        dark_palette.setColor(QPalette.Disabled, QPalette.Light, QColor(53, 53, 53))
        QApplication.setPalette(dark_palette)

    elif value == 'Light':
        # QApplication.setStyle("Fusion")
        QApplication.setStyle('windowsvista')
        palette = QPalette()
        QApplication.setPalette(palette)
    else:
        pass

    user_settings.setValue("StyleSheet", value)


def set_font():
    """

    Устанавливает шрифт для приложения.

    Этот метод предлагает пользователю выбрать шрифт с помощью QFontDialog. Если пользователь выбирает шрифт,
    он устанавливает этот шрифт для QApplication и сохраняет выбранный шрифт в user_settings

    Returns:
        None

    """
    font, ok = QFontDialog.getFont()
    if ok:
        QApplication.setFont(font)
        user_settings.setValue("Font", font)
