"""
CareFlow - EHR Event Log Simulator
------------------------------------
Generates a synthetic hospital Emergency Room event log.

Each "case" = one patient's visit.
Each case produces a sequence of (Case_ID, Activity_Name, Timestamp) rows.

We deliberately inject a specific bottleneck pattern:
  - ~40% of patients who get an X-Ray are sent BACK to Triage
    (simulating a missing-paperwork issue), which adds delay.

Output: ehr_event_log.csv with columns: Case_ID, Activity_Name, Timestamp
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)  # reproducible results

NUM_PATIENTS = 1000
START_TIME = datetime(2026, 8, 1, 6, 0, 0)  # simulation starts 6:00 AM

# Probability that an X-Ray patient gets bounced back to Triage
# due to the "missing paperwork" bottleneck
XRAY_BOUNCEBACK_PROB = 0.40

# Typical activity durations in minutes (min, max) - used to advance the clock
DURATIONS = {
    "Registration": (2, 8),
    "Triage": (5, 15),
    "Blood Draw": (5, 20),
    "X-Ray": (10, 30),
    "Doctor Consultation": (10, 25),
    "Discharge": (2, 10),
}


def random_duration(activity):
    lo, hi = DURATIONS[activity]
    return random.randint(lo, hi)


def generate_patient_journey(case_id, start_time):
    """
    Generates one patient's event sequence.
    Returns a list of (Case_ID, Activity_Name, Timestamp) tuples.
    """
    events = []
    current_time = start_time

    def log_event(activity):
        nonlocal current_time
        events.append((case_id, activity, current_time))
        current_time += timedelta(minutes=random_duration(activity))

    # Every patient starts with Registration -> Triage
    log_event("Registration")
    log_event("Triage")

    # Branch: does this patient need diagnostics?
    needs_bloodwork = random.random() < 0.55
    needs_xray = random.random() < 0.45

    if needs_bloodwork:
        log_event("Blood Draw")

    if needs_xray:
        log_event("X-Ray")

        # THE BOTTLENECK: a chunk of X-Ray patients get sent back to Triage
        # (simulating the missing intake form issue)
        if random.random() < XRAY_BOUNCEBACK_PROB:
            log_event("Triage")  # loop-back!
            # after re-triage, they may need another X-Ray or go straight to doctor
            if random.random() < 0.3:
                log_event("X-Ray")

    log_event("Doctor Consultation")

    # Small chance of a second doctor consultation (follow-up)
    if random.random() < 0.15:
        log_event("Doctor Consultation")

    log_event("Discharge")

    return events


def generate_event_log(num_patients):
    all_events = []
    # Spread patient arrivals across a simulated day
    for i in range(1, num_patients + 1):
        case_id = f"P{i:04d}"
        arrival_offset = timedelta(minutes=random.randint(0, 12 * 60))  # arrivals over 12 hrs
        arrival_time = START_TIME + arrival_offset
        patient_events = generate_patient_journey(case_id, arrival_time)
        all_events.extend(patient_events)
    return all_events


def write_csv(events, filename="ehr_event_log.csv"):
    # Sort by case then timestamp so the log reads chronologically per patient
    events.sort(key=lambda e: (e[0], e[2]))
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Case_ID", "Activity_Name", "Timestamp"])
        for case_id, activity, ts in events:
            writer.writerow([case_id, activity, ts.strftime("%Y-%m-%d %H:%M:%S")])


if __name__ == "__main__":
    print(f"Simulating {NUM_PATIENTS} patient journeys...")
    events = generate_event_log(NUM_PATIENTS)
    write_csv(events)
    print(f"Done. Wrote {len(events)} events to ehr_event_log.csv")

    # Quick sanity stats
    bounceback_count = sum(
        1 for i in range(len(events) - 1)
        if events[i][1] == "X-Ray" and events[i + 1][1] == "Triage"
        and events[i][0] == events[i + 1][0]
    )
    print(f"Approx. X-Ray -> Triage bounce-backs detected: {bounceback_count}")
