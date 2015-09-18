#!/usr/bin/env python2
import sys

import json

json_format_version = 'pconsc/json/0.1.0'


def parse_pconsc(input):
    for line in input:
        words = line.split()
        if not words:
            continue
        pos1 = int(words[0])
        pos2 = int(words[1])
        propensity = float(words[2])
        yield pos1, pos2, propensity


def parsed_results(input):
    results = list(parse_pconsc(input))
    ranking = list(sorted(results, key=lambda contact: -contact[2]))
    return dict(format=json_format_version, results=results, ranking=ranking)


def save_json(input, output):
    json.dump(parsed_results(input), output)

if __name__ == '__main__':
    result_file = sys.argv[1]
    json_file = sys.argv[2]
    save_json(open(result_file), open(json_file, 'w'))
