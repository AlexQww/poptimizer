package tables

import (
	"context"
	"errors"
	"github.com/WLM1ke/gomoex"
	"time"
)

type (
	Group   string
	Name    string
	Command struct {
	}
)

type Event struct {
	LastTradingDate time.Time
}

type Table interface {
	Group() Group
	Name() Name
	Update(ctx context.Context, cmd Command) (*Event, error)
}

var ErrRowsValidationErr = errors.New("ошибка валидации данных")

// TradingDates - таблица с диапазоном торговых дат.
//
// ID таблицы должна заполнять фабрика.
// Ряды таблицы и последняя торговая дата должны грузиться из базы.
type TradingDates struct {
	group Group
	name  Name

	iss *gomoex.ISSClient

	LastTradingDate time.Time
	Rows            []gomoex.Date
}

func (t *TradingDates) Group() Group {
	return t.group
}

func (t *TradingDates) Name() Name {
	return t.name
}

func (t *TradingDates) Update(ctx context.Context, _ Command) (*Event, error) {
	newRows, err := t.iss.MarketDates(ctx, gomoex.EngineStock, gomoex.MarketShares)
	if err != nil {
		return nil, err
	}

	if len(newRows) != 1 {
		return nil, ErrRowsValidationErr
	}

	newLastTradingDay := newRows[0].Till
	if !newLastTradingDay.After(t.LastTradingDate) {
		return nil, nil
	}

	t.LastTradingDate = newLastTradingDay
	t.Rows = newRows

	return &Event{newLastTradingDay}, nil
}

type TradingDatesFactory struct {
	iss *gomoex.ISSClient
}

func (t TradingDatesFactory) NewTable(group Group, name Name) Table {
	return &TradingDates{group: group, name: name, iss: t.iss}
}
