"""UTC scheduled-time decisions with catch-up after delayed or missed runs."""
from datetime import timedelta,datetime,timezone
from .source import instant


def full_baseline_due(scheduled_at,baseline_at):
    if baseline_at is None:return True
    due,baseline=instant(scheduled_at),instant(baseline_at)
    return (due.date()>baseline.date() and (due.hour>0 or due.minute>=30)) or due-baseline>=timedelta(hours=48)


def products_due(scheduled_at,last_products_at):
    due=instant(scheduled_at)
    return last_products_at is None or 30<=due.minute<45 or due-instant(last_products_at)>=timedelta(hours=1)


def job_timestamp(value):
    """Databricks job time references are UTC, even if rendered without an offset."""
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    return parsed.replace(tzinfo=timezone.utc).isoformat() if parsed.tzinfo is None else parsed.astimezone(timezone.utc).isoformat()
