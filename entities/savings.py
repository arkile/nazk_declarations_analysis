import logging as log
from decimal import *

getcontext().prec = 2

USD_AVG_EXCH_RATE = {'2016': 25.55, '2017': 26.59,
                     '2018': 27.20, '2019': 25.84,
                     '2020': 26.96, '2021': 27.29,
                     '2022': 32.34, '2023': 36.57 }

EUR_AVG_EXCH_RATE = {'2016': 28.29, '2017': 30.00,
                     '2018': 32.14, '2019': 28.95,
                     '2020': 30.79, '2021': 32.31,
                     '2022': 33.98, '2023': 39.56 }

USD_EXCH_RATE_RANGE = {
    '2016': (23.26 , 27.25), '2017': (25.44 , 28.06),
    '2018': (25.91 , 28.87), '2019': (23.25 , 28.27),
    '2020': (23.68 , 28.60), '2021': (26.06 , 28.43),
    '2022': (27.28 , 36.57), '2023': (36.01 , 37.98),
    '2024': (37.45 , 42.04) }

EUR_EXCH_RATE_RANGE = {
    '2016': (28.29 , 28.29), '2017': (30.00 , 30.00), # not updated, avg used
    '2018': (32.14 , 32.14), '2019': (28.95 , 28.95), # not updated, avg used
    '2020': (30.79 , 30.79), '2021': (32.31 , 32.31), # not updated, avg used
    '2022': (29.28 , 38.95), '2023': (38.23 , 42.21),
    '2024': (40.37 , 46.24) }


# TODO rewrite as dataclass
# --- class SavingsEntry ---
# stores simplified info about one row in step 12 (Грошові активи)
# contains amount, currency, owner and type of entry
class SavingsEntry:

    def __init__(self, amount: str|int|float, currency: str, owner: str|int, type_: str):
        self.amount = amount
        self.currency: str = currency
        self.owner: str = str(owner)
        self.type_: str = type_

    def to_uah_by_yearly_avg(self, year: str|int) -> float:
        if self.currency == 'UAH':
            return round(self.amount, 2)
        elif self.currency == 'USD':
            return round(self.amount * USD_AVG_EXCH_RATE[str(year)])
        elif self.currency == 'EUR':
            return round(self.amount * EUR_AVG_EXCH_RATE[str(year)])
        else:
            log.error(f'Unknown currency: {self.currency}')
            raise BaseException(f'Unknown currency: {self.currency}')

    def to_uah_by_yearly_range(self, year: str|int) -> (float, float):
        exch_func = lambda x, exch_pair : ( round(x * exch_pair[0]) , round(x * exch_pair[1]) )
        if self.currency == 'UAH':
            return round(self.amount, 2), round(self.amount, 2)
        elif self.currency == 'USD':
            return exch_func(self.amount, USD_EXCH_RATE_RANGE[str(year)])
        elif self.currency == 'EUR':
            return exch_func(self.amount, EUR_EXCH_RATE_RANGE[str(year)])
        else:
            log.error(f'Unknown currency: {self.currency}')
            raise BaseException(f'Unknown currency: {self.currency}')


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

# misc function
def to_uah_by_yearly_avg(currency: str, amount: int|float, year: str|int) -> int:
    if currency == 'UAH':
        return int(amount)
    elif currency == 'USD':
        return int(amount * USD_AVG_EXCH_RATE[str(year)])
    elif currency == 'EUR':
        return int(amount * EUR_AVG_EXCH_RATE[str(year)])
    else:
        log.error(f'Unknown currency: {currency}')
        raise BaseException(f'Unknown currency: {currency}')

# # is it needed?
# def get_converted_total_by_person(savings_entries: list[SavingsEntry], person_id: str, year: int) -> float:
#     savings = filter(lambda s: str(s.owner) == str(person_id), savings_entries)
#     total = 0.00
#     for entry_ in savings:
#         total += round(entry_.to_uah_by_yearly_avg(year), 2)
#     return total

# converter + splitter for step_12
# soon to be depricated
def convert_and_split_by_person_v1(savings_entries: list[SavingsEntry], year: int) -> dict[str|int, int|float]:
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

# splitter for step_12
# returns dictionary in a format: {'person_id': {'currency': amount}}
def split_by_person_avg(savings_entries: list[SavingsEntry]) -> dict[str, dict[str, str|int]]:
    savings_by_person = {}
    for entry_ in savings_entries:
        if entry_.owner in savings_by_person:
            if entry_.currency in savings_by_person[entry_.owner]:
                savings_by_person[entry_.owner][entry_.currency] += entry_.amount
            else:
                savings_by_person[entry_.owner][entry_.currency] = entry_.amount
        else:
            savings_by_person[entry_.owner] = {entry_.currency: entry_.amount}
    log.debug(f'savings entries split by person, result: {savings_by_person}')
    return savings_by_person

#returns {'currency': amount}
def sum_savings_by_currency_avg(savings_entries: list[SavingsEntry]) -> dict[str, int|float]:
    savings_by_currency = {}
    for entry_ in savings_entries:
        if entry_.currency in savings_by_currency:
            savings_by_currency[entry_.currency] += entry_.amount
        else:
            savings_by_currency[entry_.currency] = entry_.amount
    log.debug(f'savings entries summed up by currency, result: {savings_by_currency}')
    return savings_by_currency

# returns total amount of converted savings (converted by yearly average for each currency)
def get_total_converted_avg(savings_by_currency: dict[str, int|float], year: str) -> int|float:
    return sum( [to_uah_by_yearly_avg(curr, amount, year) for (curr, amount) in savings_by_currency.items()] )
