-- Multiple fault transitions may refer to the same last accepted heartbeat.
-- For example: recovery, then a timeout before the next heartbeat arrives.
BEGIN;
DO $$ BEGIN IF current_database() <> 'table_q_by_code' THEN RAISE EXCEPTION 'Wrong target database'; END IF; END $$;
ALTER TABLE public.device_fault_events DROP CONSTRAINT uq_fault_heartbeat;
ALTER TABLE public.device_fault_events ADD CONSTRAINT uq_fault_heartbeat UNIQUE(store_id,device_id,heartbeat_sequence,fault_code);
COMMIT;
