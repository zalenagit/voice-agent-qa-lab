"""In-memory scheduling / EHR integration the agent calls. Supports fault injection."""
import copy
import itertools
import re

from agent.data import PATIENTS, PROVIDERS, SEED_APPOINTMENTS


class IntegrationError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class SchedulingAPI:
    def __init__(self, faults=()):
        self.appointments = copy.deepcopy(SEED_APPOINTMENTS)
        self.faults = set(faults)
        self._ids = itertools.count(200)

    def _check_faults(self):
        if "ehr_500" in self.faults:
            raise IntegrationError(500, "Scheduling API returned 500 Internal Server Error")
        if "ehr_timeout" in self.faults:
            raise IntegrationError(504, "Scheduling API timed out after 8000 ms")

    def verify_identity(self, name, dob):
        """Return patient_id when name AND date of birth match, else None."""
        for pid, p in PATIENTS.items():
            if p["name"].lower() == (name or "").lower() and p["dob"] == dob:
                return pid
        return None

    def find(self, patient_id):
        self._check_faults()
        return [{"id": aid, **a} for aid, a in self.appointments.items() if a["patient_id"] == patient_id]

    def book(self, patient_id, provider, date, time):
        self._check_faults()
        if provider not in PROVIDERS:
            raise IntegrationError(400, f"Unknown provider {provider}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date)) or not re.fullmatch(r"\d{2}:\d{2}", str(time)):
            raise IntegrationError(400, f"Invalid date/time format: {date} {time}")
        if date < "2026-10-08":
            raise IntegrationError(400, "Cannot book in the past")
        for a in self.appointments.values():
            if a["provider"] == provider and a["date"] == date and a["time"] == time:
                raise IntegrationError(409, "Slot already booked")
        aid = f"A{next(self._ids)}"
        self.appointments[aid] = {"patient_id": patient_id, "provider": provider, "date": date, "time": time}
        return {"id": aid, **self.appointments[aid]}

    def cancel(self, appointment_id, patient_id):
        self._check_faults()
        appt = self.appointments.get(appointment_id)
        if not appt or appt["patient_id"] != patient_id:
            raise IntegrationError(404, "Appointment not found")
        del self.appointments[appointment_id]
        return {"id": appointment_id, "status": "cancelled"}

    def reschedule(self, appointment_id, patient_id, date, time):
        self._check_faults()
        appt = self.appointments.get(appointment_id)
        if not appt or appt["patient_id"] != patient_id:
            raise IntegrationError(404, "Appointment not found")
        if not re.fullmatch(r"\d{2}:\d{2}", str(time)):
            raise IntegrationError(400, f"Invalid time format: {time}")
        for aid, a in self.appointments.items():
            if aid != appointment_id and a["provider"] == appt["provider"] and a["date"] == date and a["time"] == time:
                raise IntegrationError(409, "Slot already booked")
        appt.update(date=date, time=time)
        return {"id": appointment_id, **appt}
