from collections import defaultdict

import requests
import json

import reports
from entities.declaration import *
from entities.earnings import *
from entities.savings import *
from entities.person import *
from entities.property import *
from entities.vehicle import get_vehicle_entries
from reports import *

import logging as log

LIST_ADDRESS = 'https://public-api.nazk.gov.ua/v2/documents/list?query='

DOC_ADDRESS = 'https://public-api.nazk.gov.ua/v2/documents/'

REGULAR_DECL_VIEW_ADDRESS = 'https://public.nazk.gov.ua/documents/'

log.basicConfig(format='{asctime} [{levelname}] {message}',
                style='{',
                datefmt="%H:%M", # datefmt="%Y-%m-%d %H:%M",
                # level=log.DEBUG)
                # level=log.INFO)
                # level=log.WARNING)
                level=log.ERROR)

report = reports.init_new_report()

# --------------------------

# --- Utils ----------------
def unify_name(full_name) -> str:
    return '+'.join(full_name.casefold().split())

def sort_decls_by_date(declarations) -> list[Declaration]:
    from operator import attrgetter
    return sorted(declarations, key=attrgetter('year', 'submit_date'))

def get_sorted_major_declarations(declarations) -> list[Declaration]:
    return sort_decls_by_date( filter(lambda decl_: not decl_.minor, declarations) )

def get_sorted_minor_declarations(declarations) -> list[Declaration]:
    return sort_decls_by_date( filter(lambda decl_: decl_.minor, declarations) )

def remove_incorrect_declarations(declarations) -> list[Declaration]:
    result = declarations.copy()
    for decl_ in declarations:
        if not decl_.minor and decl_.type_ == 3:
            for decl2_ in result:
                if ( (decl2_.year == decl_.year) and (decl2_.type_ != decl_.type_)
                        and (decl2_.declaration_type == decl_.declaration_type)):
                    result.remove(decl2_)
    return result


# --------------------------

# --- Loading\parsing ------
def get_all_declarations_by_name(full_name) -> dict[str, object]:
    url = LIST_ADDRESS + unify_name(full_name)
    print(url)
    response = requests.get(url)
    # print(response.text)

    data = json.loads(response.text)
    log.info('declarations found: ' + str(data['count']))
    # returns json with all declarations found for this name
    return data


# parse response (from query for all declarations for specified name) to a list of Declaration objects
def parse_declaration_cards(data) -> list[Declaration]:
    declarations = []
    for item in data['data']:
        declaration = Declaration(item['declaration_type'], item['id'],
                                  item['user_declarant_id'], item['date'],
                                  item['declaration_year'], item['type'],
                                  item['corruption_affected'])
        declarations.append(declaration)
        # print(str(declaration))
    # returns list of Declaration objects
    return declarations


# checks if there are different people with the same full names in the list of declarations returned by api query
def check_for_namesakes(declarations: list[Declaration]) -> bool:
    id_: int = 0
    for d_ in declarations:
        if not id_:
            id_ = d_.declarant_id
        elif d_.declarant_id != id_:
            return False
    return True


# filters out all people with different declara
def filter_namesakes_for_id(declarations: list[Declaration], declarant_id: int) -> list[Declaration]:
    return [decl for decl in declarations if decl.declarant_id == declarant_id]


# loads full info about declaration from respective page
# returns the same object that was passed as parameter
def load_full_declaration(declaration) -> Declaration:
    url = DOC_ADDRESS + declaration.declaration_id
    log.debug(f'Loading full declaration, request address: {url}')
    # print(url)
    response = requests.get(url)
    data = json.loads(response.text)
    log.debug(f'Declaration {declaration.written_type} for {declaration.year} loaded, jsonified response: \n  {data}')

    log.debug('Parsing loaded declaration')
    declaration.full_name = (  data['data']['step_1']['data']['lastname'] + ' '
                             + data['data']['step_1']['data']['firstname'] + ' '
                             + data['data']['step_1']['data']['middlename'])

    for i_ in range(2, 17):
        if (('isNotApplicable' in data['data']['step_' + str(i_)])
                and (str(data['data']['step_' + str(i_)]['isNotApplicable']) == '1' )):
            log.info(f'Step {i_} missed, isNotApplicable is true for this step')
            if i_ == 2:
                log.warning(f'No persons found in declaration {declaration.declaration_id}')
                # report.add_record(ReportLevel.STEP, 'No family members declared in this declaration')
            if i_ == 3:
                log.warning(f'No real estate property found in declaration {declaration.declaration_id}')
            if i_ == 6:
                log.warning(f'No vehicles found in declaration {declaration.declaration_id}')
            if i_ == 11:
                log.warning(f'Earnings not found in declaration {declaration.declaration_id}')
                # report.add_record(ReportLevel.STEP, 'No earnings declared in this declaration', critical=3)
            if i_ == 12:
                log.warning(f'Savings not found in declaration {declaration.declaration_id}')
                # report.add_record(ReportLevel.STEP, 'No savings declared in this declaration', critical=3)
            continue
        if 'data' in data['data']['step_' + str(i_)]:
            log.debug(f'data found for step {i_}')
            declaration.data['step_' + str(i_)] = data['data']['step_' + str(i_)]['data']
            if i_ == 2: # Члени сім'ї та пов'язані особи
                try:
                    declaration.persons = get_person_entries(data['data']['step_' + str(i_)]['data'])
                    log.debug('related persons loaded')
                except KeyError:
                    log.error(f'KeyException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                              f'while loading full declaration, step 2')
                    log.exception('')
                # add main figure to the list of related persons - to resolve references in property and savings/earnings
                try:
                    declaration.persons['1'] = get_self_entry(data['data']['step_1']['data'])
                    log.debug('key figure added as a person with id: 1, relation type: self')
                except KeyError:
                    log.error(f'KeyException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                              f'while loading full declaration, step 2')
                    log.exception('')
            if i_ == 3:  # Нерухомість
                try:
                    declaration.property_list = get_property_entries(data['data']['step_' + str(i_)]['data'])
                except KeyError:
                    log.error(f'KeyException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                              f'while loading full declaration, step 3')
                    log.exception('')
                except BaseException as e:
                    log.error(f'BaseException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                              f'while loading full declaration, step 3')
                    log.exception(e)
            if i_ == 6:  # Рухоме майно (транспортні засоби)
                try:
                    declaration.vehicle_list = get_vehicle_entries(data['data']['step_' + str(i_)]['data'])
                except KeyError:
                    log.error(
                        f'KeyException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                        f'while loading full declaration, step 6')
                    log.exception('')
                except BaseException as e:
                    log.error(
                        f'BaseException caught in declaration {declaration.declaration_id}, year: {declaration.year}, '
                        f'while loading full declaration, step 6')
                    log.exception(e)
            if i_ == 11:  # Доходи, у тому числі подарунки
                declaration.earnings = get_earnings_entries(data['data']['step_' + str(i_)]['data'])
                log.debug('earnings loaded')
                declaration.earnings_by_person = sum_taxed_and_split_by_person(declaration.earnings)
                log.debug('earnings taxed and split by person')
            if i_ == 12:  # Грошові активи
                declaration.savings = get_savings_entries(data['data']['step_' + str(i_)]['data'])
                log.debug('savings loaded')
                # TODO line below works incorrectly, needs to be rewritten
                # declaration.savings_by_person = convert_and_split_by_person_v1(declaration.savings, declaration.year)
                declaration.savings_by_prsn_and_curr = split_by_person_avg(declaration.savings)
                declaration.savings_by_currency = sum_savings_by_currency_avg(declaration.savings)
                log.debug('savings split by person')

    return declaration

# ----------------------------

# --- Comparison functions ---
#compares two full declarations
def run_comparison(prev_decl: Declaration, curr_decl: Declaration):
    report.add_record(ReportLevel.TOP,
                      f'Декларація {curr_decl.written_type} за {curr_decl.year} рік.',
                      hyperlink=f'{REGULAR_DECL_VIEW_ADDRESS+curr_decl.declaration_id}')
    log.debug(f'Report row added: Declaration {curr_decl.written_type}, year {curr_decl.year}')

    # TODO rewrite every report entry and output - add checks for declaration being first to report
    if prev_decl == curr_decl:
        report.add_record(ReportLevel.STEP,
                          f'Перша декларація - ігноруйте повідомлення про зміни, буде виправлено у наступних версіях')

    # compare property - step 3
    report.add_record(ReportLevel.STEP, 'Нерухомість: ')
    if not bool(curr_decl.property_list):
        report.add_record(ReportLevel.SUBSTEP, 'Не задекларовано жодного об\'єкта нерухомості', critical=2)
    compare_property_list(prev_decl, curr_decl) # if curr is emtpy, reports removed if any

    # compare cars - step 6
    report.add_record(ReportLevel.STEP, 'Рухоме майно (транспортні засоби): ')
    if not bool(curr_decl.vehicle_list):
        report.add_record(ReportLevel.SUBSTEP, 'Не задекларовано жодного об\'єкта рухомого майна')
    compare_vehicle_list(prev_decl, curr_decl) # should it be here or in the else block above?

    # compare earnings - step 11
    report.add_record(ReportLevel.STEP, 'Доходи: ')
    if not bool(curr_decl.earnings_by_person):
        report.add_record(ReportLevel.SUBSTEP, 'Не задекларовано жодних доходів', critical=3)
        total_income_taxed = 0
    else:
        total_income = sum([entry_.amount for entry_ in curr_decl.earnings])
        report.add_record(ReportLevel.SUBSTEP, f'Загальний задекларований дохід:')
        report.add_record(ReportLevel.DETAILS, f' {total_income} грн')
        total_income_taxed = sum([entry_.amount_taxed for entry_ in curr_decl.earnings])
        report.add_record(ReportLevel.SUBSTEP,
                          f'Загальний задекларований дохід після вирахування податків '
                          f'(податки вирахувані лише із відповідних категорій доходів): ')
        report.add_record(ReportLevel.DETAILS, f' {total_income_taxed} грн')

    # compare savings - step 12
    if not bool(curr_decl.savings_by_currency): # fool check
        curr_decl.savings_by_currency = sum_savings_by_currency_avg(curr_decl.savings)
    report.add_record(ReportLevel.STEP, 'Грошові активи: ')
    if not bool(curr_decl.savings_by_currency):
        report.add_record(ReportLevel.SUBSTEP, 'Не задекларовано жодних грошових активів', critical=3)
        get_savings_diff_by_person_v2(prev_decl, curr_decl) # to print all those who were in previous declaration, but aren't present here
    else:
        log.debug(curr_decl.savings_by_currency)
        # code below is deprecated, rewrite if ratio for savings/income by person is needed
        # savings_diff_by_person_ = get_savings_diff_by_person_v1(prev_decl, curr_decl)
        # percentage_by_person_ = get_savings_percentage_by_person(prev_decl.earnings_by_person, savings_diff_by_person_)
        # for person_, percentage_ in percentage_by_person_.items():
        #     log.debug(f'Percentage of accumulated savings by person between following declarations: '
        #                 f'\'{prev_decl.written_type}\' for {prev_decl.year} '
        #                 f'and \'{curr_decl.written_type}\' for {curr_decl.year} : '
        #                 f'\n {person_} - {percentage_}')
        #     report.add_record(ReportLevel.SUBSTEP,
        #                       f'Особа {curr_decl.get_person_name_by_id(person_)} - приріст грошових активів '
        #                       f'склав близько {percentage_:.0%} від задекларованих доходів за цей рік',
        #                       critical=1)

        # to print all those who were in previous declaration, but aren't present here
        # without using returned value
        get_savings_diff_by_person_v2(prev_decl, curr_decl)

        report.add_record(ReportLevel.SUBSTEP, f'Загальний стан задекларованих рахунків: ')
        report.add_record(
            ReportLevel.DETAILS,
            ';  '.join("{}: {}".format(k, v) for k, v in dict(sorted(curr_decl.savings_by_currency.items())).items()))
        savings_diff = get_savings_diff_by_avg(prev_decl,curr_decl)
        diff_total = get_total_converted_avg(savings_diff, curr_decl.year)
        if diff_total != 0: # if there were any changes
            report.add_record(ReportLevel.SUBSTEP, f'Зміни з попередньої декларації: ')
            report.add_record(
                ReportLevel.DETAILS,
                ';  '.join("{}: {}".format(k, v) for k, v in dict(sorted(savings_diff.items())).items()))
            sign_ = '+' if diff_total >= 0 else ''
            report.add_record(ReportLevel.SUBSTEP, f'Сума змін на всіх грошових рахунках (у гривневому еквіваленті, за середньорічним курсом): ')
            report.add_record(ReportLevel.DETAILS, f' {sign_}{diff_total} ')
            # TODO add total diff in range
            if total_income_taxed and total_income_taxed != 0:
                ratio_avg = diff_total / total_income_taxed
                report.add_record(ReportLevel.SUBSTEP, f'Сума змін на всіх грошових рахунках склала близько {ratio_avg:.0%} від задекларованих доходів (після вирахування податків)')
            elif diff_total > 0:
                report.add_record(ReportLevel.SUBSTEP, f'Сума змін на рахунках склала {sign_}{diff_total}, але жодних доходів не було задекларовано', critical=3)
        else:
            report.add_record(ReportLevel.SUBSTEP, f'Змін у задекларованих рахунках не зафіксовано (перерозподіл коштів між членами родини ігнорується)')
        # TODO complete this part (what is there to complete, past me? I forgot)



# returns amount of savings (converted to UAH) that each person accumulated (or lost) since previous declaration
# should be deprecated
def get_savings_diff_by_person_v1(prev_decl: Declaration, curr_decl: Declaration) -> dict[str, float]:
    diffs_by_person = {}
    # TODO: rewrite - calculate diff by currency for each person, and only then convert and get total
    if bool(prev_decl.savings_by_person) and bool(curr_decl.savings_by_person):
        for person_ in (prev_decl.savings_by_person.keys() & curr_decl.savings_by_person.keys()):
            diffs_by_person[person_] = curr_decl.savings_by_person[person_] - prev_decl.savings_by_person[person_]
        for person_ in (curr_decl.savings_by_person.keys() - prev_decl.savings_by_person.keys()):
            diffs_by_person[person_] = curr_decl.savings_by_person[person_]
    if bool(prev_decl.savings_by_person):
        for person_ in prev_decl.savings_by_person.keys() - curr_decl.savings_by_person.keys():
            log.info((f'There are no more savings that belong to {curr_decl.persons[person_].full_name}'
                      f' in declaration ({curr_decl.written_type}, {curr_decl.year})'))
            report.add_record(ReportLevel.SUBSTEP, f'There are no more savings that belong to a person with ID {person_}', critical=2)
    elif bool(curr_decl.savings_by_person):
        diffs_by_person = curr_decl.savings_by_person.copy()
    # elif bool(curr_decl.savings_by_person):
    log.debug(f'get_savings_diff_by_person_v1() executed, result: {diffs_by_person}')
    return diffs_by_person


def get_savings_diff_by_person_v2(prev_decl: Declaration, curr_decl: Declaration) -> dict[str, dict[str, str|int|float]]:
    diffs_by_person: dict[str, dict[str, str|int|float]] = defaultdict(dict) # just create emtpy dictionary
    if bool(prev_decl.savings_by_prsn_and_curr) and bool(curr_decl.savings_by_prsn_and_curr):
        for person_ in (prev_decl.savings_by_prsn_and_curr.keys() & curr_decl.savings_by_prsn_and_curr.keys()):
            # diffs_by_person[person_] = curr_decl.savings_by_person[person_] - prev_decl.savings_by_person[person_]
            for currency_ in (curr_decl.savings_by_prsn_and_curr[person_].keys() | prev_decl.savings_by_prsn_and_curr[person_].keys()):
                if currency_ not in prev_decl.savings_by_prsn_and_curr[person_].keys():
                    diffs_by_person[person_][currency_] = curr_decl.savings_by_prsn_and_curr[person_][currency_]
                elif currency_ not in curr_decl.savings_by_prsn_and_curr[person_].keys():
                    diffs_by_person[person_][currency_] = - prev_decl.savings_by_prsn_and_curr[person_][currency_] # hope it works like I want it to
                else:
                    diffs_by_person[person_][currency_] = curr_decl.savings_by_prsn_and_curr[person_][currency_] - prev_decl.savings_by_prsn_and_curr[person_][currency_]
        for person_ in (curr_decl.savings_by_prsn_and_curr.keys() - prev_decl.savings_by_prsn_and_curr.keys()):
            diffs_by_person[person_] = curr_decl.savings_by_prsn_and_curr[person_]
        # for every person that had savings declared in previous declaration, but does not have now
        for person_ in prev_decl.savings_by_prsn_and_curr.keys() - curr_decl.savings_by_prsn_and_curr.keys():
            log.debug(f'no more person savings. previous list: {prev_decl.savings_by_prsn_and_curr.keys()}')
            log.debug(f'no more person savings. current list: {curr_decl.savings_by_prsn_and_curr.keys()}')
            log.debug(f'no more person savings. person id: {person_}')
            log.info((f'There are no more savings that belong to a person with ID {person_}'
                      f' in declaration ({curr_decl.written_type}, {curr_decl.year})'))
            report.add_record(ReportLevel.SUBSTEP, f'There are no more savings that belong to {curr_decl.persons[person_].full_name} ({curr_decl.persons[person_].relation_type})', critical=2)
    # if current declaration has no savings, then report every person as the one whose savings are not declared now
    elif bool(prev_decl.savings_by_prsn_and_curr):
        for person_ in prev_decl.savings_by_prsn_and_curr.keys():
            log.info((f'There are no more savings that belong to a person with ID {person_}'
                      f' in declaration ({curr_decl.written_type}, {curr_decl.year})'))
            report.add_record(ReportLevel.SUBSTEP, f'There are no more savings that belong to {curr_decl.persons[person_].full_name} ({curr_decl.persons[person_].relation_type})', critical=2)
    elif bool(curr_decl.savings_by_prsn_and_curr):
        diffs_by_person = curr_decl.savings_by_prsn_and_curr.copy()
    log.debug(f'get_savings_diff_by_person_v2() executed, result: {diffs_by_person}')
    return diffs_by_person


# returns amount of savings (converted to UAH) accumulated overall since previous declaration
# soon to be deprecated
def get_total_savings_diff_v1(prev_decl: Declaration, curr_decl: Declaration):
    diff = None
    for person_ in prev_decl.savings_by_person.keys() & curr_decl.savings_by_person.keys():
        diff += curr_decl.savings_by_person[person_] - prev_decl.savings_by_person[person_]
    for person_ in curr_decl.savings_by_person.keys() - prev_decl.savings_by_person.keys():
        diff += curr_decl.savings_by_person[person_]
    for person_ in prev_decl.savings_by_person.keys() ^ curr_decl.savings_by_person.keys():
        # TODO add warnings
        # TODO add report output
        continue # replace with reports and warnings
    # TODO add report output
    if diff is None:
        log.warning(f'Something wrong in get_overall_savings_diff() - final difference is None.  '
                    f'\n Previous declaration: {prev_decl}; \n Current declaration: {curr_decl}')
    log.debug(f'get_overall_savings_diff() called, result:  {diff}')
    return diff


# returns percentage of savings accumulated by person related to their declared earnings
# is it deprecated?
def get_savings_percentage_by_person(earnings_by_person: dict[str, float], savings_diff_by_person: dict[str, float]):
    ratios = {}
    for person_ in savings_diff_by_person.keys():
        if person_ not in earnings_by_person.keys():
            log.warning(f'There are accumulated savings, but no earnings for a person with ID {person_}')
        ratios[person_] = savings_diff_by_person[person_] / earnings_by_person[person_]
    log.debug(f'get_savings_percentage_by_person called, result: {ratios}')
    return ratios


# returns percentage of savings accumulated in total related to declared earnings (in one declaration)
# soon to be deprecated
def get_total_savings_to_earnings_ratio_v1(prev_decl: Declaration, curr_decl: Declaration):
    total_savings = get_total_savings_diff_v1(prev_decl, curr_decl)
    total_earnings = sum(curr_decl.earnings_by_person.values())
    log.info(f'Total percentage of earnings: {(total_earnings / total_savings):.0%}')
    return total_savings / total_earnings

# returns difference in savings (accumulated since last declaration) by currency
def get_savings_diff_by_avg(prev_decl: Declaration, curr_decl: Declaration) -> dict[str, int|float]:
    savings_diff: dict[str, int|float] = {}
    for curr in (curr_decl.savings_by_currency.keys() - prev_decl.savings_by_currency.keys()):
        savings_diff[curr] = curr_decl.savings_by_currency[curr] # save new currency entries as is
    for curr in (prev_decl.savings_by_currency.keys() - curr_decl.savings_by_currency.keys()):
        savings_diff[curr] = - prev_decl.savings_by_currency[curr] # amount for removed currencies are saved as negative
    for curr in (prev_decl.savings_by_currency.keys() & curr_decl.savings_by_currency.keys()):
        savings_diff[curr] = curr_decl.savings_by_currency[curr] - prev_decl.savings_by_currency[curr]
    log.debug(f'get_savings_diff_by_avg() executed for declaration [{curr_decl.declaration_id}] '
              f'and previous one [{prev_decl.declaration_id}], result: {savings_diff}')
    return savings_diff


# TODO complete  (is it needed?)
def compare_savings_and_earnings(prev_decl: Declaration, curr_decl: Declaration):
    if curr_decl.savings_by_currency:
        savings_by_curr = curr_decl.savings_by_currency.copy()
    else:
        savings_by_curr = sum_savings_by_currency_avg(curr_decl.savings)
        curr_decl.savings_by_currency = savings_by_curr.copy()
    savings_diff = get_savings_diff_by_avg(prev_decl, curr_decl)

    # if this one is going to contain all of the code for step_12 for run_comparison, then it should be like that:
    # 1. show overall difference in savings
    # 2. show overall ratio savings / income (taxed)
    pass



# compares changes in declared property and reports differences
def compare_property_list(prev_decl: Declaration, curr_decl: Declaration):
    removed_ = [prop for prop in prev_decl.property_list if prop not in curr_decl.property_list]
    added_ = [prop for prop in curr_decl.property_list if prop not in prev_decl.property_list]
    for prop in removed_:
        log.debug(f'Removed property: {prop}')
        report.add_record(ReportLevel.SUBSTEP, f'Видалено нерухомість: ')
        report.add_record(ReportLevel.DETAILS, f' {prop} ')
    for prop in added_:
        log.debug(f'Added property: {prop}')
        report.add_record(ReportLevel.SUBSTEP, f'Додано нерухомість: ')
        report.add_record(ReportLevel.DETAILS, f' {prop} ')
        # if str(curr_decl.year) in prop.acquire_date or :
        #     report.add_record(ReportLevel.SUBSTEP, f'')
    for prop in curr_decl.property_list:
        for old_prop in prev_decl.property_list:
            if prop == old_prop:
                change_ = prop.get_changes_since(old_prop)
                if change_:
                    log.debug(f'Property change computed, concatenated outcome: {change_}')
                    report.add_record(ReportLevel.SUBSTEP, change_)
        if prop.get_year_acquired() >= (curr_decl.year-2): # check recent purchases/acquisitions
            if not prop.cost:
                log.debug(f'Property price not declared, but acquisition date is recent for property: {prop}')
                report.add_record(ReportLevel.SUBSTEP, f'Власність набута нещодавно, проте вартість не вказана: ')
                report.add_record(ReportLevel.DETAILS, f' {prop} ')
            elif not str(prop.cost).isdigit() and 'родич' in prop.cost.lower():
                log.debug(f'Property price not declared by a relative, but acquisition date is recent for property: {prop}')
                report.add_record(ReportLevel.SUBSTEP, f'Власність набута родичами нещодавно, проте родичі не надали інформацію про ціну: ')
                report.add_record(ReportLevel.DETAILS, f' {prop} ')

def compare_vehicle_list(prev_decl: Declaration, curr_decl: Declaration):
    added_ = [vehicle for vehicle in curr_decl.vehicle_list if vehicle not in prev_decl.vehicle_list]
    removed_ = [vehicle for vehicle in prev_decl.vehicle_list if vehicle not in curr_decl.vehicle_list]
    for vehicle in removed_:
        log.debug(f'Removed vehicle: {vehicle}')
        report.add_record(ReportLevel.SUBSTEP, f'Видалено нерухоме майно (транспортний засіб): ')
        report.add_record(ReportLevel.DETAILS, f' {vehicle} ')
    for vehicle in added_:
        log.debug(f'Added vehicle: {vehicle}')
        report.add_record(ReportLevel.SUBSTEP, f'Додано нерухоме майно (транспортний засіб): ')
        report.add_record(ReportLevel.DETAILS, f' {vehicle} ')
    for vehicle in curr_decl.vehicle_list:
        for old_vehicle in prev_decl.vehicle_list:
            if vehicle == old_vehicle:
                change_ = vehicle.get_changes_since(old_vehicle)
                if change_:
                    log.debug(f'Changes in vehicle list computed, concatenated outcome: {change_}')
                    report.add_record(ReportLevel.SUBSTEP, change_)
        if vehicle.get_acquire_year() >= (curr_decl.year - 2) and (not vehicle.cost or not str(vehicle.cost).isdecimal()):
            log.debug(f'Vehicle price not declared, but acquisition date is recent for property: {vehicle}')
            report.add_record(ReportLevel.SUBSTEP,
                        f'Рухоме майно (транспортний засіб) набуте нещодавно, проте вартість не вказана: {vehicle}')
            report.add_record(ReportLevel.DETAILS, f' {vehicle} ')

# ----------------------------

def check_person(full_name, declarant_id = 0):
    global report
    report = reports.init_new_report()
    declarations_json = get_all_declarations_by_name(full_name)
    declarations_list = parse_declaration_cards(declarations_json)

    # fail if there are namesakes - need to run again with declarant_id specified TODO rewrite this part
    if not check_for_namesakes(declarations_list):
        report.add_record(ReportLevel.TOP, 'Знайдено декілька осіб з однаковим повним ім\'ям, але різними ID. Перезапустіть зі вказаним declarant_id')
        raise BaseException # expand on this
    if declarant_id:
        declarations_list = filter_namesakes_for_id(declarations_list, declarant_id)

    major_declarations = get_sorted_major_declarations(declarations_list)
    # removes all declarations that were corrected later
    major_declarations = remove_incorrect_declarations(major_declarations)
    # print(major_declarations)
    # мінорні - це про суттєві зміни у майновому стані
    minor_declarations = get_sorted_minor_declarations(declarations_list)

    if len(major_declarations) > 1:
        year_range = (major_declarations[0].year, major_declarations[-1].year)
    elif len(major_declarations) == 0:
        report.add_top_info(full_name, (0, 0))
        report.add_record(ReportLevel.TOP, 'Декларацій не знайдено', critical=3)
        return report
    else:
        year_range = (major_declarations[0].year, major_declarations[0].year)
    report.add_top_info(full_name, year_range)

    for decl in major_declarations:
        load_full_declaration(decl)

    run_comparison(major_declarations[0], major_declarations[0]) #to report very first declaration
    for i_ in range(1, len(major_declarations)):
        # print(major_declarations[i_])
        run_comparison(major_declarations[i_-1], major_declarations[i_])
        # report.add_empty_line()
    # print(report)
    return report


# -------------------------

def run_for_one():
    name = 'НЕБИЛИЦЯ Ольга Дмитрівна'
    person_report = check_person(name)
    # print(person_report)
    person_report.print_to_docx()


def run_namelist():
    name_list = [
        'МОРДАЧ Віктор Олексійович',
        'АГУТІН Михайло Миколайович',
        'МІРОШНИК Тетяна Тихонівна',
        'БАШЛАК Микола Миколайович',
        'РАХУБОВСЬКИЙ Сергій Валентинович',
        'НЕБИЛИЦЯ Ольга Дмитрівна',
        # 'СТРІЛЬЧУК Петро',
        'Кривовʼяз Андрій Тихонович',
        'ЧУЯШЕНКО Ігор Геннадійович',
        'БАБІЦЬКИЙ Петро Олександрович',
        'ДОДАТКО Світлана Андріївна',
        'ПОГОРЄЛОВ Сергій Семенович',
        'МИХАНЧУК Валентина Володимирівна'
    ]
    err_list = []
    for name_ in name_list:
        try:
            rep = check_person(name_)
            print(f'{name_} checked')
            rep.print_to_docx()
            print(f'{name_} report printed to docx')
        except Exception as err:
            err_list.append(name_)
            print(f'Could not process declarations for {name_}')
            print(f"Unexpected {err=}, {type(err)=}")
    print(f'Not processed: {err_list}')


if __name__ == '__main__':
    # run_for_one()
    run_namelist()