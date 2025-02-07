import os
from dataclasses import dataclass
from enum import Enum
from docx import *

class ReportLevel(Enum):
    TOP = 1
    STEP = 2
    DETAILS = 3

@dataclass
class Entry:
    text: str
    level: ReportLevel
    criticality: int


class GeneralReport(object):

    def __init__(self):
        self.full_name = None
        self.period = None
        self.entry_list: list[Entry] = []
        # self.text = ''
        # self.summary = ''


    def add_header(self, full_name: str, period: tuple[int, int]):
        self.full_name = full_name
        # self.text += '\n' + f'{period[0]} - {period[1]}'
        self.period = period

    # TODO for backward compatibility, remove later
    def add_top_info(self, full_name: str, period: tuple[int, int]):
        self.add_header(full_name, period)

    # critical level:
    # 1 - regular info
    # 2 - questionable information - may be a risk, may not
    # 3 - very likely to be a risk
    def add_record(self, report_level: ReportLevel, line: str, critical: int = 1):
        self.entry_list.append(Entry(text=line, level=report_level, criticality=critical))


    def print_to_docx(self):
        doc = Document()
        doc.add_heading(self.full_name, level=1)
        doc.add_heading(f'{self.period[0]} - {self.period[1]}', level=2)

        doc.add_paragraph(self.full_name)

        for entry in self.entry_list:
            match entry.level:
                case ReportLevel.TOP:
                    doc.add_heading(entry.text, level=3)
                case ReportLevel.STEP:
                    paragraph = doc.add_paragraph()
                    paragraph.add_run(entry.text).bold = True
                case ReportLevel.DETAILS:
                    paragraph = doc.add_paragraph()
                    paragraph.add_run(entry.text)
        if os.path.exists('report.docx'):
            os.remove('report.docx')
        doc.save('report.docx')


    def __str__(self):
        text = self.full_name
        text += '\n' + f'{self.period[0]} - {self.period[1]}'
        for entry_ in self.entry_list:
            text += '\n'
            text += '\t' * (entry_.level.value - 1)
            line_ = entry_.text.replace('\n', '\n' + ('\t' * (entry_.level.value - 1)), -1)
            if entry_.criticality == 2:
                line_ = '! ' + line_ + ' !'
                text += line_
                # self.summary += f'\n {line_}'
            elif entry_.criticality == 3:
                line_ = line_ + ' !!!!!!!'
                text += line_
                # self.summary += f'\n {line_}'
            else:
                text += line_
        return text


    def __repr__(self):
        #TODO rewrite
        return self.__str__()
    # --- class Report end ---


def init_new_report():
    return GeneralReport()