# MeetingSTT-models

[![Validate manifest](https://img.shields.io/github/actions/workflow/status/Eric-YHS/MeetingSTT-models/validate.yml?label=manifest)](https://github.com/Eric-YHS/MeetingSTT-models/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Public model assets used by **MeetingSTT** for local ASR (automatic speech
recognition) downloads. This repository holds the manifest that describes every
release plus the tooling that generates and validates it, so MeetingSTT clients
can download and verify a model without bundling gigabytes of weights in the
application package. The weights themselves live on the GitHub Releases of this
repository.

## Published models

| Model id | What it is | Version | Download size |
| --- | --- | --- | --- |
| `large-v3` | Whisper large-v3 | `v1.0.0` | 2.85 GB (2 parts) |
| `turbo` | Whisper large-v3-turbo | `v1.0.0` | 1.49 GB |
| `medium.en` | Whisper medium.en (English) | `v1.0.0` | 1.41 GB |
| `small` | Whisper small | `v1.0.0` | 0.45 GB |

## Layout

```text
MeetingSTT-models/
├── manifest.json          # machine-readable description of every release (generated)
├── manifest.example.json  # hand-written example showing the schema
├── scripts/
│   ├── build_manifest.py  # regenerates manifest.json from the GitHub Releases API
│   └── validate_manifest.py
└── README.md
```

## Generating the manifest

`manifest.json` is generated, never hand-edited — GitHub already reports the exact
byte length and `sha256` digest of every release asset:

```bash
python3 scripts/build_manifest.py            # rewrite manifest.json from the live releases
python3 scripts/build_manifest.py --check    # fail if manifest.json no longer matches the releases
```

`--check` is what CI runs, so a re-uploaded asset that changed bytes (or a release
published without regenerating the manifest) fails the build instead of silently
breaking every client's digest verification.

Asset file names are parsed as `MeetingSTT-model-<variant>-<tag>.zip`; `<variant>`
becomes the model id. Any variant not listed in `MODEL_META` in the script still
works, it just gets the raw variant token as its display name.

## Manifest format

`manifest.json` maps a model id to the released versions of that model. Asset file
names follow `MeetingSTT-model-<variant>-<tag>.zip` and the release tag doubles as
the version:

```json
{
  "schema_version": 1,
  "models": [
    {
      "id": "small",
      "display_name": "Whisper small",
      "task": "asr",
      "language": ["zh", "en"],
      "latest": "v1.0.0",
      "versions": [
        {
          "version": "v1.0.0",
          "assets": [
            {
              "filename": "MeetingSTT-model-small-v1.0.0.zip",
              "url": "https://github.com/Eric-YHS/MeetingSTT-models/releases/download/v1.0.0/MeetingSTT-model-small-v1.0.0.zip",
              "sha256": "<64 hex characters>",
              "size_bytes": 446457149,
              "unpack_dir": "MeetingSTT-model-small"
            }
          ]
        }
      ]
    }
  ]
}
```

Required fields per asset: `filename`, `url`, `sha256`, `size_bytes`.
A client must reject an asset whose downloaded digest or length differs from
the manifest.

A version whose package is too large for a single upload is published as several
`*.partNN.zip` assets. They stay a list inside one version, ordered by part
number: the client downloads them in the listed order, concatenates them and
unzips the result (`cat …part01.zip …part02.zip > model.zip && unzip model.zip`).
That is currently the case for `large-v3`.

See [`manifest.example.json`](manifest.example.json) for a copy-paste starting
point.

## Adding a model release

1. Build the model package and zip it (one top-level directory inside the zip).
2. Publish the zip as a GitHub Release asset named
   `MeetingSTT-model-<variant>-<tag>.zip` (split packages use
   `MeetingSTT-model-<variant>-<tag>.part01.zip`, `.part02.zip`, …).
3. Regenerate the manifest and validate it before pushing:
   ```bash
   python3 scripts/build_manifest.py            # reads digests from the release API
   python3 scripts/validate_manifest.py manifest.json
   ```
   (Manual alternative: `sha256sum model.zip` and `stat -c %s model.zip`, then add
   the entry by hand. Keep older versions listed so installed clients keep working.)
4. Never overwrite a published version: bump the version instead, otherwise a
   client that already verified the old digest will fail.

## License

The manifest, the tooling and the documentation in this repository are MIT
licensed (see [`LICENSE`](LICENSE)). The model weights they point at are **not**
covered: they stay under the license of their upstream authors (the published
assets are Whisper checkpoints).

## Notes

- Binary weights are kept out of the working tree and served from GitHub
  Releases; this keeps `git clone` cheap.
- `manifest.json` must match the live release assets byte for byte; CI enforces it.
- Never overwrite a published version: bump the version instead, otherwise a
  client that already verified the old digest will fail.
