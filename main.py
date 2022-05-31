import pandas as pd
import pdfplumber
import re


schedule_pdf = pdfplumber.open('schedule30.pdf')
teachers_pdf = pdfplumber.open('teachers30.pdf')

schedule_pages = schedule_pdf.pages
teachers_pages = teachers_pdf.pages

teachers_list = []
teacher_pattern = re.compile(r'\s*\.*\s*[A-ZА-ЯЁ][a-zа-яё]+\s+[A-ZА-ЯЁ][.]\s*[A-ZА-ЯЁ][.]\s*\.*\s*')
groups_list = []
group_pattern = re.compile(r'\s*\.*\s*(^[А-Я]{1,3}-\d{3}(,\s\d{3})*$)|(^[А-Я]-\d{6}-\d[а-я]-\d{2}\/\d$)\s*\.*\s*')

for page in teachers_pages:
    words = page.extract_words(use_text_flow=True, keep_blank_chars=True)
    teachers_list += [x['text'] for x in words if teacher_pattern.match(x['text'])]
teachers_list.sort()
teachers_list = list(dict.fromkeys(teachers_list))  # remove duplicates
print("Loaded teachers", teachers_list)
assert "Литаврин И.С." in teachers_list
assert "Крайнюков А.Н." in teachers_list

for page in schedule_pages:
    words = page.extract_words(use_text_flow=True, keep_blank_chars=True)
    groups_list += [x['text'] for x in words if group_pattern.match(x['text'])]
groups_list.sort()
groups_list = list(dict.fromkeys(groups_list))
print("Loaded groups", groups_list)
assert "У-090205-9о-20/1" in groups_list
assert "ИСП-207" in groups_list
assert "КС-401, 402, 403" in groups_list

# 'Кузьменко С.Ю.МДК.05.01 Проектирование и дизайн информационных системМухортова Н.Н.'

spaces_re = re.compile(r'\s+')


def find_first_teacher(test: str) -> int:
    first_teacher_pos = 0xFFFFFFFF
    for teacher in teachers_list:
        pos = cell_words.find(teacher)
        if -1 < pos < first_teacher_pos:
            first_teacher_pos = pos

    if first_teacher_pos == 0xFFFFFFFF:
        first_teacher_pos = -1
    return first_teacher_pos


def split_amalgam(text: str):
    first_teacher_pos = find_first_teacher(text)
    for teacher in teachers_list:
        pos = text.find(teacher, first_teacher_pos + 1)
        if pos > -1:
            return text[:pos], text[pos:]
    return text, None


schedule_table = []

for page_i, page in enumerate(schedule_pages):
    print("Processing page ", page_i)
    schedule_words = page.extract_words(use_text_flow=True, keep_blank_chars=True)
    tables = page.find_tables()
    for table in tables:
        schedule_rows = table.rows
        for row_i, row in enumerate(schedule_rows):
            row_cells = []
            overflow = None
            for cell_i, cell in enumerate(row.cells):
                if cell is None:
                    continue
                x0, top, x1, bottom = cell
                cell_words = ""
                for word in schedule_words:
                    if x1 > word['x0'] > x0:
                        if bottom > (word['top'] + word['bottom']) / 2 > top:
                            text: str = word['text']
                            cell_words += text + " "
                            for teacher in teachers_list:
                                pos = text.find(teacher)
                                # if pos > -1:

                cell_words = re.sub(r'\s+', " ", cell_words)
                # Check for amalgamated words
                if overflow:
                    print(f"adding overflow {cell_words} + {overflow}")
                    cell_words += overflow
                    overflow = None
                cell_words, overflow = split_amalgam(cell_words)
                if overflow:
                    print(f"Found amalgam at ({row_i}, {cell_i}): {cell_words} | {overflow}")
                    # TODO: загрузить элементы из overflow в их законные клетки
                row_cells.append(cell_words)
            schedule_table.append(row_cells)
schedule_df = pd.DataFrame(schedule_table[3:])

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

print(schedule_df)
path = "__result.csv"
'''
while True:
    try:
        schedule_df.to_csv(path)
        break
    except PermissionError:
        path = "_" + path
        pass
'''
