"""Признак - доходность за последний месяц."""
from typing import Tuple

import pandas as pd

from poptimizer import data
from poptimizer.ml.feature.feature import AbstractFeature, DaysParamsMixin


class Mom1m(DaysParamsMixin, AbstractFeature):
    """1-month momentum - средняя доходность примерно за 1 предыдущий месяц.

    Хотя в общем акции демонстрируют сохранение роста, если они росли в предыдущие периоды,
    на горизонте в один-два месяца эта зависимость обычно нарушается - short term reversal.

    При оптимизации гиперпараметров выбирается оптимальное количество торговых дней для расчета
    краткосрочной реверсии.
    """

    def __init__(self, tickers: Tuple[str, ...], last_date: pd.Timestamp, params: dict):
        super().__init__(tickers, last_date, params)
        self._returns = data.log_total_returns(tickers, last_date)

    def get(self, params=None) -> pd.Series:
        """Средняя доходность за указанное количество предыдущих дней."""
        params = params or self._params
        days = params["days"]
        mom1m = self._returns.rolling(days).mean()
        return mom1m.stack()