#!/usr/bin/env python3
"""Check literal references in simple CI run commands, without executing them."""

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

DYNAMIC = re.compile(r"[$`*?\[\]{}~]")
CONTROL = {
    "if",
    "then",
    "elif",
    "else",
    "fi",
    "for",
    "while",
    "until",
    "case",
    "esac",
    "do",
    "done",
    "function",
    "cd",
    "pushd",
    "popd",
}
DISPLAY = {"echo", "printf"}


def mapping(value, context):
    if not isinstance(value, dict):
        raise ValueError(f"{context}: expected a YAML mapping")
    return value


def working_directory(value, fallback="."):
    defaults = mapping(value.get("defaults", {}), "defaults")
    return mapping(defaults.get("run", {}), "defaults.run").get("working-directory", fallback)


def commands(run):
    """Tokenize only simple logical lines; never interpret substitutions or control flow."""
    lines = run.replace("\\\n", " ").splitlines()
    parsed = []
    for line in lines:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        words = list(lexer)
        if words:
            parsed.append(words)
    # Never reinterpret an unsupported block or continued compound command's body.
    if any(
        words[0] in CONTROL
        or any("<<" in word for word in words)
        or any(word in {"{", "}", "(", ")", "()"} for word in words)
        or words[0] in {"&&", "||", "|"}
        or words[-1] in {"&&", "||", "|"}
        for words in parsed
    ):
        return [None]
    result = []
    for words in parsed:
        if (
            "=" in words[0]
            or any(DYNAMIC.search(word) for word in words)
            or any(word and set(word) <= set("();<>|&") for word in words)
            or (words[0] == "just" and (len(words) < 2 or words[1].startswith("-")))
        ):
            result.append(None)
        elif words[0] not in DISPLAY:
            result.append(words)
    return result


def check(root):
    dump = subprocess.run(
        ["just", "--justfile", str(root / "justfile"), "--dump", "--dump-format", "json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    namespace = json.loads(dump.stdout)
    recipes = set(namespace["recipes"]) | set(namespace["aliases"])
    folder = root / ".github/workflows"
    workflows = sorted([*folder.glob("*.yml"), *folder.glob("*.yaml")])
    if not workflows:
        raise ValueError("no workflow YAML files found")
    findings, checked, skipped = [], 0, 0
    for path in workflows:
        data = mapping(yaml.safe_load(path.read_text()), str(path))
        for job_id, job in mapping(data.get("jobs"), f"{path}:jobs").items():
            job = mapping(job, f"{path}:{job_id}")
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                raise ValueError(f"{path}:{job_id}: steps must be a list")
            for ordinal, step in enumerate(steps, 1):
                step = mapping(step, f"{path}:{job_id}:step {ordinal}")
                if "run" not in step:
                    continue
                context = f"{path.relative_to(root)}:{job_id}:step {ordinal}"
                run = step["run"]
                directory = step.get("working-directory", working_directory(job, working_directory(data)))
                if not isinstance(run, str) or not isinstance(directory, str):
                    raise ValueError(f"{context}: run and working-directory must be strings")
                if DYNAMIC.search(directory):
                    skipped += 1
                    continue
                for words in commands(run):
                    if words is None:
                        skipped += 1
                        continue
                    checked += 1
                    if words[0] == "just" and words[1] not in recipes:
                        findings.append(f"{context}: missing just recipe {words[1]!r}")
                    for word in words[1:]:
                        candidate = word.split("=", 1)[-1] if word.startswith("-") else word
                        if (
                            candidate.startswith(("config/", "./config/"))
                            and not (root / directory / candidate).exists()
                        ):
                            findings.append(
                                f"{context}: missing config path {candidate!r} (working-directory {directory!r})"
                            )
    return findings, checked, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        findings, checked, skipped = check(args.root.resolve())
    except (OSError, ValueError, KeyError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        print(f"[CI_REFERENCES_INVALID] {exc}", file=sys.stderr)
        return 1
    for finding in findings:
        print(f"[CI_REFERENCE_MISSING] {finding}", file=sys.stderr)
    print(f"[CI_REFERENCES: checked={checked} skipped={skipped} errors={len(findings)}]")
    if skipped:
        print("[CI_REFERENCES: skipped commands are unverified dynamic or unsupported shell forms]")
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
