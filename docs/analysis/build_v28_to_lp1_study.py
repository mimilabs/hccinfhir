"""Build the V28-to-LEAD Prospective V1 documentation study.

This is an illustrative, prevalence-weighted mock study—not a payment forecast.
It uses marginal HCC prevalence from CMS's 2024 Risk Adjustment Report to
Congress, as staged in Mimilabs, and assumes independence between HCCs.
"""

from __future__ import annotations

import csv
import html
import math
import random
from collections import defaultdict
from pathlib import Path

from hccinfhir.constants import LEAD_PROSPECTIVE_MODEL
from hccinfhir.defaults import coefficients_default, hierarchies_default
from hccinfhir.model_coefficients import apply_coefficients
from hccinfhir.model_demographics import categorize_demographics
from hccinfhir.model_hierarchies import apply_hierarchies
from hccinfhir.model_interactions import apply_interactions


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "docs" / "data"
ASSET_DIR = ROOT / "docs" / "assets"
PREVALENCE_FILE = DATA_DIR / "v28_report_to_congress_prevalence_2024.csv"

V28 = "CMS-HCC Model V28"
LP1 = LEAD_PROSPECTIVE_MODEL
REPORT_DENOMINATOR = 28_248_982
SIMULATION_SEED = 20261126
SIMULATED_HCC_PROFILES = 10_000

# Deliberately illustrative—not an estimate of the LEAD population mix.
SEGMENTS = {
    "CNA": {"label": "Non-dual aged", "age": 72, "dual": "00", "orec": "0", "weight": 0.50},
    "CND": {"label": "Non-dual disabled", "age": 60, "dual": "00", "orec": "1", "weight": 0.10},
    "CFA": {"label": "Full-dual aged", "age": 72, "dual": "02", "orec": "0", "weight": 0.15},
    "CFD": {"label": "Full-dual disabled", "age": 60, "dual": "02", "orec": "1", "weight": 0.05},
    "CPA": {"label": "Partial-dual aged", "age": 72, "dual": "01", "orec": "0", "weight": 0.15},
    "CPD": {"label": "Partial-dual disabled", "age": 60, "dual": "01", "orec": "1", "weight": 0.05},
}

EXAMPLES = [
    ("No payment HCCs", set()),
    ("Diabetes with chronic complications", {"37"}),
    ("Morbid obesity", {"48"}),
    ("Specified heart arrhythmia", {"238"}),
    ("Acute-on-chronic heart failure", {"224"}),
    ("Diabetes + heart failure", {"37", "224"}),
    ("Heart failure + stage 4 CKD", {"224", "327"}),
    ("Six-condition profile", {"37", "48", "224", "238", "280", "327"}),
]


def load_prevalence() -> list[dict]:
    with PREVALENCE_FILE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["sample_size"] = int(float(row["sample_size"])) if row["sample_size"] else None
        row["prevalence"] = float(row["prevalence"]) if row["prevalence"] else None
    return rows


def demographics(segment: str, sex: str):
    spec = SEGMENTS[segment]
    return categorize_demographics(
        age=spec["age"],
        sex=sex,
        dual_elgbl_cd=spec["dual"],
        orec=spec["orec"],
        crec="0",
        version="V2",
    )


def score_hccs(hccs: set[str], model: str, segment: str, sex: str) -> float:
    demo = demographics(segment, sex)
    active = apply_hierarchies(set(hccs), model, hierarchies_default)
    interactions = apply_interactions(demo, active, model)
    applied = apply_coefficients(
        demo,
        active,
        interactions,
        model,
        coefficients_default,
    )
    return sum(applied.values())


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def svg_style() -> str:
    return """
    <style>
      :root { --bg:#ffffff; --fg:#172033; --muted:#60708a; --grid:#d7deea;
              --v28:#2563eb; --lp1:#d97706; --positive:#047857; --negative:#b91c1c; }
      @media (prefers-color-scheme: dark) {
        :root { --bg:#111827; --fg:#f3f4f6; --muted:#b3bfd1; --grid:#374151;
                --v28:#60a5fa; --lp1:#fbbf24; --positive:#34d399; --negative:#f87171; }
      }
      .bg { fill:var(--bg); } .fg { fill:var(--fg); } .muted { fill:var(--muted); }
      .grid { stroke:var(--grid); stroke-width:1; } .v28 { fill:var(--v28); stroke:var(--v28); }
      .lp1 { fill:var(--lp1); stroke:var(--lp1); } .positive { fill:var(--positive); }
      .negative { fill:var(--negative); } text { font-family:system-ui,-apple-system,sans-serif; }
      .title { font-size:20px; font-weight:600; } .subtitle { font-size:12px; }
      .label { font-size:12px; } .value { font-size:11px; font-variant-numeric:tabular-nums; }
      .axis { font-size:11px; fill:var(--muted); }
    </style>
    """


def save_example_chart(rows: list[dict]) -> None:
    width, left, right, top, row_h = 980, 285, 35, 85, 50
    height = top + row_h * len(rows) + 60
    max_value = max(max(row["v28_score"], row["lp1_score"]) for row in rows) * 1.08
    plot_w = width - left - right
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {width} {height}">',
        svg_style(),
        f'<rect class="bg" width="{width}" height="{height}"/>',
        '<title id="title">Representative V28 and LP1 scores</title>',
        '<desc id="desc">Grouped horizontal bars compare risk scores for eight non-dual aged example profiles.</desc>',
        '<text class="title fg" x="20" y="30">Representative scores: non-dual aged, male age 72</text>',
        '<text class="subtitle muted" x="20" y="52">Same V28 HCCs; only scoring behavior changes</text>',
        f'<rect class="v28" x="{left}" y="62" width="12" height="12"/><text class="label fg" x="{left + 18}" y="72">CMS V28</text>',
        f'<rect class="lp1" x="{left + 95}" y="62" width="12" height="12"/><text class="label fg" x="{left + 113}" y="72">LEAD LP1</text>',
    ]
    for tick in range(6):
        value = max_value * tick / 5
        x = left + plot_w * tick / 5
        pieces.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 5}" x2="{x:.1f}" y2="{height - 35}"/>')
        pieces.append(f'<text class="axis" text-anchor="middle" x="{x:.1f}" y="{height - 15}">{value:.1f}</text>')
    for index, row in enumerate(rows):
        y = top + index * row_h
        label = html.escape(row["case"])
        pieces.append(f'<text class="label fg" x="{left - 10}" y="{y + 22}" text-anchor="end">{label}</text>')
        for offset, key, css in ((8, "v28_score", "v28"), (27, "lp1_score", "lp1")):
            value = row[key]
            bar_w = plot_w * value / max_value
            pieces.append(f'<rect class="{css}" x="{left}" y="{y + offset}" width="{bar_w:.1f}" height="13" opacity="0.88"/>')
            pieces.append(f'<text class="value fg" x="{left + bar_w + 5:.1f}" y="{y + offset + 11}">{value:.3f}</text>')
    pieces.append(f'<text class="axis" text-anchor="middle" x="{left + plot_w / 2}" y="{height - 1}">Risk score</text>')
    pieces.append('</svg>')
    (ASSET_DIR / "v28-to-lp1-example-scores.svg").write_text("\n".join(pieces), encoding="utf-8")


def save_coefficient_chart(rows: list[dict]) -> None:
    width, left, right, top, row_h = 1160, 490, 55, 85, 39
    height = top + row_h * len(rows) + 55
    max_value = max(max(row["v28_coefficient"], row["lp1_coefficient"]) for row in rows) * 1.08
    plot_w = width - left - right
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {width} {height}">',
        svg_style(),
        f'<rect class="bg" width="{width}" height="{height}"/>',
        '<title id="title">Common HCC coefficient comparison</title>',
        '<desc id="desc">Dumbbell chart compares V28 and LP1 CNA coefficients for the twelve most prevalent HCCs with reported counts.</desc>',
        '<text class="title fg" x="20" y="30">Common HCCs can move in very different directions</text>',
        '<text class="subtitle muted" x="20" y="52">CNA segment; 12 highest Report-to-Congress marginal prevalences</text>',
        f'<circle class="v28" cx="{left}" cy="69" r="5"/><text class="label fg" x="{left + 11}" y="73">CMS V28</text>',
        f'<circle class="lp1" cx="{left + 95}" cy="69" r="5"/><text class="label fg" x="{left + 106}" y="73">LEAD LP1</text>',
    ]
    for tick in range(6):
        value = max_value * tick / 5
        x = left + plot_w * tick / 5
        pieces.append(f'<line class="grid" x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{height - 28}"/>')
        pieces.append(f'<text class="axis" text-anchor="middle" x="{x:.1f}" y="{height - 10}">{value:.1f}</text>')
    for index, row in enumerate(rows):
        y = top + index * row_h + 15
        label = f'HCC {row["hcc"]} · {row["short_label"]} ({row["prevalence"] * 100:.1f}%)'
        x1 = left + plot_w * row["v28_coefficient"] / max_value
        x2 = left + plot_w * row["lp1_coefficient"] / max_value
        pieces.append(f'<text class="label fg" x="{left - 10}" y="{y + 4}" text-anchor="end">{html.escape(label)}</text>')
        pieces.append(f'<line x1="{x1:.1f}" y1="{y}" x2="{x2:.1f}" y2="{y}" stroke="var(--grid)" stroke-width="3"/>')
        pieces.append(f'<circle class="v28" cx="{x1:.1f}" cy="{y}" r="5"/>')
        pieces.append(f'<circle class="lp1" cx="{x2:.1f}" cy="{y}" r="5"/>')
    pieces.append('</svg>')
    (ASSET_DIR / "v28-to-lp1-common-hcc-coefficients.svg").write_text("\n".join(pieces), encoding="utf-8")


def save_population_chart(rows: list[dict]) -> None:
    width, height, left, right, top, bottom = 1020, 570, 75, 35, 85, 105
    plot_w, plot_h = width - left - right, height - top - bottom
    max_value = max(max(row["mean_v28"], row["mean_lp1"]) for row in rows) * 1.15
    group_w = plot_w / len(rows)
    bar_w = min(42, group_w * 0.28)
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {width} {height}">',
        svg_style(),
        f'<rect class="bg" width="{width}" height="{height}"/>',
        '<title id="title">Prevalence-weighted mock population results</title>',
        '<desc id="desc">Grouped bars compare mean V28 and LP1 scores across six community segments and an illustrative weighted mix.</desc>',
        '<text class="title fg" x="20" y="30">Mock population: impact differs sharply by segment</text>',
        f'<text class="subtitle muted" x="20" y="52">{SIMULATED_HCC_PROFILES:,} independent HCC profiles per segment · fixed representative ages · not a forecast</text>',
        f'<rect class="v28" x="{left}" y="64" width="12" height="12"/><text class="label fg" x="{left + 18}" y="74">CMS V28</text>',
        f'<rect class="lp1" x="{left + 95}" y="64" width="12" height="12"/><text class="label fg" x="{left + 113}" y="74">LEAD LP1</text>',
    ]
    for tick in range(6):
        value = max_value * tick / 5
        y = top + plot_h - plot_h * value / max_value
        pieces.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}"/>')
        pieces.append(f'<text class="axis" text-anchor="end" x="{left - 8}" y="{y + 4:.1f}">{value:.1f}</text>')
    for index, row in enumerate(rows):
        center = left + group_w * (index + 0.5)
        for x, key, css in ((center - bar_w - 2, "mean_v28", "v28"), (center + 2, "mean_lp1", "lp1")):
            value = row[key]
            bar_h = plot_h * value / max_value
            y = top + plot_h - bar_h
            pieces.append(f'<rect class="{css}" x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" opacity="0.88"/>')
        delta = row["percent_change"]
        delta_css = "positive" if delta >= 0 else "negative"
        pieces.append(f'<text class="value {delta_css}" text-anchor="middle" x="{center:.1f}" y="{top + plot_h + 22}">{delta:+.1f}%</text>')
        pieces.append(f'<text class="label fg" text-anchor="middle" x="{center:.1f}" y="{top + plot_h + 42}">{html.escape(row["segment"])}</text>')
        pieces.append(f'<text class="axis" text-anchor="middle" x="{center:.1f}" y="{top + plot_h + 58}">{html.escape(row["label"])}</text>')
    pieces.append(f'<text class="axis" text-anchor="middle" transform="translate(18 {top + plot_h / 2}) rotate(-90)">Mean risk score</text>')
    pieces.append('</svg>')
    (ASSET_DIR / "v28-to-lp1-mock-population.svg").write_text("\n".join(pieces), encoding="utf-8")


def common_examples() -> list[dict]:
    output = []
    for label, hccs in EXAMPLES:
        v28 = score_hccs(hccs, V28, "CNA", "M")
        lp1 = score_hccs(hccs, LP1, "CNA", "M")
        output.append({
            "case": label,
            "hccs": ";".join(sorted(hccs, key=int)) or "none",
            "v28_score": round(v28, 4),
            "lp1_score": round(lp1, 4),
            "absolute_change": round(lp1 - v28, 4),
            "percent_change": round((lp1 / v28 - 1) * 100, 1) if v28 else None,
        })
    return output


def common_coefficients(prevalence_rows: list[dict]) -> list[dict]:
    available = [row for row in prevalence_rows if row["prevalence"] is not None]
    available.sort(key=lambda row: row["prevalence"], reverse=True)
    output = []
    for row in available[:12]:
        hcc = row["hcc"]
        v28 = coefficients_default.get((f"cna_hcc{hcc}".lower(), V28), 0.0)
        lp1 = coefficients_default.get((f"cna_hcc{hcc}".lower(), LP1), 0.0)
        short_label = row["hcc_label"]
        if len(short_label) > 36:
            short_label = short_label[:33].rstrip() + "…"
        output.append({
            "hcc": hcc,
            "hcc_label": row["hcc_label"],
            "short_label": short_label,
            "sample_size": row["sample_size"],
            "prevalence": row["prevalence"],
            "v28_coefficient": v28,
            "lp1_coefficient": lp1,
            "absolute_change": lp1 - v28,
        })
    return output


def simulate_population(prevalence_rows: list[dict]) -> list[dict]:
    rng = random.Random(SIMULATION_SEED)
    available = [(row["hcc"], row["prevalence"]) for row in prevalence_rows if row["prevalence"]]
    totals = {segment: defaultdict(float) for segment in SEGMENTS}

    for _ in range(SIMULATED_HCC_PROFILES):
        hccs = {hcc for hcc, prevalence in available if rng.random() < prevalence}
        sex = "F" if rng.random() < 0.5 else "M"
        for segment in SEGMENTS:
            v28 = score_hccs(hccs, V28, segment, sex)
            lp1 = score_hccs(hccs, LP1, segment, sex)
            delta = lp1 - v28
            totals[segment]["v28"] += v28
            totals[segment]["lp1"] += lp1
            totals[segment]["delta"] += delta
            totals[segment]["delta_sq"] += delta * delta

    output = []
    for segment, spec in SEGMENTS.items():
        total = totals[segment]
        mean_v28 = total["v28"] / SIMULATED_HCC_PROFILES
        mean_lp1 = total["lp1"] / SIMULATED_HCC_PROFILES
        mean_delta = total["delta"] / SIMULATED_HCC_PROFILES
        variance = max(
            0.0,
            (total["delta_sq"] - SIMULATED_HCC_PROFILES * mean_delta**2)
            / (SIMULATED_HCC_PROFILES - 1),
        )
        se = math.sqrt(variance / SIMULATED_HCC_PROFILES)
        output.append({
            "segment": segment,
            "label": spec["label"],
            "assumed_weight": spec["weight"],
            "profiles": SIMULATED_HCC_PROFILES,
            "mean_v28": mean_v28,
            "mean_lp1": mean_lp1,
            "mean_change": mean_delta,
            "percent_change": (mean_lp1 / mean_v28 - 1) * 100,
            "paired_delta_ci_low": mean_delta - 1.96 * se,
            "paired_delta_ci_high": mean_delta + 1.96 * se,
        })

    weighted_v28 = sum(row["mean_v28"] * row["assumed_weight"] for row in output)
    weighted_lp1 = sum(row["mean_lp1"] * row["assumed_weight"] for row in output)
    output.append({
        "segment": "Mix",
        "label": "Illustrative mix",
        "assumed_weight": 1.0,
        "profiles": SIMULATED_HCC_PROFILES * len(SEGMENTS),
        "mean_v28": weighted_v28,
        "mean_lp1": weighted_lp1,
        "mean_change": weighted_lp1 - weighted_v28,
        "percent_change": (weighted_lp1 / weighted_v28 - 1) * 100,
        "paired_delta_ci_low": "",
        "paired_delta_ci_high": "",
    })
    return output


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prevalence_rows = load_prevalence()
    if len(prevalence_rows) != 115:
        raise RuntimeError(f"Expected 115 V28 payment HCCs, found {len(prevalence_rows)}")
    if sum(row["sample_size"] is None for row in prevalence_rows) != 3:
        raise RuntimeError("Expected three grouped HCC rows without standalone sample sizes")

    examples = common_examples()
    coefficients = common_coefficients(prevalence_rows)
    population = simulate_population(prevalence_rows)

    write_csv(
        DATA_DIR / "v28_to_lp1_common_examples.csv",
        ["case", "hccs", "v28_score", "lp1_score", "absolute_change", "percent_change"],
        examples,
    )
    write_csv(
        DATA_DIR / "v28_to_lp1_common_hcc_coefficients.csv",
        ["hcc", "hcc_label", "short_label", "sample_size", "prevalence", "v28_coefficient", "lp1_coefficient", "absolute_change"],
        coefficients,
    )
    write_csv(
        DATA_DIR / "v28_to_lp1_mock_population.csv",
        ["segment", "label", "assumed_weight", "profiles", "mean_v28", "mean_lp1", "mean_change", "percent_change", "paired_delta_ci_low", "paired_delta_ci_high"],
        population,
    )

    save_example_chart(examples)
    save_coefficient_chart(coefficients)
    save_population_chart(population)

    print(f"source_hccs={len(prevalence_rows)} denominator={REPORT_DENOMINATOR}")
    print(f"profiles_per_segment={SIMULATED_HCC_PROFILES} seed={SIMULATION_SEED}")
    for row in population:
        print(
            f"{row['segment']}: V28={row['mean_v28']:.4f} "
            f"LP1={row['mean_lp1']:.4f} change={row['percent_change']:+.1f}%"
        )


if __name__ == "__main__":
    main()
