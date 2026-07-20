# Support Ops Analytics

An end-to-end support operations analytics project: synthetic Zendesk-style ticket data → dbt models on BigQuery → dashboards answering the questions support leadership actually asks.

Built by [Kenny Peter-Obiagwu](https://www.linkedin.com/in/ekene-peter-obiagwu-47718263) — product/data analyst with 5 years across support tooling (Zendesk at Digit.co) and marketing analytics (BigQuery/Looker Studio at WPP).

## The problem this simulates

A fast-growing dev-tools company's support volume is scaling faster than its ability to make sense of it. Leadership needs to know:

1. **Are we meeting SLA — and where are we not?** By region, tier, and priority, week over week.
2. **Are we getting faster but less accurate?** First-response speed joined against reopen rate and CSAT on the same weekly grain.
3. **What should Engineering fix next?** A multi-signal prioritization score that ranks issue categories by frequency, breadth, support cost, and sentiment — so the answer is defensible, not vibes.

## Architecture

```
scripts/generate_tickets.py      # 54k synthetic tickets, 18 months
        |                        # growth trend, weekly seasonality,
        v                        # 3 incident spikes, SLA breach logic,
data/*.csv --> BigQuery          # biased CSAT response behavior
        |
        v
models/staging/                  # typing, cleaning, SLA flags
models/marts/
  |-- fct_sla_attainment.sql     # weekly SLA %, median/p90 FRT, reopen rate
  |-- fct_csat_weekly.sql        # CSAT with response-rate denominator
  \-- fct_issue_priority_score.sql  # the multi-signal ranking model
```

## The prioritization model

Each issue category gets a 0-1 score from four min-max-normalized signals:

| Signal | Weight | What it captures |
|---|---|---|
| Frequency | 0.30 | How often it happens (ticket volume) |
| Breadth | 0.20 | How widely (distinct region x tier segments) |
| Support cost | 0.25 | Handling hours consumed |
| Sentiment | 0.25 | Inverted avg CSAT on the category |

Weights live at the top of the model and are meant to be re-tuned with stakeholders — the point is that the tradeoffs are explicit and auditable.

## Honest limitations (by design)

- **CSAT is biased.** Response rate is ~28% and dissatisfied users respond more after SLA breaches, so raw CSAT understates satisfaction. `fct_csat_weekly` ships the response rate next to the score so dashboards never show one without the other.
- **The data is synthetic.** The generator intentionally bakes in the failure modes real support data has — incident spikes, breach clustering, open-ticket right-censoring — so the models have something real to handle.
- **Min-max normalization is window-sensitive.** A quiet month compresses the score range. An alternative (z-scores against a trailing baseline) is discussed in `analyses/`.

## Running it

```bash
pip install dbt-bigquery
python scripts/generate_tickets.py
# load data/*.csv to BigQuery (bq load or the console)
dbt run && dbt test
```

## Stack

Python · SQL (BigQuery) · dbt · Looker Studio

