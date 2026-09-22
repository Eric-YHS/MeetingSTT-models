# MeetingSTT-models

Public model assets used by **MeetingSTT** for local ASR (automatic speech
recognition) downloads. This repository holds the published artefacts and the
manifest that describes them, so MeetingSTT clients can download and verify a
model without bundling gigabytes of weights in the application package.

## Layout

```text
MeetingSTT-models/
├── manifest.json          # machine-readable description of every release
├── models/                # model archives, one file per release
│   └── <model-id>/<version>/<file>
└── README.md
```

## Manifest format

`manifest.json` maps a model id to the released versions of that model:

```json
{
  "schema_version": 1,
  "models": [
    {
      "id": "sensevoice-small",
      "display_name": "SenseVoice Small",
      "task": "asr",
      "language": ["zh", "en"],
      "latest": "2026.04",
      "versions": [
        {
          "version": "2026.04",
          "assets": [
            {
              "filename": "sensevoice-small-2026.04.zip",
              "url": "https://github.com/Eric-YHS/MeetingSTT-models/releases/download/sensevoice-small-2026.04/sensevoice-small-2026.04.zip",
              "sha256": "<64 hex characters>",
              "size_bytes": 0,
              "unpack_dir": "sensevoice-small"
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

See [`manifest.example.json`](manifest.example.json) for a copy-paste starting
point.

## Adding a model release

1. Build the model package and zip it (one top-level directory inside the zip).
2. Publish the zip as a GitHub Release asset named
   `<model-id>-<version>/<model-id>-<version>.zip`.
3. Compute the digest and size:
   ```bash
   sha256sum model.zip
   stat -c %s model.zip   # Linux
   stat -f %z model.zip   # macOS
   ```
4. Add a new entry to `manifest.json` (keep older versions listed so installed
   clients keep working) and update `latest`.
5. Validate the JSON before pushing:
   ```bash
   python3 -m json.tool manifest.json > /dev/null && echo OK
   ```

## Notes

- Binary weights are kept out of the working tree and served from GitHub
  Releases; this keeps `git clone` cheap.
- Never overwrite a published version: bump the version instead, otherwise a
  client that already verified the old digest will fail.
