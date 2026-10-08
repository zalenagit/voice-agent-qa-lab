"""Classical QA for the integration behind the agent: the scheduling / EHR API."""
import pytest

from agent.scheduling import IntegrationError, SchedulingAPI


def status_of(fn, *args):
    with pytest.raises(IntegrationError) as e:
        fn(*args)
    return e.value.status


def test_book_success_returns_new_appointment():
    api = SchedulingAPI()
    appt = api.book("P003", "Dr. Okafor", "2026-10-14", "15:00")
    assert appt["id"].startswith("A") and appt["provider"] == "Dr. Okafor"
    assert any(a["id"] == appt["id"] for a in api.find("P003"))


@pytest.mark.parametrize("args, status", [
    (("P003", "Dr. Patel", "2026-10-20", "09:30"), 409),        # slot already taken
    (("P003", "Dr. Who", "2026-10-20", "10:00"), 400),          # unknown provider
    (("P003", "Dr. Patel", "2026-10-01", "10:00"), 400),        # in the past
    (("P003", "Dr. Patel", "2026-10-20", "3:00 PM"), 400),      # wrong time format
    (("P003", "Dr. Patel", "Oct 20", "10:00"), 400),            # wrong date format
], ids=["conflict", "unknown-provider", "past-date", "bad-time-format", "bad-date-format"])
def test_book_rejects_invalid_requests(args, status):
    assert status_of(SchedulingAPI().book, *args) == status


def test_cannot_cancel_another_patients_appointment():
    assert status_of(SchedulingAPI().cancel, "A100", "P002") == 404


def test_reschedule_into_taken_slot_is_rejected():
    api = SchedulingAPI()
    api.book("P003", "Dr. Patel", "2026-10-27", "14:00")
    assert status_of(api.reschedule, "A100", "P001", "2026-10-27", "14:00") == 409


@pytest.mark.parametrize("fault, status", [("ehr_500", 500), ("ehr_timeout", 504)])
def test_injected_faults_surface_as_http_errors(fault, status):
    assert status_of(SchedulingAPI([fault]).find, "P001") == status


@pytest.mark.parametrize("name, dob, expected", [
    ("Jordan Lee", "1985-04-12", "P001"),
    ("jordan lee", "1985-04-12", "P001"),
    ("Jordan Lee", "1985-04-13", None),
    ("Maria Santos", None, None),
])
def test_identity_requires_name_and_date_of_birth(name, dob, expected):
    assert SchedulingAPI().verify_identity(name, dob) == expected
