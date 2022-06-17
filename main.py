import pandas as pd
import pdfplumber
import re
import camelot
import os
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from bs4 import BeautifulSoup
import requests

headers = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0"
}


def build_download_link(url: str):
    base_url = "https://drive.google.com/uc?export=download&id="
    split_link = url.split('/')
    return base_url + split_link[5]


def get_actual_schedule_links():
    url = "https://sites.google.com/a/mgkit.ru/www/studentu/raspisanie-zanatij"
    req = requests.get(url, headers=headers)
    schedule = req.text

    with open("schedule_page.html", "w") as f:
        f.write(schedule)
    with open("schedule_page.html") as f:
        schedule_page_data = f.read()

    soup = BeautifulSoup(schedule_page_data, "lxml")
    hrefs = soup.find_all(class_="XqQF9c")

    hrefs_list = []
    for href in hrefs:
        item_text = href.text
        item_href = href["href"]
        hrefs_list.append(
            {
                "link_text": item_text,
                "link": item_href
            }
        )

    links_list = []
    df = pd.DataFrame(hrefs_list)
    df['link_text'] = df.groupby(['link'])['link_text'].transform(lambda x: ''.join(x))
    df = df.drop_duplicates()
    schedules_pattern = re.compile(r'.*(\d{2}[.]){2}\d{4}')

    for link_item_i, link_text in enumerate(df['link_text']):
        if schedules_pattern.match(link_text):
            link = [link for link in df['link']][link_item_i]
            links_list.append(
                {
                    'link_name': link_text,
                    'link': build_download_link(link)
                }
            )

    [print(link) for link in links_list]
    return links_list


def download_pdfs_from_url(schedule_urls: [dict]):
    for url in schedule_urls:
        response = requests.get(url['link'])
        with open(f"/schedules/{url['link_name']}.pdf", 'wb') as f:
            f.write(response.content)


def parse_schedule_to_json(pdfs: []):

    json_list = []
    #for pdf in pdfs:
    schedule_pdf = pdfplumber.open('schedule0706.pdf')
    teachers_pdf = pdfplumber.open('teachers0706.pdf')

        #schedule_pdf = pdfplumber.open(pdf)
        #teachers_pdf = pdfplumber.open()

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

                    cell_words = re.sub(r'\s+', " ", cell_words)
                    # Check for amalgamated words
                    if overflow:
                        #                       print(f"adding overflow {cell_words} + {overflow}")
                        cell_words += overflow
                        overflow = None
                    cell_words, overflow = split_amalgam(cell_words)
                    #if overflow:
                        #                       print(f"Found amalgam at ({row_i}, {cell_i}): {cell_words} | {overflow}")
                    row_cells.append(cell_words)
                schedule_table.append(row_cells)

    fixed = [[]]
    count = 0
    for row in schedule_table[3:]:
        count += 1
        if "Группа:" in row[1]:
            count = 0
        if len(fixed) <= count:
            fixed.append([])
        fixed[count].extend(row[2:])

    schedule_df = pd.DataFrame(fixed[1:], columns=fixed[0])
    schedule_df = schedule_df.replace(r'^\s*$', None, regex=True)

    #print(schedule_df)  # schedule_df = schedule_df.loc[:, ~schedule_df.columns.isin([0, 1])]

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    json_string = schedule_df.to_json(orient='columns').replace("\\/", "/").encode().decode('unicode_escape').replace('\n',
                                                                                                                      '')
    json_string = json_string.replace('"Оператор электронно-вычислительных и вычислительных машин"',
                                      'Оператор электронно-вычислительных и вычислительных машин')

    #print('\n' * 15)
    print(f"\n{json_string}\n")

    return json.dumps(json_string)


schedule_links = get_actual_schedule_links()
print('\n')
get_json = parse_schedule_to_json([])

class S(BaseHTTPRequestHandler):



    def _set_headers(self, code, location, header_type):
        self.send_response(code)
        self.send_header(location, header_type)
        self.end_headers()

    def do_GET(self):
        self._set_headers(200, "Content-type", "application/json")
        self.wfile.write(bytes(get_json, 'utf-8'))

    def do_POST(self):
        self._set_headers(302, "Location", "https://google.com/")


def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=80):
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
