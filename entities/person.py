
# TODO rewrite as dataclass
class Person:
    def __init__(self, person_id: str|int, full_name: str, relation_type: str, mentions: list[str|int]):
        if not person_id.isdigit():
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


