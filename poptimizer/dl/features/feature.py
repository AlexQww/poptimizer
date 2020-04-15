"""Абстрактный класс признака."""
import abc
import enum
from typing import Tuple

from torch import Tensor

from poptimizer.dl.data_params import DataParams


@enum.unique
class FeatureType(enum.Enum):
    """Типы признаков.

    По разному обрабатываются нейронной сетью.
    """

    # noinspection PyMethodParameters
    def _generate_next_value_(name, start, count, last_values):
        return name

    LABEL = enum.auto()
    WEIGHT = enum.auto()
    SEQUENCE = enum.auto()
    EMBEDDING = enum.auto()


class Feature(abc.ABC):
    """Абстрактный класс признака.

    Умеет выдавать значение признака для тикера по индексу и информацию о типе признака.
    """

    # noinspection PyUnusedLocal
    def __init__(self, ticker: str, params: DataParams):
        """Каждый признак должен сам сохранять необходимую для быстрого вычисления информацию."""

    @abc.abstractmethod
    def __getitem__(self, item: int) -> Tensor:
        """Нумерация идет с начала ряда данных в кэше параметров данных."""

    @property
    @abc.abstractmethod
    def type_and_size(self) -> Tuple[FeatureType, int]:
        """Тип признака и размер признака."""
