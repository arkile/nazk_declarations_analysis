
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

    def has_changed(self, other):
        change:str = ''
        if self.owners != other.owners:
            change += f'Власники змінились {self.__repr__()} \n' # TODO expand on this
        if self.ownership_type != other.ownership_type:
            change += f'Тип власності змінився з {self.ownership_type} на {other.ownership_type}. \n'
        if (self.place.lower() != other.place.lower()
                and self.place.lower() not in other.place.lower()
                and other.place.lower() not in self.place.lower()):
            change += f'Місце реєстрації змінилось із {self.place} на {other.place} (тип, площа та дата набуття однакові). \n'
        if not self.cost and other.cost:
            change += f'Вартість була вказана у попередній декларації: {other.cost} , але не вказана у цій. \n'
        elif not other.cost and self.cost:
            change += f'Вартість не була вказана раніше, проте вказана зараз: {self.cost} . \n'
        elif self.cost and other.cost and self.cost != other.cost:
            change += f'Вартість змінилась із {self.cost} на {other.cost}. \n'

        if len(change) != 0:  # or simply if(change) ?
            change += f'{self.__repr__()} \n'
        return change

    def get_year_acquired(self):
        if len(self.acquire_date) == 4:
            _year = self.acquire_date
        else:
            _year = self.acquire_date[-4:]
        assert(len(_year) == 4)
        return _year

    def __eq__(self, other):
        return (self.property_type == other.property_type
                and self.total_area == other.total_area
                and self.acquire_date == other.acquire_date)

    def __str__(self):
        return f"Property '{self.property_type}' (acquired: {self.acquire_date}, total area:{self.total_area})"

    def __repr__(self):
        return self.__str__()


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
        if 'city' in entry_:
            place = entry_['city']
        elif 'ua_cityType' in entry_:
            place = entry_['ua_cityType']
        else:
            raise BaseException("No city or ua_cityType found")
        ownership_type = entry_['rights'][0]['ownershipType']
        owners = {item['rightBelongs'] : item['percent-ownership'] for item in entry_['rights']}
        if 'cost_date_assessment' in entry_ and entry_['cost_date_assessment']:
            cost = _parse_cost_assessment(entry_['cost_date_assessment'])
        elif 'costAssessment' in entry_ and entry_['costAssessment']:
            cost = _parse_cost_assessment(entry_['costAssessment'])
        else:
            raise BaseException("No cost assessment found")
        property_ = Property(place=place, property_type=entry_['objectType'],
                             acquire_date=entry_['owningDate'], total_area=float(entry_['totalArea']),
                             ownership_type=ownership_type, owners=owners, cost=cost)
        property_list.append(property_)
    return property_list