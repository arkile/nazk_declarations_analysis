
# TODO rewrite as dataclass
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

