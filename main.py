import pandas as pd
import pdfplumber
import re
import camelot
import os
import json
import urllib.request
from pprint import pprint

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

schedule_pdf = pdfplumber.open('schedule0706.pdf')  # pdfplumber.open('schedule30.pdf')
teachers_pdf = pdfplumber.open('teachers0706.pdf')  # pdfplumber.open('teachers30.pdf')

'''
schedule_pages = schedule_pdf.pages
teachers_pages = teachers_pdf.pages

teachers_list = []
teacher_pattern = re.compile(r'\s*\.*\s*[A-ZА-ЯЁ][a-zа-яё]+\s+[A-ZА-ЯЁ][.]\s*[A-ZА-ЯЁ][.]\s*\.*\s*')
groups_list = []
group_pattern = re.compile(r'\s*\.*\s*(^[А-Я]{1,3}-\d{3}(,\s*\d{3})*$)|(^[А-Я]-\d{6}-\d[а-я]-\d{2}/\d$)\s*\.*\s*')

for page in teachers_pages:
    words = page.extract_words(use_text_flow=True, keep_blank_chars=True)
    teachers_list += [x['text'] for x in words if teacher_pattern.match(x['text'])]
teachers_list.sort()
teachers_list = list(dict.fromkeys(teachers_list))  # remove duplicates


for page in schedule_pages:
    words = page.extract_words(use_text_flow=True, keep_blank_chars=True)
    groups_list += [x['text'] for x in words if group_pattern.match(x['text'])]
groups_list.sort()
groups_list = list(dict.fromkeys(groups_list))
'''
'''
def to_json(self, path, **kwargs):

    json_string = self.df.to_json(**kwargs).replace("\\/", "/").encode().decode('unicode_escape').replace('\n', '')
    #pattern_before = re.compile("\.+\s+\"[A-Za-zА-Яа-яЁё]+\.+")
    #pattern_after = re.compile("[A-Za-zА-Яа-яЁё]")
    json_string = json_string.replace('"Оператор электронно- вычислительных и  406 вычислительных  машин"', 'Оператор электронно-вычислительных и  406 вычислительных  машин')
    #re.sub(pattern, '', json_string)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(json_string)



camelot.core.Table.to_json = to_json
tables = camelot.io.read_pdf('schedule30.pdf', pages='all', encoding='utf-8')

output_path = "bar.json"
tables.export('bar.json', f='json')
'''

# with open('bar-page-1-table-1.json', 'r', encoding='utf-8') as read_json:
#    data = json.load(read_json)

#pprint(data)


'''
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


# base_path = os.path.dirname(__file__)
'''
schedule_pages = schedule_pdf.pages
teachers_pages = teachers_pdf.pages

teachers_list = []
teacher_pattern = re.compile(r'\s*\.*\s*[A-ZА-ЯЁ][a-zа-яё]+\s+[A-ZА-ЯЁ][.]\s*[A-ZА-ЯЁ][.]\s*\.*\s*')
groups_list = []
group_pattern = re.compile(r'\s*\.*\s*([А-Я]{1,3}-\d{3}(,\s*\d{3})*\s*$)|([А-Я]-\d{6}-\d[а-я]-\d{2}\/\d)\s*\.*\s*')

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
schedule_df = schedule_df.loc[:, ~schedule_df.columns.isin([0, 1])]
#print(schedule_df)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


json_string = schedule_df.to_json(orient='columns').replace("\\/", "/").encode().decode('unicode_escape').replace('\n', '')
json_string = json_string.replace('"Оператор электронно-вычислительных и вычислительных машин"', 'Оператор электронно-вычислительных и вычислительных машин')

'''
with open('schedule.json', 'w', encoding='utf-8') as f:
    f.write(json_string)

with open('schedule.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    data_list = [print([k, v]) for k, v in data.items()]
'''
data = json.loads(json_string)
#data_array = [print(item) for item in data['2']]
#for rows in data['2']['0']:
#    print(rows[1])

#data_list = [[k, v] for k, v in data.items()]
#values = [print([k, v]) for k, v in data_list]

'''
========================================
{
    "2": {
             "0": "",
             "1": "",
             ........
         }
}
========================================
                    |
                    |
                    V
====================================================================
{
    "group": "",
    "lessons": [
                  {
                        "lesson_number": i,
                        "subject": "",
                        "teacher_classroom": [
                                                {
                                                    "teacher": "",
                                                    "classroom": ""
                                                }
                        ]
                  }
    ]
}
====================================================================
'''

matches_list = []
print('\n'*15)


# Вывод

#for i in data:
#    for k in data[i]:
#        print(data[i][k])


'''
res_json = ""
lesson_counter = 0

for k in data["2"]:
    if group_pattern.match(data["2"][k]):
        lesson_counter = 1
        res_json += "{\"group\": " + "\"" + data["2"][k] + "\"," \
                    "\"lessons\":[{" + "\"lesson_number\": " + lesson_counter + ","
    if teacher_pattern.match(data["2"][k]):

        lesson_counter += 1
'''
'''
for cols, rows in data.items():
    for row_key, row_value in rows.items():
        if row_value is None:
            continue
        row_match = re.finditer(group_pattern, row_value)

        for old_name in row_key:
            if row_value in row_match:
                row_key['group'] = row_key.pop(old_name)

        #if row == row_match:
        #    row['group'] = row.pop(f'{i}')
        #print(row_key, row_value)

        #for match in row_match:
        #    if match is None:
        #        continue
            #print(match)
        #    matches_list.append(match)
#print(matches_list)
'''
#print('\n'+data)
# print('\n'+json_string)

class S(BaseHTTPRequestHandler):
    def _set_headers(self, code, location, header_type):
        self.send_response(code)
        self.send_header(location, header_type)
        self.end_headers()

    def do_GET(self):
        res = json.dumps(json_string)
        self._set_headers(200, "Content-type", "application/json")
        return json_string

    def do_POST(self):
        self._set_headers(302, "Location", "https://google.com/")


def run(server_class=HTTPServer, handler_class=S, addr="192.168.1.5", port=80):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)
    print(f"[MGKIT] server works at: {addr}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--listen",
        default="192.168.1.5",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=80,
        help="Specify the port on which the server listens",
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port)






