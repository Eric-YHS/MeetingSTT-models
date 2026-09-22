#!/usr/bin/env python3
"""Validate a MeetingSTT model manifest.

Checks structural rules that the MeetingSTT downloader relies on:

* required keys are present on every model, version and asset;
* ``sha256`` values are 64 lowercase hex characters;
* ``size_bytes`` is a positive integer;
* ``latest`` matches one of the declared versions;
* model ids are unique and version strings are unique per model.

Usage:
    python3 scripts/validate_manifest.py [manifest.json]

Exits with status 0 when the manifest is valid, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

MODEL_KEYS = ("id", "display_name", "task", "latest", "versions")
VERSION_KEYS = ("version", "assets")
ASSET_KEYS = ("filename", "url", "sha256", "size_bytes")


def check_asset(asset: dict, where: str, errors: list[str]) -> None:
    for key in ASSET_KEYS:
        if key not in asset:
            errors.append(f"{where}: missing key '{key}'")
    digest = asset.get("sha256")
    if isinstance(digest, str) and not SHA256_RE.match(digest):
        errors.append(f"{where}: sha256 must be 64 lowercase hex chars, got {digest!r}")
    size = asset.get("size_bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        errors.append(f"{where}: size_bytes must be a positive integer, got {size!r}")
    url = asset.get("url")
    if isinstance(url, str) and not url.startswith(("https://", "http://")):
        errors.append(f"{where}: url must be an http(s) URL")


def check_version(version: dict, where: str, errors: list[str]) -> None:
    for key in VERSION_KEYS:
        if key not in version:
            errors.append(f"{where}: missing key '{key}'")
    assets = version.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append(f"{where}: assets must be a non-empty list")
        return
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            errors.append(f"{where}: asset #{index} must be an object")
            continue
        check_asset(asset, f"{where}/asset[{index}]", errors)


def check_model(model: dict, errors: list[str]) -> None:
    model_id = model.get("id", "<no-id>")
    for key in MODEL_KEYS:
        if key not in model:
            errors.append(f"model {model_id}: missing key '{key}'")
    versions = model.get("versions")
    if not isinstance(versions, list) or not versions:
        errors.append(f"model {model_id}: versions must be a non-empty list")
        return
    seen = set()
    for index, version in enumerate(versions):
        if not isinstance(version, dict):
            errors.append(f"model {model_id}: version #{index} must be an object")
            continue
        label = str(version.get("version", f"#{index}"))
        if label in seen:
            errors.append(f"model {model_id}: duplicate version '{label}'")
        seen.add(label)
        check_version(version, f"model {model_id}/version[{label}]", errors)
    if model.get("latest") not in seen:
        errors.append(
            f"model {model_id}: latest={model.get('latest')!r} is not declared in versions"
        )


def validate(manifest: dict) -> list[str]:
    errors: list[str] = []
    if "schema_version" not in manifest:
        errors.append("manifest: missing key 'schema_version'")
    models = manifest.get("models")
    if not isinstance(models, list) or not models:
        errors.append("manifest: models must be a non-empty list")
        return errors
    ids = set()
    for model in models:
        if not isinstance(model, dict):
            errors.append("manifest: every model entry must be an object")
            continue
        model_id = model.get("id")
        if model_id in ids:
            errors.append(f"manifest: duplicate model id '{model_id}'")
        ids.add(model_id)
        check_model(model, errors)
    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path("manifest.json")
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 1
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: {path} is not valid JSON: {exc}", file=sys.stderr)
        return 1
    errors = validate(manifest)
    if errors:
        for error in errors:
            print(f"invalid: {error}", file=sys.stderr)
        return 1
    models = manifest.get("models", [])
    total = sum(len(m.get("versions", [])) for m in models)
    print(f"{path}: OK ({len(models)} models, {total} versions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
