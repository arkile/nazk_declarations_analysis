
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
        self.cost: int = int(cost)

    def has_changed(self, other):
        change:str = ''
        if self.owners != other.owners:
            change += f'Warning: owners changed of {self.__repr__()} \n' # TODO expand on this
        if self.cost != other.cost:
            change += f'Warning: cost of property changed from {self.cost} to {other.cost}. {self.__repr__()} \n'
        if self.ownership_type != other.ownership_type:
            change += f'Warning: ownership type changed from {self.ownership_type} to {other.ownership_type}. {self.__repr__()} \n'
        if (self.place.lower() != other.place.lower()
                and self.place.lower() not in other.place.lower()
                and other.place.lower() not in self.place.lower()):
            change += f'Warning: place changed from {self.place} to {other.place}. {self.__repr__()} \n'
        return change

    def __eq__(self, other):
        return (self.property_type == other.property_type
                and self.total_area == other.total_area
                and self.acquire_date == other.acquire_date)

    def __str__(self):
        return f"Property '{self.property_type}' (acquired: {self.acquire_date}, total area:{self.total_area})"

    def __repr__(self):
        return self.__str__()


# -------- Tools ----------

def is_valid_cost_assessment(cost_assessment: str) -> bool:
    if not cost_assessment:
        return False
    elif cost_assessment == '[Не застосовується]':
        return False
    elif cost_assessment.isdigit():
        return True
    else:
        raise BaseException("Cost assessment is not valid")

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
            cost = is_valid_cost_assessment(entry_['cost_date_assessment'])
        elif 'costAssessment' in entry_ and entry_['costAssessment']:
            cost = is_valid_cost_assessment(entry_['costAssessment'])
        else:
            raise BaseException("No cost assessment found")
        property_ = Property(place=place, property_type=entry_['objectType'],
                             acquire_date=entry_['owningDate'], total_area=float(entry_['totalArea']),
                             ownership_type=ownership_type, owners=owners, cost=cost)
        property_list.append(property_)
    return property_list