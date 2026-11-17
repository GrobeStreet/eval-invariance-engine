"""Regression checks for independently reproduced input and verdict defects."""
import json
import random
import pytest
from eval_invariance_engine.cli import main, _load_results
from eval_invariance_engine.report import build_report, results_from_rows


def rows():
    return [
        {"item_id": "x", "condition": "a", "correct": True},
        {"item_id": "y", "condition": "a", "correct": False},
        {"item_id": "x", "condition": "b", "correct": False},
        {"item_id": "y", "condition": "b", "correct": True},
    ]

@pytest.mark.parametrize('bad', ['false','true',0,1,None,[],{}])
def test_core_rejects_truthiness(bad):
    with pytest.raises(ValueError, match='booleans'):
        build_report({'a':[bad], 'b':[False]})

@pytest.mark.parametrize('bad', ['false','true',0,1,None,[],{}])
def test_rows_reject_truthiness(bad):
    r=rows(); r[0]['correct']=bad
    with pytest.raises(ValueError, match='boolean'):
        results_from_rows(r)

@pytest.mark.parametrize('bad', [{},{'a':[],'b':[]},{'a':[True]},None,[]])
def test_no_comparison_rejected(bad):
    with pytest.raises(ValueError): build_report(bad)

@pytest.mark.parametrize('threshold', [float('nan'),float('inf'),-0.1,1.1,True,'0.03',None])
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError, match='threshold'):
        build_report({'a':[True], 'b':[False]},fragile_threshold=threshold)

@pytest.mark.parametrize('count', [0,-1,True,1.5,None])
def test_invalid_bootstrap(count):
    with pytest.raises(ValueError, match='n_boot'):
        build_report({'a':[True], 'b':[False]},n_boot=count)

@pytest.mark.parametrize('seed', range(10))
def test_row_permutation_does_not_change_pairing(seed):
    original=rows(); shuffled=rows(); random.Random(seed).shuffle(shuffled)
    assert results_from_rows(shuffled)==results_from_rows(original)
    r=build_report(results_from_rows(shuffled),n_boot=20)
    assert r.max_drift==0 and r.flip_rate==1
    assert r.verdict=='below_threshold'
    assert 'INVARIANT' not in r.summary()

@pytest.mark.parametrize('bad', [rows()+[rows()[0]],rows()[:-1],[{'condition':'a','correct':True}],[],{},[None]])
def test_pairing_failures(bad):
    with pytest.raises(ValueError): results_from_rows(bad)

@pytest.mark.parametrize('bad', ['', '   ', None, True, [], 1.5])
def test_bad_id(bad):
    r=rows(); r[0]['item_id']=bad
    with pytest.raises(ValueError, match='item_id'): results_from_rows(r)

def test_typed_ids_remain_distinct():
    r=rows()
    for row in r: row['item_id']=1 if row['item_id']=='x' else '1'
    assert len(results_from_rows(r)['a'])==2

def test_mismatched_coverage_same_lengths():
    r=rows(); r[3]['item_id']='z'
    with pytest.raises(ValueError, match='same item IDs'): results_from_rows(r)

def test_cli_mapping_requires_acknowledgment(tmp_path):
    p=tmp_path/'input.json'; p.write_text('{"a":[true],"b":[false]}')
    with pytest.raises(SystemExit) as ex: main(['report',str(p)])
    assert ex.value.code==2
    assert main(['report',str(p),'--assume-aligned','--fail-on-fragile'])==1

def test_cli_false_string_errors(tmp_path):
    p=tmp_path/'input.json'; p.write_text('{"a":["false"],"b":[false]}')
    with pytest.raises(SystemExit) as ex: main(['report',str(p),'--assume-aligned'])
    assert ex.value.code==2

def test_duplicate_json_keys_errors(tmp_path):
    p=tmp_path/'input.json'; p.write_text('{"a":[true],"a":[false],"b":[false]}')
    with pytest.raises(ValueError, match='duplicate JSON key'): _load_results(str(p),True)

def test_unequal_lengths():
    with pytest.raises(ValueError): build_report({'a':[True,False],'b':[True]})

def test_deterministic_bootstrap():
    r={'a':[True,True,False,True],'b':[False,True,False,True]}
    assert build_report(r,seed=7)==build_report(r,seed=7)

def test_baseline_numbers_preserved():
    r=build_report({'a':[True]*4,'b':[True,True,False,False]})
    assert (r.max_drift,r.flip_rate,r.verdict)==(0.5,0.5,'fragile')

def test_cli_rows(tmp_path,capsys):
    p=tmp_path/'input.json'; p.write_text(json.dumps(rows()))
    assert main(['report',str(p)])==0
    text=capsys.readouterr().out
    assert 'flip_rate=1.000' in text and 'BELOW_THRESHOLD' in text
