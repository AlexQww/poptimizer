"""Основные настраиваемые параметры"""
import logging
import pathlib

import pandas as pd


class POptimizerError(Exception):
    """Базовое исключение."""


# Конфигурация логгера
logging.basicConfig(level=logging.INFO)

# Количество колонок в распечатках без переноса на несколько страниц
pd.set_option("display.max_columns", 20)
pd.set_option("display.width", None)

# Путь к директории с данными
DATA_PATH = pathlib.Path(__file__).parents[1] / "data"

# Путь к директории с отчетам
REPORTS_PATH = pathlib.Path(__file__).parents[1] / "reports"

# Множитель, для переходя к после налоговым значениям
AFTER_TAX = 1 - 0.13

# Параметр для доверительных интервалов
T_SCORE = 2.0

# Максимальный объем одной торговой операции в долях портфеля
MAX_TRADE = 0.01

# Период в торговых днях, за который медианный оборот торгов
TURNOVER_PERIOD = 21

# Минимальный оборот - преимущества акции снижаются при приближении медианного оборота к данному уровню
TURNOVER_CUT_OFF = 0.88 * MAX_TRADE

# Параметры ML-модели
LABEL_RANGE = [27, 74]
STD_RANGE = [134, 275]
MOM12M_RANGE = [250, 524]
DIVYIELD_RANGE = [240, 444]
MOM1M_RANGE = [16, 21]

ML_PARAMS = (
    (
        (True, {"days": 62}),
        (True, {"days": 225}),
        (True, {}),
        (True, {"days": 330}),
        (True, {"days": 396}),
        (True, {"days": 18}),
    ),
    {
        "bagging_temperature": 0.8401168021849872,
        "depth": 7,
        "l2_leaf_reg": 1.433660330544913,
        "learning_rate": 0.08376204151234184,
        "one_hot_max_size": 100,
        "random_strength": 1.0614056607524265,
        "ignored_features": [],
    },
)
