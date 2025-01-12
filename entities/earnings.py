import logging as log

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
def sum_taxed_and_split_by_person(earnings_entries: list[EarningsEntry]):
    earnings_by_person = {}
    for entry_ in earnings_entries:
        if str(entry_.owner) in earnings_by_person:
            earnings_by_person[entry_.owner] += round(entry_.amount_taxed, 2)
        else:
            earnings_by_person[entry_.owner] = round(entry_.amount_taxed, 2)
            log.debug(f'earnings entries taxed, split by person and summed up, result: {earnings_by_person}')
    return earnings_by_person
