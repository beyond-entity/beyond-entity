import hashlib
from lakehouse.pipeline import CustomerPipeline
from lakehouse.modeled import Warehouse
from lakehouse.storage import LocalStore
from lakehouse.batch import SourcePipeline,PartnerPipeline
from lakehouse.silver import SilverPipeline
from lakehouse.streaming import EventPipeline
from lakehouse.gold import GoldPipeline,ActivityPipeline
from lakehouse.ml import register_model,MLPipeline
from lakehouse.exports import Exports
from lakehouse.runtime import customer_inputs
from lakehouse.epochs import Epochs,versions
from test_customer import Source,row,request
from test_batch import Commerce
from test_streaming import events
from test_ml import artifact

class CustomerTables:
    mapping={'raw':'raw_customers','quarantine':'quality_quarantine','normalized':'normalized_customers','identity':'customer_identity_map','silver':'silver_customers'}
    def __init__(self,w):self.w=w;self.names={k:w.name(t) for k,t in self.mapping.items()}
    def exists(self,k):return self.w.exists(self.mapping[k])
    def read(self,k,version=None):return self.w.read(self.mapping[k],version)
    def write(self,k,frame,mode):return self.w.write(self.mapping[k],frame,mode)


def test_complete_source_to_score_and_handoff(spark,tmp_path):
    store=LocalStore(tmp_path/'objects');w=Warehouse(spark,root=str(tmp_path/'delta'))
    CustomerPipeline(spark,store,CustomerTables(w),Source([row()]),'synthetic-id','synthetic-email','v1').run(request())
    req={'run_id':'commerce','window_start':'2026-09-01T00:00:00Z','window_end':'2026-09-03T00:00:00Z','full_snapshot':True}
    SourcePipeline(spark,w,store).run(req,Commerce())
    payload=b'partner_id,product_code,brand,supplier_region,effective_date\np1,SKU,Brand,US,2026-09-01\n'
    PartnerPipeline(spark,w,store).run({**req,'run_id':'partner'},payload,hashlib.sha256(payload).hexdigest(),'p1')
    raw=events(spark,[{}]);rv=w.write('raw_customer_events',raw)
    EventPipeline(spark,w,lambda:customer_inputs(store,w)[0]['identity'],store).reconcile(rv,'replay1')
    SilverPipeline(spark,w,store,lambda:customer_inputs(store,w)).run({**req,'run_id':'silver'},['USD'],'p1')
    gold=GoldPipeline(spark,w,store).run({'run_id':'gold','as_of_date':'2026-09-03'},'USD',['USD'])
    original_activity=versions(gold)['customer_activity_summary']
    ActivityPipeline(spark,w,store).run({'run_id':'live','window_end':'2026-09-03T12:00:00Z'})
    # Live table replacement does not change the daily version pinned by Gold and later ML.
    assert versions(Epochs(store,'gold').current()[0])['customer_activity_summary']==original_activity
    register_model(spark,w,store,artifact())
    pub=MLPipeline(spark,w,store).run({'run_id':'ml','as_of_date':'2026-09-03'},'synthetic-v1','USD')
    features=w.read('churn_feature_snapshots',versions(pub)['churn_feature_snapshots']).first()
    assert str(features.total_revenue)=='20.00' and features.total_orders==1 and features.views_30d==1
    assert Exports(spark,w,store).activation('handoff','2026-09-03','synthetic-v1','USD')['rows_written']==1
    assert Exports(spark,w,store).report('report','2026-09-01','2026-09-02')['rows_written']==1
    assert any(x['source_table']=='customer_activity_summary' and x['source_delta_version']==original_activity for x in pub['dependencies'])
