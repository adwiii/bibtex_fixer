import re
from typing import Dict, List

# match things of the form @bibtex{title, ...}
BIBTEX_REGEX = re.compile(r'@(\w+)\s*\{\s*(\w+)\s*,(\s*(\s*\w+\s*=\s*["{].*["}]\s*,?)*)\s*}')
# match things of the form `key = {value},` except that value is allowed to have matched curly braces inside
DICT_REGEX = re.compile(r'\s*(\w+)\s*=\s*\{((?:(?:[^{}]*\{[^{}]*\})*[^{}]*|[^}]*))}')


class BibTexEntry:
    @classmethod
    def from_match(cls, file, match):
        file = file
        orig = match.group(0)
        bibtex_type = match.group(1)
        name = match.group(2)
        body = match.group(3)
        if '\\}' in body:
            raise ValueError('Cannot parse a bibtex with an escaped close brace')
        body_dict = {}
        for body_match in re.finditer(DICT_REGEX, body):
            body_dict[body_match.group(1)] = body_match.group(2)
        return cls([file], bibtex_type, name, body_dict, body, orig)

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
        return f'@{self.bibtex_type}{{{self.name}, {self.body}}}\n'


class BibTexFile:
    def __init__(self, file: str) -> None:
        with open(file) as f:
            text = f.read()
            self.entries = [BibTexEntry.from_match(file, match) for match in re.finditer(BIBTEX_REGEX, text)]
            self.entries_dict = {entry.name: entry for entry in self.entries}
            if len(self.entries) < len(self.entries_dict):
                print(f'Warning, parsed {len(self.entries)} entries, but only {len(self.entries_dict)} unique')
            else:
                print(f'Parsed {len(self.entries)} entries from {file}')
