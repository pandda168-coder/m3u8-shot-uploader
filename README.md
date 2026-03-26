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
├── SKILL.md
├── references/
│   └── env-example.txt
└── scripts/
    └── main.py
```

## What the skill is for

Use this skill when you need to automate an admin workflow like:

1. receive one or more full `m3u8` links
2. convert each video into 10 random screenshots
3. upload those screenshots to a configured file service
4. submit the uploaded `filePath` array back to a business API

It is especially useful when the update API expects the relative `m3u8` path instead of the full signed URL.

## Requirements

- Python 3
- `ffmpeg`
- `ffprobe`
- valid API credentials or cookies

## Configuration

Copy `m3u8-shot-uploader/references/env-example.txt` to a local `.env` file and fill in your runtime values.

Important fields:

- `UPLOAD_API_URL`
- `UPLOAD_COOKIE`
- `UPDATE_API_URL`
- `UPDATE_COOKIE`
- `UPDATE_M3U8_VALUE`

By default, the skill sends `m3u8Url` as the relative path:

```env
UPDATE_M3U8_VALUE=relative_path
```

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

Optional flags:

```bash
python3 m3u8-shot-uploader/scripts/main.py \
  --input-file ./urls.txt \
  --count 10 \
  --workdir ./tmp
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

## OpenClaw integration

This repo contains a real AgentSkill folder that can be:

- installed into an OpenClaw workspace
- packaged as a `.skill` file
- published to ClawHub

Packaged artifact prepared in local workspace:

- `/Users/panda/.openclaw/workspace/m3u8-shot-uploader.skill`

## Notes

- Do not commit live cookies or tokens.
- The update API payload may fail if you send the full signed URL instead of the relative `m3u8` path.
- Batch mode processes URLs sequentially and reports aggregate counts at the end.
