"""
Generate a realistic synthetic support ticket dataset (Zendesk-style).

Simulates 18 months of support operations for a fast-growing dev-tools company:
- Ticket volume grows over time with weekly seasonality
- Enterprise / Pro / Free tiers with different SLA targets
- Regions: AMER, EMEA, APAC
- Issue categories tied to product areas, with a few "bug spike" incidents
- CSAT responses (biased: unhappy users respond more)
- First response + resolution timestamps with realistic breaches

Output: data/tickets.csv, data/csat_responses.csv, data/agents.csv
"""

import csv
import os
import random
from datetime import datetime, timedelta

random.seed(42)

START = datetime(2025, 1, 1)
DAYS = 545  # ~18 months

REGIONS = ["AMER", "EMEA", "APAC"]
REGION_WEIGHTS = [0.5, 0.3, 0.2]

TIERS = ["free", "pro", "enterprise"]
TIER_WEIGHTS = [0.55, 0.35, 0.10]

# SLA targets in hours (first response) by tier/priority
SLA_FIRST_RESPONSE = {
    ("enterprise", "urgent"): 1,
    ("enterprise", "high"): 4,
    ("enterprise", "normal"): 8,
    ("enterprise", "low"): 24,
    ("pro", "urgent"): 4,
    ("pro", "high"): 8,
    ("pro", "normal"): 24,
    ("pro", "low"): 48,
    ("free", "urgent"): 24,
    ("free", "high"): 24,
    ("free", "normal"): 48,
    ("free", "low"): 72,
}

CATEGORIES = {
    "billing": 0.14,
    "authentication": 0.10,
    "editor_performance": 0.16,
    "ai_completions": 0.20,
    "extensions": 0.08,
    "sync_settings": 0.07,
    "installation": 0.09,
    "account_management": 0.08,
    "feature_request": 0.08,
}

# Incident windows: (start_day, length_days, category, volume multiplier)
INCIDENTS = [
    (120, 6, "ai_completions", 3.5),
    (260, 4, "authentication", 4.0),
    (400, 8, "editor_performance", 2.5),
]

AGENT_COUNT = 24


def pick(weights_dict):
    cats = list(weights_dict.keys())
    w = list(weights_dict.values())
    return random.choices(cats, weights=w)[0]


def main():
    os.makedirs("data", exist_ok=True)

    agents = []
    for i in range(1, AGENT_COUNT + 1):
        agents.append({
            "agent_id": f"AG{i:03d}",
            "region": random.choices(REGIONS, REGION_WEIGHTS)[0],
            "hired_at": (START - timedelta(days=random.randint(30, 900))).date().isoformat(),
        })

    tickets, csat = [], []
    ticket_id = 100000

    for day in range(DAYS):
        date = START + timedelta(days=day)
        # Growth + weekly seasonality (weekends lighter)
        base = 60 + day * 0.22
        dow_factor = 0.45 if date.weekday() >= 5 else 1.0
        n = int(random.gauss(base * dow_factor, base * 0.12))

        # Incident spikes
        spike_cat = None
        for (s, ln, cat, mult) in INCIDENTS:
            if s <= day < s + ln:
                spike_cat = (cat, mult)

        for _ in range(max(n, 5)):
            ticket_id += 1
            tier = random.choices(TIERS, TIER_WEIGHTS)[0]
            region = random.choices(REGIONS, REGION_WEIGHTS)[0]

            if spike_cat and random.random() < (spike_cat[1] - 1) / spike_cat[1]:
                category = spike_cat[0]
            else:
                category = pick(CATEGORIES)

            priority = random.choices(
                ["urgent", "high", "normal", "low"],
                weights=[0.05, 0.18, 0.55, 0.22] if tier != "enterprise"
                else [0.12, 0.28, 0.45, 0.15],
            )[0]

            created = date + timedelta(
                hours=random.uniform(0, 23), minutes=random.uniform(0, 59)
            )

            sla_target = SLA_FIRST_RESPONSE[(tier, priority)]
            # First response: mostly within SLA, degraded during incidents
            breach_p = 0.12 + (0.25 if spike_cat else 0) + (0.05 if tier == "free" else 0)
            if random.random() < breach_p:
                frt = sla_target * random.uniform(1.05, 3.0)
            else:
                frt = sla_target * random.uniform(0.05, 0.95)

            resolution_hours = frt + abs(random.gauss(
                {"urgent": 8, "high": 16, "normal": 30, "low": 50}[priority], 12
            ))
            # ~6% of recent tickets still open at snapshot
            is_open = random.random() < 0.06 and day > DAYS - 30

            agent = random.choice([a for a in agents if a["region"] == region] or agents)

            tickets.append({
                "ticket_id": ticket_id,
                "created_at": created.isoformat(timespec="minutes"),
                "region": region,
                "tier": tier,
                "priority": priority,
                "category": category,
                "channel": random.choices(["email", "chat", "web_form"], [0.5, 0.3, 0.2])[0],
                "agent_id": agent["agent_id"],
                "first_response_hours": round(frt, 2),
                "sla_target_hours": sla_target,
                "resolved_at": "" if is_open else (created + timedelta(hours=resolution_hours)).isoformat(timespec="minutes"),
                "status": "open" if is_open else "solved",
                "reopened": int(random.random() < 0.07),
            })

            # CSAT: response rate ~28%, unhappy respond more when SLA breached
            if not is_open and random.random() < 0.28:
                breached = frt > sla_target
                if breached:
                    score = random.choices([1, 2, 3, 4, 5], [0.25, 0.2, 0.2, 0.2, 0.15])[0]
                else:
                    score = random.choices([1, 2, 3, 4, 5], [0.04, 0.06, 0.12, 0.33, 0.45])[0]
                csat.append({
                    "ticket_id": ticket_id,
                    "score": score,
                    "responded_at": (created + timedelta(hours=resolution_hours + random.uniform(1, 48))).isoformat(timespec="minutes"),
                })

    with open("data/tickets.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=tickets[0].keys())
        w.writeheader()
        w.writerows(tickets)

    with open("data/csat_responses.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csat[0].keys())
        w.writeheader()
        w.writerows(csat)

    with open("data/agents.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=agents[0].keys())
        w.writeheader()
        w.writerows(agents)

    print(f"Generated {len(tickets):,} tickets, {len(csat):,} CSAT responses, {len(agents)} agents")


if __name__ == "__main__":
    main()
