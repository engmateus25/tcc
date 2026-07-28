from datetime import datetime, timezone

from app.services import alerts_store
from app.services.alerts_store import build_alert_id, list_alerts, normalize_alert


def test_alert_id_is_stable_for_event_and_type():
    first = build_alert_id("sensores/doc-1", "unexpected_low_repeat")
    second = build_alert_id("sensores/doc-1", "unexpected_low_repeat")

    assert first == second
    assert first != build_alert_id("sensores/doc-1", "duplicate_event")


def test_normalize_alert_applies_defaults():
    sensor_timestamp = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)

    alert = normalize_alert(
        {
            "event_id": "sensores/doc-1",
            "type": "unexpected_low_repeat",
            "title": "Sensor baixo repetiu",
            "message": "Evento suspeito.",
            "sensor_timestamp": sensor_timestamp,
        }
    )

    assert alert["id"] == build_alert_id("sensores/doc-1", "unexpected_low_repeat")
    assert alert["severity"] == "warning"
    assert alert["status"] == "open"
    assert alert["acknowledged"] is False
    assert alert["sensor_timestamp"] == sensor_timestamp


def test_list_alerts_filters_status_and_severity_after_period_query(monkeypatch):
    start = datetime(2026, 7, 27, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 7, 28, 0, 0, tzinfo=timezone.utc)
    query = FakeAlertQuery(
        [
            FakeAlertDoc("ack", {"status": "acknowledged", "severity": "warning"}),
            FakeAlertDoc("info", {"status": "open", "severity": "info"}),
            FakeAlertDoc("warning", {"status": "open", "severity": "warning"}),
        ]
    )

    monkeypatch.setattr(alerts_store, "_init_firebase_admin_once", lambda: None)
    monkeypatch.setattr(alerts_store, "_get_period_range", lambda period: (start, end))
    monkeypatch.setattr(alerts_store, "firestore_operation_timeout_seconds", lambda: 1)
    monkeypatch.setattr(alerts_store.firestore, "client", lambda: FakeAlertDb(query))

    alerts = list_alerts(period="7d", status="open", severity="warning", limit=1)

    assert alerts == [{"id": "warning", "status": "open", "severity": "warning"}]
    assert query.where_count == 2
    assert query.limit_value == 5


class FakeAlertDoc:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self.data = data

    def to_dict(self):
        return dict(self.data)


class FakeAlertQuery:
    def __init__(self, docs):
        self.docs = docs
        self.where_count = 0
        self.limit_value = None

    def where(self, *args, **kwargs):
        self.where_count += 1
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def stream(self, *args, **kwargs):
        return iter(self.docs)


class FakeAlertDb:
    def __init__(self, query):
        self.query = query

    def collection(self, name):
        return self.query
