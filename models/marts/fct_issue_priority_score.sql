-- Multi-signal issue prioritization model.
--
-- Ranks product issue categories by user impact so Engineering sees a
-- defensible picture of what to fix next. Four weighted signals:
--
--   frequency   : ticket volume in the window (how often it happens)
--   breadth     : share of regions x tiers affected (how widely it happens)
--   support_cost: total handling hours (what it costs the support org)
--   sentiment   : inverted avg CSAT on the category (how much users hate it)
--
-- Each signal is min-max normalized to 0-1 within the window, then combined:
--   score = 0.30*frequency + 0.20*breadth + 0.25*support_cost + 0.25*sentiment
--
-- Weights are deliberately explicit and easy to re-tune with stakeholders.

{% set lookback_days = 28 %}

with tickets as (
    select * from {{ ref('stg_tickets') }}
    where date(created_at) >= date_sub(current_date(), interval {{ lookback_days }} day)
),

csat as (
    select * from {{ ref('stg_csat_responses') }}
),

by_category as (
    select
        t.category,
        count(*)                                        as ticket_count,
        count(distinct concat(t.region, '-', t.tier))   as segments_affected,
        sum(coalesce(t.resolution_hours, t.first_response_hours)) as handling_hours,
        avg(c.score)                                    as avg_csat,
        countif(t.tier = 'enterprise')                  as enterprise_tickets
    from tickets t
    left join csat c using (ticket_id)
    group by 1
),

bounds as (
    select
        min(ticket_count) as min_ct, max(ticket_count) as max_ct,
        min(segments_affected) as min_seg, max(segments_affected) as max_seg,
        min(handling_hours) as min_hh, max(handling_hours) as max_hh,
        min(avg_csat) as min_cs, max(avg_csat) as max_cs
    from by_category
),

scored as (
    select
        c.category,
        c.ticket_count,
        c.segments_affected,
        round(c.handling_hours, 1)      as handling_hours,
        round(c.avg_csat, 2)            as avg_csat,
        c.enterprise_tickets,
        safe_divide(c.ticket_count - b.min_ct, b.max_ct - b.min_ct)      as freq_norm,
        safe_divide(c.segments_affected - b.min_seg, b.max_seg - b.min_seg) as breadth_norm,
        safe_divide(c.handling_hours - b.min_hh, b.max_hh - b.min_hh)    as cost_norm,
        1 - safe_divide(c.avg_csat - b.min_cs, b.max_cs - b.min_cs)      as sentiment_norm
    from by_category c
    cross join bounds b
)

select
    category,
    ticket_count,
    segments_affected,
    handling_hours,
    avg_csat,
    enterprise_tickets,
    round(
        0.30 * coalesce(freq_norm, 0)
      + 0.20 * coalesce(breadth_norm, 0)
      + 0.25 * coalesce(cost_norm, 0)
      + 0.25 * coalesce(sentiment_norm, 0)
    , 3) as priority_score
from scored
order by priority_score desc

