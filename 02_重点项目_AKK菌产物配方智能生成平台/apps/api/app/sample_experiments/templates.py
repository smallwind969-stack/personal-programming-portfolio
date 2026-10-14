from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import StringIO
from math import exp, sin


TEMPLATE_KEY = "algae-culture"
TEMPLATE_VERSION = "algae-culture-v1"
FILE_NAME = f"{TEMPLATE_VERSION}.csv"


def build_algae_culture_csv() -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "timestamp", "temperature_c", "ph", "agitation_rpm",
        "dissolved_oxygen_pct", "od600",
    ])
    started_at = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
    for index in range(36):
        hours = index * 2
        growth = 0.16 + 2.7 / (1 + exp(-0.24 * (hours - 32)))
        writer.writerow([
            (started_at + timedelta(hours=hours)).isoformat(),
            f"{36.8 + 0.25 * sin(index / 4):.2f}",
            f"{7.15 - 0.012 * index + 0.04 * sin(index / 5):.3f}",
            f"{145 + min(index, 18) * 3.2:.1f}",
            f"{68 - min(index, 22) * 1.7 + 2.5 * sin(index / 3):.2f}",
            f"{growth:.4f}",
        ])
    return output.getvalue()


def template_content_hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()
