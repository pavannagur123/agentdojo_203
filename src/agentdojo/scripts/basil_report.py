"""Create a machine-readable BASIL report from AgentDojo trace files."""

import argparse
import csv
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from agentdojo.approval.report import aggregate_traces, load_traces


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def _write_tcr_svg(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write a dependency-free TCR@k curve suitable for the project report."""

    series: dict[tuple[str, str], list[tuple[int, float]]] = defaultdict(list)
    for row in rows:
        if row.get("k") is None or row.get("tcr_at_k") is None:
            continue
        series[(str(row["attack_type"]), str(row["approval_policy"]))].append(
            (int(row["k"]), float(row["tcr_at_k"]))
        )

    width, height = 960, 600
    left, right, top, bottom = 90, 260, 55, 80
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum_k = max((point[0] for values in series.values() for point in values), default=1)
    maximum_k = max(maximum_k, 1)
    colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf"]

    def x_position(k: int) -> float:
        return left + plot_width * k / maximum_k

    def y_position(rate: float) -> float:
        return top + plot_height * (1.0 - rate)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="480" y="28" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold">Safe Task Completion at Escalation Budget k</text>',
    ]
    for step in range(6):
        rate = step / 5
        y = y_position(rate)
        svg.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" stroke="#dddddd"/>')
        svg.append(
            f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" font-family="Arial" font-size="12">{rate:.0%}</text>'
        )
    for k in range(maximum_k + 1):
        x = x_position(k)
        svg.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_height}" stroke="#eeeeee"/>')
        svg.append(
            f'<text x="{x:.1f}" y="{top + plot_height + 24}" text-anchor="middle" font-family="Arial" font-size="12">{k}</text>'
        )
    svg.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#222222" stroke-width="1.5"/>',
            f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#222222" stroke-width="1.5"/>',
            f'<text x="{left + plot_width / 2:.1f}" y="{height - 24}" text-anchor="middle" font-family="Arial" font-size="14">Escalation budget k</text>',
            f'<text x="24" y="{top + plot_height / 2:.1f}" text-anchor="middle" transform="rotate(-90 24 {top + plot_height / 2:.1f})" font-family="Arial" font-size="14">Safe task completion rate</text>',
        ]
    )
    for index, (label, points) in enumerate(sorted(series.items())):
        color = colors[index % len(colors)]
        points = sorted(set(points))
        coordinates = " ".join(f"{x_position(k):.1f},{y_position(rate):.1f}" for k, rate in points)
        if len(points) > 1:
            svg.append(f'<polyline points="{coordinates}" fill="none" stroke="{color}" stroke-width="3"/>')
        for k, rate in points:
            svg.append(f'<circle cx="{x_position(k):.1f}" cy="{y_position(rate):.1f}" r="5" fill="{color}"/>')
        legend_y = top + 22 * index
        svg.append(f'<line x1="{left + plot_width + 25}" y1="{legend_y}" x2="{left + plot_width + 52}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        svg.append(
            f'<text x="{left + plot_width + 60}" y="{legend_y + 5}" font-family="Arial" font-size="12">{html.escape(label[0])} / {html.escape(label[1])}</text>'
        )
    svg.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(svg))


def write_report_artifacts(
    trace_directory: Path,
    output: Path,
    summary_csv: Path | None = None,
    curve_csv: Path | None = None,
    curve_svg: Path | None = None,
    escalation_csv: Path | None = None,
) -> dict[str, Any]:
    report = aggregate_traces(load_traces(trace_directory))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True))
    if summary_csv is not None:
        _write_csv(summary_csv, report["summary"])
    if curve_csv is not None:
        _write_csv(curve_csv, report["tcr_curves"])
    if curve_svg is not None:
        _write_tcr_svg(curve_svg, report["tcr_curves"])
    if escalation_csv is not None:
        _write_csv(escalation_csv, report["escalation_value"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_directory", type=Path, help="AgentDojo runs directory")
    parser.add_argument("--output", type=Path, default=Path("basil-report.json"))
    parser.add_argument("--csv", type=Path, default=None, help="Optional summary CSV path")
    parser.add_argument("--curve-csv", type=Path, default=None, help="Optional TCR@k curve-data CSV path")
    parser.add_argument("--curve-svg", type=Path, default=None, help="Optional TCR@k SVG chart path")
    parser.add_argument("--escalation-csv", type=Path, default=None, help="Optional escalation-value CSV path")
    args = parser.parse_args()

    report = write_report_artifacts(
        args.trace_directory,
        args.output,
        args.csv,
        args.curve_csv,
        args.curve_svg,
        args.escalation_csv,
    )
    print(f"Analysed {report['trace_count']} traces; wrote {args.output}")


if __name__ == "__main__":
    main()
