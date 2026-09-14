"""Source application adapters. Authentication is injected, never synthesized."""
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
from threading import Lock
from uuid import UUID
from .storage import encode


class ServiceError(RuntimeError):
    def __init__(self,status,code,message):
        self.status,self.code,self.message=status,code,message
        super().__init__(message)


class DeliveryError(RuntimeError):pass


@dataclass(frozen=True)
class Principal:
    customer_id:int
    roles:frozenset=frozenset()


class KafkaPublisher:
    def __init__(self,producer,topic):
        self.producer,self.topic,self.lock=producer,topic,Lock()
    @classmethod
    def configured(cls,options,topic):
        from confluent_kafka import Producer
        # Required reliability options cannot be overridden by weaker caller settings.
        return cls(Producer({**options,'acks':'all','enable.idempotence':True}),topic)
    def publish(self,event):
        result={'called':False,'error':None}
        def delivered(error,message):result.update(called=True,error=error)
        with self.lock:
            try:
                self.producer.produce(self.topic,key=str(event['customer_id']).encode(),value=encode(event),on_delivery=delivered)
                pending=self.producer.flush(30)
            except Exception:
                raise DeliveryError('Broker delivery unavailable') from None
            if pending or not result['called'] or result['error'] is not None:
                raise DeliveryError('Broker delivery was not acknowledged')


def update_profile(conn,principal,customer_id,profile):
    if principal.customer_id!=customer_id and 'customer_profile_admin' not in principal.roles:
        raise ServiceError(403,'FORBIDDEN','Profile ownership required')
    fields=['full_name','email','phone','address','country_code','marketing_consent']
    row=conn.execute('UPDATE public.customers SET '+','.join(f'{f}=%s' for f in fields)+',updated_at=CURRENT_TIMESTAMP '
        'WHERE customer_id=%s AND is_deleted=FALSE RETURNING customer_id,updated_at',tuple(profile[f] for f in fields)+(customer_id,)).fetchone()
    if row is None:raise ServiceError(404,'NOT_FOUND','Profile not found')
    return {'customer_id':row['customer_id'],'updated_at':row['updated_at'].isoformat()}


def commit_order_lifecycle(conn,principal,order_id,event_id,event_type,new_status):
    UUID(event_id)
    allowed={'order_created':'created','order_cancelled':'cancelled'}
    if allowed.get(event_type)!=new_status:raise ServiceError(400,'INVALID_TRANSITION','Event and order state differ')
    with conn.transaction():
        order=conn.execute('SELECT order_id,customer_id,order_status FROM public.orders WHERE order_id=%s AND is_deleted=FALSE FOR UPDATE',(order_id,)).fetchone()
        if order is None:raise ServiceError(404,'NOT_FOUND','Order not found')
        if order['customer_id']!=principal.customer_id:raise ServiceError(403,'FORBIDDEN','Order ownership required')
        existing=conn.execute('SELECT event_id,order_id,event_type FROM public.order_event_outbox WHERE event_id=%s',(event_id,)).fetchone()
        if existing:
            if existing['order_id']==order_id and existing['event_type']==event_type:return {'event_id':event_id}
            raise ServiceError(409,'EVENT_CONFLICT','Event identifier already used')
        repeated=conn.execute('SELECT event_id FROM public.order_event_outbox WHERE order_id=%s AND event_type=%s',(order_id,event_type)).fetchone()
        if repeated:raise ServiceError(409,'TRANSITION_CONFLICT','Order event already exists')
        if (event_type=='order_created' and order['order_status']!='created') or (event_type=='order_cancelled' and order['order_status'] not in ('created','paid')):
            raise ServiceError(409,'INVALID_TRANSITION','Order cannot enter the requested state')
        conn.execute('UPDATE public.orders SET order_status=%s,updated_at=CURRENT_TIMESTAMP WHERE order_id=%s AND customer_id=%s',(new_status,order_id,principal.customer_id))
        conn.execute('INSERT INTO public.order_event_outbox(event_id,event_type,customer_id,order_id,occurred_at,publish_attempts) VALUES(%s,%s,%s,%s,CURRENT_TIMESTAMP,0)',(event_id,event_type,principal.customer_id,order_id))
        return {'event_id':event_id}


def relay_order_events(conn,publisher,limit=100):
    if not isinstance(limit,int) or not 1<=limit<=1000:raise ValueError('Invalid relay batch size')
    delivered=failed=0
    with conn.transaction():
        rows=conn.execute('SELECT event_id,event_type,customer_id,order_id,occurred_at FROM public.order_event_outbox WHERE published_at IS NULL ORDER BY occurred_at,event_id LIMIT %s FOR UPDATE SKIP LOCKED',(limit,)).fetchall()
        for row in rows:
            conn.execute('UPDATE public.order_event_outbox SET publish_attempts=publish_attempts+1 WHERE event_id=%s',(row['event_id'],))
            event=dict(event_id=row['event_id'],event_type=row['event_type'],customer_id=str(row['customer_id']),session_id=None,product_id=None,
                       order_id=str(row['order_id']),event_time=row['occurred_at'].astimezone(timezone.utc).isoformat(),schema_version='1')
            try:publisher.publish(event)
            except DeliveryError:failed+=1;continue
            conn.execute('UPDATE public.order_event_outbox SET published_at=CURRENT_TIMESTAMP WHERE event_id=%s',(row['event_id'],));delivered+=1
    return {'delivered':delivered,'failed':failed}


def create_app(connect,authenticate,publisher):
    """authenticate(Request) must return a verified Principal or None. No default verifier."""
    if not callable(authenticate):raise ValueError('A real credential verifier must be configured')
    from fastapi import FastAPI,Request,Depends
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from pydantic import BaseModel,ConfigDict,StrictBool,StrictInt,StrictStr,AwareDatetime,Field
    from typing import Annotated,Literal
    class Profile(BaseModel):
        model_config=ConfigDict(extra='forbid')
        full_name:StrictStr
        email:Annotated[StrictStr,Field(pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')]
        phone:StrictStr
        address:StrictStr
        country_code:Annotated[StrictStr,Field(pattern='^[A-Za-z]{2}$')]
        marketing_consent:StrictBool
    class Behavior(BaseModel):
        model_config=ConfigDict(extra='forbid')
        event_id:UUID
        event_type:Literal['product_viewed','product_added_to_cart']
        session_id:Annotated[StrictStr,Field(min_length=1)]
        product_id:Annotated[StrictInt,Field(gt=0)]
        event_time:AwareDatetime
    app=FastAPI(title='Retail Lakehouse Source API',version='0.1.0')
    def principal(request:Request):
        value=authenticate(request)
        if not isinstance(value,Principal):raise ServiceError(401,'UNAUTHORIZED','Valid credentials required')
        return value
    @app.exception_handler(ServiceError)
    async def service_error(request,error):return JSONResponse(status_code=error.status,content={'code':error.code,'message':error.message})
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,error):return JSONResponse(status_code=400,content={'code':'INVALID_REQUEST','message':'Request violates the API contract'})
    @app.put('/customers/{customer_id}')
    def profile(customer_id:int,body:Profile,actor=Depends(principal)):
        with connect() as conn:return update_profile(conn,actor,customer_id,body.model_dump())
    @app.post('/behavior-events',status_code=202)
    def behavior(body:Behavior,actor=Depends(principal)):
        if not body.session_id.strip() or body.event_time>datetime.now(timezone.utc)+timedelta(minutes=5):
            raise ServiceError(400,'INVALID_REQUEST','Invalid event time or session')
        event=dict(event_id=str(body.event_id),event_type=body.event_type,customer_id=str(actor.customer_id),session_id=body.session_id,
                   product_id=str(body.product_id),order_id=None,event_time=body.event_time.astimezone(timezone.utc).isoformat(),schema_version='1')
        try:publisher.publish(event)
        except DeliveryError:raise ServiceError(503,'BROKER_UNAVAILABLE','Event was not acknowledged') from None
        return {'event_id':event['event_id'],'accepted_at':datetime.now(timezone.utc).isoformat()}
    return app
