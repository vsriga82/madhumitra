"""
MadhuMitra — Protocol Validator
--------------------------------
Checks that taxonomy_v1.md and protocol_rules.yaml are in sync.
Runs automatically when the app starts.
If versions don't match, the app refuses to run.

Usage:
    python validate_protocol.py
"""

import yaml
import re
import sys
from pathlib import Path


RULES_FILE    = Path(__file__).parent / "protocol_rules.yaml"
TAXONOMY_FILE = Path(__file__).parent / "taxonomy_v1.md"


def get_rules_version(rules_path: Path) -> str:
    """Read version from protocol_rules.yaml"""
    with open(rules_path, "r") as f:
        rules = yaml.safe_load(f)
    return rules["meta"]["version"]


def get_taxonomy_version(taxonomy_path: Path) -> str:
    """
    Read version from taxonomy_v1.md.
    Looks for the line: | Version | v1.0 | in the header table.
    """
    with open(taxonomy_path, "r") as f:
        content = f.read()

    # Look for: | Version | v1.0 |
    match = re.search(r"\|\s*Version\s*\|\s*([\d.]+)\s*\|", content)
    if not match:
        raise ValueError(
            f"Could not find version in {taxonomy_path}. "
            "Make sure the header table contains a 'Version' row."
        )
    return match.group(1)


def get_approval_status(rules_path: Path) -> dict:
    """Check if the protocol has been approved by a doctor."""
    with open(rules_path, "r") as f:
        rules = yaml.safe_load(f)

    meta = rules.get("meta", {})
    return {
        "approved_by": meta.get("approved_by"),
        "clinic":      meta.get("clinic"),
        "status":      meta.get("status"),
    }


def validate_protocol() -> bool:
    """
    Main validation function.
    Returns True if everything is valid, raises SystemExit if not.
    """
    print("\n─────────────────────────────────────")
    print("  MadhuMitra — Protocol Validator")
    print("─────────────────────────────────────")

    errors   = []
    warnings = []

    # ── 1. Check files exist ──────────────────────────
    if not RULES_FILE.exists():
        errors.append(f"Missing file: {RULES_FILE}")

    if not TAXONOMY_FILE.exists():
        errors.append(f"Missing file: {TAXONOMY_FILE}")

    if errors:
        for e in errors:
            print(f"  ✗  {e}")
        print("\n  App cannot start. Fix the errors above.\n")
        sys.exit(1)

    # ── 2. Read versions ──────────────────────────────
    try:
        rules_version    = get_rules_version(RULES_FILE)
        taxonomy_version = get_taxonomy_version(TAXONOMY_FILE)
    except Exception as e:
        print(f"  ✗  Could not read versions: {e}")
        sys.exit(1)

    print(f"\n  protocol_rules.yaml  → version {rules_version}")
    print(f"  taxonomy_v1.md       → version {taxonomy_version}")

    # ── 3. Check versions match ───────────────────────
    if rules_version != taxonomy_version:
        print(f"\n  ✗  VERSION MISMATCH")
        print(f"     rules={rules_version}, taxonomy={taxonomy_version}")
        print(f"\n     These files are out of sync.")
        print(f"     Update the version number in both files to match,")
        print(f"     then get doctor sign-off before restarting.\n")
        sys.exit(1)

    print(f"\n  ✓  Versions match ({rules_version})")

    # ── 4. Check approval status ──────────────────────
    approval = get_approval_status(RULES_FILE)

    if approval["status"] == "draft":
        warnings.append(
            "Protocol status is DRAFT — doctor sign-off not yet recorded. "
            "Running in development mode only."
        )

    if approval["approved_by"] is None:
        warnings.append("No doctor approval recorded in protocol_rules.yaml.")

    if approval["clinic"] is None:
        warnings.append("No clinic name recorded in protocol_rules.yaml.")

    # ── 5. Print warnings ─────────────────────────────
    if warnings:
        print("\n  Warnings:")
        for w in warnings:
            print(f"  ⚠  {w}")

    # ── 6. Final status ───────────────────────────────
    if not warnings:
        print(f"  ✓  Approved by: {approval['approved_by']}")
        print(f"  ✓  Clinic: {approval['clinic']}")
        print(f"  ✓  Status: {approval['status']}")
        print(f"\n  Protocol is valid and approved. Safe to run.\n")
    else:
        print(f"\n  Protocol valid for development. Not approved for production.\n")

    print("─────────────────────────────────────\n")
    return True


# ── Run directly or import ────────────────────────────────────
if __name__ == "__main__":
    validate_protocol()
