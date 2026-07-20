-- SLA attainment by week, region, tier, and priority.
-- Powers the "are we getting faster but less accurate?" style questions:
-- join to fct_csat_weekly on the same grain to see speed vs. quality together.
with tickets as (
    select * from {{ ref('stg_tickets') }}
)

select
    date_trunc(date(created_at), week(monday))  as week_start,
    region,
    tier,
    priority,
    count(*)                                    as tickets_created,
    countif(met_first_response_sla)             as sla_met,
    round(countif(met_first_response_sla) / count(*), 4) as sla_attainment_rate,
    round(approx_quantiles(first_response_hours, 100)[offset(50)], 2) as median_frt_hours,
    round(approx_quantiles(first_response_hours, 100)[offset(90)], 2) as p90_frt_hours,
    round(avg(resolution_hours), 2)             as avg_resolution_hours,
    countif(was_reopened)                       as reopened_tickets,
    round(countif(was_reopened) / count(*), 4)  as reopen_rate
from tickets
group by 1, 2, 3, 4
