from typing import TypeVar, Generic, List, Optional
from django.db.models import Model, QuerySet

T = TypeVar('T', bound=Model)