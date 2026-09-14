"""Attribute-level mappings of normalize_customers and pseudonymize_customers."""
from pyspark.sql import functions as F, Window
from .source import COLUMNS

RAW_SCHEMA = ', '.join(f'{c} STRING' for c in (*COLUMNS, 'source_file', 'batch_id')) + ', ingested_at TIMESTAMP'


class QualityError(RuntimeError):
    pass


def transform(raw, identity_pepper, email_pepper, key_version):
    if not all(isinstance(x, str) and x.strip() for x in (identity_pepper, email_pepper, key_version)):
        raise ValueError('Nonempty secret bindings and key version required')
    parsed = (raw.withColumn('_id', F.expr('try_cast(customer_id as bigint)'))
              .withColumn('_updated', F.expr('try_cast(updated_at as timestamp)'))
              .withColumn('_created', F.expr('try_cast(created_at as timestamp)'))
              .withColumn('_deleted', F.expr('try_cast(is_deleted as boolean)')))
    # Canonical source IDs ensure raw and typed partition grains are identical.
    unorderable = F.col('_id').isNull() | F.col('_updated').isNull() | (F.col('customer_id') != F.col('_id').cast('string'))
    invalid = (unorderable | F.col('_deleted').isNull() |
               ((F.col('_deleted') == F.lit(False)) &
                (F.col('email').isNull() | ~F.col('email').like('%@%') | F.col('_created').isNull())))
    parsed = parsed.withColumn('_invalid', invalid)
    rejects = parsed.filter('_invalid').select(
        F.sha2(F.concat(F.coalesce('customer_id', F.lit('null')), F.lit(':'), 'batch_id', F.lit(':'), 'source_file'), 256).alias('reject_id'),
        F.lit('raw_customers').alias('source_table'), F.col('customer_id').alias('source_record_id'),
        'batch_id', F.lit('INVALID_CUSTOMER').alias('reason_code'), 'source_file', F.current_timestamp().alias('detected_at'))
    # Ranking ties with distinct payloads are a contract violation, not a random winner.
    distinct = parsed.dropDuplicates(list(raw.columns))
    tie_keys = ['customer_id', '_updated', 'ingested_at', 'batch_id']
    ties = distinct.groupBy(*tie_keys).count().filter('count > 1').limit(1).count()
    w = Window.partitionBy('customer_id').orderBy(F.col('_updated').desc(), F.col('ingested_at').desc(), F.col('batch_id').desc())
    latest = distinct.withColumn('_rank', F.row_number().over(w)).filter('_rank = 1')
    blocking = bool(ties or parsed.filter(unorderable).limit(1).count() or latest.filter('_invalid').limit(1).count())
    live = latest.filter(~F.col('_invalid') & (F.col('_deleted') == F.lit(False)))
    normalized = live.select(
        F.col('_id').alias('customer_id'), F.trim('full_name').alias('full_name'),
        F.lower(F.trim('email')).alias('email_norm'), F.regexp_replace('phone', '[^0-9]', '').alias('phone_norm'),
        F.trim('address').alias('address'), F.upper(F.trim('country_code')).alias('country_code'),
        F.coalesce(F.expr('try_cast(marketing_consent as boolean)'), F.lit(False)).alias('marketing_consent'),
        F.col('_created').alias('created_at'), F.col('_updated').alias('updated_at'))
    # Closures keep secret literals out of Catalyst plans / Spark SQL UI.
    def hash_with(pepper):
        def digest(value):
            import hashlib
            return None if value is None else hashlib.sha256((pepper + ':' + str(value)).encode()).hexdigest()
        return F.udf(digest, 'string')
    masked = (normalized.withColumn('customer_key', hash_with(identity_pepper)('customer_id'))
              .withColumn('email_hash', hash_with(email_pepper)('email_norm')))
    identity = masked.select('customer_id', 'customer_key', F.lit(key_version).alias('key_version'), 'updated_at')
    silver = masked.select('customer_key', 'email_hash', 'country_code', 'marketing_consent', 'created_at', 'updated_at')
    return normalized, identity, silver, rejects, blocking
