from .declaration_details import Person, Property
from .finances import SavingsEntry, EarningsEntry

# TODO rewrite as dataclass
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
        self.savings: list[SavingsEntry] = []
        self.earnings: list[EarningsEntry] = []
        self.savings_by_person: dict[str|int, int|float] = {}
        self.earnings_by_person: dict[str|int, int|float] = {}
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
