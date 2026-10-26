"""Create a machine-readable BASIL report from AgentDojo trace files."""

import argparse
import csv
import json
from pathlib import Path

from agentdojo.approval.report import aggregate_traces, load_traces


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_directory", type=Path, help="AgentDojo runs directory")
    parser.add_argument("--output", type=Path, default=Path("basil-report.json"))
    parser.add_argument("--csv", type=Path, default=None, help="Optional summary CSV path")
    args = parser.parse_args()

    report = aggregate_traces(load_traces(args.trace_directory))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True))
    if args.csv is not None:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        rows = report["summary"]
        if rows:
            with args.csv.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
    print(f"Analysed {report['trace_count']} traces; wrote {args.output}")


if __name__ == "__main__":
    main()
