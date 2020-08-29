"""Загрузка данных по потребительской инфляции."""
import pandas as pd

from poptimizer.data import names, ports
from poptimizer.data.adapters.updaters import updater

# Параметры загрузки валидации данных
URL_CPI = "https://rosstat.gov.ru/storage/mediabank/chSxGUk7/i_ipc.xlsx"
END_OF_JAN = 31
PARSING_PARAMETERS = dict(sheet_name="ИПЦ", header=3, skiprows=[4], skipfooter=3, index_col=0)
NUM_OF_MONTH = 12
FIRST_YEAR = 1991
FIRST_MONTH = "январь"


def _validate(df: pd.DataFrame) -> None:
    """Проверка заголовков таблицы."""
    months, _ = df.shape
    first_year = df.columns[0]
    first_month = df.index[0]
    if months != NUM_OF_MONTH:
        raise ports.DataError("Таблица должна содержать 12 строк с месяцами")
    if first_year != FIRST_YEAR:
        raise ports.DataError("Первый год должен быть 1991")
    if first_month != FIRST_MONTH:
        raise ports.DataError("Первый месяц должен быть январь")


class CPIUpdater(updater.BaseUpdater):
    """Обновление данных инфляции с https://rosstat.gov.ru."""

    def __call__(self, table_name: ports.TableName) -> pd.DataFrame:
        """Получение данных по  инфляции."""
        name = self._log_and_validate_group(table_name, ports.CPI)
        if name != ports.CPI:
            raise ports.DataError(f"Некорректное имя таблицы для обновления {table_name}")

        df = pd.read_excel(URL_CPI, **PARSING_PARAMETERS)
        _validate(df)
        df = df.transpose().stack()
        first_year = df.index[0][0]
        df.index = pd.date_range(
            name=names.DATE,
            freq="M",
            start=pd.Timestamp(year=first_year, month=1, day=END_OF_JAN),
            periods=len(df),
        )
        # Данные должны быть не в процентах, а в долях
        df = df.div(100)
        return df.to_frame(names.CPI)
