#!/usr/bin/env python3
"""Generate (or check) ``manifest.json`` from the GitHub Releases of this repo.

The release assets are the single source of truth: GitHub already exposes the
exact byte length and a ``sha256`` digest for every release asset, so the
manifest never has to be maintained by hand.

    python3 scripts/build_manifest.py                       # write ./manifest.json
    python3 scripts/build_manifest.py --check               # fail if manifest.json is stale
    python3 scripts/build_manifest.py --tag v1.0.0 --out -  # print to stdout

Assets are grouped into models by their file name:

    MeetingSTT-model-<variant>-<version>.zip                -> one asset
    MeetingSTT-model-<variant>-<version>.part01.zip, ...     -> split package, parts in order

Split packages stay a *list* of assets inside one version (ordered by part
number): a client has to download them in the listed order, concatenate them and
unzip the result. Model id / display name / language / task come from
``MODEL_META`` below; anything published that is not listed there falls back to
the variant token itself, so a new release never breaks the generator.

Authentication is optional: set GITHUB_TOKEN to avoid the anonymous API limit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request

API = "https://api.github.com/repos/{repo}/releases"

# Asset naming: MeetingSTT-model-<variant>-<version>.(part01.)?zip
# The variant may itself contain dashes (large-v3), so the version part is anchored
# to the release-tag shape ('v' + digits) instead of being matched lazily.
ASSET_RE = re.compile(
    r"^MeetingSTT-model-(?P<variant>.+)-(?P<version>v\d[\w.\-]*)"
    r"(?:\.part(?P<part>\d+))?\.zip$"
)

# Optional presentation metadata per variant token. Unknown variants still work.
MODEL_META: dict[str, dict] = {
    "large-v3": {"display_name": "Whisper large-v3"},
    "medium.en": {"display_name": "Whisper medium.en", "language": ["en"]},
    "small": {"display_name": "Whisper small"},
    "turbo": {"display_name": "Whisper large-v3-turbo"},
}
DEFAULT_META = {"display_name": None, "language": ["zh", "en"], "task": "asr"}


def fetch(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def sha256_of(asset: dict) -> str:
    digest = asset.get("digest") or ""
    if digest.startswith("sha256:"):
        return digest.split(":", 1)[1]
    raise ValueError(
        f"{asset['name']}: GitHub did not report a sha256 digest; "
        "compute it manually before publishing"
    )


def build(repo: str, tags: list[str]) -> dict:
    releases = fetch(f"{API.format(repo=repo)}")
    if tags:
        releases = [r for r in releases if r["tag_name"] in tags]

    # variant -> version -> [asset descriptors]  (a version may span several releases)
    grouped: dict[str, dict[str, list[dict]]] = {}
    for release in releases:
        if release.get("draft"):
            continue
        for asset in release.get("assets", []):
            match = ASSET_RE.match(asset["name"])
            if not match:
                print(f"warning: skipping unrecognised asset {asset['name']}", file=sys.stderr)
                continue
            variant = match.group("variant")
            # Version comes from the release tag so that split parts of one release
            # always land in the same version entry.
            version = release["tag_name"]
            entry = {
                "filename": asset["name"],
                "url": asset["browser_download_url"],
                "sha256": sha256_of(asset),
                "size_bytes": asset["size"],
                "_order": int(match.group("part") or 0),
            }
            grouped.setdefault(variant, {}).setdefault(version, []).append(entry)

    models = []
    for variant in sorted(grouped):
        meta = {**DEFAULT_META, **MODEL_META.get(variant, {})}
        versions = []
        for version in sorted(grouped[variant]):
            assets = sorted(grouped[variant][version], key=lambda a: a["_order"])
            for asset in assets:
                asset.pop("_order")
                asset["unpack_dir"] = f"MeetingSTT-model-{variant}"
            versions.append({"version": version, "assets": assets})
        models.append(
            {
                "id": variant,
                "display_name": meta["display_name"] or variant,
                "task": meta["task"],
                "language": meta["language"],
                "latest": versions[-1]["version"],
                "versions": versions,
            }
        )
    return {"schema_version": 1, "models": models}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="Eric-YHS/MeetingSTT-models")
    parser.add_argument("--tag", action="append", help="only include this tag (repeatable)")
    parser.add_argument("--out", default="manifest.json", help="output path, '-' for stdout")
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare the generated manifest with the committed one and fail on drift",
    )
    args = parser.parse_args()

    manifest = build(args.repo, args.tag or [])
    rendered = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            args.out if args.out != "-" else "manifest.json")
        if not os.path.exists(path):
            print(f"error: {path} does not exist", file=sys.stderr)
            return 1
        current = open(path, encoding="utf-8").read()
        if json.loads(current) != manifest:
            print(f"error: {path} does not match the published release assets", file=sys.stderr)
            print("run: python3 scripts/build_manifest.py", file=sys.stderr)
            return 1
        n = len(manifest["models"])
        print(f"{path}: up to date with {args.repo} releases ({n} models)")
        return 0

    if args.out == "-":
        sys.stdout.write(rendered)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        models = ", ".join(m["id"] for m in manifest["models"])
        print(f"wrote {args.out}: {len(manifest['models'])} models ({models})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
