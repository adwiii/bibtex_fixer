import argparse
import glob
import os
from collections import defaultdict
from typing import Dict

import yaml

from bibparse import *


def parseargs():
    parser = argparse.ArgumentParser(
        prog='BibtexFixer',
        description='Finds duplicated bibtex entries and attempts to reconcile them.')
    parser.add_argument('--input_folder', required=True)
    parser.add_argument('--output_folder', required=True)
    return parser.parse_args()


def main():
    args = parseargs()
    input_folder = args.input_folder
    output_folder = args.output_folder
    overall_dict: Dict[str, BibTexEntry] = {}
    conflicts: Dict[str, List[BibTexEntry]] = defaultdict(list)
    for file in glob.glob(input_folder + os.sep + '*.bib'):
        bibtex_file = BibTexFile(file)
        for name, entry in bibtex_file.entries_dict.items():
            name = name.lower()
            if name in conflicts:
                conflicts[name].append(entry)
            elif name in overall_dict:
                try:
                    overall_dict[name] = overall_dict[name].get_superset(entry)
                except ValueError:
                    conflicts[name].append(entry)
                    conflicts[name].append(overall_dict[name])
                    del overall_dict[name]
            else:
                overall_dict[name] = entry
    os.makedirs(output_folder, exist_ok=True)
    print(f'Found {len(conflicts)} conflicted names: {", ".join(conflicts.keys())}')
    with open(f'{output_folder}{os.sep}no_conflict_result.bib', 'w') as f:
        for entry in overall_dict.values():
            f.write(f'{entry.to_latex()}\n')
    with open(f'{output_folder}{os.sep}conflicts.yml', 'w') as f:
        yaml.dump(dict(conflicts), f)


if __name__ == '__main__':
    main()
