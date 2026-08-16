#!/usr/bin/env python3
"""Safely patch Clash Verge Rev for coexistence with a corporate VPN."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from datetime import datetime


DEFAULT_ROOT = Path.home() / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"


def replace_scalar(text: str, key: str, value: str) -> tuple[str, bool]:
    pattern = re.compile(rf"(?m)^(\s*{re.escape(key)}:\s*).*$")
    updated, count = pattern.subn(lambda match: f"{match.group(1)}{value}", text)
    return updated, count > 0 and updated != text


def ensure_dns_mode(text: str) -> tuple[str, bool]:
    updated, changed = replace_scalar(text, "enhanced-mode", "redir-host")
    if changed or re.search(r"(?m)^\s*enhanced-mode:\s*redir-host\s*$", updated):
        return updated, changed

    dns_match = re.search(r"(?m)^dns:\s*$", text)
    if dns_match:
        insertion = dns_match.end()
        return text[:insertion] + "\n  enhanced-mode: redir-host" + text[insertion:], True

    suffix = "" if text.endswith("\n") else "\n"
    return text + suffix + "\ndns:\n  enhanced-mode: redir-host\n", True


def infer_merge_file(root: Path) -> Path | None:
    profiles_file = root / "profiles.yaml"
    if not profiles_file.exists():
        return None
    text = profiles_file.read_text(encoding="utf-8")
    current_match = re.search(r"(?m)^current:\s*([^\s#]+)", text)
    if not current_match:
        return None
    current = re.escape(current_match.group(1))
    block_match = re.search(rf"(?ms)^- uid:\s*{current}\s*$.*?(?=^- uid:|\Z)", text)
    if not block_match:
        return None
    merge_match = re.search(r"(?m)^\s+merge:\s*([^\s#]+)", block_match.group(0))
    if not merge_match:
        return None
    merge_uid = re.escape(merge_match.group(1))
    merge_block = re.search(rf"(?ms)^- uid:\s*{merge_uid}\s*$.*?(?=^- uid:|\Z)", text)
    if not merge_block:
        return None
    file_match = re.search(r"(?m)^\s+file:\s*(.+?)\s*$", merge_block.group(0))
    if not file_match:
        return None
    return root / "profiles" / file_match.group(1).strip("'\"")


def atomic_write(path: Path, content: str) -> None:
    mode = path.stat().st_mode
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_name = handle.name
    os.chmod(temp_name, mode)
    os.replace(temp_name, path)


def plan_changes(root: Path, merge_file: Path | None) -> dict[Path, tuple[str, str, str]]:
    changes: dict[Path, tuple[str, str, str]] = {}
    verge = root / "verge.yaml"
    if not verge.exists():
        raise FileNotFoundError(f"Missing Clash Verge settings: {verge}")
    old = verge.read_text(encoding="utf-8")
    new, changed = replace_scalar(old, "enable_system_proxy", "false")
    if changed:
        changes[verge] = (old, new, "disable Clash system proxy")

    candidates = [root / "clash-verge.yaml", root / "clash-verge-check.yaml", root / "dns_config.yaml"]
    if merge_file:
        candidates.append(merge_file)
    for path in candidates:
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        new, changed = ensure_dns_mode(old)
        if changed:
            changes[path] = (old, new, "set DNS enhanced-mode to redir-host")
    return changes


def make_backup(root: Path, files: list[Path]) -> Path:
    backup = root / "codex-backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    manifest: list[str] = []
    for path in files:
        relative = path.relative_to(root)
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        manifest.append(str(relative))
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return backup


def rollback(root: Path, backup: Path) -> None:
    manifest_file = backup / "manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Invalid backup: {manifest_file} is missing")
    members = json.loads(manifest_file.read_text(encoding="utf-8"))
    for relative_text in members:
        relative = Path(relative_text)
        source = backup / relative
        destination = root / relative
        if not source.exists():
            raise FileNotFoundError(f"Backup member missing: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    print(f"Restored {len(members)} files from {backup}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--merge-file", type=Path, help="Absolute path or path relative to config root")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="Create a backup and write changes")
    action.add_argument("--rollback", type=Path, help="Restore a backup created by this script")
    args = parser.parse_args()

    root = args.config_root.expanduser().resolve()
    if sys.platform != "darwin" and root == DEFAULT_ROOT.resolve():
        print("This script targets macOS. Pass --config-root only for fixture testing.", file=sys.stderr)
        return 2
    if args.rollback:
        rollback(root, args.rollback.expanduser().resolve())
        return 0

    merge_file = args.merge_file
    if merge_file and not merge_file.is_absolute():
        merge_file = root / merge_file
    if not merge_file:
        merge_file = infer_merge_file(root)

    changes = plan_changes(root, merge_file)
    print(f"Config root: {root}")
    print(f"Active merge: {merge_file if merge_file else 'not detected'}")
    if not changes:
        print("No changes needed.")
        return 0
    for path, (_, _, reason) in changes.items():
        print(f"PLAN {path.relative_to(root)}: {reason}")
    if not args.apply:
        print("Dry run only. Re-run with --apply after explicit user confirmation.")
        return 0

    backup = make_backup(root, list(changes))
    for path, (_, new, _) in changes.items():
        atomic_write(path, new)
    print(f"Applied {len(changes)} changes.")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
