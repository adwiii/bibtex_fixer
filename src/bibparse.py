import re
from typing import Dict, List

# match things of the form @bibtex{title, ...}
BIBTEX_REGEX = re.compile(r'@(\w+)\s*\{\s*(\w+)\s*,(\s*(\s*\w+\s*=\s*["{].*["}]\s*,?)*)\s*}')

def is_escaped(body, index):
    substring = body[:index]
    substring.replace('\\\\', '_')
    return len(substring) > 0 and substring[-1] == '\\'


def extract_matched_braces(body: str) -> str:
    assert body[0] == '{'
    count = 1
    index = 1
    while count > 0 and index < len(body):
        if body[index] == '{' and not is_escaped(body, index):
            count += 1
        if body[index] == '}' and not is_escaped(body, index):
            count -= 1
        index += 1
    assert body[index-1] == '}'
    return body[:index]


def extract_matched_quotes(body: str) -> str:
    count = 1
    index = 1
    while count > 0 and index < len(body):
        if body[index] == '"' and not is_escaped(body, index):
            count -= 1
        index += 1
    assert body[index - 1] == '"'
    return body[:index]


class BibTexEntry:
    @classmethod
    def from_parse(cls, file, orig, bibtex_type, name, body):
        file = file
        if '\\}' in body:
            raise ValueError('Cannot parse a bibtex with an escaped close brace')
        body_dict = {}
        body_copy = body
        while len(body) > 0:
            if body[0] == ',':
                body = body[1:].lstrip()
            end_of_key = body.find('=')
            if end_of_key < 0:
                break
            key = body[:end_of_key].strip()
            body = body[end_of_key+1:].lstrip()
            match_braces = (body[0] == '{')
            match_quotes = (body[0] == '"')
            if match_braces:
                value = extract_matched_braces(body)
                body_dict[key] = value[1:-1]
                body = body[len(value):].lstrip()
            elif match_quotes:
                value = extract_matched_quotes(body)
                body_dict[key] = value[1:-1]
                body = body[len(value):].lstrip()
            else:
                comma_index = body.find(',')
                body_dict[key] = body[:comma_index].strip()
                body = body[comma_index:].lstrip()
        # for body_match in re.finditer(DICT_REGEX, body):
        #     body_dict[body_match.group(1)] = body_match.group(2)
        return cls([file], bibtex_type, name, body_dict, body_copy, orig)

    def __init__(self, files: List[str], bibtex_type: str, name: str, body_dict: Dict[str, str], body=None, orig=None):
        self.orig = orig
        self.file = ','.join(files)
        self.bibtex_type = bibtex_type
        self.name = name
        self.body_dict = body_dict
        if body is not None:
            self.body = body
        else:
            self.body = self.body_from_dict()

    def body_from_dict(self):
        return ',\n'.join([f'{key} = {{{value}}}' for key, value in self.body_dict.items()])

    def get_superset(self, other):
        if self.bibtex_type != other.bibtex_type:
            raise ValueError(f'Found incompatible type conflicts {self}, {other}')
        intersecting_keys = set(self.body_dict.keys()).intersection(other.body_dict.keys())
        for key in intersecting_keys:
            if self.body_dict[key] != other.body_dict[key]:
                raise ValueError(f'Found incompatible value conflicts {self}, {other}')
        union_body_dict = self.body_dict.copy()
        union_body_dict.update(other.body_dict)
        return BibTexEntry([self.file, other.file], self.bibtex_type, self.name, union_body_dict)

    def __repr__(self):
        return f'BibTexEntry(file={repr(self.file)},\n@{repr(self.bibtex_type)},\n{repr(self.body_from_dict())}\n)'

    def to_latex(self):
        return f'@{self.bibtex_type.lower()}{{{self.name},\n{self.body_from_dict()}\n}}\n'


def __remove_comments(line):
    line = line.lstrip()
    perc_index = line.find('%')
    if perc_index == -1:
        return line
    if not is_escaped(line, perc_index):
        return line[:perc_index]
    return line


def remove_comments(line):
    temp = __remove_comments(line)
    while temp != line:
        line = temp
        temp = __remove_comments(line)
    return temp


class BibTexFile:
    def __init__(self, file: str) -> None:
        with open(file) as f:
            text_lines = f.readlines()
            # remove all lines that are comments
            text = '\n'.join([remove_comments(line) for line in text_lines])

            self.entries = []
            while len(text) > 0:
                text = text.strip()
                orig = ''
                assert text[0] == '@'
                begin_index = text.find('{')
                bibtex_type = text[1:begin_index]
                orig += text[:begin_index]
                text = text[begin_index:]
                full_data = extract_matched_braces(text)
                if bibtex_type != 'String':
                    name_index = full_data.find(',')
                    name = full_data[1:name_index].strip()
                    body = full_data[name_index + 1:-1]
                    orig += text[:len(full_data)]
                    self.entries.append(BibTexEntry.from_parse(file, orig, bibtex_type, name, body))
                text = text[len(full_data):]
            # self.entries = [BibTexEntry.from_match(file, match) for match in re.finditer(BIBTEX_REGEX, text)]
            self.entries_dict = {entry.name: entry for entry in self.entries}
            if len(self.entries) < len(self.entries_dict):
                print(f'Warning, parsed {len(self.entries)} entries, but only {len(self.entries_dict)} unique')
            else:
                print(f'Parsed {len(self.entries)} entries from {file}')
