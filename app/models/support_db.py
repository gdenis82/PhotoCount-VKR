import sqlalchemy as db
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()  # базовый класс для декларативных моделей


class Sites(Base):
    __tablename__ = "support_site_id"

    site = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    site_name = db.Column(db.Text, nullable=False)
    area = db.Column(db.Text)
    lat_dec = db.Column(db.Float, nullable=False)
    lon_dec = db.Column(db.Float, nullable=False)
    is_rookery = db.Column(db.Text, nullable=False)
    country = db.Column(db.Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Species(Base):
    __tablename__ = "support_species_id"

    species = db.Column(db.Text, primary_key=True, unique=True, nullable=False)
    species_name = db.Column(db.Text, nullable=False)
    common_name = db.Column(db.Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Observers(Base):
    __tablename__ = "support_observer_id"

    observer = db.Column(db.Text, primary_key=True, unique=True, nullable=False)
    observer_name = db.Column(db.Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class LocalSites(Base):
    __tablename__ = "support_local_sites"

    __table_args__ = (
        ForeignKeyConstraint(
            ['site'],
            ['support_site_id.site'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    site = db.Column(db.Integer, primary_key=True, nullable=False)
    local_site_id = db.Column(db.Text, primary_key=True, nullable=False)
    local_site_name = db.Column(db.Text, nullable=False)
    datecreated = db.Column(db.String, default=db.func.now())

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class CountTypes(Base):
    __tablename__ = "support_count_type_id"

    type_id = db.Column(db.Text, primary_key=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    folder = db.Column(db.Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class EffortTypes(Base):
    __tablename__ = "support_effort_type_id"

    type_id = db.Column(db.Text, primary_key=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    type_category = db.Column(db.Text, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class AnimalCategories(Base):
    __tablename__ = "support_age_sex_categories"

    __table_args__ = (
        ForeignKeyConstraint(
            ['species'],
            ['support_species_id.species'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    species = db.Column(db.Text, primary_key=True, nullable=False)
    animal_category = db.Column(db.Text, primary_key=True, nullable=False)
    color_representation_large = db.Column(db.Text)
    color_representation_small = db.Column(db.Text)
    count_category = db.Column(db.Boolean)
    description = db.Column(db.Text)
    order = db.Column(db.Integer)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class AnimalNames(Base):
    __tablename__ = "id_animal_id"

    __table_args__ = (
        ForeignKeyConstraint(
            ['species'],
            ['support_species_id.species'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    species = db.Column(db.Text, primary_key=True, nullable=False)
    animal_name = db.Column(db.Text, primary_key=True, nullable=False)
    pos1 = db.Column(db.Text)
    pos2 = db.Column(db.Text)
    pos3 = db.Column(db.Text)
    pos4 = db.Column(db.Text)
    pos5 = db.Column(db.Text)
    type = db.Column(db.Text, nullable=False)
    t_side = db.Column(db.Text)
    t_sex = db.Column(db.Text, nullable=False)
    t_date = db.Column(db.Integer, nullable=False)
    t_site = db.Column(db.Integer, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class AnimalStatus(Base):
    __tablename__ = "support_animal_status"

    __table_args__ = (
        ForeignKeyConstraint(
            ['species'],
            ['support_species_id.species'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    species = db.Column(db.Text, primary_key=True)
    status = db.Column(db.Text, primary_key=True)
    sex_r = db.Column(db.Text, primary_key=True)
    description = db.Column(db.Text)
    priority = db.Column(db.Integer, nullable=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class AnimalInfo(Base):
    __tablename__ = "support_animal_info"

    __table_args__ = (
        ForeignKeyConstraint(
            ['species'],
            ['support_species_id.species'],
            onupdate="CASCADE", ondelete="CASCADE"
        ),)

    species = db.Column(db.Text, primary_key=True)
    info_id = db.Column(db.Integer, primary_key=True)
    info_description = db.Column(db.Text, default=None)
    display_order = db.Column(db.Integer, default=None)
    applicable_sex = db.Column(db.VARCHAR(1), default=None)
    info_data_type = db.Column(db.Text, default=None)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
