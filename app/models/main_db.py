import sqlalchemy as db
from pyinstaller_versionfile.exceptions import ValidationError
from sqlalchemy import ForeignKeyConstraint, DDL, event

from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()  # базовый класс для декларативных моделей


class SurveyEffort(Base):
    __tablename__ = "survey_effort"

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    comments = db.Column(db.Text, default=None)

    count_list = relationship("CountList", back_populates="survey_effort", cascade="all, delete-orphan")
    resight_table = relationship("Resight", back_populates="survey_effort", cascade="all, delete-orphan")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class CountList(Base):
    __tablename__ = "count_list"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'species'],
            ['survey_effort.r_year', 'survey_effort.site', 'survey_effort.species'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    creator = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    comments = db.Column(db.Text, default=None)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    effort_types = relationship("CountEffortTypes", back_populates="count_list", cascade="all, delete-orphan")
    survey_effort = relationship("SurveyEffort", back_populates="count_list")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class CountEffortTypes(Base):
    __tablename__ = "count_effort_types"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'r_date', 'time_start', 'creator', 'species'],
            ['count_list.r_year', 'count_list.site', 'count_list.r_date',
             'count_list.time_start', 'count_list.creator', 'count_list.species'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String, primary_key=True, nullable=False)
    creator = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)
    count_type = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    comments = db.Column(db.Text, default=None)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    effort_sites = relationship("CountEffortSites", back_populates="effort_types", cascade="all, delete-orphan")
    effort_categories = relationship("CountEffortCategories", back_populates="effort_types",
                                     cascade="all, delete-orphan")

    count_files = relationship("CountFiles", back_populates="effort_types", cascade="all, delete-orphan")
    count_list = relationship("CountList", back_populates="effort_types")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class CountEffortSites(Base):
    __tablename__ = "count_effort_sites"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'r_date', 'time_start', 'creator', 'species', 'count_type'],
            ['count_effort_types.r_year', 'count_effort_types.site', 'count_effort_types.r_date',
             'count_effort_types.time_start', 'count_effort_types.creator', 'count_effort_types.species',
             'count_effort_types.count_type'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String, primary_key=True, nullable=False)
    creator = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)
    local_site = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    comments = db.Column(db.Text, default=None)
    visibility = db.Column(db.String(collation='NOCASE'), nullable=False)
    rain = db.Column(db.String(collation='NOCASE'), nullable=False)
    distance = db.Column(db.String(collation='NOCASE'), nullable=False)
    splash = db.Column(db.String(collation='NOCASE'), nullable=False)
    quality = db.Column(db.String(collation='NOCASE'), nullable=False)
    count_type = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    count_performed = db.Column(db.Boolean, nullable=False, default=False)
    coverage = db.Column(db.Integer, nullable=False, default=0)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    effort_types = relationship("CountEffortTypes", back_populates="effort_sites")


    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class CountEffortCategories(Base):
    __tablename__ = "count_effort_categories"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'r_date', 'time_start', 'creator', 'species', 'count_type'],
            ['count_effort_types.r_year', 'count_effort_types.site', 'count_effort_types.r_date',
             'count_effort_types.time_start', 'count_effort_types.creator', 'count_effort_types.species',
             'count_effort_types.count_type'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String, primary_key=True, nullable=False)
    creator = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    animal_category = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    count_type = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    effort_types = relationship("CountEffortTypes", back_populates="effort_categories")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class CountFiles(Base):
    __tablename__ = "count_source"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'r_date', 'time_start', 'creator', 'species', 'count_type'],
            ['count_effort_types.r_year', 'count_effort_types.site', 'count_effort_types.r_date',
             'count_effort_types.time_start', 'count_effort_types.creator', 'count_effort_types.species',
             'count_effort_types.count_type'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String, primary_key=True, nullable=False)
    creator = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)
    comments = db.Column(db.Text, default=None)
    file_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    count_type = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    points_count = relationship("PointsCount", back_populates="count_files", cascade="all, delete-orphan")
    pattern_count = relationship("PatternCount", back_populates="count_files", cascade="all, delete-orphan")
    groups_count = relationship("GroupsCount", back_populates="count_files", cascade="all, delete-orphan")

    effort_types = relationship("CountEffortTypes", back_populates="count_files")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class PointsCount(Base):
    __tablename__ = "count_pointscount"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'r_date', 'time_start', 'creator', 'species', 'file_name', 'count_type'],
            ['count_source.r_year', 'count_source.site', 'count_source.r_date',
             'count_source.time_start', 'count_source.creator', 'count_source.species',
             'count_source.file_name', 'count_source.count_type'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String, primary_key=True, nullable=False)
    creator = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)
    local_site = db.Column(db.String(collation='NOCASE'), nullable=False)
    animal_category = db.Column(db.String(collation='NOCASE'), nullable=False)
    iLeft = db.Column(db.Integer, primary_key=True, nullable=False)
    iTop = db.Column(db.Integer, primary_key=True, nullable=False)
    file_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    count_type = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    count_files = relationship("CountFiles", back_populates="points_count")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class PatternCount(Base):
    __tablename__ = "count_patternscount"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'r_date', 'time_start', 'creator', 'species', 'file_name', 'count_type'],
            ['count_source.r_year', 'count_source.site', 'count_source.r_date',
             'count_source.time_start', 'count_source.creator', 'count_source.species',
             'count_source.file_name', 'count_source.count_type'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String, primary_key=True, nullable=False)
    creator = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)
    local_site = db.Column(db.String(collation='NOCASE'), nullable=False)
    animal_category = db.Column(db.String(collation='NOCASE'), nullable=False)
    iLeft = db.Column(db.Integer, primary_key=True, nullable=False)
    iTop = db.Column(db.Integer, primary_key=True, nullable=False)
    file_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    count_type = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    count_files = relationship("CountFiles", back_populates="pattern_count")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class GroupsCount(Base):
    __tablename__ = "count_groupscount"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'r_date', 'time_start', 'creator', 'species', 'file_name', 'count_type'],
            ['count_source.r_year', 'count_source.site', 'count_source.r_date',
             'count_source.time_start', 'count_source.creator', 'count_source.species',
             'count_source.file_name', 'count_source.count_type'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String, primary_key=True, nullable=False)
    creator = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)
    local_site = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    time_s = db.Column(db.String, nullable=False)
    time_f = db.Column(db.String, nullable=True)
    animal_category = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    file_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    count_type = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    count_files = relationship("CountFiles", back_populates="groups_count")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


# Animal Id
class Resight(Base):
    __tablename__ = "id_resight"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'species'],
            ['survey_effort.r_year', 'survey_effort.site', 'survey_effort.species'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    animal_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    brand_quality = db.Column(db.String(collation='NOCASE'))
    sex_r = db.Column(db.String(collation='NOCASE'), nullable=False)
    status = db.Column(db.String(collation='NOCASE'), nullable=False)
    comments = db.Column(db.Text)
    id_status = db.Column(db.Integer, default=0)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    survey_effort = relationship("SurveyEffort", back_populates="resight_table")

    daily_table = relationship("Daily", back_populates="resight_table", cascade="all, delete-orphan")
    animal_info = relationship("AnimalInfo", back_populates="resight_table", cascade="all, delete-orphan")



    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class Daily(Base):
    __tablename__ = "id_daily"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'species', 'animal_name'],
            ['id_resight.r_year', 'id_resight.site', 'id_resight.species', 'id_resight.animal_name'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    animal_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    status = db.Column(db.String(collation='NOCASE'), nullable=False)
    local_site = db.Column(db.String(collation='NOCASE'))
    comments = db.Column(db.Text)
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    resight_table = relationship("Resight", back_populates="daily_table")

    location_table = relationship("Location", back_populates="daily_table", cascade="all, delete-orphan")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class Location(Base):
    __tablename__ = "id_location"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'species', 'animal_name', 'r_date'],
            ['id_daily.r_year', 'id_daily.site', 'id_daily.species', 'id_daily.animal_name', 'id_daily.r_date'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    animal_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    r_date = db.Column(db.Integer, primary_key=True, nullable=False)
    time_start = db.Column(db.String, nullable=False)
    local_site = db.Column(db.String(collation='NOCASE'))
    animal_type = db.Column(db.String(collation='NOCASE'), nullable=False)
    iLeft = db.Column(db.Integer, primary_key=True, nullable=False)
    iTop = db.Column(db.Integer, primary_key=True, nullable=False)
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)
    file_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    type_photo = db.Column(db.String(collation='NOCASE'))
    is_prediction_point = db.Column(db.Integer, nullable=False)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    daily_table = relationship("Daily", back_populates="location_table")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


class AnimalInfo(Base):
    __tablename__ = "id_animal_info"

    __table_args__ = (
        ForeignKeyConstraint(
            ['r_year', 'site', 'species', 'animal_name'],
            ['id_resight.r_year', 'id_resight.site', 'id_resight.species', 'id_resight.animal_name'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    species = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    r_year = db.Column(db.Integer, primary_key=True, nullable=False)
    site = db.Column(db.Integer, primary_key=True, nullable=False)
    animal_name = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    info_type = db.Column(db.String(collation='NOCASE'), primary_key=True, nullable=False)
    info_value = db.Column(db.String(collation='NOCASE'))
    observer = db.Column(db.String(collation='NOCASE'), nullable=False)

    datecreated = db.Column(db.String, default=db.func.now())
    dateupdated = db.Column(db.String, default=None, onupdate=db.func.now())

    resight_table = relationship("Resight", back_populates="animal_info")

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def validate(self):
        validate_required(self)


def validate_required(parent):
    """
    Проверка заполнения ключей
    """
    pKeys = parent.__table__.primary_key.columns.keys()
    for field in pKeys:
        if getattr(parent, field) is None:
            raise ValidationError(f"In the {parent.__table__} table, the {field} field  must be set! ")


count_effort_sites_AFTER_UPDATE = DDL('''
    CREATE TRIGGER count_effort_sites_AFTER_UPDATE
                 AFTER UPDATE
                    ON count_effort_sites
              FOR EACH ROW
        BEGIN
            UPDATE count_pointscount
               SET local_site = NEW.local_site
             WHERE r_year = OLD.r_year AND
                   site = OLD.site AND
                   r_date = OLD.r_date AND
                   time_start = OLD.time_start AND
                   creator = OLD.creator AND
                   local_site = OLD.local_site AND
                   count_type = OLD.count_type AND
                   species = OLD.species;
        END;''')

event.listen(CountEffortSites.__table__, 'after_create', count_effort_sites_AFTER_UPDATE)
