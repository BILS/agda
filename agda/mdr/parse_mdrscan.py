import json
import sys

from core import fasta

json_format_version = 'mdrscan/json/0.1.0'


class FamilyData(dict):
    fields = ['id',
              'max_score',
              'min_score',
              'name',
              'representative_description',
              'size']

    @classmethod
    def load(cls, file):
        return cls(json.load(file))

    @classmethod
    def dumps(cls, families):
        data = dict((f.id, dict((name, getattr(f, name)) for name in cls.fields)) for f in families)
        return json.dumps(data)


def parse_mdrscan(hmmpfam_file, query, family_data):
    if isinstance(hmmpfam_file, basestring):
        hmmpfam_file = open(hmmpfam_file)
    if isinstance(query, basestring):
        query = open(query)
    queries = fasta.FastaDict.from_text(query)
    results = dict(strong_hits=[], weak_hits=[])

    def _add_hit(family_list, family, hit):
        for fam in family_list:
            if fam['id'] == family['id']:
                fam['hits'].append(hit)
                return
        family['hits'].append(hit)
        family_list.append(family)

    parsing_domain_hits = False
    for line in hmmpfam_file:
        if parsing_domain_hits:
            words = line.split()
            if not words or '[no hits above thresholds]' in line:
                parsing_domain_hits = False
                continue
            # Model    Domain  seq-f seq-t    hmm-f hmm-t      score  E-value
            # -------- ------- ----- -----    ----- -----      -----  -------
            # MDR021     1/1      29   300 ..     1   272 []   531.9 6.7e-159
            score = float(words[8])
            # if score < 0:
            #    continue
            family_id = words[0][:6]
            family = dict(family_data[family_id], hits=[])
            margin = score / family['min_score']
            hit = dict(first=int(words[2]),
                       last=int(words[3]),
                       length=int(words[3]) - int(words[2]) + 1,
                       score=score,
                       evalue=float(words[9]),
                       margin=margin)
            confidence = 'strong_hits' if margin >= 1 else 'weak_hits'
            _add_hit(results[confidence][-1]['families'], family, hit)
        elif line.startswith('Query sequence:'):
            query_id = line.split(None, 2)[2].strip()
            query_info = dict(id=query_id,
                              families=[],
                              description='',
                              length=len(queries[query_id]))
            results['strong_hits'].append(query_info)
            results['weak_hits'].append(dict(query_info, families=[]))
        elif line.startswith('Description:'):
            description = line.split(None, 1)[1].strip()
            results['strong_hits'][-1]['description'] = description
            results['weak_hits'][-1]['description'] = description
        elif line.startswith('Parsed for domains:'):
            # Skip over headers
            hmmpfam_file.next()
            hmmpfam_file.next()
            parsing_domain_hits = True
    for confidence in results:
        for query in results[confidence]:
            for family in query['families']:
                family['hits'].sort(key=lambda hit: -hit['margin'])
            query['families'].sort(key=lambda family: -family['hits'][0]['margin'])
    return results

if __name__ == '__main__':
    hmmpfam_file = 'mdrscan.hmmpfam'
    results_file = 'mdrscan.json'
    query_file = 'query.fasta'
    family_data_file = 'family_data.json'
    if len(sys.argv) > 4:
        family_data_file = sys.argv[4]
    if len(sys.argv) > 3:
        query_file = sys.argv[3]
    if len(sys.argv) > 2:
        results_file = sys.argv[2]
    if len(sys.argv) > 1:
        hmmpfam_file = sys.argv[1]
    family_data = FamilyData.load(open(family_data_file))
    results = parse_mdrscan(open(hmmpfam_file), open(query_file), family_data)
    info = dict(format=json_format_version, results=results)
    json.dump(info, open(results_file, 'w'))
