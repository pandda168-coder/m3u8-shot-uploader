---
name: m3u8-shot-uploader
description: Download one or more m3u8 videos, extract random screenshots, upload them to a configured image API, and call a second API to save screenshot paths. Use when processing m3u8 video links into screenshot assets for admin systems, especially when the workflow requires parsing the relative m3u8 path, generating 10 screenshots with ffmpeg, batch-uploading images, and updating backend metadata with the uploaded file paths.
---

# m3u8 Shot Uploader

Use this skill for an end-to-end m3u8 screenshot workflow.

## Workflow

1. Read `scripts/main.py` and `.env.example` in this skill.
2. Copy `.env.example` to `.env` and fill the API URLs, cookies, and request settings.
3. Pass one or more full m3u8 URLs with repeated `--m3u8-url`, or provide `--input-file` with one URL per line.
4. Let the script parse the relative m3u8 path and `videoId` from the URL path.
5. Let the script download the stream, capture random screenshots, upload them, and call the update API.
6. Review the final JSON summary for `total`, `successCount`, `failedCount`, and per-item results.

## Important details

- Require `ffmpeg` and `ffprobe` on the host.
- Default screenshot count is `10`; override with `--count` if needed.
- The update API may require the relative m3u8 path instead of the full URL. This skill defaults to `UPDATE_M3U8_VALUE=relative_path`.
- Keep tokens and cookies in `.env`, not in source code or chat replies.

## Files

- `scripts/main.py`: batch-capable pipeline script
- `references/env-example.txt`: config template to copy into `.env`

## Run

Single URL:

```bash
python3 scripts/main.py --m3u8-url 'https://example.com/video.m3u8?token=xxx'
```

Multiple URLs:

```bash
python3 scripts/main.py \
  --m3u8-url 'https://example.com/a.m3u8?token=xxx' \
  --m3u8-url 'https://example.com/b.m3u8?token=yyy'
```

Input file:

```bash
python3 scripts/main.py --input-file ./urls.txt
```
