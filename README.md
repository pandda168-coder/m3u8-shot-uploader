# m3u8-shot-uploader

A reusable OpenClaw skill for processing one or more `m3u8` video URLs into screenshot assets.

It does the whole pipeline:

- parse the relative `m3u8` path and `videoId`
- download the video with `ffmpeg`
- extract random screenshots
- batch upload screenshots to an image API
- call a second API to save screenshot metadata
- print final success and failure counts for batch runs

## Repository layout

```text
m3u8-shot-uploader/
├── .gitignore
├── SKILL.md
├── references/
│   ├── env-example.txt
│   └── local-config.example.env
└── scripts/
    └── main.py
```

## Configuration strategy

This repo separates public examples from private operations config:

- `references/env-example.txt`: safe public example for docs and open-source distribution
- `references/local-config.example.env`: local operations template for private runtime values
- `.env` or `.env.local`: your real local config, ignored by git

## Recommended config shape

Use one shared API base URL plus per-endpoint routes:

```env
COMMON_API_BASE_URL=https://example-api.example.com/api/web
WEB_ORIGIN=https://example-api.example.com
M3U8_API_ROUTE=/admin/vid/m3u8
UPLOAD_API_ROUTE=/admin/vid/uploadStaticBatch
UPDATE_API_ROUTE=/admin/vid/upload/screenshots
```

If one endpoint does not follow the shared base, override it directly with:

- `UPLOAD_API_URL`
- `UPDATE_API_URL`

## What the skill is for

Use this skill when you need to automate an admin workflow like:

1. receive one or more `m3u8` links or relative paths
2. convert each video into 10 random screenshots
3. upload those screenshots to a configured file service
4. submit the uploaded `filePath` array back to a business API

It is especially useful when the update API expects the relative `m3u8` path instead of the full signed URL.

## Requirements

- Python 3
- `ffmpeg`
- `ffprobe`
- valid API credentials or cookies

## Usage

Single URL:

```bash
python3 m3u8-shot-uploader/scripts/main.py \
  --m3u8-url 'https://example.com/path/video.m3u8?token=xxx'
```

Multiple URLs:

```bash
python3 m3u8-shot-uploader/scripts/main.py \
  --m3u8-url 'https://example.com/a.m3u8?token=xxx' \
  --m3u8-url 'https://example.com/b.m3u8?token=yyy'
```

From file:

```bash
python3 m3u8-shot-uploader/scripts/main.py --input-file ./urls.txt
```

## Output

The script prints a JSON summary like this:

```json
{
  "total": 2,
  "successCount": 2,
  "failedCount": 0,
  "results": []
}
```

Each item in `results` contains either:

- a full success payload with `videoId`, `relativePath`, `filePath`, and API responses
- or a failure payload with the original `m3u8Url` and an `error`

## Notes

- Do not commit live cookies or tokens.
- Keep local runtime config in `.env` or `.env.local`.
- The update API payload may fail if you send the full signed URL instead of the relative `m3u8` path.
- Batch mode processes URLs sequentially and reports aggregate counts at the end.
