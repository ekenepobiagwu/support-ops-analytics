-- Weekly CSAT by region and tier.
-- Caveat surfaced deliberately: CSAT response rate is ~28% and skews toward
-- dissatisfied users after SLA breaches, so raw CSAT understates true
-- satisfaction. response_rate is included so dashboards can show the
-- denominator alongside the score.
with tickets as (
    select * from {{ ref('stg_tickets') }}
),

csat as (
    select * from {{ ref('stg_csat_responses') }}
)

select
    date_trunc(date(t.created_at), week(monday)) as week_start,
    t.region,
    t.tier,
    count(*)                                     as solved_tickets,
    count(c.ticket_id)                           as csat_responses,
    round(count(c.ticket_id) / count(*), 4)      as response_rate,
    round(avg(c.score), 3)                       as avg_csat,
    round(countif(c.is_satisfied) / nullif(count(c.ticket_id), 0), 4) as csat_pct
from tickets t
left join csat c using (ticket_id)
where t.status = 'solved'
group by 1, 2, 3

