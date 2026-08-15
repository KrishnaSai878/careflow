-- Staging model: cleans and standardizes the raw patient event log
-- into the strict format process mining tools require:
-- Case_ID, Activity_Name, Timestamp (deduplicated, sorted, correctly typed)

with source as (

    select * from {{ source('hospital_data', 'patient_events_raw') }}

),

cleaned as (

    select
        cast(Case_ID as string) as case_id,
        trim(cast(Activity_Name as string)) as activity_name,
        cast(Timestamp as timestamp) as event_timestamp

    from source
    where Case_ID is not null
      and Activity_Name is not null
      and Timestamp is not null

),

deduplicated as (

    select distinct
        case_id,
        activity_name,
        event_timestamp

    from cleaned

)

select
    case_id,
    activity_name,
    event_timestamp
from deduplicated
order by case_id, event_timestamp
