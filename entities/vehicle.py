
#TODO rewrite as dataclass
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
            change = f'Змін не виявлено:\n   {self.__repr__()}'
        return change

    def __eq__(self, other):
        return (self.model.lower() == other.model.lower()
                and self.brand.lower() == other.brand.lower()
                and self.manufacture_year == other.manufacture_year )

    def __str__(self):
        if self.cost:
            price_str = f'{self.cost} грн'
        else:
            price_str = 'не вказано'
        return (f'Транспортний засіб {self.brand} {self.model}, {self.manufacture_year} року випуску. '
                f'Дата набуття: {self.acquire_date}, задекларована вартість: {price_str}')

    def __repr__(self):
        return self.__str__()


# ------ Tools -------
def _parse_cost(cost_: str) -> int | str:
    if (not cost_
            or cost_ == '[Не застосовується]'
            or cost_ == '[Не відомо]'
            or cost_ == 'Не вказано'
            or cost_ == '[Не вказано]'
            or cost_ == '[Член сім\'ї не надав інформацію]'):
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
                if len(entry_['rights']) == 1 and 'ownershipType' in item and 'rightBelongs' in item:
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

