from pathlib import Path
import ast
import yaml
from lakehouse.cadence import full_baseline_due,products_due,job_timestamp


def test_catchup_cadence_and_utc_job_values():
    assert full_baseline_due('2026-09-03T01:40:00Z','2026-09-02T00:30:00Z')
    assert not full_baseline_due('2026-09-03T00:15:00Z','2026-09-02T00:30:00Z')
    assert not full_baseline_due('2026-09-03T02:00:00Z','2026-09-03T00:30:00Z')
    assert products_due('2026-09-03T02:00:00Z','2026-09-03T00:45:00Z')
    assert job_timestamp('2026-09-03T03:00:00')=='2026-09-03T03:00:00+00:00'


def test_bundle_has_complete_acyclic_paused_jobs_and_real_notebooks():
    root=Path(__file__).resolve().parents[1]
    config=yaml.safe_load((root/'databricks.yml').read_text())
    jobs=config['resources']['jobs']
    assert {'customers','commerce_source','events_bronze','events_silver','daily_refresh','live_activity','activation_refresh','partner_delivery','model_release','outbox_relay'}==set(jobs)
    for job in jobs.values():
        assert job['max_concurrent_runs']==1
        if 'schedule' in job:assert job['schedule']['pause_status']=='PAUSED'
        if 'continuous' in job:assert job['continuous']['pause_status']=='PAUSED'
        tasks={t['task_key']:t for t in job['tasks']};visited=set()
        def visit(key,stack):
            assert key in tasks and key not in stack
            if key in visited:return
            for dep in tasks[key].get('depends_on',[]):visit(dep['task_key'],stack|{key})
            visited.add(key)
        for key,t in tasks.items():
            visit(key,set())
            path=root/t['notebook_task']['notebook_path']
            assert path.exists();ast.parse(path.read_text())
            assert t['max_retries']==3
    daily={t['task_key']:t for t in jobs['daily_refresh']['tasks']}
    assert {'silver','reconcile_events'}=={x['task_key'] for x in daily['gold']['depends_on']}
    assert daily['report']['depends_on']==[{'task_key':'gold'}]


def test_modeled_sql_namespaces_and_literal_provenance():
    from lakehouse.modeled import ModeledSQL
    from unittest.mock import MagicMock
    one,two=ModeledSQL(MagicMock()),ModeledSQL(MagicMock())
    sql="SELECT 'raw_orders' AS source_table FROM raw_orders"
    a,b=one.qualify(sql),two.qualify(sql)
    assert "'raw_orders'" in a and a!=b
    assert 'FROM global_temp.'+one.prefix+'raw_orders' in a
