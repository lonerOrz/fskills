#!/usr/bin/env python3
"""parity_check.py — differential/golden test harness for a Rust migration.

The old implementation is the oracle. This runs the OLD and NEW commands over the same
corpus of inputs and reports every mismatch, so you can prove behavior parity BEFORE you
cut over (see references/verification.md). No third-party dependencies.

Two modes:

  1. Live differential — run both commands, diff their outputs:

       ./parity_check.py \
         --old "python legacy/cli.py" \
         --new "./target/release/mytool" \
         --inputs corpus/

  2. Golden — record the oracle once, then check the new impl against the recording:

       ./parity_check.py --old "python legacy/cli.py" --inputs corpus/ --record golden/
       ./parity_check.py --new "./target/release/mytool" --inputs corpus/ --check  golden/

Each input file is passed on stdin; its captured stdout is the output under comparison.
Adapt run_command / normalize below for argv-based tools, JSON tolerance, float epsilon,
or library (non-CLI) calls — those are the parts you are expected to tune per project.
"""
from __future__ import annotations

import argparse
import difflib
import json
import shlex
import subprocess
import sys
from pathlib import Path


def run_command(command: str, input_bytes: bytes, timeout: float) -> bytes:
    """Run `command`, feeding input_bytes on stdin, returning stdout bytes.

    Adapt this if your tool takes the input as an argv path instead of stdin, or if you
    need to compare stderr / exit codes too.
    """
    proc = subprocess.run(
        shlex.split(command),
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if proc.returncode != 0:
        # A nonzero exit is itself behavior — surface it rather than hiding it.
        return b"<<exit %d>>\n%s" % (proc.returncode, proc.stderr)
    return proc.stdout


def normalize(output: bytes, json_mode: bool) -> str:
    """Canonicalize output so *acceptable* nondeterminism doesn't count as a mismatch.

    Decide deliberately what is acceptable (dict/key ordering, whitespace) vs a real bug
    (a different number). In --json mode, dict key order is canonicalized. Extend this for
    timestamps, RNG, or float tolerance as your data requires.
    """
    text = output.decode("utf-8", errors="replace")
    if json_mode:
        try:
            return json.dumps(json.loads(text), sort_keys=True, indent=2)
        except json.JSONDecodeError:
            pass  # not JSON; fall through to raw text
    return text.strip("\n")


def iter_inputs(inputs_dir: Path):
    for path in sorted(inputs_dir.rglob("*")):
        if path.is_file():
            yield path


def main() -> int:
    ap = argparse.ArgumentParser(description="Differential/golden parity harness for Rust migration.")
    ap.add_argument("--old", help="Command for the OLD/oracle implementation (stdin -> stdout).")
    ap.add_argument("--new", help="Command for the NEW Rust implementation (stdin -> stdout).")
    ap.add_argument("--inputs", required=True, type=Path, help="Directory of input files (each fed on stdin).")
    ap.add_argument("--record", type=Path, help="Golden mode: record --old outputs into this directory.")
    ap.add_argument("--check", type=Path, help="Golden mode: check --new outputs against this directory.")
    ap.add_argument("--json", action="store_true", help="Treat outputs as JSON and ignore key ordering.")
    ap.add_argument("--timeout", type=float, default=30.0, help="Per-run timeout in seconds (default 30).")
    ap.add_argument("--max-diff-lines", type=int, default=40, help="Max diff lines to print per mismatch.")
    args = ap.parse_args()

    if not args.inputs.is_dir():
        print(f"error: --inputs '{args.inputs}' is not a directory", file=sys.stderr)
        return 2

    inputs = list(iter_inputs(args.inputs))
    if not inputs:
        print(f"error: no input files found under {args.inputs}", file=sys.stderr)
        return 2

    mismatches = 0
    errors = 0
    checked = 0

    for path in inputs:
        data = path.read_bytes()
        rel = path.relative_to(args.inputs)

        # ---- Golden record: capture oracle output to disk, then continue. ----
        if args.record:
            if not args.old:
                print("error: --record requires --old", file=sys.stderr)
                return 2
            try:
                out = run_command(args.old, data, args.timeout)
            except Exception as exc:  # noqa: BLE001 - report and keep going
                print(f"[ERROR] {rel}: old command failed: {exc}", file=sys.stderr)
                errors += 1
                continue
            dest = args.record / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(out)
            checked += 1
            continue

        # ---- Resolve the two sides to compare. ----
        try:
            if args.check:
                if not args.new:
                    print("error: --check requires --new", file=sys.stderr)
                    return 2
                golden_path = args.check / rel
                if not golden_path.exists():
                    print(f"[SKIP]  {rel}: no golden file recorded", file=sys.stderr)
                    continue
                left = normalize(golden_path.read_bytes(), args.json)
                right = normalize(run_command(args.new, data, args.timeout), args.json)
                left_label, right_label = "golden(old)", "new"
            else:
                if not (args.old and args.new):
                    print("error: live mode requires both --old and --new", file=sys.stderr)
                    return 2
                left = normalize(run_command(args.old, data, args.timeout), args.json)
                right = normalize(run_command(args.new, data, args.timeout), args.json)
                left_label, right_label = "old", "new"
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {rel}: {exc}", file=sys.stderr)
            errors += 1
            continue

        checked += 1
        if left == right:
            continue

        mismatches += 1
        print(f"\n[MISMATCH] {rel}")
        diff = difflib.unified_diff(
            left.splitlines(), right.splitlines(),
            fromfile=left_label, tofile=right_label, lineterm="",
        )
        for i, line in enumerate(diff):
            if i >= args.max_diff_lines:
                print(f"  ... (diff truncated at {args.max_diff_lines} lines)")
                break
            print(f"  {line}")

    # ---- Summary. ----
    print("\n" + "=" * 60)
    if args.record:
        print(f"Recorded {checked} golden outputs to {args.record}")
        return 0 if errors == 0 else 1
    print(f"Checked {checked} inputs: {mismatches} mismatch(es), {errors} error(s)")
    if mismatches == 0 and errors == 0:
        print("PARITY OK — new implementation matches the oracle on this corpus.")
        return 0
    print("PARITY FAILED — investigate before cutover (see references/verification.md).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
