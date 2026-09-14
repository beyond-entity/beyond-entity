from datetime import datetime,timezone,date
from decimal import Decimal
from lakehouse.gold import build_gold,GoldPipeline
from lakehouse.modeled import Warehouse
from lakehouse.storage import LocalStore
from lakehouse.epochs import Epochs


def gold_tables(spark):
    ts=datetime(2026,9,1,1,tzinfo=timezone.utc)
    return {
      'silver_customers':spark.createDataFrame([('c1','hash','US',True,ts,ts),('cold','hash2','KR',False,ts,ts)],'customer_key string,email_hash string,country_code string,marketing_consent boolean,created_at timestamp,updated_at timestamp'),
      'silver_orders':spark.createDataFrame([(1,'c1','completed',ts,'USD',ts),(2,'c1','completed',ts,'EUR',ts),(3,'c1','cancelled',ts,'USD',ts)],'order_id long,customer_key string,order_status string,ordered_at timestamp,currency string,updated_at timestamp'),
      'silver_order_items':spark.createDataFrame([(1,1,10,2,Decimal('10'),Decimal('20'),ts),(2,1,10,1,Decimal('5'),Decimal('5'),ts),(3,2,10,1,Decimal('7'),Decimal('7'),ts),(4,3,10,1,Decimal('99'),Decimal('99'),ts)],'order_item_id long,order_id long,product_id long,quantity int,unit_price decimal(18,2),line_amount decimal(18,2),updated_at timestamp'),
      'enriched_products':spark.createDataFrame([(10,'SKU','Widget','tools','Brand','US')],'product_id long,product_code string,product_name string,category string,brand string,supplier_region string'),
      'silver_customer_events':spark.createDataFrame([('e1','product_viewed','c1','s',10,None,ts,date(2026,9,1)),('e2','product_added_to_cart','c1','s',10,None,ts,date(2026,9,1))],'event_id string,event_type string,customer_key string,session_id string,product_id long,order_id long,event_time timestamp,event_date date')}


def test_all_gold_marts_currency_fanout_and_cold_start(spark):
    out=build_gold(spark,gold_tables(spark),'2026-09-03','USD')
    sales={r.currency:r.asDict() for r in out['daily_sales'].collect()}
    assert sales['USD']['gross_revenue']==Decimal('25') and sales['USD']['order_count']==1
    assert sales['EUR']['gross_revenue']==Decimal('7')
    assert out['product_performance'].count()==2
    assert out['customer_activity_summary'].first().product_views==1
    cold=out['customer_360'].filter("customer_key='cold'").first()
    assert cold.currency=='USD' and cold.total_orders==0 and cold.total_revenue==0
    assert out['customer_lifetime_value'].count()==2


def test_gold_publication_pins_customer_and_event_versions(spark,tmp_path):
    w=Warehouse(spark,root=str(tmp_path/'delta'));store=LocalStore(tmp_path/'objects');tables=gold_tables(spark)
    customer_version=w.write('silver_customers',tables.pop('silver_customers'))
    event_version=w.write('silver_customer_events',tables.pop('silver_customer_events'))
    v={t:w.write(t,f) for t,f in tables.items()}
    e=Epochs(store,'silver_commerce')
    with e.run({'run_id':'silver1'}) as (prior,token):
        e.commit({'run_id':'silver1'},v,prior,token,[('customers','c1','silver_customers',customer_version)])
    req={'run_id':'g1','as_of_date':'2026-09-03'}
    p=GoldPipeline(spark,w,store);first=p.run(req,'USD',['USD','EUR'])
    assert p.run(req,'USD',['USD','EUR'])==first
    assert len(first['tables'])==5
    assert any(d['source_table']=='silver_customer_events' and d['source_delta_version']==event_version for d in first['dependencies'])
