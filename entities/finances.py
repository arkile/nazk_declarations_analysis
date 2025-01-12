import logging as log
import math

import numpy as np
from decimal import *

getcontext().prec = 2

# TODO rewrite as dataclass
# --- class SavingsEntry ---
# stores simplified info about one row in step 12 (Грошові активи)
# contains amount, currency, owner and type of entry
class SavingsEntry:
    USD_AVG_EXCHANGE_RATE = {'2016': 25.55, '2017': 26.59,
                             '2018': 27.20, '2019': 25.84,
                             '2020': 26.96, '2021': 27.29,
                             '2022': 32.34, '2023': 36.57 }
    EUR_AVG_EXCHANGE_RATE = {'2016': 28.29, '2017': 30.00,
                             '2018': 32.14, '2019': 28.95,
                             '2020': 30.79, '2021': 32.31,
                             '2022': 33.98, '2023': 39.56 }

    def __init__(self, amount: str|int|float, currency: str, owner: str|int, type_: str):
        self.amount = amount
        self.currency: str = currency
        self.owner: str|int = owner
        self.type_: str = type_

    def to_uah_by_yearly_avg(self, year: str|int):
        if self.currency == 'UAH':
            return round(self.amount, 2)
        elif self.currency == 'USD':
            return round(self.amount * self.USD_AVG_EXCHANGE_RATE[str(year)])
        elif self.currency == 'EUR':
            return round(self.amount * self.EUR_AVG_EXCHANGE_RATE[str(year)])
        else:
            log.error(f'Unknown currency: {self.currency}')
            raise BaseException(f'Unknown currency: {self.currency}')

    # --- class SavingsEntry end ---


# TODO rewrite as dataclass
class EarningsEntry:
    def __init__(self, amount: str|float, owner: str|int, origin: str):
        self.amount: float = float(amount)
        self.owner = owner
        self.origin: str = origin
        if self._is_salary():
            self.amount_taxed: float = self.__subtract_taxes()
        else:
            self.amount_taxed: float = self.amount

    def __subtract_taxes(self) -> float:
        return round(self.amount * 0.8, 2)

    def _is_salary(self) -> bool:
        return 'заробітна плата' in str(self.origin).lower()

    # --- class EarningsEntry end ---


# -------- Tools ----------

# parser for step_12 - Грошові активи
def get_savings_entries(step12_data: list[dict]) -> list[SavingsEntry]:
    # log.debug('call to get_savings_entries, data: ' + str(step12_data))
    savings_entries: list[SavingsEntry] = []
    for entry_ in step12_data:
        # log.debug(entry_)
        if len(entry_['rights']) > 1:
            log.warning('Some strange shit with rights for savings entry')
        s_ = SavingsEntry(float(entry_['sizeAssets']), entry_['assetsCurrency'],
                         entry_['rights'][0]['rightBelongs'], entry_['objectType'])
        savings_entries.append(s_)
    # returns list of SavingsEntry objects
    return savings_entries


# is it needed?
def get_converted_total_by_person(savings_entries: list[SavingsEntry], person_id: str, year: int) -> float:
    savings = filter(lambda s: str(s.owner) == str(person_id), savings_entries)
    total = 0.00
    for entry_ in savings:
        total += round(entry_.to_uah_by_yearly_avg(year), 2)
    return total

# converter + splitter for step_12
def convert_and_split_by_person(savings_entries: list[SavingsEntry], year: int) -> dict[str | int, int | float]:
    savings_by_person = {}
    for entry_ in savings_entries:
        if str(entry_.owner) in savings_by_person:
            # log.debug('-------')
            # log.debug(savings_by_person[str(entry_.owner)])
            # log.debug(entry_.to_uah_by_yearly_avg(year))
            savings_by_person[str(entry_.owner)] += round(entry_.to_uah_by_yearly_avg(year), 2)
        else:
            savings_by_person[str(entry_.owner)] = round(entry_.to_uah_by_yearly_avg(year), 2)
    log.debug(f'savings entries converted to uah, split by person and summed up, result: {savings_by_person}')
    return savings_by_person


# parser for step_11 - Доходи, у тому числі подарунки
def get_earnings_entries(step11_data: list[dict]) -> list[EarningsEntry]:
    earnings_entries = []
    for entry_ in step11_data:
        e_ = None
        if 'rights' in entry_:
            if len(entry_['rights']) > 1:
                log.warning('Some strange shit with rights field for savings entry')
            e_= EarningsEntry(entry_['sizeIncome'], entry_['rights'][0]['rightBelongs'], entry_['objectType'])
        elif 'person_who_care' in entry_:
            if len(entry_['person_who_care']) > 1:
                log.warning('Some strange shit with person_who_care field for savings entry')
            e_= EarningsEntry(entry_['sizeIncome'], entry_['person_who_care'][0]['person'], entry_['objectType'])
        assert e_ is not None
        earnings_entries.append(e_)
    return earnings_entries

# splitter for step_11
def sum_taxed_and_split_by_person(earnings_entries: list[EarningsEntry]):
    earnings_by_person = {}
    for entry_ in earnings_entries:
        if str(entry_.owner) in earnings_by_person:
            earnings_by_person[entry_.owner] += round(entry_.amount_taxed, 2)
        else:
            earnings_by_person[entry_.owner] = round(entry_.amount_taxed, 2)
            log.debug(f'earnings entries taxed, split by person and summed up, result: {earnings_by_person}')
    return earnings_by_person




