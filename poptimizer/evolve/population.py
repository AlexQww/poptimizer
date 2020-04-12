"""Класс организма и операции с популяцией организмов."""
from typing import Iterable, Tuple, NoReturn, Optional, Dict, Any

import bson
import pandas as pd
from pymongo.collection import Collection

from poptimizer.config import POptimizerError
from poptimizer.dl.trainer import Trainer
from poptimizer.evolve.genotype import Genotype
from poptimizer.store.mongo import DB, MONGO_CLIENT

# Коллекция для хранения моделей
COLLECTION = MONGO_CLIENT[DB]["models"]

# Ключи для хранения описания организма
ID = "_id"
GENOTYPE = "genotype"
WINS = "wins"
MODEL = "model"
SHARPE = "sharpe"
SHARPE_DATE = "sharpe_date"
SHARPE_TICKERS = "tickers"


class OrganismIdError(POptimizerError):
    """Ошибка попытки загрузить организм с отсутствующим в базе ID."""


class Organism:
    """Хранящийся в MongoDB организм.

    Загружается по id, создается из описания генотипа или с нуля с генотипом по умолчанию.
    Умеет рассчитывать качество организма для проведения естественного отбора, убивать другой
    организм, умирать, размножаться и отображать количество уничтоженных организмов.
    """

    def __init__(
        self,
        *,
        _id: Optional[bson.ObjectId] = None,
        genotype: Optional[Genotype] = None,
        collection: Collection = None,
    ):
        collection = collection or COLLECTION
        self.collection = collection

        if _id is None:
            _id = bson.ObjectId()
            organism = {ID: _id, GENOTYPE: genotype}
            collection.insert_one(organism)

        organism = collection.find_one({ID: _id})
        if organism is None:
            raise OrganismIdError(f"В популяции нет организма с ID: {_id}")
        organism[GENOTYPE] = Genotype(organism[GENOTYPE])
        self._data = organism

    def __str__(self) -> str:
        return str(self._data[GENOTYPE])

    @property
    def id(self) -> bson.ObjectId:
        """ID организма."""
        return self._data[ID]

    def die(self) -> NoReturn:
        """Организм удаляется из популяции."""
        self.collection.delete_one({ID: self._data[ID]})

    def _update(self, update: Dict[str, Any]) -> NoReturn:
        """Обновление данных в MongoDB и внутреннего состояния организма."""
        self._data.update(update)
        self.collection.update_one({ID: self._data[ID]}, {"$set": update})

    @property
    def wins(self) -> int:
        """Количество побед."""
        return self._data.get(WINS, 0)

    def kill(self, organism: "Organism") -> NoReturn:
        """Убивает другой организм и ведет счет побед."""
        update = {WINS: self.wins + 1}
        self._update(update)
        organism.die()

    def evaluate_fitness(self, tickers: Tuple[str, ...], end: pd.Timestamp) -> float:
        """Вычисляет коэффициент Шарпа."""
        organism = self._data

        if organism.get(SHARPE_DATE) == end and organism.get(SHARPE_TICKERS) == sorted(
            tickers
        ):
            return organism[SHARPE]

        trainer = Trainer(tickers, end, organism[GENOTYPE].get_phenotype())
        sharpe = trainer.sharpe
        model = trainer.model

        update = {
            SHARPE: sharpe,
            SHARPE_DATE: end,
            SHARPE_TICKERS: sorted(tickers),
            MODEL: model,
        }
        self._update(update)

        return sharpe

    def make_child(self) -> "Organism":
        """Создает новый организм с помощью дифференциальной мутации."""
        genotypes = [organism._data[GENOTYPE] for organism in _sample_organism(3)]
        child_genotype = self._data[GENOTYPE].make_child(*genotypes)
        return Organism(genotype=child_genotype)


def _sample_organism(num: int, collection: Collection = None) -> Iterable[Organism]:
    """Выбирает несколько случайных организмов.

    Необходимо для реализации размножения и отбора.
    """
    collection = collection or COLLECTION
    pipeline = [{"$sample": {"size": num}}, {"$project": {"_id": True}}]
    organisms = collection.aggregate(pipeline)
    yield from (Organism(**organism) for organism in organisms)


def count(collection: Collection = None) -> int:
    """Количество организмов в популяции."""
    collection = collection or COLLECTION
    return collection.count_documents({})


def create_new_organism(collection: Collection = None) -> Organism:
    """Создает новый организм с пустым генотипом."""
    collection = collection or COLLECTION
    return Organism(collection=collection)


def get_random_organism(collection: Collection = None) -> Organism:
    """Получить случайный организм из популяции."""
    collection = collection or COLLECTION
    organism, *_ = tuple(_sample_organism(1, collection))
    return organism


def get_all_organisms(collection=None) -> Iterable[Organism]:
    """Получить все имеющиеся организмы."""
    collection = collection or COLLECTION
    id_dicts = collection.find(filter={}, projection=["_id"], sort=[(SHARPE, 1)])
    for id_dict in id_dicts:
        yield Organism(**id_dict)


def print_stat(collection=None) -> NoReturn:
    """Статистика - минимальное и максимальное значение коэффициента Шарпа."""
    collection = collection or COLLECTION
    db_find = collection.find

    sort_type = (1, -1)
    params = {"filter": {SHARPE: {"$exists": True}}, "projection": [SHARPE], "limit": 1}
    cursors = (db_find(sort=[(SHARPE, up_down)], **params) for up_down in sort_type)
    cursors = [tuple(cursor) for cursor in cursors]
    sharpes = [f"{cursor[0][SHARPE]:.4f}" if cursor else "-" for cursor in cursors]
    print(f"Коэффициент Шарпа - ({', '.join(sharpes)})")

    params = {
        "filter": {WINS: {"$exists": True}},
        "projection": [WINS],
        "sort": [(WINS, -1)],
        "limit": 1,
    }
    wins = list(db_find(**params))
    max_wins = None
    if wins:
        max_wins, *_ = wins
        max_wins = max_wins[WINS]
    print(f"Максимум побед - {max_wins}")
