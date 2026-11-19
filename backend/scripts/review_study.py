"""Prepare blind research report reviews and score completed anonymous ballots."""
import argparse
import csv
import json
import random
from pathlib import Path
from statistics import mean

CRITERIA = ('correctness', 'source_support', 'coverage', 'clarity')


def prepare(results, dataset, directory):
    import hashlib
    report = json.loads(results.read_bytes())
    raw = dataset.read_bytes()
    if hashlib.sha256(raw).hexdigest() != report['dataset_sha256']:
        raise ValueError('Dataset differs from the recorded experiment')
    fixture = json.loads(raw)
    questions = {item['id']:item['question'] for item in fixture['cases']}
    rows = list(report['runs'])
    random.SystemRandom().shuffle(rows)
    directory.mkdir(exist_ok=False,parents=True)
    items = [{'id':f'R{i:03d}','question':questions[row['case']],
              'answer':row.get('answer','[No answer produced]')} for i,row in enumerate(rows,1)]
    packet = {'instructions':'Participation is voluntary. Compare each answer against the source independently. Score 1 (poor) to 5 (excellent) for correctness, source support, coverage and clarity. Leave unanswered ratings blank. Do not enter names or contact details.',
              'source':fixture['document'],'items':items}
    (directory/'participant.json').write_text(json.dumps(packet,indent=2))
    key = {item['id']:row['strategy'] for item,row in zip(items,rows,strict=True)}
    (directory/'organizer-key.json').write_text(json.dumps(key,indent=2))
    with (directory/'blank-ballot.csv').open('w',newline='') as file:
        writer=csv.writer(file)
        writer.writerow(('id',*CRITERIA))
        writer.writerows((item['id'],*(['']*len(CRITERIA))) for item in items)


def aggregate(key, ballots):
    mapping=json.loads(key.read_bytes())
    scores={}
    for ballot in ballots:
        with ballot.open(newline='') as file:
            entries=list(csv.DictReader(file))
        seen=set()
        for row in entries:
            record=row['id']
            if record not in mapping or record in seen:
                raise ValueError('Unknown or duplicate ballot row')
            seen.add(record)
            totals=scores.setdefault(mapping[record],{name:[] for name in CRITERIA})
            for name in CRITERIA:
                if row[name] in ('',None):
                    continue
                if row[name] not in {'1','2','3','4','5'}:
                    raise ValueError('Ratings must be integers from 1 to 5')
                totals[name].append(int(row[name]))
    return {strategy:{name:{'ratings':len(values),'mean':mean(values) if values else None}
                      for name, values in totals.items()} for strategy,totals in scores.items()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare')
    prep.add_argument('results',type=Path)
    prep.add_argument('dataset',type=Path)
    prep.add_argument('directory',type=Path)
    score=sub.add_parser('score')
    score.add_argument('key',type=Path)
    score.add_argument('ballots',type=Path,nargs='+')
    args=parser.parse_args()
    if args.command=='prepare':
        prepare(args.results,args.dataset,args.directory)
    else:
        print(json.dumps(aggregate(args.key,args.ballots),indent=2))
