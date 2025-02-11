
# TODO rewrite as dataclass
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
            change = f'Змінені дані:\n      {self.__repr__()}:' + change
        else:
            change = f'Змін не виявлено:\n   {self.__repr__()}'
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