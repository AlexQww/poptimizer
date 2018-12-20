import pandas as pd
import pytest

from poptimizer import portfolio, config, optimizer
from poptimizer.ml import feature
from poptimizer.portfolio import finder


def test_feature_days():
    assert finder.feature_days(feature.Label) == 21


def test_get_turnover(monkeypatch):
    monkeypatch.setattr(config, "TURNOVER_CUT_OFF", 0.0012)
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.get_turnover(port, ("KZOS", "AKRN"))
    assert isinstance(df, pd.Series)
    assert df.size == 4
    assert df["KZOS"] == pytest.approx(0.986873)


def test_find_momentum():
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.find_momentum(port, 0.02)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (5, 5)
    assert list(df.columns) == ["Mean", "STD", "TURNOVER", "T_SCORE", "ADD"]
    assert list(df.index) == ["TATN", "BANEP", "NVTK", "KZOS", "SIBN"]
    assert df.loc["TATN", "ADD"] == ""
    assert df.loc["KZOS", "ADD"] == ""
    assert df.loc["BANEP", "ADD"] == "ADD"


def test_find_dividends():
    date = pd.Timestamp("2018-12-18")
    positions = dict(CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    df = finder.find_dividends(port, 0.02)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (5, 4)
    assert list(df.columns) == ["Dividends", "TURNOVER", "SCORE", "ADD"]
    assert list(df.index) == ["CHMF", "MTLRP", "LSNGP", "ENRU", "TATNP"]
    assert df.loc["CHMF", "ADD"] == ""
    assert df.loc["MTLRP", "ADD"] == "ADD"


def test_find_zero_turnover_and_weight():
    date = pd.Timestamp("2018-12-18")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    tickers = finder.find_zero_turnover_and_weight(port)
    assert "KAZT" not in tickers
    assert "KAZTP" in tickers


def test_find_low_gradient():
    date = pd.Timestamp("2018-12-19")
    positions = dict(
        AKRN=563,
        BANE=236,
        CHMF=2000,
        BANEP=1644,
        KAZT=0,
        KAZTP=0,
        KZOS=3400,
        LKOH=270,
        TATN=420,
        MGNT=0,
        MTLRP=0,
    )
    port = portfolio.Portfolio(date, 0, positions)
    opt = optimizer.Optimizer(port, months=11)
    bad_tickers = finder.find_low_gradient(opt)
    assert len(bad_tickers) == 1
    assert "MGNT" in bad_tickers


def test_add_tickers(capsys):
    date = pd.Timestamp("2018-12-19")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    finder.add_tickers(port)
    captured = capsys.readouterr()
    assert "МОМЕНТУМ ТИКЕРЫ" in captured.out
    assert "ДИВИДЕНДНЫЕ ТИКЕРЫ" in captured.out


def test_remove_tickers(capsys):
    date = pd.Timestamp("2018-12-19")
    positions = dict(KAZT=1, KAZTP=0, CHMF=20000, TATN=20000, KZOS=20000, LKOH=20000)
    port = portfolio.Portfolio(date, 0, positions)
    opt = optimizer.Optimizer(port, months=11)
    finder.remove_tickers(opt)
    captured = capsys.readouterr()
    assert "БУМАГИ С НУЛЕВЫМ ОБОРОТОМ И ВЕСОМ" in captured.out
    assert "БУМАГИ С НИЗКИМ ГРАДИЕНТОМ" in captured.out
