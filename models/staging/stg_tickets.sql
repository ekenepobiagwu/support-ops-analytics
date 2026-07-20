-- Staging: clean and type raw ticket data
with source as (
    select * from {{ source('support', 'tickets') }}
),

renamed as (
    select
        cast(ticket_id as int64)                as ticket_id,
        cast(created_at as timestamp)           as created_at,
        region,
        tier,
        priority,
        category,
        channel,
        agent_id,
        cast(first_response_hours as float64)   as first_response_hours,
        cast(sla_target_hours as float64)       as sla_target_hours,
        cast(nullif(resolved_at, '') as timestamp) as resolved_at,
        status,
        cast(reopened as int64) = 1             as was_reopened
    from source
)

select
    *,
    first_response_hours <= sla_target_hours    as met_first_response_sla,
    timestamp_diff(resolved_at, created_at, minute) / 60.0 as resolution_hours
from renamed

