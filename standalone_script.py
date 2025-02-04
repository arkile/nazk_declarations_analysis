from collections import defaultdict

import requests
import json

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

LIST_ADDRESS = 'https://public-api.nazk.gov.ua/v2/documents/list?query='

DOC_ADDRESS = 'https://public-api.nazk.gov.ua/v2/documents/'

REGULAR_DECL_VIEW_ADDRESS = 'https://public.nazk.gov.ua/documents/'

log.basicConfig(format='{asctime} [{levelname}] {message}',
                style='{',
                datefmt="%H:%M", # datefmt="%Y-%m-%d %H:%M",
                level=log.DEBUG)
                # level=log.INFO)
                # level=log.WARNING)


# -------------------------------
# Report
from enum import Enum

class ReportLevel(Enum):
    TOP = 1
    STEP = 2
    DETAILS = 3


class Report(object):

    def __init__(self):
        self.period = None
        self.text = ''
        self.summary = ''

    def add_top_info(self, full_name: str, period: tuple[int, int]):
        self.text += full_name
        # self.text += '\n' + job
        self.text += '\n' + f'{period[0]} - {period[1]}'
        self.period = period

    # critical level:
    # 1 - regular info
    # 2 - questionable information - may be a risk, may not
    # 3 - very likely to be a risk
    def add_record(self, report_level: ReportLevel, line: str, critical: int = 1):
        self.text += '\n'
        self.text += '\t' * (report_level.value - 1)
        line_ = line.replace('\n', '\n' + ('\t' * (report_level.value - 1)), -1)
        if critical == 2:
            line_ = '! ' + line_ + ' !'
            self.text += line_
            self.summary += f'\n {line_}'
        elif critical == 3:
            line_ = line_ + ' !!!!!!!'
            self.text += line_
            self.summary += f'\n {line_}'
        else:
            self.text += line_
        return self

    def add_empty_line(self):
        self.text += '\n'

    def __str__(self):
        return self.text

    def __repr__(self):
        #TODO rewrite
        return self.summary
    # --- class Report end ---


def init_new_report():
    return Report()
# -------------------------------

# -------------------------------
# Declaration
class Declaration:
    """
    Declaration type + type combination meanings are as follows:
    0 type 2 - Про суттєві зміни у майновому стані
    1 type 1 - Щорічна
      type 3 - Виправлена щорічна
    2 type 1 - При звільненні
    3 type 1 - Після звільнення
    4 type 1 - Кандидата на посаду
      type 3 - Виправлена кандидата на посаду
    """
    def __init__(self, declaration_type: str|int, declaration_id: str,
                 declarant_id: str|int, submit_date: str, year: str|int, type_: str|int,
                 corruption_affected: str|int = None):
        self.declaration_type: int = int(declaration_type) # corresponds to declaration_type, not type
        self.declaration_id: str = declaration_id
        # self.declarant_name = declarant_name
        self.declarant_id: int = int(declarant_id)
        self.submit_date: str = submit_date
        self.year: int = int(year)
        self.type_: int = int(type_)  # corresponds to this card's color on UI - blue for yearly, green for corrected yearly etc
        self.corruption_affected = corruption_affected

        # automatically defined properties
        if declaration_type == 0 and type_ == 2:
            self.minor = True
            self.written_type = 'Про суттєві зміни у майновому стані'
        else:
            self.minor = False

        match declaration_type:
            case 1:
                if type_ == 1:
                    self.written_type = 'Щорічна'
                elif type_ == 3:
                    self.written_type = 'Виправлена щорічна'
                else:
                    self.written_type = 'Невідомий підтип щорічної декларації'
            case 2:
                if type_ == 1:
                    self.written_type = 'При звільненні'
                else:
                    self.written_type = 'Невідомий підтип декларації при звільненні'
            case 3:
                if type_ == 1:
                    self.written_type = 'Після звільнення'
                else:
                    self.written_type = 'Невідомий підтип декларації після звільнення'
            case 4:
                if type_ == 1:
                    self.written_type = 'Кандидата на посаду'
                elif type_ == 3:
                    self.written_type = 'Виправлена кандидата на посаду'
                else:
                    self.written_type = 'Невідомий підтип декларації кандидата на посаду'
            case _:
                self.written_type = 'Невідомий тип або неправильні дані'
                # print(declaration_type)

        #extended info with details, loaded later directly from declaration page
        self.data = {}
        self.full_name = None
        self.persons: dict[str, Person] = {}
        self.property_list: list[Property] = []
        self.vehicle_list: list[Vehicle] = []

        self.earnings: list[EarningsEntry] = []
        self.earnings_by_person: dict[str|int, int|float] = {}

        self.savings: list[SavingsEntry] = []
        self.savings_by_person: dict[str|int, int|float] = {}
        self.savings_by_currency: dict[str, int|float] = {}
        self.savings_by_prsn_and_curr: dict[str, dict[str, str|int]] = {}
    # __init__ end


    def get_person_name_by_id(self, person_id) -> str:
        if person_id == 1 or person_id == '1':
            return self.full_name
        x = self.persons[person_id]
        return self.persons[person_id].full_name


    def __str__(self):
        if not self.data:
            return (f'\n --- Declaration # {self.declaration_id} --- \n type: {self.written_type} \n '
                     f'declarant id: {self.declarant_id} \n year: {self.year} \n submit date: {self.submit_date}')
        else:
            # TODO expand alter - add steps
            return (f'\n --- Declaration # {self.declaration_id} --- \n type: {self.written_type} \n '
                     f'declarant id: {self.declarant_id} \n year: {self.year} \n submit date: {self.submit_date}')


    def __repr__(self):
        return self.__str__()
# -------------------------------

# -------------------------------
# Person
class Person:
    def __init__(self, person_id: str|int, full_name: str, relation_type: str, mentions: list[str|int]):
        if not isinstance(person_id, int) and not person_id.isdigit():
            raise BaseException("Person ID is not valid")
        self.person_id: int = int(person_id)
        self.full_name: str = full_name
        self.relation_type: str = relation_type
        self.mentions: list[str|int] = mentions


# -------- Tools ----------

def get_person_entries(step2_data: list[dict]) -> dict[str, Person]:
    related_persons: dict[str, Person] = {}
    for entry_ in step2_data:
        full_name = entry_['lastname'] + ' ' + entry_['firstname'] + ' ' + entry_['middlename']
        person_ = Person(person_id=entry_['id'], full_name=full_name,
                         relation_type=entry_['subjectRelation'], mentions=['usage'])
        related_persons[entry_['id']] = person_
    return related_persons

def get_self_entry(step1_data: dict) -> Person:
    first_name = step1_data['firstname']
    middle_name = step1_data['middlename']
    last_name = step1_data['lastname']
    full_name = first_name + ' ' + middle_name + ' ' + last_name
    key_figure = Person(person_id=1, full_name=full_name, relation_type='self', mentions=[])
    return key_figure
# -------------------------------

# -------------------------------
# Property
class Property:
    def __init__(self, place: str, property_type: str, acquire_date: str, total_area: str|int|float,
                ownership_type: str, owners: dict[int: str], cost: str|int):
        self.place: str = place
        self.property_type: str = property_type.lower()
        self.acquire_date: str = acquire_date
        self.total_area: float = float(total_area)
        self.ownership_type: str = ownership_type
        self.owners: dict[int: str] = owners
        self.cost: int | str = cost

    def get_changes_since(self, other):
        #TODO add logs
        change: str = ''
        if self.owners != other.owners:
            change += f'\n  - власники змінились {self.__repr__()}' # TODO expand on this
        if self.ownership_type != other.ownership_type:
            change += f'\n  - тип власності змінився з {self.ownership_type} на {other.ownership_type}.'
        if (self.place.lower() != other.place.lower()
                and self.place.lower() not in other.place.lower()
                and other.place.lower() not in self.place.lower()):
            change += f'\n  - місце реєстрації змінилось із {self.place} на {other.place} (тип, площа та дата набуття однакові).'
        if not self.cost and other.cost:
            change += f'\n  - вартість була вказана у попередній декларації: {other.cost} грн, але не вказана у цій.'
        elif not other.cost and self.cost:
            change += f'\n  - вартість не була вказана раніше, проте вказана зараз: {self.cost} грн.'
        elif self.cost and other.cost and self.cost != other.cost:
            change += f'\n  - вартість змінилась із {other.cost} грн на {self.cost} грн.'

        if len(change) != 0:  # or simply if(change) ?
            change = f'Змінені дані:      {self.__repr__()}:' + change
        else:
            change = f'Змін не виявлено:   {self.__repr__()}'
        return change

    def get_year_acquired(self):
        if len(self.acquire_date) == 4:
            _year = self.acquire_date
        else:
            _year = self.acquire_date[-4:]
        assert(len(_year) == 4)
        return int(_year)

    def __eq__(self, other):
        return (self.property_type == other.property_type
                and self.total_area == other.total_area
                and self.acquire_date == other.acquire_date)

    def __str__(self):
        return f"Власність '{self.property_type}' (набута: {self.acquire_date}, загальна площа: {self.total_area} кв.м., ціна: {self.cost} грн)"

    def __repr__(self):
        return f"Власність '{self.property_type}' (набута: {self.acquire_date}, загальна площа: {self.total_area} кв.м., ціна: {self.cost} грн)"


# -------- Tools ----------

def _parse_cost_assessment(cost_assessment: str) -> int | str:
    if (not cost_assessment
            or cost_assessment == '[Не застосовується]'
            or cost_assessment == '[Не відомо]'
            or cost_assessment == 'Не вказано'
            or cost_assessment == '[Не вказано]'):
        return ''
    elif cost_assessment == 'Родич не надав інформацію' or 'Родич' in cost_assessment:
        return cost_assessment
    elif cost_assessment.isdigit():
        return int(cost_assessment)
    else:
        raise BaseException("Cost assessment cannot be parsed")


# parser for step_03
def get_property_entries(step3_data: list[dict]) -> list[Property]:
    property_list: list[Property] = []
    for entry_ in step3_data:
        if 'city_txt' in entry_:
            place = entry_['city_txt']
        elif 'city' in entry_:
            place = entry_['city']
        elif 'ua_cityType' in entry_:
            place = entry_['ua_cityType']
        else:
            raise BaseException("No city or ua_cityType found")
        ownership_type = entry_['rights'][0]['ownershipType']
        if 'власність' in ownership_type.lower():
            owners = {}
            for item in entry_['rights']:
                if 'percent-ownership' in item:
                    owners[item['rightBelongs']] = item['percent-ownership']
                elif 'percentownership' in item:
                    owners[item['rightBelongs']] = item['percentownership']
                elif len(item.keys()) == 2 and 'ownershipType' in item and 'rightBelongs' in item:
                    owners[item['rightBelongs']] = '100'
                else:
                    raise BaseException(f'ownership percentage is absent in step_3 for step3_data entry {entry_}')
        else:
            # для випадків типу оренди - тоді ключ - той, хто використовує/розпоряджається згідно декларації
            owners = {entry_['rights'][0]['rightBelongs'] : '0'}
        if 'cost_date_assessment' in entry_ and entry_['cost_date_assessment']:
            cost = _parse_cost_assessment(entry_['cost_date_assessment'])
        elif 'costAssessment' in entry_ and entry_['costAssessment']:
            cost = _parse_cost_assessment(entry_['costAssessment'])
        else:
            raise BaseException(f'No cost assessment found for step3_data entry {entry_}')
        property_ = Property(place=place, property_type=entry_['objectType'],
                             acquire_date=entry_['owningDate'], total_area=float(entry_['totalArea'].replace(',', '.')),
                             ownership_type=ownership_type, owners=owners, cost=cost)
        property_list.append(property_)
    return property_list
# -------------------------------

# -------------------------------
# Vehicle
class Vehicle:
    def __init__(self, vehicle_type: str, brand: str, model: str, manufacture_year: str|int,
                 acquire_date: str, owners: dict[int: str], cost: str|int):
        self.vehicle_type: str = vehicle_type.lower()
        self.brand: str = brand
        self.model: str = model
        self.manufacture_year: int = _get_year(manufacture_year)
        self.acquire_date: str = acquire_date
        self.owners: dict[int: str] = owners
        self.cost: int|str = cost

    def get_acquire_year(self) -> int:
        if len(self.acquire_date) == 4 and self.acquire_date.isdecimal():
            return int(self.acquire_date)
        elif len(self.acquire_date) > 4:
            return int(self.acquire_date[-4:])
        else:
            raise BaseException(f'Exception: Could not get year from acquisition date for vehicle {self.__repr__()}')

    def get_changes_since(self, other):
        change: str = ''
        #TODO add difference checks
        if self.owners != other.owners:
            change += f'\n  - власники змінились {self.__repr__()}' # TODO expand on this
        if not self.cost and other.cost:
            change += f'\n  - вартість була вказана у попередній декларації: {other.cost} , але не вказана у цій.'
        elif self.cost:
            if not other.cost:
                change += f'\n  - вартість не була вказана раніше, проте вказана зараз: {self.cost} грн.'
            elif self.cost != other.cost:
                change += f'\n  - вартість змінилась із {other.cost} грн на {self.cost} грн.'
        if self.acquire_date != other.acquire_date:
            change += f'\n  - дата набуття змінилась із {other.acquire_date} на {self.acquire_date}'
        if len(change) != 0:  # or simply if(change) ?
            change = f'{self.__repr__()}:' + change
        else:
            change = f'Змін не виявлено:   {self.__repr__()}'
        return change

    def __eq__(self, other):
        return (self.model.lower() == other.model.lower()
                and self.brand.lower() == other.brand.lower()
                and self.manufacture_year == other.manufacture_year )

    def __str__(self):
        return (f'Транспортний засіб {self.brand} {self.model}, {self.manufacture_year} року випуску. '
                f'Дата набуття: {self.acquire_date}, задекларована вартість: {self.cost} грн')

    def __repr__(self):
        return self.__str__()


# ------ Tools -------
def _parse_cost(cost_: str) -> int | str:
    if (not cost_
            or cost_ == '[Не застосовується]'
            or cost_ == '[Не відомо]'
            or cost_ == 'Не вказано'
            or cost_ == '[Не вказано]'):
        return ''
    elif cost_.isdecimal():
        return int(cost_)
    elif cost_.isnumeric():
        return int(float(cost_))
    else:
        raise ValueError("Cost cannot be parsed correctly")

def _get_year(year: str | int):
    if year.isdecimal():
        return int(year)
    elif len(year) > 4:
        return int(year[-4:])
    else:
        raise ValueError('Cannot parse manufacture year')

# parser for step_06
def get_vehicle_entries(step6_data: list[dict]) -> list[Vehicle]:
    vehicle_list: list[Vehicle] = []
    for entry_ in step6_data:
        ownership_type = entry_['rights'][0]['ownershipType']
        if 'власність' in ownership_type.lower():
            owners = {}
            for item in entry_['rights']:
                if len(item.keys()) == 2 and 'ownershipType' in item and 'rightBelongs' in item:
                    owners[item['rightBelongs']] = '100'
                else:
                    raise BaseException(f'ownership is shared in step_6 for step6_data entry {entry_}')
        else:
            # для випадків типу оренди - тоді ключ - той, хто використовує/розпоряджається згідно декларації
            owners = {entry_['rights'][0]['rightBelongs'] : '0'}
        cost_parsed = _parse_cost(entry_['costDate'])
        vehicle_ = Vehicle(entry_['objectType'], entry_['brand'], entry_['model'], entry_['graduationYear'],
                           entry_['owningDate'], owners, cost_parsed)
        vehicle_list.append(vehicle_)
    return vehicle_list
# -------------------------------

# -------------------------------
# Earnings
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


# -------- Tools ----------

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
def sum_taxed_and_split_by_person(earnings_entries: list[EarningsEntry]) -> dict[str|int, int|float]:
    earnings_by_person = {}
    for entry_ in earnings_entries:
        if str(entry_.owner) in earnings_by_person:
            earnings_by_person[entry_.owner] += round(entry_.amount_taxed, 2)
        else:
            earnings_by_person[entry_.owner] = round(entry_.amount_taxed, 2)
            log.debug(f'earnings entries taxed, split by person and summed up, result: {earnings_by_person}')
    return earnings_by_person

def get_total_earnings(earnings_entries: list[EarningsEntry]) -> int:
    return sum([entry_.amount for entry_ in earnings_entries])
# -------------------------------

# -------------------------------
# Savings
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

# converter + splitter for step_12
# soon to be deprecated
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
def get_total_converted_avg(savings_by_currency: dict[str, int|float], year: str|int) -> int|float:
    return sum( [to_uah_by_yearly_avg(curr, amount, year) for (curr, amount) in savings_by_currency.items()] )
# -------------------------------


# -------------------------------------------------
# Main part
report = init_new_report()


# --- Utils ----------------
def unify_name(full_name) -> str:
    return '+'.join(full_name.casefold().split())

def sort_decls_by_date(declarations) -> list[Declaration]:
    from operator import attrgetter
    return sorted(declarations, key=attrgetter('year', 'submit_date'))

def get_sorted_major_declarations(declarations) -> list[Declaration]:
    return sort_decls_by_date( filter(lambda decl_: not decl_.minor, declarations) )

def get_sorted_minor_declarations(declarations) -> list[Declaration]:
    return sort_decls_by_date( filter(lambda decl_: decl_.minor, declarations) )

def remove_incorrect_declarations(declarations) -> list[Declaration]:
    result = declarations.copy()
    for decl_ in declarations:
        if not decl_.minor and decl_.type_ == 3:
            for decl2_ in result:
                if ( (decl2_.year == decl_.year) and (decl2_.type_ != decl_.type_)
                        and (decl2_.declaration_type == decl_.declaration_type)):
                    result.remove(decl2_)
    return result


# --------------------------

# --- Loading\parsing ------
def get_all_declarations_by_name(full_name) -> dict[str, object]:
    url = LIST_ADDRESS + unify_name(full_name)
    print(url)
    response = requests.get(url)
    # print(response.text)

    data = json.loads(response.text)
    log.info('declarations found: ' + str(data['count']))
    # returns json with all declarations found for this name
    return data


def parse_declaration_cards(data) -> list[Declaration]:
    declarations = []
    for item in data['data']:
        declaration = Declaration(item['declaration_type'], item['id'],
                                  item['user_declarant_id'], item['date'],
                                  item['declaration_year'], item['type'],
                                  item['corruption_affected'])
        declarations.append(declaration)
        # print(str(declaration))
    # returns list of Declaration objects
    return declarations


# loads full info about declaration from respective page
# returns the same object that was passed as parameter
def load_full_declaration(declaration) -> Declaration:
    url = DOC_ADDRESS + declaration.declaration_id
    log.debug(f'Loading full declaration, request address: {url}')
    # print(url)
    response = requests.get(url)
    data = json.loads(response.text)
    log.debug(f'Declaration {declaration.written_type} for {declaration.year} loaded, jsonified response: \n  {data}')

    log.debug('Parsing loaded declaration')
    declaration.full_name = (  data['data']['step_1']['data']['lastname'] + ' '
                             + data['data']['step_1']['data']['firstname'] + ' '
                             + data['data']['step_1']['data']['middlename'])

    for i_ in range(2, 17):
        if (('isNotApplicable' in data['data']['step_' + str(i_)])
                and (str(data['data']['step_' + str(i_)]['isNotApplicable']) == '1' )):
            log.info(f'Step {i_} missed, isNotApplicable is true for this step')
            if i_ == 2:
                log.warning(f'No persons found in declaration {declaration.declaration_id}')
                report.add_record(ReportLevel.STEP, 'No family members declared in this declaration')
            if i_ == 3:
                log.warning(f'No real estate property found in declaration {declaration.declaration_id}')
            if i_ == 6:
                log.warning(f'No vehicles found in declaration {declaration.declaration_id}')
            if i_ == 11:
                log.warning(f'Earnings not found in declaration {declaration.declaration_id}')
                # report.add_record(ReportLevel.STEP, 'No earnings declared in this declaration', critical=3)
            if i_ == 12:
                log.warning(f'Savings not found in declaration {declaration.declaration_id}')
                # report.add_record(ReportLevel.STEP, 'No savings declared in this declaration', critical=3)
            continue
        if 'data' in data['data']['step_' + str(i_)]:
            log.debug(f'data found for step {i_}')
            declaration.data['step_' + str(i_)] = data['data']['step_' + str(i_)]['data']
            if i_ == 2: # Члени сім'ї та пов'язані особи
                try:
                    declaration.persons = get_person_entries(data['data']['step_' + str(i_)]['data'])
                    log.debug('related persons loaded')
                except KeyError:
                    log.error(f'KeyException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                              f'while loading full declaration, step 2')
                    log.exception('')
                # add main figure to the list of related persons - to resolve references in property and savings/earnings
                try:
                    declaration.persons['1'] = get_self_entry(data['data']['step_1']['data'])
                    log.debug('key figure added as a person with id: 1, relation type: self')
                except KeyError:
                    log.error(f'KeyException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                              f'while loading full declaration, step 2')
                    log.exception('')
            if i_ == 3:  # Нерухомість
                try:
                    declaration.property_list = get_property_entries(data['data']['step_' + str(i_)]['data'])
                except KeyError:
                    log.error(f'KeyException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                              f'while loading full declaration, step 3')
                    log.exception('')
                except BaseException as e:
                    log.error(f'BaseException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                              f'while loading full declaration, step 3')
                    log.exception(e)
            if i_ == 6:  # Рухоме майно (транспортні засоби)
                try:
                    declaration.vehicle_list = get_vehicle_entries(data['data']['step_' + str(i_)]['data'])
                except KeyError:
                    log.error(
                        f'KeyException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                        f'while loading full declaration, step 6')
                    log.exception('')
                except BaseException as e:
                    log.error(
                        f'BaseException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                        f'while loading full declaration, step 6')
                    log.exception(e)
            if i_ == 11:  # Доходи, у тому числі подарунки
                declaration.earnings = get_earnings_entries(data['data']['step_' + str(i_)]['data'])
                log.debug('earnings loaded')
                declaration.earnings_by_person = sum_taxed_and_split_by_person(declaration.earnings)
                log.debug('earnings taxed and split by person')
            if i_ == 12:  # Грошові активи
                declaration.savings = get_savings_entries(data['data']['step_' + str(i_)]['data'])
                log.debug('savings loaded')
                # TODO line below works incorrectly, needs to be rewritten
                # declaration.savings_by_person = convert_and_split_by_person_v1(declaration.savings, declaration.year)
                declaration.savings_by_prsn_and_curr = split_by_person_avg(declaration.savings)
                declaration.savings_by_currency = sum_savings_by_currency_avg(declaration.savings)
                log.debug('savings split by person')

    return declaration

# ----------------------------

# --- Comparison functions ---
#compares two full declarations
def run_comparison(prev_decl: Declaration, curr_decl: Declaration):
    report.add_record(ReportLevel.TOP, f'Декларація {curr_decl.written_type} за {curr_decl.year} рік.'
                                       f'           {REGULAR_DECL_VIEW_ADDRESS+curr_decl.declaration_id}')
    log.debug(f'Report row added: Declaration {curr_decl.written_type}, year {curr_decl.year}')

    # compare property - step 3
    if not bool(curr_decl.property_list):
        report.add_record(ReportLevel.STEP, 'Нерухомість:   Не задекларовано жодного об\'єкта нерухомості')
    else:
        report.add_record(ReportLevel.STEP, 'Нерухомість: ')
    compare_property_list(prev_decl, curr_decl) # if curr is emtpy, reports removed if any

    # compare cars - step 6
    if not bool(curr_decl.vehicle_list):
        report.add_record(ReportLevel.STEP, 'Рухоме майно (транспортні засоби) - не задекларовано')
    else:
        report.add_record(ReportLevel.STEP, 'Рухоме майно: ')
    compare_vehicle_list(prev_decl, curr_decl) # should it be here or in the else block above?

    # compare earnings - step 11
    if not bool(curr_decl.earnings_by_person):
        report.add_record(ReportLevel.STEP, 'Доходи: Не задекларовано жодних доходів', critical=3)
        total_income_taxed = 0
    else:
        report.add_record(ReportLevel.STEP, 'Доходи: ')
        total_income = sum([entry_.amount for entry_ in curr_decl.earnings])
        report.add_record(ReportLevel.DETAILS, f'Загальний задекларований дохід: {total_income}')
        total_income_taxed = sum([entry_.amount_taxed for entry_ in curr_decl.earnings])
        report.add_record(ReportLevel.DETAILS,
                          f'Загальний задекларований дохід після вирахування податків: {total_income_taxed}  '
                          f' (податки вирахувані лише із відповідних категорій доходів)')

    # compare savings - step 12
    if not bool(curr_decl.savings_by_currency): # fool check
        curr_decl.savings_by_currency = sum_savings_by_currency_avg(curr_decl.savings)
    if not bool(curr_decl.savings_by_currency):
        report.add_record(ReportLevel.STEP, 'Грошові активи: Не задекларовано жодних грошових активів', critical=3)
        get_savings_diff_by_person_v2(prev_decl, curr_decl) # to print all those who were in previous declaration, but aren't present here
    else:
        log.debug(curr_decl.savings_by_currency)
        report.add_record(ReportLevel.STEP, 'Грошові активи: ')
        # code below is deprecated, rewrite if ratio for savings/income by person is needed
        # savings_diff_by_person_ = get_savings_diff_by_person_v1(prev_decl, curr_decl)
        # percentage_by_person_ = get_savings_percentage_by_person(prev_decl.earnings_by_person, savings_diff_by_person_)
        # for person_, percentage_ in percentage_by_person_.items():
        #     log.debug(f'Percentage of accumulated savings by person between following declarations: '
        #                 f'\'{prev_decl.written_type}\' for {prev_decl.year} '
        #                 f'and \'{curr_decl.written_type}\' for {curr_decl.year} : '
        #                 f'\n {person_} - {percentage_}')
        #     report.add_record(ReportLevel.DETAILS,
        #                       f'Особа {curr_decl.get_person_name_by_id(person_)} - приріст грошових активів '
        #                       f'склав близько {percentage_:.0%} від задекларованих доходів за цей рік',
        #                       critical=1)

        # to print all those who were in previous declaration, but aren't present here
        # without using returned value
        get_savings_diff_by_person_v2(prev_decl, curr_decl)

        report.add_record(ReportLevel.DETAILS, f'Загальний стан задекларованих рахунків: {curr_decl.savings_by_currency}')
        savings_diff = get_savings_diff_by_avg(prev_decl,curr_decl)
        diff_total = get_total_converted_avg(savings_diff, curr_decl.year)
        if diff_total != 0: # if there were any changes
            report.add_record(ReportLevel.DETAILS, f'Зміни з попередньої декларації: {savings_diff}')
            sign_ = '+' if diff_total >= 0 else '-'
            report.add_record(ReportLevel.DETAILS, f'Сума змін на всіх грошових рахунках (у гривневому еквіваленті, за середньорічним курсом): {sign_}{diff_total}')
            # TODO add total diff in range
            if total_income_taxed and total_income_taxed != 0:
                ratio_avg = diff_total / total_income_taxed
                report.add_record(ReportLevel.DETAILS, f'Сума змін на всіх грошових рахунках склала близько {ratio_avg:.0%} від задекларованих доходів (після вирахування податків)')
            elif diff_total > 0:
                report.add_record(ReportLevel.DETAILS, f'Сума змін на рахунках склала {sign_}{diff_total}, але жодних доходів не було задекларовано', critical=3)
        else:
            report.add_record(ReportLevel.DETAILS, f'Змін у задекларованих рахунках не зафіксовано (перерозподіл коштів між членами родини ігнорується)')
        # TODO complete this part (what is there to complete, past me? I forgot)



# returns amount of savings (converted to UAH) that each person accumulated (or lost) since previous declaration
# should be deprecated
def get_savings_diff_by_person_v1(prev_decl: Declaration, curr_decl: Declaration) -> dict[str, float]:
    diffs_by_person = {}
    # TODO: rewrite - calculate diff by currency for each person, and only then convert and get total
    if bool(prev_decl.savings_by_person) and bool(curr_decl.savings_by_person):
        for person_ in (prev_decl.savings_by_person.keys() & curr_decl.savings_by_person.keys()):
            diffs_by_person[person_] = curr_decl.savings_by_person[person_] - prev_decl.savings_by_person[person_]
        for person_ in (curr_decl.savings_by_person.keys() - prev_decl.savings_by_person.keys()):
            diffs_by_person[person_] = curr_decl.savings_by_person[person_]
    if bool(prev_decl.savings_by_person):
        for person_ in prev_decl.savings_by_person.keys() - curr_decl.savings_by_person.keys():
            log.info((f'There are no more savings that belong to {curr_decl.persons[person_].full_name}'
                      f' in declaration ({curr_decl.written_type}, {curr_decl.year})'))
            report.add_record(ReportLevel.DETAILS, f'There are no more savings that belong to a person with ID {person_}', critical=2)
    elif bool(curr_decl.savings_by_person):
        diffs_by_person = curr_decl.savings_by_person.copy()
    # elif bool(curr_decl.savings_by_person):
    log.debug(f'get_savings_diff_by_person_v1() executed, result: {diffs_by_person}')
    return diffs_by_person


def get_savings_diff_by_person_v2(prev_decl: Declaration, curr_decl: Declaration) -> dict[str, dict[str, str|int|float]]:
    diffs_by_person: dict[str, dict[str, str|int|float]] = defaultdict(dict) # just create emtpy dictionary
    if bool(prev_decl.savings_by_prsn_and_curr) and bool(curr_decl.savings_by_prsn_and_curr):
        for person_ in (prev_decl.savings_by_prsn_and_curr.keys() & curr_decl.savings_by_prsn_and_curr.keys()):
            # diffs_by_person[person_] = curr_decl.savings_by_person[person_] - prev_decl.savings_by_person[person_]
            for currency_ in (curr_decl.savings_by_prsn_and_curr[person_].keys() | prev_decl.savings_by_prsn_and_curr[person_].keys()):
                if currency_ not in prev_decl.savings_by_prsn_and_curr[person_].keys():
                    diffs_by_person[person_][currency_] = curr_decl.savings_by_prsn_and_curr[person_][currency_]
                elif currency_ not in curr_decl.savings_by_prsn_and_curr[person_].keys():
                    diffs_by_person[person_][currency_] = - prev_decl.savings_by_prsn_and_curr[person_][currency_] # hope it works like I want it to
                else:
                    diffs_by_person[person_][currency_] = curr_decl.savings_by_prsn_and_curr[person_][currency_] - prev_decl.savings_by_prsn_and_curr[person_][currency_]
        for person_ in (curr_decl.savings_by_prsn_and_curr.keys() - prev_decl.savings_by_prsn_and_curr.keys()):
            diffs_by_person[person_] = curr_decl.savings_by_prsn_and_curr[person_]
        # for every person that had savings declared in previous declaration, but does not have now
        for person_ in prev_decl.savings_by_prsn_and_curr.keys() - curr_decl.savings_by_prsn_and_curr.keys():
            log.debug(f'no more person savings. previous list: {prev_decl.savings_by_prsn_and_curr.keys()}')
            log.debug(f'no more person savings. current list: {curr_decl.savings_by_prsn_and_curr.keys()}')
            log.debug(f'no more person savings. person id: {person_}')
            log.info((f'There are no more savings that belong to a person with ID {person_}'
                      f' in declaration ({curr_decl.written_type}, {curr_decl.year})'))
            report.add_record(ReportLevel.DETAILS, f'There are no more savings that belong to {curr_decl.persons[person_].full_name} ({curr_decl.persons[person_].relation_type})', critical=2)
    # if current declaration has no savings, then report every person as the one whose savings are not declared now
    elif bool(prev_decl.savings_by_prsn_and_curr):
        for person_ in prev_decl.savings_by_prsn_and_curr.keys():
            log.info((f'There are no more savings that belong to a person with ID {person_}'
                      f' in declaration ({curr_decl.written_type}, {curr_decl.year})'))
            report.add_record(ReportLevel.DETAILS, f'There are no more savings that belong to {curr_decl.persons[person_].full_name} ({curr_decl.persons[person_].relation_type})', critical=2)
    elif bool(curr_decl.savings_by_prsn_and_curr):
        diffs_by_person = curr_decl.savings_by_prsn_and_curr.copy()
    log.debug(f'get_savings_diff_by_person_v2() executed, result: {diffs_by_person}')
    return diffs_by_person


# returns amount of savings (converted to UAH) accumulated overall since previous declaration
# soon to be deprecated
def get_total_savings_diff_v1(prev_decl: Declaration, curr_decl: Declaration):
    diff = None
    for person_ in prev_decl.savings_by_person.keys() & curr_decl.savings_by_person.keys():
        diff += curr_decl.savings_by_person[person_] - prev_decl.savings_by_person[person_]
    for person_ in curr_decl.savings_by_person.keys() - prev_decl.savings_by_person.keys():
        diff += curr_decl.savings_by_person[person_]
    for person_ in prev_decl.savings_by_person.keys() ^ curr_decl.savings_by_person.keys():
        # TODO add warnings
        # TODO add report output
        continue # replace with reports and warnings
    # TODO add report output
    if diff is None:
        log.warning(f'Something wrong in get_overall_savings_diff() - final difference is None.  '
                    f'\n Previous declaration: {prev_decl}; \n Current declaration: {curr_decl}')
    log.debug(f'get_overall_savings_diff() called, result:  {diff}')
    return diff


# returns percentage of savings accumulated by person related to their declared earnings
# is it deprecated?
def get_savings_percentage_by_person(earnings_by_person: dict[str, float], savings_diff_by_person: dict[str, float]):
    ratios = {}
    for person_ in savings_diff_by_person.keys():
        if person_ not in earnings_by_person.keys():
            log.warning(f'There are accumulated savings, but no earnings for a person with ID {person_}')
        ratios[person_] = savings_diff_by_person[person_] / earnings_by_person[person_]
    log.debug(f'get_savings_percentage_by_person called, result: {ratios}')
    return ratios


# returns percentage of savings accumulated in total related to declared earnings (in one declaration)
# soon to be deprecated
def get_total_savings_to_earnings_ratio_v1(prev_decl: Declaration, curr_decl: Declaration):
    total_savings = get_total_savings_diff_v1(prev_decl, curr_decl)
    total_earnings = sum(curr_decl.earnings_by_person.values())
    log.info(f'Total percentage of earnings: {(total_earnings / total_savings):.0%}')
    return total_savings / total_earnings

# returns difference in savings (accumulated since last declaration) by currency
def get_savings_diff_by_avg(prev_decl: Declaration, curr_decl: Declaration) -> dict[str, int|float]:
    savings_diff: dict[str, int|float] = {}
    for curr in (curr_decl.savings_by_currency.keys() - prev_decl.savings_by_currency.keys()):
        savings_diff[curr] = curr_decl.savings_by_currency[curr] # save new currency entries as is
    for curr in (prev_decl.savings_by_currency.keys() - curr_decl.savings_by_currency.keys()):
        savings_diff[curr] = - prev_decl.savings_by_currency[curr] # amount for removed currencies are saved as negative
    for curr in (prev_decl.savings_by_currency.keys() & curr_decl.savings_by_currency.keys()):
        savings_diff[curr] = curr_decl.savings_by_currency[curr] - prev_decl.savings_by_currency[curr]
    log.debug(f'get_savings_diff_by_avg() executed for declaration [{curr_decl.declaration_id}] '
              f'and previous one [{prev_decl.declaration_id}], result: {savings_diff}')
    return savings_diff


# TODO complete  (is it needed?)
def compare_savings_and_earnings(prev_decl: Declaration, curr_decl: Declaration):
    if curr_decl.savings_by_currency:
        savings_by_curr = curr_decl.savings_by_currency.copy()
    else:
        savings_by_curr = sum_savings_by_currency_avg(curr_decl.savings)
        curr_decl.savings_by_currency = savings_by_curr.copy()
    savings_diff = get_savings_diff_by_avg(prev_decl, curr_decl)
    # if this one is going to contain all of the code for step_12 for run_comparison, then it should be like that:
    # 1. show overall difference in savings
    # 2. show overall ratio savings / income (taxed)
    pass

# compares changes in declared property and reports differences
def compare_property_list(prev_decl: Declaration, curr_decl: Declaration):
    removed_ = [prop for prop in prev_decl.property_list if prop not in curr_decl.property_list]
    added_ = [prop for prop in curr_decl.property_list if prop not in prev_decl.property_list]
    for prop in removed_:
        log.debug(f'Removed property: {prop}')
        report.add_record(ReportLevel.DETAILS, f'Видалено нерухомість: {prop}')
    for prop in added_:
        log.debug(f'Added property: {prop}')
        report.add_record(ReportLevel.DETAILS, f'Додано нерухомість: {prop}')
        # if str(curr_decl.year) in prop.acquire_date or :
        #     report.add_record(ReportLevel.DETAILS, f'')
    for prop in curr_decl.property_list:
        for old_prop in prev_decl.property_list:
            if prop == old_prop:
                change_ = prop.get_changes_since(old_prop)
                if change_:
                    log.debug(f'Property change computed, concatenated outcome: {change_}')
                    report.add_record(ReportLevel.DETAILS, change_)
        if prop.get_year_acquired() >= (curr_decl.year-2): # check recent purchases/acquisitions
            if not prop.cost:
                log.debug(f'Property price not declared, but acquisition date is recent for property: {prop}')
                report.add_record(ReportLevel.DETAILS, f'Власність набута нещодавно, проте вартість не вказана: {prop}')
            elif not str(prop.cost).isdigit() and 'родич' in prop.cost.lower():
                log.debug(f'Property price not declared by a relative, but acquisition date is recent for property: {prop}')
                report.add_record(ReportLevel.DETAILS, f'Власність набута родичами нещодавно, проте родичі не надали інформацію про ціну: {prop}')


def compare_vehicle_list(prev_decl: Declaration, curr_decl: Declaration):
    added_ = [vehicle for vehicle in curr_decl.vehicle_list if vehicle not in prev_decl.vehicle_list]
    removed_ = [vehicle for vehicle in prev_decl.vehicle_list if vehicle not in curr_decl.vehicle_list]
    for vehicle in removed_:
        log.debug(f'Removed vehicle: {vehicle}')
        report.add_record(ReportLevel.DETAILS, f'Видалено нерухоме майно (транспортний засіб): {vehicle}')
    for vehicle in added_:
        log.debug(f'Added vehicle: {vehicle}')
        report.add_record(ReportLevel.DETAILS, f'Додано нерухоме майно (транспортний засіб): {vehicle}')
    for vehicle in curr_decl.vehicle_list:
        for old_vehicle in prev_decl.vehicle_list:
            if vehicle == old_vehicle:
                change_ = vehicle.get_changes_since(old_vehicle)
                if change_:
                    log.debug(f'Changes in vehicle list computed, concatenated outcome: {change_}')
                    report.add_record(ReportLevel.DETAILS, change_)
        if vehicle.get_acquire_year() >= (curr_decl.year - 2) and (not vehicle.cost or not str(vehicle.cost).isdecimal()):
            log.debug(f'Vehicle price not declared, but acquisition date is recent for property: {vehicle}')
            report.add_record(ReportLevel.DETAILS,
                        f'Рухоме майно (транспортний засіб) набуте нещодавно, проте вартість не вказана: {vehicle}')


# ----------------------------

def check_person(full_name):
    global report
    report = init_new_report()
    declarations_json = get_all_declarations_by_name(full_name)
    declarations_list = parse_declaration_cards(declarations_json)

    major_declarations = get_sorted_major_declarations(declarations_list)
    major_declarations = remove_incorrect_declarations(major_declarations)
    # print(major_declarations)
    minor_declarations = get_sorted_minor_declarations(declarations_list)

    year_range = (major_declarations[0].year, major_declarations[-1].year)
    report.add_top_info(full_name, year_range)

    for decl in major_declarations:
        load_full_declaration(decl)

    for i_ in range(1, len(major_declarations)):
        # print(major_declarations[i_])
        run_comparison(major_declarations[i_-1], major_declarations[i_])
        report.add_empty_line()
    print(report)



if __name__ == '__main__':
    # name = ' прокоф’єв олександр іванович '
    name = 'Андріяш Микола Михайлович'
    check_person(name)


