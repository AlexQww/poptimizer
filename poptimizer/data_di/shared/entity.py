"""Доменные сущности."""
from typing import Dict, Generic, Iterator, List, TypeVar

from poptimizer.data_di.shared import events


class BaseID:
    """Базовый идентификатор доменного сущности.

    Реализует необходимую логику для удобства сохранения в MongoDB.
    """

    def __init__(self, db: str, collection: str, _id: str):
        """Сохраняет необходимую информацию."""
        self._db = db
        self._collection = collection
        self._id = _id


AttrValues = TypeVar("AttrValues")


class BaseEntity(Generic[AttrValues]):
    """Абстрактный класс сущности.

    Обязательно имеет поле и идентификатором, механизм сохранения и извлечения событий и
    автоматического статуса изменений.
    """

    def __init__(self, id_: BaseID) -> None:
        """Формирует список событий и отметку об изменениях."""
        self._id = id_
        self._events: List[events.AbstractEvent] = []
        self._changed_state: Dict[str, AttrValues] = {}

    def __setattr__(self, key: str, attr_value: AttrValues) -> None:
        """Сохраняет изменное значение."""
        if key in vars(self):  # noqa: WPS421
            self._changed_state[key] = attr_value
        super().__setattr__(key, attr_value)

    @property
    def id_(self) -> BaseID:
        """Уникальный идентификатор сущности."""
        return self._id

    def changed_state(self) -> Dict[str, AttrValues]:
        """Показывает измененные атрибуты."""
        return {**self._changed_state}

    def clear(self) -> None:
        """Сбрасывает изменения."""
        self._changed_state.clear()

    def pop_event(self) -> Iterator[events.AbstractEvent]:
        """Возвращает события возникшие в за время существования сущности."""
        while self._events:
            yield self._events.pop()