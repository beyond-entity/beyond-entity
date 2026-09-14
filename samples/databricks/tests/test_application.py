from contextlib import contextmanager
from datetime import datetime,timezone
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from lakehouse.application import *


def test_api_auth_ownership_identity_and_acknowledgement():
    publisher=MagicMock();actor=[Principal(7)]
    conn=MagicMock();conn.__enter__.return_value=conn
    conn.execute.return_value.fetchone.return_value={'customer_id':7,'updated_at':datetime.now(timezone.utc)}
    client=TestClient(create_app(lambda:conn,lambda req:actor[0],publisher))
    profile=dict(full_name='Test',email='test@example.com',phone='1',address='Test',country_code='US',marketing_consent=True)
    assert client.put('/customers/8',json=profile).status_code==403
    assert client.put('/customers/7',json=profile).status_code==200
    payload=dict(event_id=str(uuid4()),event_type='product_viewed',session_id='s',product_id=10,event_time='2026-09-01T00:00:00Z')
    assert client.post('/behavior-events',json=payload).status_code==202
    assert publisher.publish.call_args.args[0]['customer_id']=='7'
    assert client.post('/behavior-events',json={**payload,'customer_id':'999'}).status_code==400
    publisher.publish.side_effect=DeliveryError()
    assert client.post('/behavior-events',json=payload).status_code==503
    actor[0]=None
    assert client.post('/behavior-events',json=payload).status_code==401


def test_producer_requires_delivery_ack():
    producer=MagicMock();producer.flush.return_value=0
    p=KafkaPublisher(producer,'events')
    with pytest.raises(DeliveryError):p.publish({'customer_id':'1'})
    def produce(*a,**kw):kw['on_delivery'](None,None)
    producer.produce.side_effect=produce
    p.publish({'customer_id':'1'})
    assert producer.produce.call_args.kwargs['key']==b'1'


def test_order_state_and_outbox_are_in_same_transaction():
    conn=MagicMock();conn.transaction.return_value.__enter__.return_value=conn
    conn.execute.return_value.fetchone.side_effect=[{'order_id':1,'customer_id':7,'order_status':'paid'},None,None]
    eid=str(uuid4())
    assert commit_order_lifecycle(conn,Principal(7),1,eid,'order_cancelled','cancelled')['event_id']==eid
    statements=[c.args[0] for c in conn.execute.call_args_list]
    assert 'FOR UPDATE' in statements[0]
    assert any(s.startswith('UPDATE public.orders') for s in statements)
    assert any(s.startswith('INSERT INTO public.order_event_outbox') for s in statements)
    conn.transaction.return_value.__exit__.assert_called_once()


def test_relay_failure_keeps_unpublished_and_counts_attempt():
    conn=MagicMock();conn.execute.return_value.fetchall.return_value=[dict(event_id=str(uuid4()),event_type='order_created',customer_id=1,order_id=2,occurred_at=datetime.now(timezone.utc))]
    publisher=MagicMock();publisher.publish.side_effect=DeliveryError()
    assert relay_order_events(conn,publisher)=={'delivered':0,'failed':1}
    sql=[c.args[0] for c in conn.execute.call_args_list]
    assert any('SKIP LOCKED' in s for s in sql)
    assert any('publish_attempts=publish_attempts+1' in s for s in sql)
    assert not any('SET published_at' in s for s in sql)
