-- Beyond Entity Table Q By Codex; generated from MCP schema and canonical constraint documents.

-- Target: table_q_by_code only. No existing database contents are changed.

BEGIN;

DO $$ BEGIN IF current_database() <> 'table_q_by_code' THEN RAISE EXCEPTION 'Wrong target database'; END IF; END $$;

CREATE TABLE public."administrative_audit_events" (
  "admin_event_id" uuid NOT NULL,
  "organization_id" uuid NOT NULL,
  "actor_account_id" uuid NOT NULL,
  "store_id" uuid,
  "action_code" text NOT NULL,
  "resource_id" uuid NOT NULL,
  "occurred_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."administrative_audit_events" IS 'Append-only typed administrative audit. No raw PIN/password/email or arbitrary notes. Every admin mutation must append one in the same transaction; actor and organization come from verified middleware.';

COMMENT ON COLUMN public."administrative_audit_events"."admin_event_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."administrative_audit_events"."organization_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."administrative_audit_events"."actor_account_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."administrative_audit_events"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."administrative_audit_events"."action_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."administrative_audit_events"."resource_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."administrative_audit_events"."occurred_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."operator_sessions" (
  "operator_session_id" uuid NOT NULL,
  "account_id" uuid NOT NULL,
  "token_hash" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "expires_at" timestamp with time zone NOT NULL,
  "revoked_at" timestamp with time zone
);

COMMENT ON TABLE public."operator_sessions" IS 'Secure HttpOnly SameSite cookie with8h absolute lifetime. Check account disabled/grants at every request. Logout revokes current session; CSRF token/origin protections on cookie-authenticated writes.';

COMMENT ON COLUMN public."operator_sessions"."operator_session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_sessions"."account_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_sessions"."token_hash" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 4}';

COMMENT ON COLUMN public."operator_sessions"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_sessions"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_sessions"."revoked_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."delivery_receipts" (
  "store_id" uuid NOT NULL,
  "receipt_id" uuid NOT NULL,
  "job_id" uuid NOT NULL,
  "attempt_id" uuid NOT NULL,
  "source_kind" text NOT NULL,
  "source_event_digest" text NOT NULL,
  "receipt_status" text NOT NULL,
  "reported_at" timestamp with time zone NOT NULL,
  "received_at" timestamp with time zone NOT NULL,
  "applied" boolean NOT NULL
);

COMMENT ON TABLE public."delivery_receipts" IS 'Authenticated simulator acknowledgement, deduplicated by stable source event ID digest. Attempt/job/channel/device binding required. applied records whether live delivery state changed; late contradictory receipts remain evidence. No external real provider contract selected.';

COMMENT ON COLUMN public."delivery_receipts"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_receipts"."receipt_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_receipts"."job_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_receipts"."attempt_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_receipts"."source_kind" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_receipts"."source_event_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."delivery_receipts"."receipt_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_receipts"."reported_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_receipts"."received_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_receipts"."applied" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."delivery_attempts" (
  "store_id" uuid NOT NULL,
  "attempt_id" uuid NOT NULL,
  "job_id" uuid NOT NULL,
  "attempt_number" integer NOT NULL,
  "lease_token" uuid NOT NULL,
  "started_at" timestamp with time zone NOT NULL,
  "finished_at" timestamp with time zone,
  "outcome" text NOT NULL,
  "provider_request_id" text,
  "error_code" text
);

COMMENT ON TABLE public."delivery_attempts" IS 'One append-on-start, finish-once attempt record per claimed send. Error codes are bounded enums, never raw provider bodies. Lease token fences worker writes; stable job_id deduplicates remote effects across attempts.';

COMMENT ON COLUMN public."delivery_attempts"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_attempts"."attempt_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_attempts"."job_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_attempts"."attempt_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_attempts"."lease_token" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."delivery_attempts"."started_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_attempts"."finished_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_attempts"."outcome" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_attempts"."provider_request_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_attempts"."error_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."device_sync_commands" (
  "store_id" uuid NOT NULL,
  "sync_command_id" uuid NOT NULL,
  "device_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "authority_epoch" bigint NOT NULL,
  "device_sequence" bigint NOT NULL,
  "base_version" bigint NOT NULL,
  "layout_id" uuid NOT NULL,
  "operation" text NOT NULL,
  "group_id" uuid,
  "call_id" uuid,
  "allocation_id" uuid,
  "table_id" uuid,
  "occurred_at" timestamp with time zone NOT NULL,
  "command_digest" text NOT NULL,
  "sync_status" text NOT NULL,
  "received_at" timestamp with time zone NOT NULL,
  "resolved_at" timestamp with time zone,
  "result_version" bigint,
  "reason_code" text
);

COMMENT ON TABLE public."device_sync_commands" IS 'Typed immutable offline evidence. Per-device sequence dedup; mismatched digest409. Stale epoch evidence preserved as rejected; never automatically applied. No raw credentials or JSON command payload.';

COMMENT ON COLUMN public."device_sync_commands"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_sync_commands"."sync_command_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_sync_commands"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_sync_commands"."authority_epoch" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_sync_commands"."device_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."base_version" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."layout_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."operation" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."call_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."allocation_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."table_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."occurred_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."command_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 4}';

COMMENT ON COLUMN public."device_sync_commands"."sync_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."received_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."resolved_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."result_version" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_commands"."reason_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."device_sync_cursors" (
  "store_id" uuid NOT NULL,
  "device_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "authority_epoch" bigint NOT NULL,
  "last_received_sequence" bigint NOT NULL,
  "last_resolved_sequence" bigint NOT NULL,
  "updated_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."device_sync_cursors" IS 'Cursor only advances atomically with matching command disposition. Intake requires consecutive sequence; resolved cursor stops at first unresolved conflict. Later physical evidence can still be received.';

COMMENT ON COLUMN public."device_sync_cursors"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_sync_cursors"."device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_sync_cursors"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_sync_cursors"."authority_epoch" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_sync_cursors"."last_received_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_cursors"."last_resolved_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_sync_cursors"."updated_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."dining_tables" (
  "store_id" uuid NOT NULL,
  "table_id" uuid NOT NULL,
  "row_id" uuid NOT NULL,
  "table_number" text NOT NULL,
  "row_position" integer NOT NULL,
  "seat_count" integer NOT NULL,
  "is_window" boolean NOT NULL,
  "order_qr_enabled" boolean NOT NULL
);

COMMENT ON TABLE public."dining_tables" IS 'Belongs to immutable version through row. Availability derived from active allocation; no duplicated occupancy flag. Table number must also be unique across rows of same layout, checked at publish.';

COMMENT ON COLUMN public."dining_tables"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."dining_tables"."table_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."dining_tables"."row_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."dining_tables"."table_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."dining_tables"."row_position" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."dining_tables"."seat_count" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."dining_tables"."is_window" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."dining_tables"."order_qr_enabled" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

CREATE TABLE public."command_receipts" (
  "store_id" uuid NOT NULL,
  "command_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "actor_digest" text NOT NULL,
  "operation_name" text NOT NULL,
  "key_digest" text NOT NULL,
  "request_digest" text NOT NULL,
  "command_status" text NOT NULL,
  "authority_epoch" bigint NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "completed_at" timestamp with time zone,
  "replay_until" timestamp with time zone,
  "http_status" integer,
  "result_group_id" uuid,
  "result_ticket_code" text,
  "result_group_status" text,
  "result_arrival_confirmed" boolean,
  "result_state_version" bigint,
  "result_call_id" uuid,
  "result_assigned_table" text,
  "result_called_at" timestamp with time zone,
  "result_review_due_at" timestamp with time zone,
  "result_recall_count" integer,
  "result_table_status" text,
  "result_expires_at" timestamp with time zone,
  "result_access_scope" text
);

COMMENT ON TABLE public."command_receipts" IS 'One typed successful result per actor/operation/key, atomic with domain writes. Processing row must never commit: deferred migration trigger and controller commit guard. Validation failures roll back. Tombstone prevents re-execution after replay expiry. No JSON result payload.';

COMMENT ON COLUMN public."command_receipts"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."command_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."actor_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."command_receipts"."operation_name" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."key_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."command_receipts"."request_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."command_receipts"."command_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."authority_epoch" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."completed_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."replay_until" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."http_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_ticket_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_group_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_arrival_confirmed" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_state_version" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_call_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_assigned_table" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_called_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_review_due_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_recall_count" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_table_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_receipts"."result_access_scope" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."group_calls" (
  "store_id" uuid NOT NULL,
  "call_id" uuid NOT NULL,
  "group_id" uuid NOT NULL,
  "call_number" integer NOT NULL,
  "call_status" text NOT NULL,
  "called_at" timestamp with time zone NOT NULL,
  "review_due_at" timestamp with time zone NOT NULL,
  "last_notified_at" timestamp with time zone,
  "recall_count" integer NOT NULL,
  "closed_at" timestamp with time zone
);

COMMENT ON TABLE public."group_calls" IS 'One call cycle holds one table. Recall increments count without extending grace; manual no-show after grace. Notification attempt records are later stage.';

COMMENT ON COLUMN public."group_calls"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."call_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."call_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."call_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."called_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."review_due_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."last_notified_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."recall_count" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."group_calls"."closed_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."hq_policy_templates" (
  "organization_id" uuid NOT NULL,
  "template_id" uuid NOT NULL,
  "version_number" integer NOT NULL,
  "join_radius_metres" integer NOT NULL,
  "arrival_radius_metres" integer NOT NULL,
  "call_grace_seconds" integer NOT NULL,
  "allow_join_override" boolean NOT NULL,
  "allow_arrival_override" boolean NOT NULL,
  "allow_grace_override" boolean NOT NULL,
  "created_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."hq_policy_templates" IS 'Immutable head-office defaults and override permissions. Effective store policy is frozen when published, then pinned at session open. Unchanged active sessions never inherit a later default.';

COMMENT ON COLUMN public."hq_policy_templates"."organization_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."hq_policy_templates"."template_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."hq_policy_templates"."version_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."hq_policy_templates"."join_radius_metres" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."hq_policy_templates"."arrival_radius_metres" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."hq_policy_templates"."call_grace_seconds" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."hq_policy_templates"."allow_join_override" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."hq_policy_templates"."allow_arrival_override" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."hq_policy_templates"."allow_grace_override" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."hq_policy_templates"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."device_health" (
  "store_id" uuid NOT NULL,
  "device_id" uuid NOT NULL,
  "heartbeat_sequence" bigint NOT NULL,
  "last_seen_at" timestamp with time zone NOT NULL,
  "device_time" timestamp with time zone NOT NULL,
  "fault_code" text NOT NULL,
  "connectivity_status" text NOT NULL
);

COMMENT ON TABLE public."device_health" IS 'Latest authenticated heartbeat using server receive time. Every10s heartbeat; stale after30s. Stale owner tablet pauses remote joins but never transfers authority.';

COMMENT ON COLUMN public."device_health"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_health"."device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_health"."heartbeat_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_health"."last_seen_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_health"."device_time" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_health"."fault_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_health"."connectivity_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."operator_store_grants" (
  "store_id" uuid NOT NULL,
  "account_id" uuid NOT NULL,
  "granted_at" timestamp with time zone NOT NULL,
  "revoked_at" timestamp with time zone
);

COMMENT ON TABLE public."operator_store_grants" IS 'Manager assigned stores, same organization enforced by authorization before grant. Head office organization scope does not need one row per store.';

COMMENT ON COLUMN public."operator_store_grants"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operator_store_grants"."account_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_store_grants"."granted_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_store_grants"."revoked_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."operator_accounts" (
  "account_id" uuid NOT NULL,
  "organization_id" uuid NOT NULL,
  "login_digest" text NOT NULL,
  "email_ciphertext" text NOT NULL,
  "display_name" text NOT NULL,
  "password_verifier" text NOT NULL,
  "account_role" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "disabled_at" timestamp with time zone
);

COMMENT ON TABLE public."operator_accounts" IS 'Named head-office/manager identity. Login digest HMAC normalized email; AEAD encrypted email incl nonce/tag envelope and external key version encoded. Password Argon2id runtime verifier, never raw. Initial head-office account seeded securely; no public account registration.';

COMMENT ON COLUMN public."operator_accounts"."account_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_accounts"."organization_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operator_accounts"."login_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."operator_accounts"."email_ciphertext" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 2, "integrity": "H", "pii_level": 3, "sensitivity_level": 4}';

COMMENT ON COLUMN public."operator_accounts"."display_name" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 3, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_accounts"."password_verifier" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."operator_accounts"."account_role" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_accounts"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."operator_accounts"."disabled_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."physical_table_facts" (
  "store_id" uuid NOT NULL,
  "fact_id" uuid NOT NULL,
  "sync_command_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "table_id" uuid NOT NULL,
  "group_id" uuid NOT NULL,
  "fact_kind" text NOT NULL,
  "occurred_at" timestamp with time zone NOT NULL,
  "recorded_at" timestamp with time zone NOT NULL,
  "quarantine_active" boolean NOT NULL
);

COMMENT ON TABLE public."physical_table_facts" IS 'Preserves seating/clearing observations even when ticket is cancelled server-side. Unresolved seated fact blocks automatic table allocation. Clear observation is evidence, not permission to release a later canonical occupancy. Manager verifies before quarantine release.';

COMMENT ON COLUMN public."physical_table_facts"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."physical_table_facts"."fact_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."physical_table_facts"."sync_command_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."physical_table_facts"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."physical_table_facts"."table_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."physical_table_facts"."group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."physical_table_facts"."fact_kind" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."physical_table_facts"."occurred_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."physical_table_facts"."recorded_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."physical_table_facts"."quarantine_active" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."sync_conflicts" (
  "store_id" uuid NOT NULL,
  "conflict_id" uuid NOT NULL,
  "sync_command_id" uuid NOT NULL,
  "server_version" bigint NOT NULL,
  "reason_code" text NOT NULL,
  "conflict_status" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "resolved_at" timestamp with time zone,
  "resolution_code" text,
  "resolver_account_id" uuid
);

COMMENT ON TABLE public."sync_conflicts" IS 'Manager-reviewed discrepancy. Never use timestamps alone to override canonical state. Resolver account relation added with Stage7 accounts; resolution requires physical occupancy cleared/explicitly reconciled.';

COMMENT ON COLUMN public."sync_conflicts"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."sync_conflicts"."conflict_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."sync_conflicts"."sync_command_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."sync_conflicts"."server_version" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."sync_conflicts"."reason_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."sync_conflicts"."conflict_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."sync_conflicts"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."sync_conflicts"."resolved_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."sync_conflicts"."resolution_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."sync_conflicts"."resolver_account_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

CREATE TABLE public."command_secret_replays" (
  "store_id" uuid NOT NULL,
  "command_id" uuid NOT NULL,
  "secret_kind" text NOT NULL,
  "ciphertext" text NOT NULL,
  "key_version" text NOT NULL,
  "nonce" text NOT NULL,
  "auth_tag" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "expires_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."command_secret_replays" IS 'Separate short-lived AEAD ciphertext. Key held outside DB, AAD binds store/command/actor/operation/kind/expiry. Replay checks current credential and original capability/challenge liveness; never extends expiry. Purge expired ciphertext while retaining command tombstone.';

COMMENT ON COLUMN public."command_secret_replays"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_secret_replays"."command_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_secret_replays"."secret_kind" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_secret_replays"."ciphertext" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 2, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."command_secret_replays"."key_version" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_secret_replays"."nonce" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 4}';

COMMENT ON COLUMN public."command_secret_replays"."auth_tag" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 4}';

COMMENT ON COLUMN public."command_secret_replays"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."command_secret_replays"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."queue_events" (
  "store_id" uuid NOT NULL,
  "event_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "event_sequence" bigint NOT NULL,
  "group_id" uuid,
  "call_id" uuid,
  "allocation_id" uuid,
  "actor_device_id" uuid,
  "actor_kind" text NOT NULL,
  "event_type" text NOT NULL,
  "previous_status" text,
  "next_status" text,
  "previous_queue_sequence" bigint,
  "next_queue_sequence" bigint,
  "occurred_at" timestamp with time zone NOT NULL,
  "recorded_at" timestamp with time zone NOT NULL,
  "reason" text
);

COMMENT ON TABLE public."queue_events" IS 'Append-only history. Backend-recorded monotonic sequence orders events, not client clock. Typed lineage fields, no opaque JSON. Command journal and delivery outbox are separate stage5/6 entities.';

COMMENT ON COLUMN public."queue_events"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."event_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."event_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."call_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."allocation_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."actor_device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."actor_kind" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."event_type" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."previous_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."next_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."previous_queue_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."next_queue_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."occurred_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."recorded_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_events"."reason" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

CREATE TABLE public."partner_credentials" (
  "partner_id" uuid NOT NULL,
  "organization_id" uuid NOT NULL,
  "partner_name" text NOT NULL,
  "token_hash" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "expires_at" timestamp with time zone NOT NULL,
  "revoked_at" timestamp with time zone
);

COMMENT ON TABLE public."partner_credentials" IS 'Organization-scoped aggregate read only. No join/mutation permission; limit60 requests/minute per credential plus network abuse limit, shared rate-window service. Expire and revoke credentials.';

COMMENT ON COLUMN public."partner_credentials"."partner_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."partner_credentials"."organization_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."partner_credentials"."partner_name" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."partner_credentials"."token_hash" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 4}';

COMMENT ON COLUMN public."partner_credentials"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."partner_credentials"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."partner_credentials"."revoked_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."device_credentials" (
  "store_id" uuid NOT NULL,
  "credential_id" uuid NOT NULL,
  "device_id" uuid NOT NULL,
  "token_hash" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "expires_at" timestamp with time zone NOT NULL,
  "revoked_at" timestamp with time zone
);

COMMENT ON TABLE public."device_credentials" IS 'Opaque revocable store/device-bound credential. Device kind limits actions; tablet queue actions additionally require current session owner. No individual staff login. Display new token once via protected enrollment; cannot recover hash.';

COMMENT ON COLUMN public."device_credentials"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_credentials"."credential_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_credentials"."device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_credentials"."token_hash" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 4}';

COMMENT ON COLUMN public."device_credentials"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_credentials"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_credentials"."revoked_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."device_fault_events" (
  "store_id" uuid NOT NULL,
  "fault_event_id" uuid NOT NULL,
  "device_id" uuid NOT NULL,
  "heartbeat_sequence" bigint NOT NULL,
  "previous_fault_code" text,
  "fault_code" text NOT NULL,
  "received_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."device_fault_events" IS 'Append only when accepted heartbeat fault code changes; includes recovery to none. No raw device logs. Connectivity latest state remains device_health, fault metrics count explicit code transitions.';

COMMENT ON COLUMN public."device_fault_events"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_fault_events"."fault_event_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_fault_events"."device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."device_fault_events"."heartbeat_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_fault_events"."previous_fault_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_fault_events"."fault_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."device_fault_events"."received_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."organizations" (
  "organization_id" uuid NOT NULL,
  "organization_name" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."organizations" IS 'Chain owner. Account/permission tables are stage 7.';

COMMENT ON COLUMN public."organizations"."organization_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."organizations"."organization_name" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."organizations"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

CREATE TABLE public."stores" (
  "store_id" uuid NOT NULL,
  "organization_id" uuid NOT NULL,
  "store_code" text NOT NULL,
  "store_name" text NOT NULL,
  "address" text NOT NULL,
  "time_zone" text NOT NULL,
  "latitude" double precision NOT NULL,
  "longitude" double precision NOT NULL,
  "store_status" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "contact_phone_ciphertext" text,
  "contact_email_ciphertext" text
);

COMMENT ON TABLE public."stores" IS 'Coordinates are store location, never customer location history. Opening-hour calendars deferred.';

COMMENT ON COLUMN public."stores"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."stores"."organization_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."stores"."store_code" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "L", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 1}';

COMMENT ON COLUMN public."stores"."store_name" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "L", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 1}';

COMMENT ON COLUMN public."stores"."address" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "L", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 1}';

COMMENT ON COLUMN public."stores"."time_zone" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "L", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 1}';

COMMENT ON COLUMN public."stores"."latitude" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "L", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 1}';

COMMENT ON COLUMN public."stores"."longitude" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "L", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 1}';

COMMENT ON COLUMN public."stores"."store_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "L", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 1}';

COMMENT ON COLUMN public."stores"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."stores"."contact_phone_ciphertext" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 2, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."stores"."contact_email_ciphertext" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "H", "encryption_level": 2, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

CREATE TABLE public."watch_codes" (
  "store_id" uuid NOT NULL,
  "watch_code_id" uuid NOT NULL,
  "group_id" uuid NOT NULL,
  "code_digest" text NOT NULL,
  "issued_at" timestamp with time zone NOT NULL,
  "expires_at" timestamp with time zone NOT NULL,
  "revoked_at" timestamp with time zone
);

COMMENT ON TABLE public."watch_codes" IS 'Four-digit global demo code; keyed HMAC prevents offline enumeration from DB. Expires at session close or 12h maximum, earlier on seating/cancel/no-show. Expired rows revoked before reuse; no overwrite or collision. Ten thousand active code limit must return capacity error; larger deployments need store scope or longer code.';

COMMENT ON COLUMN public."watch_codes"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."watch_codes"."watch_code_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."watch_codes"."group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."watch_codes"."code_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."watch_codes"."issued_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."watch_codes"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."watch_codes"."revoked_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."arrival_challenges" (
  "store_id" uuid NOT NULL,
  "challenge_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "code_digest" text NOT NULL,
  "valid_from" timestamp with time zone NOT NULL,
  "expires_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."arrival_challenges" IS 'Store-scoped rotating presence code, 60s validity. Verify while customer within50m or staff confirms in person. Static join QR alone never confirms arrival; raw location discarded after distance check.';

COMMENT ON COLUMN public."arrival_challenges"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."arrival_challenges"."challenge_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."arrival_challenges"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."arrival_challenges"."code_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 4}';

COMMENT ON COLUMN public."arrival_challenges"."valid_from" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."arrival_challenges"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

CREATE TABLE public."store_devices" (
  "store_id" uuid NOT NULL,
  "device_id" uuid NOT NULL,
  "device_kind" text NOT NULL,
  "device_label" text NOT NULL,
  "registered_at" timestamp with time zone NOT NULL,
  "revoked_at" timestamp with time zone
);

COMMENT ON TABLE public."store_devices" IS 'Minimum registration for operating authority and event actor attribution. Heartbeats/commands/credentials are later stages.';

COMMENT ON COLUMN public."store_devices"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_devices"."device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_devices"."device_kind" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_devices"."device_label" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_devices"."registered_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_devices"."revoked_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

CREATE TABLE public."store_join_qr_versions" (
  "store_id" uuid NOT NULL,
  "qr_id" uuid NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "revoked_at" timestamp with time zone
);

COMMENT ON TABLE public."store_join_qr_versions" IS 'Public opaque QR version ID, not an authentication secret. Encode real URL /q/{qr_id}; regeneration revokes older version and prints a new URL. Existing owner tickets unaffected. Static QR never confirms arrival.';

COMMENT ON COLUMN public."store_join_qr_versions"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_join_qr_versions"."qr_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."store_join_qr_versions"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."store_join_qr_versions"."revoked_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."store_policy_versions" (
  "store_id" uuid NOT NULL,
  "policy_id" uuid NOT NULL,
  "version_number" integer NOT NULL,
  "join_radius_metres" integer NOT NULL,
  "arrival_radius_metres" integer NOT NULL,
  "call_grace_seconds" integer NOT NULL,
  "max_party_size" integer NOT NULL,
  "max_deferrals" integer,
  "created_at" timestamp with time zone NOT NULL,
  "source_template_id" uuid
);

COMMENT ON TABLE public."store_policy_versions" IS 'Immutable effective policy snapshot. Initial 300m join, 50m arrival, 300s no-show review, max8, unlimited deferrals. HQ override administration later.';

COMMENT ON COLUMN public."store_policy_versions"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."policy_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."version_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."join_radius_metres" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."arrival_radius_metres" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."call_grace_seconds" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."max_party_size" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."max_deferrals" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_policy_versions"."source_template_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

CREATE TABLE public."operating_sessions" (
  "store_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "business_date" date NOT NULL,
  "layout_id" uuid NOT NULL,
  "policy_id" uuid NOT NULL,
  "owner_device_id" uuid NOT NULL,
  "authority_epoch" bigint NOT NULL,
  "next_queue_sequence" bigint NOT NULL,
  "next_ticket_number" integer NOT NULL,
  "last_event_sequence" bigint NOT NULL,
  "state_version" bigint NOT NULL,
  "opened_at" timestamp with time zone NOT NULL,
  "closed_at" timestamp with time zone,
  "sync_snapshot_revision" bigint NOT NULL DEFAULT 0
);

COMMENT ON TABLE public."operating_sessions" IS 'One active owner tablet and one pinned policy/layout. Queue sequence allocation and state changes lock this row. No forced takeover during unknown offline state; physical handover reconciles first.';

COMMENT ON COLUMN public."operating_sessions"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."business_date" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."layout_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."policy_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."owner_device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."authority_epoch" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."next_queue_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."next_ticket_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."last_event_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."state_version" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."opened_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."closed_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."operating_sessions"."sync_snapshot_revision" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

CREATE TABLE public."layout_versions" (
  "store_id" uuid NOT NULL,
  "layout_id" uuid NOT NULL,
  "version_number" integer NOT NULL,
  "layout_status" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."layout_versions" IS 'Published layouts are immutable. Operating session pins one layout; edits apply next session.';

COMMENT ON COLUMN public."layout_versions"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."layout_versions"."layout_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."layout_versions"."version_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."layout_versions"."layout_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."layout_versions"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

CREATE TABLE public."store_pin_verifiers" (
  "store_id" uuid NOT NULL,
  "pin_verifier" text NOT NULL,
  "rotated_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."store_pin_verifiers" IS 'Salted slow PIN verifier with deployment pepper; checked only on enrolled tablet with rate limit. PIN is additional unlock gate, never a standalone public store credential.';

COMMENT ON COLUMN public."store_pin_verifiers"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_pin_verifiers"."pin_verifier" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 4}';

COMMENT ON COLUMN public."store_pin_verifiers"."rotated_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."store_opening_periods" (
  "store_id" uuid NOT NULL,
  "period_id" uuid NOT NULL,
  "weekday" integer NOT NULL,
  "opens_minute" integer NOT NULL,
  "closes_minute" integer NOT NULL
);

COMMENT ON TABLE public."store_opening_periods" IS 'Store time_zone interprets weekly periods; split overnight periods across days. Reject overlap transactionally. Store operational status remains explicit; hours do not silently close active session.';

COMMENT ON COLUMN public."store_opening_periods"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."store_opening_periods"."period_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."store_opening_periods"."weekday" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."store_opening_periods"."opens_minute" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."store_opening_periods"."closes_minute" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."table_allocations" (
  "store_id" uuid NOT NULL,
  "allocation_id" uuid NOT NULL,
  "table_id" uuid NOT NULL,
  "call_id" uuid NOT NULL,
  "allocation_status" text NOT NULL,
  "held_at" timestamp with time zone NOT NULL,
  "seated_at" timestamp with time zone,
  "released_at" timestamp with time zone
);

COMMENT ON TABLE public."table_allocations" IS 'One unreleased allocation per table. Group/session inferred through call. Transactions validate same session layout, capacity and preference. Clearing releases allocation and completes seated group.';

COMMENT ON COLUMN public."table_allocations"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."table_allocations"."allocation_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."table_allocations"."table_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."table_allocations"."call_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."table_allocations"."allocation_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."table_allocations"."held_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."table_allocations"."seated_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."table_allocations"."released_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."layout_rows" (
  "store_id" uuid NOT NULL,
  "row_id" uuid NOT NULL,
  "layout_id" uuid NOT NULL,
  "row_number" integer NOT NULL,
  "row_label" text NOT NULL
);

COMMENT ON TABLE public."layout_rows" IS 'Table Layout Row';

COMMENT ON COLUMN public."layout_rows"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."layout_rows"."row_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."layout_rows"."layout_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."layout_rows"."row_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

COMMENT ON COLUMN public."layout_rows"."row_label" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "M", "confidentiality": "M", "encryption_level": 0, "integrity": "M", "pii_level": 0, "sensitivity_level": 2}';

CREATE TABLE public."ticket_access_grants" (
  "store_id" uuid NOT NULL,
  "access_id" uuid NOT NULL,
  "group_id" uuid NOT NULL,
  "token_hash" text NOT NULL,
  "access_scope" text NOT NULL,
  "created_at" timestamp with time zone NOT NULL,
  "expires_at" timestamp with time zone NOT NULL,
  "revoked_at" timestamp with time zone
);

COMMENT ON TABLE public."ticket_access_grants" IS 'Hash opaque browser capability; never store raw token. Owner may mutate before seating, watch is read-only. Revoke watch on seating/cancellation/no-show; owner grants can show terminal result until expiry.';

COMMENT ON COLUMN public."ticket_access_grants"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."ticket_access_grants"."access_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."ticket_access_grants"."group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."ticket_access_grants"."token_hash" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."ticket_access_grants"."access_scope" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."ticket_access_grants"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."ticket_access_grants"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."ticket_access_grants"."revoked_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."delivery_jobs" (
  "store_id" uuid NOT NULL,
  "job_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "event_id" uuid NOT NULL,
  "group_id" uuid NOT NULL,
  "call_id" uuid NOT NULL,
  "target_device_id" uuid,
  "channel" text NOT NULL,
  "lane_key" text NOT NULL,
  "event_sequence" bigint NOT NULL,
  "job_status" text NOT NULL,
  "attempt_count" integer NOT NULL,
  "next_attempt_at" timestamp with time zone NOT NULL,
  "expires_at" timestamp with time zone NOT NULL,
  "lease_token" uuid,
  "lease_until" timestamp with time zone,
  "accepted_at" timestamp with time zone,
  "delivered_at" timestamp with time zone,
  "terminal_reason" text,
  "created_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."delivery_jobs" IS 'Two jobs per called/recalled event: customer simulator route keyed by group, bell route snapshots registered device. No contact PII. Lane blocks later events until terminal. Acceptance is not delivery. Worker sends outside transaction using stable job_id as destination dedup key; late receipts retained without resurrecting obsolete calls.';

COMMENT ON COLUMN public."delivery_jobs"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."job_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."event_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."call_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."target_device_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."channel" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."lane_key" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."event_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."job_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."attempt_count" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."next_attempt_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."lease_token" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."delivery_jobs"."lease_until" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."accepted_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."delivered_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."terminal_reason" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."delivery_jobs"."created_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."queue_groups" (
  "store_id" uuid NOT NULL,
  "group_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "ticket_number" integer NOT NULL,
  "queue_sequence" bigint NOT NULL,
  "party_size" integer NOT NULL,
  "wants_window" boolean NOT NULL,
  "join_source" text NOT NULL,
  "group_status" text NOT NULL,
  "arrival_confirmed_at" timestamp with time zone,
  "joined_at" timestamp with time zone NOT NULL,
  "deferral_count" integer NOT NULL,
  "ended_at" timestamp with time zone
);

COMMENT ON TABLE public."queue_groups" IS 'Defer changes status to waiting, assigns new last sequence, increments count. Never delete cancellations/no-shows. Ticket display A-### is derived; digits expand after999.';

COMMENT ON COLUMN public."queue_groups"."store_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 0, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."group_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."session_id" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."ticket_number" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."queue_sequence" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."party_size" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."wants_window" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."join_source" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."group_status" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."arrival_confirmed_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."joined_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."deferral_count" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."queue_groups"."ended_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE TABLE public."api_rate_windows" (
  "scope_digest" text NOT NULL,
  "window_start" timestamp with time zone NOT NULL,
  "request_count" integer NOT NULL,
  "expires_at" timestamp with time zone NOT NULL
);

COMMENT ON TABLE public."api_rate_windows" IS 'Global fixed-minute buckets. HMAC trusted IP network scope or browser nonce, never raw IP; count invalid and valid exchange attempts. Serialized per scope; shared across API instances. Retain 2 minutes then purge. Proxy identity trust is required.';

COMMENT ON COLUMN public."api_rate_windows"."scope_digest" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 2, "sensitivity_level": 4}';

COMMENT ON COLUMN public."api_rate_windows"."window_start" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."api_rate_windows"."request_count" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

COMMENT ON COLUMN public."api_rate_windows"."expires_at" IS 'Beyond Entity security classification (metadata, not automatic enforcement): {"availability": "H", "confidentiality": "H", "encryption_level": 0, "integrity": "H", "pii_level": 1, "sensitivity_level": 3}';

CREATE INDEX "ix_admin_audit" ON public."administrative_audit_events" ("organization_id", "occurred_at");

ALTER TABLE public."administrative_audit_events" ADD CONSTRAINT "pk_administrative_audit_events" PRIMARY KEY ("admin_event_id");

ALTER TABLE public."operator_sessions" ADD CONSTRAINT "ck_operator_session_expiry" CHECK (expires_at > created_at);

ALTER TABLE public."operator_sessions" ADD CONSTRAINT "pk_operator_sessions" PRIMARY KEY ("operator_session_id");

ALTER TABLE public."operator_sessions" ADD CONSTRAINT "uq_operator_session_hash" UNIQUE ("token_hash");

ALTER TABLE public."delivery_receipts" ADD CONSTRAINT "ck_receipt_source" CHECK (source_kind IN ('notification_simulator','device_simulator'));

ALTER TABLE public."delivery_receipts" ADD CONSTRAINT "ck_receipt_status" CHECK (receipt_status IN ('delivered','failed'));

ALTER TABLE public."delivery_receipts" ADD CONSTRAINT "pk_delivery_receipts" PRIMARY KEY ("store_id", "receipt_id");

ALTER TABLE public."delivery_receipts" ADD CONSTRAINT "uq_delivery_receipt_event" UNIQUE ("source_kind", "source_event_digest");

ALTER TABLE public."delivery_attempts" ADD CONSTRAINT "ck_attempt_number" CHECK (attempt_number BETWEEN 1 AND 5);

ALTER TABLE public."delivery_attempts" ADD CONSTRAINT "ck_attempt_outcome" CHECK (outcome IN ('started','accepted','delivered','retryable_failure','permanent_failure','unknown'));

ALTER TABLE public."delivery_attempts" ADD CONSTRAINT "pk_delivery_attempts" PRIMARY KEY ("store_id", "attempt_id");

ALTER TABLE public."delivery_attempts" ADD CONSTRAINT "uq_delivery_attempt_lease" UNIQUE ("lease_token");

ALTER TABLE public."delivery_attempts" ADD CONSTRAINT "uq_delivery_attempt_number" UNIQUE ("store_id", "job_id", "attempt_number");

ALTER TABLE public."device_sync_commands" ADD CONSTRAINT "ck_sync_sequence" CHECK (device_sequence > 0 AND authority_epoch > 0 AND base_version >= 0 AND operation IN ('call','seat','clear') AND sync_status IN ('received','applied','conflict','rejected'));

ALTER TABLE public."device_sync_commands" ADD CONSTRAINT "pk_device_sync_commands" PRIMARY KEY ("store_id", "sync_command_id");

ALTER TABLE public."device_sync_commands" ADD CONSTRAINT "uq_sync_device_sequence" UNIQUE ("store_id", "device_id", "session_id", "authority_epoch", "device_sequence");

ALTER TABLE public."device_sync_cursors" ADD CONSTRAINT "ck_sync_cursor" CHECK (last_received_sequence >= last_resolved_sequence AND last_resolved_sequence >= 0);

ALTER TABLE public."device_sync_cursors" ADD CONSTRAINT "pk_device_sync_cursors" PRIMARY KEY ("store_id", "device_id", "session_id", "authority_epoch");

ALTER TABLE public."dining_tables" ADD CONSTRAINT "ck_table_capacity" CHECK (seat_count BETWEEN 1 AND 8 AND row_position > 0);

ALTER TABLE public."dining_tables" ADD CONSTRAINT "pk_dining_tables" PRIMARY KEY ("store_id", "table_id");

ALTER TABLE public."dining_tables" ADD CONSTRAINT "uq_row_table_number" UNIQUE ("store_id", "row_id", "table_number");

ALTER TABLE public."dining_tables" ADD CONSTRAINT "uq_row_table_position" UNIQUE ("store_id", "row_id", "row_position");

ALTER TABLE public."command_receipts" ADD CONSTRAINT "ck_command_completion" CHECK (authority_epoch > 0 AND ((command_status = 'processing' AND completed_at IS NULL AND http_status IS NULL) OR (command_status = 'succeeded' AND completed_at IS NOT NULL AND replay_until IS NOT NULL AND http_status BETWEEN 200 AND 299)));

ALTER TABLE public."command_receipts" ADD CONSTRAINT "ck_command_status" CHECK (command_status IN ('processing','succeeded'));

CREATE INDEX "ix_command_session" ON public."command_receipts" ("store_id", "session_id", "created_at");

ALTER TABLE public."command_receipts" ADD CONSTRAINT "pk_command_receipts" PRIMARY KEY ("store_id", "command_id");

ALTER TABLE public."command_receipts" ADD CONSTRAINT "uq_command_key" UNIQUE ("store_id", "actor_digest", "operation_name", "key_digest");

ALTER TABLE public."group_calls" ADD CONSTRAINT "ck_call_closed" CHECK ((call_status = 'active' AND closed_at IS NULL) OR (call_status <> 'active' AND closed_at IS NOT NULL AND closed_at >= called_at));

ALTER TABLE public."group_calls" ADD CONSTRAINT "ck_call_status" CHECK (call_status IN ('active','seated','deferred','cancelled','no_show'));

ALTER TABLE public."group_calls" ADD CONSTRAINT "ck_call_values" CHECK (call_number > 0 AND recall_count >= 0 AND review_due_at >= called_at);

ALTER TABLE public."group_calls" ADD CONSTRAINT "pk_group_calls" PRIMARY KEY ("store_id", "call_id");

ALTER TABLE public."group_calls" ADD CONSTRAINT "uq_group_call_number" UNIQUE ("store_id", "group_id", "call_number");

CREATE UNIQUE INDEX "uq_group_open_call" ON public."group_calls" ("store_id", "group_id") WHERE call_status = 'active';

ALTER TABLE public."hq_policy_templates" ADD CONSTRAINT "pk_hq_policy_templates" PRIMARY KEY ("organization_id", "template_id");

ALTER TABLE public."hq_policy_templates" ADD CONSTRAINT "uq_hq_policy_version" UNIQUE ("organization_id", "version_number");

ALTER TABLE public."device_health" ADD CONSTRAINT "ck_device_health" CHECK (heartbeat_sequence >= 0 AND connectivity_status IN ('online','stale') AND fault_code IN ('none','paper_out','jam','adapter_error'));

ALTER TABLE public."device_health" ADD CONSTRAINT "pk_device_health" PRIMARY KEY ("store_id", "device_id");

ALTER TABLE public."operator_store_grants" ADD CONSTRAINT "pk_operator_store_grants" PRIMARY KEY ("store_id", "account_id");

ALTER TABLE public."operator_accounts" ADD CONSTRAINT "ck_operator_role" CHECK (account_role IN ('head_office','manager'));

ALTER TABLE public."operator_accounts" ADD CONSTRAINT "pk_operator_accounts" PRIMARY KEY ("account_id");

ALTER TABLE public."operator_accounts" ADD CONSTRAINT "uq_operator_login" UNIQUE ("login_digest");

ALTER TABLE public."physical_table_facts" ADD CONSTRAINT "ck_physical_kind" CHECK (fact_kind IN ('seated','cleared'));

ALTER TABLE public."physical_table_facts" ADD CONSTRAINT "pk_physical_table_facts" PRIMARY KEY ("store_id", "fact_id");

ALTER TABLE public."physical_table_facts" ADD CONSTRAINT "uq_physical_command" UNIQUE ("store_id", "sync_command_id");

ALTER TABLE public."sync_conflicts" ADD CONSTRAINT "ck_conflict_state" CHECK (conflict_status IN ('open','resolved'));

ALTER TABLE public."sync_conflicts" ADD CONSTRAINT "pk_sync_conflicts" PRIMARY KEY ("store_id", "conflict_id");

ALTER TABLE public."sync_conflicts" ADD CONSTRAINT "uq_conflict_command" UNIQUE ("store_id", "sync_command_id");

ALTER TABLE public."command_secret_replays" ADD CONSTRAINT "ck_replay_window" CHECK (expires_at > created_at);

ALTER TABLE public."command_secret_replays" ADD CONSTRAINT "pk_command_secret_replays" PRIMARY KEY ("store_id", "command_id");

ALTER TABLE public."queue_events" ADD CONSTRAINT "ck_event_actor" CHECK (actor_kind IN ('customer','store_device','manager','system'));

ALTER TABLE public."queue_events" ADD CONSTRAINT "ck_event_sequence" CHECK (event_sequence > 0);

ALTER TABLE public."queue_events" ADD CONSTRAINT "ck_event_type" CHECK (event_type IN ('joined','arrival_confirmed','called','recalled','seated','cleared','deferred','cancelled','no_show','session_opened','session_closed','authority_changed','conflict_resolved'));

CREATE INDEX "ix_event_history" ON public."queue_events" ("store_id", "recorded_at");

ALTER TABLE public."queue_events" ADD CONSTRAINT "pk_queue_events" PRIMARY KEY ("store_id", "event_id");

ALTER TABLE public."queue_events" ADD CONSTRAINT "uq_session_event_sequence" UNIQUE ("store_id", "session_id", "event_sequence");

ALTER TABLE public."partner_credentials" ADD CONSTRAINT "pk_partner_credentials" PRIMARY KEY ("partner_id");

ALTER TABLE public."partner_credentials" ADD CONSTRAINT "uq_partner_token_hash" UNIQUE ("token_hash");

ALTER TABLE public."device_credentials" ADD CONSTRAINT "pk_device_credentials" PRIMARY KEY ("store_id", "credential_id");

ALTER TABLE public."device_credentials" ADD CONSTRAINT "uq_device_credential_hash" UNIQUE ("token_hash");

ALTER TABLE public."device_fault_events" ADD CONSTRAINT "pk_device_fault_events" PRIMARY KEY ("store_id", "fault_event_id");

ALTER TABLE public."device_fault_events" ADD CONSTRAINT "uq_fault_heartbeat" UNIQUE ("store_id", "device_id", "heartbeat_sequence");

ALTER TABLE public."organizations" ADD CONSTRAINT "pk_organizations" PRIMARY KEY ("organization_id");

ALTER TABLE public."stores" ADD CONSTRAINT "ck_store_coordinates" CHECK (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180);

ALTER TABLE public."stores" ADD CONSTRAINT "ck_store_status" CHECK (store_status IN ('open','waitlist_closed','closed'));

ALTER TABLE public."stores" ADD CONSTRAINT "pk_stores" PRIMARY KEY ("store_id");

ALTER TABLE public."stores" ADD CONSTRAINT "uq_store_code" UNIQUE ("store_code");

ALTER TABLE public."watch_codes" ADD CONSTRAINT "ck_watch_expiry" CHECK (expires_at > issued_at);

ALTER TABLE public."watch_codes" ADD CONSTRAINT "pk_watch_codes" PRIMARY KEY ("store_id", "watch_code_id");

CREATE UNIQUE INDEX "uq_group_watch_code" ON public."watch_codes" ("store_id", "group_id") WHERE revoked_at IS NULL;

CREATE UNIQUE INDEX "uq_live_watch_digest" ON public."watch_codes" ("code_digest") WHERE revoked_at IS NULL;

ALTER TABLE public."arrival_challenges" ADD CONSTRAINT "ck_arrival_window" CHECK (expires_at > valid_from);

ALTER TABLE public."arrival_challenges" ADD CONSTRAINT "pk_arrival_challenges" PRIMARY KEY ("store_id", "challenge_id");

ALTER TABLE public."arrival_challenges" ADD CONSTRAINT "uq_session_arrival_digest" UNIQUE ("store_id", "session_id", "code_digest");

ALTER TABLE public."store_devices" ADD CONSTRAINT "ck_device_kind" CHECK (device_kind IN ('tablet','kiosk','printer','call_bell'));

ALTER TABLE public."store_devices" ADD CONSTRAINT "pk_store_devices" PRIMARY KEY ("store_id", "device_id");

ALTER TABLE public."store_join_qr_versions" ADD CONSTRAINT "pk_store_join_qr_versions" PRIMARY KEY ("store_id", "qr_id");

ALTER TABLE public."store_policy_versions" ADD CONSTRAINT "ck_policy_ranges" CHECK (version_number > 0 AND join_radius_metres > 0 AND arrival_radius_metres > 0 AND arrival_radius_metres <= join_radius_metres AND call_grace_seconds > 0 AND max_party_size BETWEEN 1 AND 8 AND (max_deferrals IS NULL OR max_deferrals >= 0));

ALTER TABLE public."store_policy_versions" ADD CONSTRAINT "pk_store_policy_versions" PRIMARY KEY ("store_id", "policy_id");

ALTER TABLE public."store_policy_versions" ADD CONSTRAINT "uq_store_policy_version" UNIQUE ("store_id", "version_number");

ALTER TABLE public."operating_sessions" ADD CONSTRAINT "ck_session_counters" CHECK (authority_epoch > 0 AND next_queue_sequence > 0 AND next_ticket_number > 0 AND last_event_sequence >= 0 AND state_version >= 0);

ALTER TABLE public."operating_sessions" ADD CONSTRAINT "ck_session_time" CHECK (closed_at IS NULL OR closed_at >= opened_at);

ALTER TABLE public."operating_sessions" ADD CONSTRAINT "pk_operating_sessions" PRIMARY KEY ("store_id", "session_id");

CREATE UNIQUE INDEX "uq_open_store_session" ON public."operating_sessions" ("store_id") WHERE closed_at IS NULL;

ALTER TABLE public."layout_versions" ADD CONSTRAINT "ck_layout_status" CHECK (layout_status IN ('draft','published','retired'));

ALTER TABLE public."layout_versions" ADD CONSTRAINT "pk_layout_versions" PRIMARY KEY ("store_id", "layout_id");

ALTER TABLE public."layout_versions" ADD CONSTRAINT "uq_layout_version" UNIQUE ("store_id", "version_number");

ALTER TABLE public."store_pin_verifiers" ADD CONSTRAINT "pk_store_pin_verifiers" PRIMARY KEY ("store_id");

ALTER TABLE public."store_opening_periods" ADD CONSTRAINT "ck_opening_period" CHECK (weekday BETWEEN 0 AND 6 AND opens_minute >= 0 AND closes_minute <= 1440 AND opens_minute < closes_minute);

ALTER TABLE public."store_opening_periods" ADD CONSTRAINT "pk_store_opening_periods" PRIMARY KEY ("store_id", "period_id");

ALTER TABLE public."table_allocations" ADD CONSTRAINT "ck_allocation_status" CHECK (allocation_status IN ('held','occupied','released'));

ALTER TABLE public."table_allocations" ADD CONSTRAINT "ck_allocation_times" CHECK (((allocation_status = 'held' AND seated_at IS NULL AND released_at IS NULL) OR (allocation_status = 'occupied' AND seated_at IS NOT NULL AND released_at IS NULL) OR (allocation_status = 'released' AND released_at IS NOT NULL)) AND (seated_at IS NULL OR seated_at >= held_at) AND (released_at IS NULL OR released_at >= held_at) AND (seated_at IS NULL OR released_at IS NULL OR released_at >= seated_at));

ALTER TABLE public."table_allocations" ADD CONSTRAINT "pk_table_allocations" PRIMARY KEY ("store_id", "allocation_id");

ALTER TABLE public."table_allocations" ADD CONSTRAINT "uq_call_allocation" UNIQUE ("store_id", "call_id");

CREATE UNIQUE INDEX "uq_table_live_allocation" ON public."table_allocations" ("store_id", "table_id") WHERE released_at IS NULL;

ALTER TABLE public."layout_rows" ADD CONSTRAINT "ck_row_number" CHECK (row_number > 0);

ALTER TABLE public."layout_rows" ADD CONSTRAINT "pk_layout_rows" PRIMARY KEY ("store_id", "row_id");

ALTER TABLE public."layout_rows" ADD CONSTRAINT "uq_layout_row" UNIQUE ("store_id", "layout_id", "row_number");

ALTER TABLE public."ticket_access_grants" ADD CONSTRAINT "ck_access_time" CHECK (expires_at > created_at);

ALTER TABLE public."ticket_access_grants" ADD CONSTRAINT "ck_ticket_scope" CHECK (access_scope IN ('owner','watch'));

ALTER TABLE public."ticket_access_grants" ADD CONSTRAINT "pk_ticket_access_grants" PRIMARY KEY ("store_id", "access_id");

ALTER TABLE public."ticket_access_grants" ADD CONSTRAINT "uq_ticket_token_hash" UNIQUE ("token_hash");

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "ck_delivery_channel" CHECK (channel IN ('customer_notification','call_bell'));

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "ck_delivery_lease" CHECK ((job_status = 'leased' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) OR (job_status <> 'leased' AND lease_token IS NULL AND lease_until IS NULL));

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "ck_delivery_status" CHECK (job_status IN ('queued','leased','retry_wait','accepted','delivered','failed','expired','obsolete','uncertain'));

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "ck_delivery_values" CHECK (event_sequence > 0 AND attempt_count BETWEEN 0 AND 5 AND expires_at > created_at);

CREATE INDEX "ix_delivery_due" ON public."delivery_jobs" ("job_status", "next_attempt_at");

CREATE INDEX "ix_delivery_lane" ON public."delivery_jobs" ("store_id", "lane_key", "event_sequence");

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "pk_delivery_jobs" PRIMARY KEY ("store_id", "job_id");

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "uq_delivery_event_channel" UNIQUE ("store_id", "event_id", "channel");

ALTER TABLE public."queue_groups" ADD CONSTRAINT "ck_group_source" CHECK (join_source IN ('phone','kiosk','staff'));

ALTER TABLE public."queue_groups" ADD CONSTRAINT "ck_group_status" CHECK (group_status IN ('waiting','called','seated','completed','cancelled','no_show'));

ALTER TABLE public."queue_groups" ADD CONSTRAINT "ck_group_values" CHECK (party_size BETWEEN 1 AND 8 AND ticket_number > 0 AND queue_sequence > 0 AND deferral_count >= 0);

CREATE INDEX "ix_waiting_queue" ON public."queue_groups" ("store_id", "session_id", "group_status", "queue_sequence");

ALTER TABLE public."queue_groups" ADD CONSTRAINT "pk_queue_groups" PRIMARY KEY ("store_id", "group_id");

ALTER TABLE public."queue_groups" ADD CONSTRAINT "uq_session_queue_sequence" UNIQUE ("store_id", "session_id", "queue_sequence");

ALTER TABLE public."queue_groups" ADD CONSTRAINT "uq_session_ticket" UNIQUE ("store_id", "session_id", "ticket_number");

ALTER TABLE public."api_rate_windows" ADD CONSTRAINT "ck_rate_count" CHECK (request_count > 0);

CREATE INDEX "ix_rate_expiry" ON public."api_rate_windows" ("expires_at");

ALTER TABLE public."api_rate_windows" ADD CONSTRAINT "pk_api_rate_windows" PRIMARY KEY ("scope_digest", "window_start");

ALTER TABLE public."administrative_audit_events" ADD CONSTRAINT "fk_administrative_audit_events_actor_account_id" FOREIGN KEY ("actor_account_id") REFERENCES public."operator_accounts" ("account_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."administrative_audit_events" ADD CONSTRAINT "fk_administrative_audit_events_organization_id" FOREIGN KEY ("organization_id") REFERENCES public."organizations" ("organization_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."administrative_audit_events" ADD CONSTRAINT "fk_administrative_audit_events_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."operator_sessions" ADD CONSTRAINT "fk_operator_sessions_account_id" FOREIGN KEY ("account_id") REFERENCES public."operator_accounts" ("account_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_receipts" ADD CONSTRAINT "fk_delivery_receipts_attempt_id" FOREIGN KEY ("attempt_id", "store_id") REFERENCES public."delivery_attempts" ("attempt_id", "store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_receipts" ADD CONSTRAINT "fk_delivery_receipts_job_id" FOREIGN KEY ("store_id", "job_id") REFERENCES public."delivery_jobs" ("store_id", "job_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_receipts" ADD CONSTRAINT "fk_delivery_receipts_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_attempts" ADD CONSTRAINT "fk_delivery_attempts_job_id" FOREIGN KEY ("store_id", "job_id") REFERENCES public."delivery_jobs" ("store_id", "job_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_attempts" ADD CONSTRAINT "fk_delivery_attempts_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."device_sync_commands" ADD CONSTRAINT "fk_device_sync_commands_device_id" FOREIGN KEY ("store_id", "device_id") REFERENCES public."store_devices" ("store_id", "device_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."device_sync_commands" ADD CONSTRAINT "fk_device_sync_commands_layout_id" FOREIGN KEY ("store_id", "layout_id") REFERENCES public."layout_versions" ("store_id", "layout_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."device_sync_commands" ADD CONSTRAINT "fk_device_sync_commands_session_id" FOREIGN KEY ("store_id", "session_id") REFERENCES public."operating_sessions" ("store_id", "session_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."device_sync_cursors" ADD CONSTRAINT "fk_device_sync_cursors_device_id" FOREIGN KEY ("store_id", "device_id") REFERENCES public."store_devices" ("store_id", "device_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."device_sync_cursors" ADD CONSTRAINT "fk_device_sync_cursors_session_id" FOREIGN KEY ("store_id", "session_id") REFERENCES public."operating_sessions" ("store_id", "session_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."dining_tables" ADD CONSTRAINT "fk_dining_tables_row_id" FOREIGN KEY ("row_id", "store_id") REFERENCES public."layout_rows" ("row_id", "store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."dining_tables" ADD CONSTRAINT "fk_dining_tables_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."command_receipts" ADD CONSTRAINT "fk_command_receipts_session_id" FOREIGN KEY ("store_id", "session_id") REFERENCES public."operating_sessions" ("store_id", "session_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."command_receipts" ADD CONSTRAINT "fk_command_receipts_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."group_calls" ADD CONSTRAINT "fk_group_calls_group_id" FOREIGN KEY ("store_id", "group_id") REFERENCES public."queue_groups" ("store_id", "group_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."group_calls" ADD CONSTRAINT "fk_group_calls_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."hq_policy_templates" ADD CONSTRAINT "fk_hq_policy_templates_organization_id" FOREIGN KEY ("organization_id") REFERENCES public."organizations" ("organization_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."device_health" ADD CONSTRAINT "fk_device_health_device_id" FOREIGN KEY ("store_id", "device_id") REFERENCES public."store_devices" ("store_id", "device_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."operator_store_grants" ADD CONSTRAINT "fk_operator_store_grants_account_id" FOREIGN KEY ("account_id") REFERENCES public."operator_accounts" ("account_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."operator_store_grants" ADD CONSTRAINT "fk_operator_store_grants_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."operator_accounts" ADD CONSTRAINT "fk_operator_accounts_organization_id" FOREIGN KEY ("organization_id") REFERENCES public."organizations" ("organization_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."physical_table_facts" ADD CONSTRAINT "fk_physical_table_facts_group_id" FOREIGN KEY ("store_id", "group_id") REFERENCES public."queue_groups" ("store_id", "group_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."physical_table_facts" ADD CONSTRAINT "fk_physical_table_facts_sync_command_id" FOREIGN KEY ("sync_command_id", "store_id") REFERENCES public."device_sync_commands" ("sync_command_id", "store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."physical_table_facts" ADD CONSTRAINT "fk_physical_table_facts_table_id" FOREIGN KEY ("store_id", "table_id") REFERENCES public."dining_tables" ("store_id", "table_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."sync_conflicts" ADD CONSTRAINT "fk_sync_conflicts_sync_command_id" FOREIGN KEY ("sync_command_id", "store_id") REFERENCES public."device_sync_commands" ("sync_command_id", "store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."command_secret_replays" ADD CONSTRAINT "fk_command_secret_replays_command_id" FOREIGN KEY ("store_id", "command_id") REFERENCES public."command_receipts" ("store_id", "command_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."command_secret_replays" ADD CONSTRAINT "fk_command_secret_replays_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."queue_events" ADD CONSTRAINT "fk_queue_events_actor_device_id" FOREIGN KEY ("store_id", "actor_device_id") REFERENCES public."store_devices" ("store_id", "device_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."queue_events" ADD CONSTRAINT "fk_queue_events_allocation_id" FOREIGN KEY ("allocation_id", "store_id") REFERENCES public."table_allocations" ("allocation_id", "store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."queue_events" ADD CONSTRAINT "fk_queue_events_call_id" FOREIGN KEY ("call_id", "store_id") REFERENCES public."group_calls" ("call_id", "store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."queue_events" ADD CONSTRAINT "fk_queue_events_group_id" FOREIGN KEY ("store_id", "group_id") REFERENCES public."queue_groups" ("store_id", "group_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."queue_events" ADD CONSTRAINT "fk_queue_events_session_id" FOREIGN KEY ("store_id", "session_id") REFERENCES public."operating_sessions" ("store_id", "session_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."queue_events" ADD CONSTRAINT "fk_queue_events_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."partner_credentials" ADD CONSTRAINT "fk_partner_credentials_organization_id" FOREIGN KEY ("organization_id") REFERENCES public."organizations" ("organization_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."device_credentials" ADD CONSTRAINT "fk_device_credentials_device_id" FOREIGN KEY ("store_id", "device_id") REFERENCES public."store_devices" ("store_id", "device_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."device_fault_events" ADD CONSTRAINT "fk_device_fault_events_device_id" FOREIGN KEY ("store_id", "device_id") REFERENCES public."store_devices" ("store_id", "device_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."stores" ADD CONSTRAINT "fk_stores_organization_id" FOREIGN KEY ("organization_id") REFERENCES public."organizations" ("organization_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."watch_codes" ADD CONSTRAINT "fk_watch_codes_group_id" FOREIGN KEY ("store_id", "group_id") REFERENCES public."queue_groups" ("store_id", "group_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."watch_codes" ADD CONSTRAINT "fk_watch_codes_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."arrival_challenges" ADD CONSTRAINT "fk_arrival_challenges_session_id" FOREIGN KEY ("store_id", "session_id") REFERENCES public."operating_sessions" ("store_id", "session_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."arrival_challenges" ADD CONSTRAINT "fk_arrival_challenges_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."store_devices" ADD CONSTRAINT "fk_store_devices_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."store_join_qr_versions" ADD CONSTRAINT "fk_store_join_qr_versions_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."store_policy_versions" ADD CONSTRAINT "fk_store_policy_versions_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."operating_sessions" ADD CONSTRAINT "fk_operating_sessions_layout_id" FOREIGN KEY ("store_id", "layout_id") REFERENCES public."layout_versions" ("store_id", "layout_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."operating_sessions" ADD CONSTRAINT "fk_operating_sessions_owner_device_id" FOREIGN KEY ("store_id", "owner_device_id") REFERENCES public."store_devices" ("store_id", "device_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."operating_sessions" ADD CONSTRAINT "fk_operating_sessions_policy_id" FOREIGN KEY ("store_id", "policy_id") REFERENCES public."store_policy_versions" ("store_id", "policy_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."operating_sessions" ADD CONSTRAINT "fk_operating_sessions_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."layout_versions" ADD CONSTRAINT "fk_layout_versions_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."store_pin_verifiers" ADD CONSTRAINT "fk_store_pin_verifiers_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."store_opening_periods" ADD CONSTRAINT "fk_store_opening_periods_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."table_allocations" ADD CONSTRAINT "fk_table_allocations_call_id" FOREIGN KEY ("call_id", "store_id") REFERENCES public."group_calls" ("call_id", "store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."table_allocations" ADD CONSTRAINT "fk_table_allocations_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."table_allocations" ADD CONSTRAINT "fk_table_allocations_table_id" FOREIGN KEY ("store_id", "table_id") REFERENCES public."dining_tables" ("store_id", "table_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."layout_rows" ADD CONSTRAINT "fk_layout_rows_layout_id" FOREIGN KEY ("store_id", "layout_id") REFERENCES public."layout_versions" ("store_id", "layout_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."layout_rows" ADD CONSTRAINT "fk_layout_rows_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."ticket_access_grants" ADD CONSTRAINT "fk_ticket_access_grants_group_id" FOREIGN KEY ("store_id", "group_id") REFERENCES public."queue_groups" ("store_id", "group_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."ticket_access_grants" ADD CONSTRAINT "fk_ticket_access_grants_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "fk_delivery_jobs_call_id" FOREIGN KEY ("call_id", "store_id") REFERENCES public."group_calls" ("call_id", "store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "fk_delivery_jobs_event_id" FOREIGN KEY ("store_id", "event_id") REFERENCES public."queue_events" ("store_id", "event_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "fk_delivery_jobs_group_id" FOREIGN KEY ("store_id", "group_id") REFERENCES public."queue_groups" ("store_id", "group_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "fk_delivery_jobs_session_id" FOREIGN KEY ("store_id", "session_id") REFERENCES public."operating_sessions" ("store_id", "session_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "fk_delivery_jobs_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."delivery_jobs" ADD CONSTRAINT "fk_delivery_jobs_target_device_id" FOREIGN KEY ("store_id", "target_device_id") REFERENCES public."store_devices" ("store_id", "device_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."queue_groups" ADD CONSTRAINT "fk_queue_groups_session_id" FOREIGN KEY ("store_id", "session_id") REFERENCES public."operating_sessions" ("store_id", "session_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE public."queue_groups" ADD CONSTRAINT "fk_queue_groups_store_id" FOREIGN KEY ("store_id") REFERENCES public."stores" ("store_id") ON UPDATE NO ACTION ON DELETE NO ACTION;

-- Stage 5 requires checking the FINAL row at commit, not the deferred event's old NEW image.
CREATE FUNCTION public.enforce_completed_command_receipt() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.command_receipts AS c
             WHERE c.store_id = NEW.store_id AND c.command_id = NEW.command_id
               AND c.command_status = 'processing') THEN
    RAISE EXCEPTION 'command_receipts cannot commit processing status'
      USING ERRCODE = '23514', CONSTRAINT = 'command_receipt_completed_at_commit';
  END IF;
  RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER command_receipt_completed_at_commit
AFTER INSERT OR UPDATE ON public.command_receipts
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION public.enforce_completed_command_receipt();

COMMIT;
