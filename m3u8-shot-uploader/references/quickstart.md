# Quick Start

Use this guide when a new user installs the skill for the first time.

## 1. Prepare the runtime

Make sure these tools exist on the machine:

- `python3`
- `ffmpeg`
- `ffprobe`

Quick check:

```bash
command -v python3
command -v ffmpeg
command -v ffprobe
```

## 2. Copy the local config template

In the skill root, copy the local config example to a real local config file:

```bash
cp references/local-config.example.env .env.local
```

You can also use `.env`, but `.env.local` is recommended for first-time setup and is now the preferred file the script reads first.

## 3. Fill the required config

At minimum, set these fields in `.env.local`:

```env
COMMON_API_BASE_URL=https://your-private-api.example.com/api/web
WEB_ORIGIN=https://your-private-api.example.com
M3U8_API_ROUTE=/admin/vid/m3u8
UPLOAD_API_ROUTE=/admin/vid/uploadStaticBatch
UPDATE_API_ROUTE=/admin/vid/upload/screenshots
DEFAULT_SCREENSHOT_COUNT=10
DEFAULT_WORKERS=5
UPLOAD_COOKIE=your_private_upload_cookie_here
UPDATE_COOKIE=your_private_update_cookie_here
```

Notes:

- If `UPDATE_COOKIE` is empty, the script can fall back to `UPLOAD_COOKIE`.
- If one API does not follow the shared base URL, set `UPLOAD_API_URL` or `UPDATE_API_URL` directly.
- Keep real cookies and tokens only in `.env.local` or `.env`.

## 4. Choose a mode

The script supports two screenshot modes:

- `safe`: download the full video first, then capture screenshots
- `fast`: capture screenshots directly from the `m3u8` stream

Recommended defaults:

- short or sensitive videos: `safe`
- long videos or batch operations: `fast`
- default screenshot count comes from `.env.local` via `DEFAULT_SCREENSHOT_COUNT=10`
- default parallelism comes from `.env.local` via `DEFAULT_WORKERS=5`

## 5. Decide how to provide input

You can run the script in two ways:

- Full `m3u8` URL
- Multiple full URLs from a file

Single URL:

```bash
python3 scripts/main.py --m3u8-url 'https://example.com/path/video.m3u8?token=xxx'
```

Batch file:

```bash
python3 scripts/main.py --input-file ./urls.txt
```

## 6. Run one verification task first

Before batch processing, test one known-good video.

Safe mode:

```bash
python3 scripts/main.py --m3u8-url 'https://example.com/path/video.m3u8?token=xxx' --mode safe
```

Fast mode:

```bash
python3 scripts/main.py --m3u8-url 'https://example.com/path/video.m3u8?token=xxx' --mode fast
```

Command line values override `.env.local` defaults when both are present.

Expected result:

- video or stream is readable
- 10 screenshots are created
- upload API returns `code: 200`
- update API returns `code: 200`

## 7. Check output

The script prints a final JSON summary with:

- `total`
- `successCount`
- `failedCount`
- `mode`
- `workers`
- `count`
- `results`

If `failedCount > 0`, inspect the per-item `error` field first.

## 8. Common first-install mistakes

- `ffmpeg` not installed
- forgot to copy `local-config.example.env` into `.env.local`
- wrong cookie
- wrong `COMMON_API_BASE_URL`
- update API expects relative `m3u8` path, not full signed URL
- public example file edited, but local `.env.local` not updated
- using `fast` mode against a stream source that does not seek well
