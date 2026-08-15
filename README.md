<<<<<<< HEAD
# CareFlow — Clinical Pathway Process Mining

CareFlow analyzes raw, timestamped hospital event logs to automatically discover the real
sequence of events a patient experiences, instead of relying on static averages like
"average ER wait time." The goal is to surface hidden operational bottlenecks and present
them as an actionable finding for hospital administrators.

## The problem

Standard hospital BI dashboards show aggregate numbers ("average wait time: 47 minutes")
that hide *where* the time is actually going. Process mining reconstructs the real,
messy sequence of events patients go through — including loops and rework — directly
from the data, with no manual process mapping required.

## The finding

Running the full pipeline on a simulated hospital event log surfaced a clear bottleneck:

- **1,000** simulated patients, **5,356** total events
- **434** patients received an X-Ray
- **178** of them (**41.0%**) were sent back to Triage afterward
- Each bounce-back added an average of **20.8 minutes** of delay

This pattern — patients looping back to Triage after an X-Ray, likely due to missing
intake paperwork — was discovered by the process mining algorithm directly from the
event log, not hand-coded into the analysis.

## Architecture

```
Python simulator  →  BigQuery (raw)  →  dbt (clean, tested)  →  PM4Py (discovery)  →  PowerBI (dashboard)
```

| Stage | Technology | Purpose |
|---|---|---|
| Data generation | Python | Simulates realistic patient event logs with injected bottleneck patterns |
| Data warehouse | Google BigQuery | Stores raw and cleaned event log data |
| Transformation | dbt (dbt-core + dbt-bigquery) | Cleans and standardizes the raw log; enforces data-quality tests |
| Process mining | PM4Py | Discovers the process model (Petri net) and calculates transition-time metrics |
| Dashboard | Microsoft PowerBI | Visualizes KPIs, the process flow, and the bottleneck finding |

## Pipeline stages

1. **Simulate** — `simulate_ehr_logs.py` generates a synthetic EHR event log
   (`Case_ID, Activity_Name, Timestamp`), deliberately injecting an X-Ray → Triage
   bounce-back pattern at a known rate so the mining pipeline can be verified against
   a known ground truth.
2. **Load** — the CSV is loaded into a BigQuery table (`patient_events_raw`).
3. **Transform** — a dbt model (`stg_patient_events`) cleans, types, deduplicates, and
   sorts the log, with `not_null` and `accepted_values` tests enforcing data quality.
4. **Mine** — `process_mining_analysis.py` pulls the clean log from BigQuery, runs
   PM4Py's Inductive Miner to discover the process model, calculates transition times
   between every activity pair, and quantifies the X-Ray → Triage bottleneck.
5. **Visualize** — a PowerBI dashboard presents the KPIs, the transition-time chart, and
   the discovered process model image.

## Repository structure

```
careflow/
├── simulate_ehr_logs.py          # Stage 1: synthetic event log generator
├── careflow_dbt/                 # Stage 3: dbt project
│   └── models/staging/
│       ├── sources.yml
│       ├── stg_patient_events.sql
│       └── stg_patient_events_tests.yml
├── process_mining_analysis.py    # Stage 4: PM4Py discovery + bottleneck analysis
├── careflow_process_model.png    # Discovered process model (output)
├── transition_times.csv          # Transition-time metrics (output)
└── careflow_dashboard.pbix       # Stage 5: PowerBI dashboard
```

## Running it yourself

```bash
# 1. Generate the event log
python simulate_ehr_logs.py

# 2. Load into BigQuery
bq mk --dataset --location=US <your-project>:hospital_data
bq mk --table <your-project>:hospital_data.patient_events_raw Case_ID:STRING,Activity_Name:STRING,Timestamp:TIMESTAMP
bq load --source_format=CSV --skip_leading_rows=1 <your-project>:hospital_data.patient_events_raw ehr_event_log.csv

# 3. Run dbt
cd careflow_dbt
dbt run
dbt test
cd ..

# 4. Run the process mining analysis
python process_mining_analysis.py

# 5. Open careflow_dashboard.pbix in PowerBI Desktop
```

## Why synthetic data

Real hospital EHR data is protected under healthcare privacy regulations and isn't
accessible for a portfolio project. Generating synthetic data with a known, injected
bottleneck pattern also makes it possible to verify the pipeline actually works —
the process mining stage should (and does) rediscover the same pattern that was
deliberately built into the simulator.
=======
# careflow
>>>>>>> 43f46d34921f5e7b1bee5f7ea7a2b32f137ebd65
