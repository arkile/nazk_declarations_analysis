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
        line.replace('\n', '\n' + ('\t' * (report_level.value - 1)))
        if critical == 2:
            line_ = '! ' + line + ' !'
            self.text += line_
            self.summary += f'\n {line_}'
        elif critical == 3:
            line_ = '!!! ' + line + ' !!!'
            self.text += line_
            self.summary += f'\n {line_}'
        else:
            self.text += line
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