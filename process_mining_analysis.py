"""
CareFlow - Process Mining Analysis
------------------------------------
1. Pulls the cleaned event log (stg_patient_events) from BigQuery.
2. Formats it into PM4Py's expected event log structure.
3. Discovers the "as-is" process model using the Inductive Miner.
4. Calculates transition-time metrics between every activity pair.
5. Quantifies the X-Ray -> Triage bottleneck specifically.
6. Exports the process model as an image (careflow_process_model.png).

Run this from an activated venv with google-cloud-bigquery, pandas, and pm4py installed.
"""

import pandas as pd
from google.cloud import bigquery

import pm4py
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.visualization.petri_net import visualizer as pn_visualizer

PROJECT_ID = "careflow-project-2026"
DATASET = "hospital_data"
TABLE = "stg_patient_events"


def load_data_from_bigquery():
    """Pull the cleaned event log from BigQuery into a pandas DataFrame."""
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT case_id, activity_name, event_timestamp
        FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
        ORDER BY case_id, event_timestamp
    """
    df = client.query(query).to_dataframe()
    print(f"Loaded {len(df)} events for {df['case_id'].nunique()} cases from BigQuery.")
    return df


def prepare_pm4py_log(df):
    """
    PM4Py expects specific column names: case:concept:name, concept:name, time:timestamp.
    This renames our columns to match that convention.
    """
    df = df.rename(columns={
        "case_id": "case:concept:name",
        "activity_name": "concept:name",
        "event_timestamp": "time:timestamp",
    })
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
    event_log = log_converter.apply(df)
    return event_log


def discover_process_model(event_log):
    """Run the Inductive Miner to discover the process model (Petri net).

    Note: pm4py.discover_petri_net_inductive() is the high-level convenience
    function that runs the Inductive Miner AND converts the result into a
    Petri net (net, initial_marking, final_marking) in one step. The lower-level
    inductive_miner.apply() in recent pm4py versions returns a ProcessTree object
    instead, which is why we use this wrapper instead.
    """
    net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(event_log)
    print("Process model discovered (Petri net).")
    return net, initial_marking, final_marking


def export_process_model_image(net, initial_marking, final_marking, filename="careflow_process_model.png"):
    """Save a visual PNG of the discovered process model."""
    gviz = pn_visualizer.apply(net, initial_marking, final_marking)
    pn_visualizer.save(gviz, filename)
    print(f"Process model image saved to {filename}")


def calculate_transition_times(df):
    """
    For each case, calculate the time between consecutive activities.
    Returns a DataFrame with From_Activity, To_Activity, Avg_Duration_Minutes, Count.
    """
    df = df.sort_values(["case_id", "event_timestamp"]).copy()
    df["next_activity"] = df.groupby("case_id")["activity_name"].shift(-1)
    df["next_timestamp"] = df.groupby("case_id")["event_timestamp"].shift(-1)

    transitions = df.dropna(subset=["next_activity"]).copy()
    transitions["duration_minutes"] = (
        (transitions["next_timestamp"] - transitions["event_timestamp"]).dt.total_seconds() / 60
    )

    summary = (
        transitions.groupby(["activity_name", "next_activity"])
        .agg(avg_duration_minutes=("duration_minutes", "mean"), count=("duration_minutes", "count"))
        .reset_index()
        .rename(columns={"activity_name": "from_activity", "next_activity": "to_activity"})
        .sort_values("count", ascending=False)
    )
    return summary


def analyze_xray_triage_bottleneck(df):
    """
    Quantify the specific X-Ray -> Triage bounce-back bottleneck:
    - What % of patients who had an X-Ray got sent back to Triage?
    - What's the average added delay this causes?
    """
    df = df.sort_values(["case_id", "event_timestamp"]).copy()
    df["next_activity"] = df.groupby("case_id")["activity_name"].shift(-1)
    df["next_timestamp"] = df.groupby("case_id")["event_timestamp"].shift(-1)

    xray_events = df[df["activity_name"] == "X-Ray"]
    total_xray_patients = xray_events["case_id"].nunique()

    bounceback_events = xray_events[xray_events["next_activity"] == "Triage"].copy()
    bounceback_events["delay_minutes"] = (
        (bounceback_events["next_timestamp"] - bounceback_events["event_timestamp"]).dt.total_seconds() / 60
    )

    bounceback_count = bounceback_events["case_id"].nunique()
    bounceback_pct = (bounceback_count / total_xray_patients * 100) if total_xray_patients else 0
    avg_delay = bounceback_events["delay_minutes"].mean() if not bounceback_events.empty else 0

    print("\n--- X-Ray -> Triage Bottleneck Analysis ---")
    print(f"Total patients who had an X-Ray: {total_xray_patients}")
    print(f"Patients bounced back to Triage after X-Ray: {bounceback_count}")
    print(f"Bounce-back rate: {bounceback_pct:.1f}%")
    print(f"Average delay added by bounce-back: {avg_delay:.1f} minutes")

    return {
        "total_xray_patients": total_xray_patients,
        "bounceback_count": bounceback_count,
        "bounceback_pct": bounceback_pct,
        "avg_delay_minutes": avg_delay,
    }


if __name__ == "__main__":
    df = load_data_from_bigquery()

    event_log = prepare_pm4py_log(df)
    net, im, fm = discover_process_model(event_log)
    export_process_model_image(net, im, fm)

    print("\n--- Transition Time Summary (top 10 by frequency) ---")
    transition_summary = calculate_transition_times(df)
    print(transition_summary.head(10).to_string(index=False))
    transition_summary.to_csv("transition_times.csv", index=False)
    print("Full transition summary saved to transition_times.csv")

    bottleneck_stats = analyze_xray_triage_bottleneck(df)
