---
name: m3u8-shot-uploader
description: Download one or more m3u8 videos, extract random screenshots, upload them to a configured image API, and call a second API to save screenshot paths. Use when processing m3u8 video links into screenshot assets for admin systems, especially when the workflow requires parsing the relative m3u8 path, generating 10 screenshots with ffmpeg, batch-uploading images, and updating backend metadata with the uploaded file paths.
---

# m3u8 Shot Uploader

Use this skill for an end-to-end m3u8 screenshot workflow.

## Workflow

1. Read `scripts/main.py` and `references/env-example.txt` in this skill.
2. Copy `references/local-config.example.env` to `.env.local` or `.env` in the skill root for private runtime settings.
3. Keep local runtime config out of git; `.gitignore` already excludes `.env`, `.env.local`, and temp output.
4. Pass one or more full m3u8 URLs with repeated `--m3u8-url`, or provide `--input-file` with one URL per line.
5. Let the script parse the relative m3u8 path and `videoId` from the URL path.
6. Let the script download the stream, capture random screenshots, upload them, and call the update API.
7. Review the final JSON summary for `total`, `successCount`, `failedCount`, and per-item results.

## Important details

- Require `ffmpeg` and `ffprobe` on the host.
- Default screenshot count is `10`; override with `--count` if needed.
- The update API may require the relative m3u8 path instead of the full URL. This skill defaults to `UPDATE_M3U8_VALUE=relative_path`.
- Keep tokens and cookies in `.env`, not in source code or chat replies.

## Files

- `scripts/main.py`: batch-capable pipeline script
- `references/env-example.txt`: public example config template
- `references/local-config.example.env`: local operations config template for private runtime values
- `references/quickstart.md`: first-install guide for new users
- `.gitignore`: ignores `.env`, `.env.local`, and generated runtime files

## First-time setup

Read `references/quickstart.md` when onboarding a new user or installing the skill on a new machine. It covers dependency checks, local config setup, required fields, and the first verification run.

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
