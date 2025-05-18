from typing import Optional

from app.models.main_db import Location


class ModelRegistrationAnimal:
    """
   Класс ModelRegistrationAnimal представляет информацию о регистрации животного в модели.
    """
    def __init__(self):
        self.species: str = ''
        self.year: int = 0
        self.site: int = 0
        self.date: int = 0
        self.time_start: str = ''
        self.animal_name: str = ''
        self.brand_quality: str = ''
        self.local_site: str = ''
        self.animal_status: str = ''
        self.sex: str = ''
        self.iLeft: int = -1
        self.iTop: int = -1
        self.observer: str = ''
        self.file_name: str = ''
        self.type_photo: str = ''
        self.is_prediction_point: int = 0
        self.status_confirmation: str = ''
        self.comment: str = ''

        self.location: Optional[Location] = None

