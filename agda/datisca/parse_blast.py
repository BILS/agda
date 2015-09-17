from itertools import chain
import json
import os
import sys

from core import fasta

json_format_version = 'mdrscan/json/0.4.0'


def get_program(blast_output):
    for line in blast_output:
        words = line.split()
        if words:
            return words[0]


def get_database(blast_output):
    for line in blast_output:
        words = line.split()
        if words and words[0] == "Database:":
            return words[1]


def post_process(queries):
    for query in queries:
        for hit in query['hits']:
            hit['alignments'] = ''.join(hit['alignments'])
            for i, region in enumerate(hit['regions']):
                start, stop = region
                hit['regions'][i] = dict(start=start, length=stop - start + 1)


def parse_blast(blast_output, query_file):
    if isinstance(blast_output, basestring):
        blast_output = blast_output.splitlines(True)
    blast_output = iter(blast_output)
    query_lengths = dict((q.id, len(q)) for q in fasta.entries(query_file))
    results = dict(program=get_program(blast_output),
                   database=get_database(blast_output))
    queries = []
    results['queries'] = queries
    query = None
    hit = None
    region = None
    parsing_alignments = False
    for line in blast_output:
        if line.startswith('Query='):
            words = line.split(None, 2)
            id = words[1]
            description = words[2] if len(words) > 2 else ''
            query = dict(id=id,
                         description=description,
                         length=query_lengths[id],
                         hits=[])
            queries.append(query)
        elif line.startswith('>'):
            parsing_alignments = True
            words = line.split(None, 1)
            id = words[0].split('|')[-1]
            description = None
            if len(words) == 2:
                description = words[1]
            hit = dict(id=id,
                       evalue=None,
                       description=description,
                       regions=[],
                       alignments=[line])
            query['hits'].append(hit)
        elif parsing_alignments:
            if line.startswith('Lambda'):
                parsing_alignments = False
                continue
            hit['alignments'].append(line)
            if line.startswith(' Score'):
                if hit['evalue'] is None:
                    words = line.split()
                    i = (i for i, w in enumerate(words) if w.startswith('Expect')).next()
                    hit['evalue'] = float(words[i + 2].rstrip(','))
                region = [sys.maxint, 0]
                hit['regions'].append(region)
            elif line.startswith('Query'):
                words = line.split()
                start = int(words[1])
                stop = int(words[-1])
                if start > stop:
                    start, stop = stop, start
                region[0] = min(start, region[0])
                region[1] = max(stop, region[1])
    post_process(queries)
    return results


def get_hit_ids(results):
    ids = []
    for q in results['queries']:
        for hit in q['hits']:
            id = hit['id']
            if id not in ids:
                ids.append(id)
    return ids


def filter_sequences(db, ids):
    for entry in fasta.iter_entries(db):
        if entry.id in ids:
            yield entry
            ids.remove(entry.id)
            if not ids:
                return
    if ids:
        raise RuntimeError('not all sequences were found: ' + str(list(ids)))


def save_hit_fasta(hit_file, db, results):
    ids = get_hit_ids(results)
    entries = fasta.FastaDict()
    for entry in filter_sequences(db, set(ids)):
        entries[entry.id] = entry
    for id in ids:
        print >> hit_file, entries[id]


def get_dbfiles(dbdir, alias_file):
    for line in open(os.path.join(dbdir, alias_file)):
        if line.startswith('DBLIST'):
            return [os.path.join(dbdir, f) for f in line.split()[1:]]

if __name__ == '__main__':
    db_file = sys.argv[1]
    query_file = sys.argv[2] if len(sys.argv) > 2 else 'query.fasta'
    blast_file = sys.argv[3] if len(sys.argv) > 3 else 'results.blast'
    results_file = sys.argv[4] if len(sys.argv) > 4 else 'noduleblast.json'
    hit_file = sys.argv[5] if len(sys.argv) > 5 else 'hits.fa'

    results = parse_blast(open(blast_file), open(query_file))
    info = dict(format=json_format_version, results=results)
    json.dump(info, open(results_file, 'w'))
    dbdir, dbfile = os.path.split(db_file)
    if dbfile == 'all':
        db = chain(*[open(f) for f in get_dbfiles(dbdir, dbfile + '.nal')])
    else:
        db = open(db_file)
    save_hit_fasta(open(hit_file, 'w'), db, results)
