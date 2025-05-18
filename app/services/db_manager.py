
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.models.main_db import Base


class SessionFactoryMain:
    """
    Фабрика подключения к файлу хранения данных
    Если нет url базы, подключение будет выполнено в оперативной памяти
    """
    def __init__(self, db_url=None):
        if not db_url:
            db_url = f'sqlite:///:memory:'
        self.engine = create_engine(db_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def get_session(self):
        """
        Вернет сессию
        """
        return self.Session

    def connect_db(self, db_url):
        """
        Подключение к бд
        """
        self.engine = create_engine(db_url)
        self._make_session()

    def create_db(self, db_url):
        """
        Создание таблиц базы
        """
        self.engine = create_engine(db_url)
        Base.metadata.create_all(bind=self.engine)
        self._make_session()

    def _make_session(self):
        """
        Создаст сессию
        """
        self.Session = scoped_session(sessionmaker(bind=self.engine))


class SessionFactorySupport:
    """
    Фабрика подключения к системному дата-файлу
    """
    def __init__(self):
        db_url = f'sqlite:///support_base.sqlite'
        self.engine = create_engine(db_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def get_session(self):
        return self.Session()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
