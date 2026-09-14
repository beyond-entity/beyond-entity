"""Runtime boundary helpers; all consumers pin source-of-truth publication versions."""
from .transforms import QualityError


def customer_inputs(store,warehouse):
    cursor,_=store.json('cursors/customers.json')
    if cursor is None:raise QualityError('Customer publication required')
    pub,_=store.json(f'publications/{cursor["last_batch_id"]}.json')
    names={'normalized':'normalized_customers','identity':'customer_identity_map','silver':'silver_customers'}
    deps=[('customers',pub['batch_id'],table,pub[key+'_version']) for key,table in names.items()]
    return {key:warehouse.read(table,pub[key+'_version']) for key,table in names.items()},deps


def pin(store,pipeline,run_id,selection):
    key=f'inputs/{pipeline}/{run_id}.json'
    value,_=store.json(key)
    if value is None:
        value=selection()
        store.immutable(key,value)
    return value
