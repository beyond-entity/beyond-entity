import hashlib
import pytest
from lakehouse.batch import SourcePipeline, PartnerPipeline
from lakehouse.silver import SilverPipeline
from lakehouse.modeled import Warehouse
from lakehouse.storage import LocalStore
from lakehouse.transforms import QualityError
from lakehouse.epochs import Epochs,versions

class Commerce:
    def __init__(self):
        meta={'updated_at':'2026-09-02T00:00:00Z','is_deleted':'false'}
        self.data={'orders':[dict(order_id='100',customer_id='1',order_status='completed',ordered_at='2026-09-01T01:00:00Z',currency='usd',**meta)],
            'products':[dict(product_id='10',product_code=' sku ',product_name=' Widget ',category='TOOLS',list_price='10.00',currency='USD',**meta)],
            'order_items':[dict(order_item_id='1000',order_id='100',product_id='10',quantity='2',unit_price='10.00',**meta)]}
    def rows(self,table,request):yield from self.data[table]

def fixture(spark,tmp_path):
    store=LocalStore(tmp_path/'objects');w=Warehouse(spark,root=str(tmp_path/'tables'));provider=Commerce()
    req={'run_id':'base','window_start':'2026-09-01T00:00:00Z','window_end':'2026-09-03T00:00:00Z','full_snapshot':True}
    sp=SourcePipeline(spark,w,store);sp.run(req,provider)
    data=b'partner_id,product_code,brand,supplier_region,effective_date\np1,SKU,Brand,US,2026-09-01\n'
    PartnerPipeline(spark,w,store).run(req,data,hashlib.sha256(data).hexdigest(),'p1')
    identity=spark.createDataFrame([(1,'key')],'customer_id long,customer_key string')
    cp=lambda:({'identity':identity},[('customers','c1','customer_identity_map',0)])
    return store,w,provider,req,sp,SilverPipeline(spark,w,store,cp)

def test_batch_end_to_end_replay_join_decimal_and_gate(spark,tmp_path):
    store,w,provider,req,source,silver=fixture(spark,tmp_path)
    source.run(req,provider)
    assert w.read('raw_orders').count()==1
    pub=silver.run(req,['USD'],'p1')
    assert str(w.read('silver_order_items').first().line_amount)=='20.00'
    assert w.read('enriched_products').first().brand=='Brand'
    assert silver.run(req,['USD'],'p1')==pub
    provider.data['order_items'][0]['product_id']='999'
    nextreq={**req,'run_id':'bad','window_start':req['window_end'],'window_end':'2026-09-04T00:00:00Z','full_snapshot':True}
    source.run(nextreq,provider)
    with pytest.raises(QualityError,match='reconciliation'):silver.run(nextreq,['USD'],'p1')
    assert Epochs(store,'silver_commerce').current()[0]['request']['run_id']=='base'
    assert w.read('quality_quarantine').count()>0

def test_partner_checksum_and_duplicate_sku(spark,tmp_path):
    store=LocalStore(tmp_path/'objects');p=PartnerPipeline(spark,Warehouse(spark,root=str(tmp_path/'tables')),store)
    req={'run_id':'p','window_end':'2026-09-03T00:00:00Z','full_snapshot':True}
    with pytest.raises(QualityError,match='checksum'):p.run(req,b'bad','0'*64,'p1')
