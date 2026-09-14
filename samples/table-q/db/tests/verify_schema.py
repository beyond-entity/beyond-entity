"""Compare a JSON result from catalog.sql with the Beyond Entity migration manifest."""
import collections
import json
import pathlib
import sys
root = pathlib.Path(__file__).resolve().parents[1]
expected = json.loads((root / 'schema_manifest.json').read_text())
actual = json.loads(pathlib.Path(sys.argv[1]).read_text())
columns = {(x['table'], x['name']): x for x in actual['columns']}
assert len(columns) == sum(map(len, expected['tables'].values()))
assert {t for t, _ in columns} == set(expected['tables'])
for table, fields in expected['tables'].items():
    for field in fields:
        live = columns[table, field['name']]
        for key in ['type', 'not_null', 'default']:
            assert live[key] == field[key], (table, field['name'], key, live[key], field[key])
        assert 'Beyond Entity security classification' in live['comment']
constraints = {(x['table'], x['name']): x for x in actual['constraints']}
for item in expected['constraints']:
    live = constraints[item['table'], item['name']]
    assert live['type'] == item['type'] and live['validated'], item
    if item['type'] in ['p', 'u', 'f']:
        assert live['columns'] == item['columns'], item
    if item['type'] == 'f':
        assert live['parent'] == item['parent'] and live['parent_columns'] == item['parent_columns'], item
indexes = {(x['table'], x['name']): x for x in actual['indexes']}
for item in expected['indexes']:
    live = indexes[item['table'], item['name']]
    assert live['valid'] and live['unique'] == item['unique'], item
    assert live['columns'] == item['columns'], item
    assert bool(live['where']) == bool(item['where']), item
assert all(x['valid'] for x in actual['indexes'])
counts = collections.Counter(x['type'] for x in actual['constraints'])
assert counts['p'] == 37 and counts['f'] == 70 and counts['c'] == 44 and counts['u'] == 27
print(f"PASS: {len(expected['tables'])} tables, {len(columns)} columns, 37 primary keys, 70 foreign keys, 44 checks, 32 unique rules (five partial), seven other indexes and security comments")
