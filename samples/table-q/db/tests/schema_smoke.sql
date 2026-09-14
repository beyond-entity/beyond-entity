-- Runs against the migrated database; all fixture data is rolled back.
\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
  org uuid := gen_random_uuid(); st uuid := gen_random_uuid();
  layout uuid := gen_random_uuid(); policy uuid := gen_random_uuid();
  device uuid := gen_random_uuid(); sess uuid := gen_random_uuid(); cmd uuid := gen_random_uuid();
BEGIN
  IF current_database() <> 'table_q_by_code' THEN RAISE EXCEPTION 'Wrong target database'; END IF;
  INSERT INTO public.organizations VALUES (org, 'Migration smoke test', now());
  INSERT INTO public.stores (store_id,organization_id,store_code,store_name,address,time_zone,latitude,longitude,store_status,created_at)
    VALUES (st,org,'test-' || st,'Migration smoke test','Test address','Asia/Seoul',37,127,'open',now());
  BEGIN
    UPDATE public.stores SET latitude=100 WHERE store_id=st;
    RAISE EXCEPTION 'Coordinate CHECK failed to reject invalid data';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO public.operator_store_grants VALUES (st,gen_random_uuid(),now(),NULL);
    RAISE EXCEPTION 'Foreign key failed to reject missing account';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
  INSERT INTO public.layout_versions VALUES (st,layout,1,'published',now());
  INSERT INTO public.store_policy_versions (store_id,policy_id,version_number,join_radius_metres,arrival_radius_metres,call_grace_seconds,max_party_size,created_at)
    VALUES (st,policy,1,200,50,300,8,now());
  INSERT INTO public.store_devices VALUES (st,device,'tablet','Test tablet',now(),NULL);
  INSERT INTO public.operating_sessions (store_id,session_id,business_date,layout_id,policy_id,owner_device_id,authority_epoch,next_queue_sequence,next_ticket_number,last_event_sequence,state_version,opened_at)
    VALUES (st,sess,current_date,layout,policy,device,1,1,1,0,0,now());
  IF (SELECT sync_snapshot_revision FROM public.operating_sessions WHERE store_id=st AND session_id=sess) <> 0 THEN
    RAISE EXCEPTION 'Snapshot revision default incorrect';
  END IF;
  BEGIN
    INSERT INTO public.operating_sessions (store_id,session_id,business_date,layout_id,policy_id,owner_device_id,authority_epoch,next_queue_sequence,next_ticket_number,last_event_sequence,state_version,opened_at)
      VALUES (st,gen_random_uuid(),current_date,layout,policy,device,1,1,1,0,0,now());
    RAISE EXCEPTION 'Partial unique index allowed two open sessions';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO public.command_receipts (store_id,command_id,session_id,actor_digest,operation_name,key_digest,request_digest,command_status,authority_epoch,created_at)
      VALUES (st,cmd,sess,'test','test','unfinished','test','processing',1,now());
    SET CONSTRAINTS ALL IMMEDIATE;
    RAISE EXCEPTION 'Deferred command trigger allowed processing status';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  SET CONSTRAINTS ALL DEFERRED;
  INSERT INTO public.command_receipts (store_id,command_id,session_id,actor_digest,operation_name,key_digest,request_digest,command_status,authority_epoch,created_at)
    VALUES (st,cmd,sess,'test','test','completed','test','processing',1,now());
  UPDATE public.command_receipts SET command_status='succeeded',completed_at=now(),replay_until=now()+interval '2 minutes',http_status=200
    WHERE store_id=st AND command_id=cmd;
  SET CONSTRAINTS ALL IMMEDIATE;
  RAISE NOTICE 'PASS: CHECK, FK, partial uniqueness, default, incomplete-command rejection and final-row command completion';
END $$;
ROLLBACK;
