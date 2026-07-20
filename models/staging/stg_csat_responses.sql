with source as (
    select * from {{ source('support', 'csat_responses') }}
)

select
    cast(ticket_id as int64)        as ticket_id,
    cast(score as int64)            as score,
    cast(responded_at as timestamp) as responded_at,
    cast(score as int64) >= 4       as is_satisfied
from source

