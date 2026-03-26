#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import mimetypes
import random
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKDIR = ROOT / "tmp"


def parse_env_file(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not env_path.exists():
        return env
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def load_env(env_path: Path) -> Dict[str, str]:
    # Prefer local private config, then fall back to the explicitly requested file.
    candidates = [env_path.parent / ".env.local", env_path]
    merged: Dict[str, str] = {}
    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        merged.update(parse_env_file(candidate))
    return merged


def require_tool(name: str) -> None:
    if shutil.which(name):
        return
    raise RuntimeError(f"Missing required tool: {name}")


def get_env(env: Dict[str, str], key: str, default: str = "") -> str:
    return env.get(key, default).strip()


def join_url(base: str, route: str) -> str:
    base = base.rstrip("/")
    route = route.strip()
    if not route:
        return base
    if route.startswith("http://") or route.startswith("https://"):
        return route
    return f"{base}/{route.lstrip('/')}"


def resolve_api_url(env: Dict[str, str], url_key: str, route_key: str) -> str:
    direct_url = get_env(env, url_key)
    if direct_url:
        return direct_url
    base_url = get_env(env, "COMMON_API_BASE_URL")
    route = get_env(env, route_key)
    if base_url and route:
        return join_url(base_url, route)
    raise RuntimeError(f"{url_key} or COMMON_API_BASE_URL + {route_key} is required")


def resolve_web_origin(env: Dict[str, str]) -> str:
    explicit_origin = get_env(env, "WEB_ORIGIN")
    if explicit_origin:
        return explicit_origin
    base_url = get_env(env, "COMMON_API_BASE_URL")
    if not base_url:
        return ""
    parsed = urllib.parse.urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def resolve_referer(env: Dict[str, str], key: str) -> str:
    explicit = get_env(env, key)
    if explicit:
        return explicit
    origin = resolve_web_origin(env)
    return f"{origin}/" if origin else ""


def resolve_origin(env: Dict[str, str], key: str) -> str:
    explicit = get_env(env, key)
    if explicit:
        return explicit
    return resolve_web_origin(env)


def parse_video_info(m3u8_url: str) -> Tuple[str, str]:
    parsed = urllib.parse.urlparse(m3u8_url)
    path = parsed.path or ""
    marker = "/m3u8/"
    relative_path = path.split(marker, 1)[1] if marker in path else path.lstrip("/")
    base_name = Path(relative_path).name
    if not base_name.endswith(".m3u8"):
        raise ValueError(f"URL path does not point to an m3u8 file: {relative_path}")
    video_id = base_name[:-5]
    if not video_id:
        raise ValueError("Failed to parse video id from m3u8 path")
    return relative_path, video_id


def run(cmd: List[str], cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True, text=True, capture_output=True)


def download_video(m3u8_url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        m3u8_url,
        "-c",
        "copy",
        str(output_path),
    ]
    run(cmd)


def probe_duration_from_source(source: str) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        source,
    ]
    result = run(cmd)
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError("Video duration is not valid")
    return duration


def pick_timestamps(duration: float, count: int) -> List[float]:
    if count <= 0:
        return []
    start = min(3.0, duration * 0.1)
    end = max(duration - 3.0, start + 1.0)
    if end <= start:
        start = 0.0
        end = max(duration, 1.0)
    if duration < count:
        step = max(duration / (count + 1), 0.1)
        return [round(min(step * (i + 1), max(duration - 0.1, 0.0)), 3) for i in range(count)]
    samples = sorted(random.uniform(start, end) for _ in range(count))
    return [round(min(ts, max(duration - 0.1, 0.0)), 3) for ts in samples]


def capture_one_screenshot(source: str, shot_path: Path, timestamp: float) -> Path:
    shot_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        str(timestamp),
        "-i",
        source,
        "-frames:v",
        "1",
        str(shot_path),
    ]
    run(cmd)
    return shot_path


def capture_screenshots_parallel(source: str, output_dir: Path, timestamps: List[float], workers: int) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    shot_paths = [output_dir / f"{index:02d}.png" for index in range(1, len(timestamps) + 1)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [
            executor.submit(capture_one_screenshot, source, shot_path, ts)
            for shot_path, ts in zip(shot_paths, timestamps)
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    return shot_paths


def build_multipart_body(field_name: str, files: List[Path], boundary: str) -> Tuple[bytes, str]:
    body = bytearray()
    for file_path in files:
        content = file_path.read_bytes()
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"\r\n'.encode()
        )
        body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode())
        body.extend(content)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    content_type = f"multipart/form-data; boundary={boundary}"
    return bytes(body), content_type


def send_request(url: str, method: str, headers: Dict[str, str], body: bytes, timeout: int) -> Dict:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc


def upload_files(files: List[Path], env: Dict[str, str]) -> Dict:
    upload_url = resolve_api_url(env, "UPLOAD_API_URL", "UPLOAD_API_ROUTE")
    field_name = get_env(env, "UPLOAD_FIELD_NAME", "upload[]")
    cookie = get_env(env, "UPLOAD_COOKIE")
    referer = resolve_referer(env, "UPLOAD_REFERER")
    origin = resolve_origin(env, "UPLOAD_ORIGIN")
    timeout = int(get_env(env, "REQUEST_TIMEOUT", "120"))

    boundary = f"----OpenClawBoundary{random.randint(100000, 999999)}"
    body, content_type = build_multipart_body(field_name, files, boundary)

    headers = {
        "Accept": "*/*",
        "Content-Type": content_type,
        "User-Agent": "m3u8-shot-uploader/1.0",
    }
    if cookie:
        headers["Cookie"] = cookie
    if referer:
        headers["Referer"] = referer
    if origin:
        headers["Origin"] = origin

    return send_request(upload_url, "POST", headers, body, timeout)


def default_update_payload(m3u8_value: str, file_paths: List[str], env: Dict[str, str]) -> bytes:
    m3u8_field = get_env(env, "UPDATE_M3U8_URL_FIELD", "m3u8Url") or "m3u8Url"
    screenshots_field = get_env(env, "UPDATE_SCREENSHOTS_FIELD", "screenshots") or "screenshots"
    payload = {
        m3u8_field: m3u8_value,
        screenshots_field: file_paths,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def maybe_update_video(m3u8_url: str, video_id: str, relative_path: str, file_paths: List[str], env: Dict[str, str]) -> Dict:
    try:
        update_url = resolve_api_url(env, "UPDATE_API_URL", "UPDATE_API_ROUTE")
    except RuntimeError:
        return {"skipped": True, "reason": "UPDATE_API_URL or COMMON_API_BASE_URL + UPDATE_API_ROUTE is empty"}

    method = get_env(env, "UPDATE_API_METHOD", "POST").upper() or "POST"
    content_type = get_env(env, "UPDATE_CONTENT_TYPE", "application/json") or "application/json"
    cookie = get_env(env, "UPDATE_COOKIE") or get_env(env, "UPLOAD_COOKIE")
    referer = resolve_referer(env, "UPDATE_REFERER")
    origin = resolve_origin(env, "UPDATE_ORIGIN")
    timeout = int(get_env(env, "REQUEST_TIMEOUT", "120"))
    body_template = get_env(env, "UPDATE_BODY_TEMPLATE")

    update_m3u8_mode = get_env(env, "UPDATE_M3U8_VALUE", "relative_path") or "relative_path"
    update_m3u8_value = relative_path if update_m3u8_mode == "relative_path" else m3u8_url

    if body_template:
        body_text = body_template.replace("__M3U8_URL__", m3u8_url)
        body_text = body_text.replace("__M3U8_VALUE__", update_m3u8_value)
        body_text = body_text.replace("__VIDEO_ID__", video_id)
        body_text = body_text.replace("__RELATIVE_PATH__", relative_path)
        body_text = body_text.replace("__FILE_PATH_JSON__", json.dumps(file_paths, ensure_ascii=False))
        body = body_text.encode("utf-8")
    else:
        body = default_update_payload(update_m3u8_value, file_paths, env)

    headers = {
        "Accept": "*/*",
        "Content-Type": content_type,
        "User-Agent": "m3u8-shot-uploader/1.0",
    }
    if cookie:
        headers["Cookie"] = cookie
    if referer:
        headers["Referer"] = referer
    if origin:
        headers["Origin"] = origin

    return send_request(update_url, method, headers, body, timeout)


def process_one(m3u8_url: str, count: int, base_workdir: Path, env: Dict[str, str], mode: str, workers: int) -> Dict:
    relative_path, video_id = parse_video_info(m3u8_url)
    workdir = base_workdir.resolve() / video_id
    video_path = workdir / f"{video_id}.mp4"
    shots_dir = workdir / "shots"

    source = m3u8_url
    if mode == "safe":
        download_video(m3u8_url, video_path)
        source = str(video_path)

    duration = probe_duration_from_source(source)
    timestamps = pick_timestamps(duration, count)
    shots = capture_screenshots_parallel(source, shots_dir, timestamps, workers)
    upload_response = upload_files(shots, env)
    file_paths = upload_response.get("data", {}).get("filePath", [])
    update_response = maybe_update_video(m3u8_url, video_id, relative_path, file_paths, env)

    return {
        "ok": True,
        "mode": mode,
        "workers": workers,
        "videoId": video_id,
        "relativePath": relative_path,
        "m3u8Url": m3u8_url,
        "videoPath": str(video_path) if mode == "safe" else None,
        "duration": duration,
        "timestamps": timestamps,
        "shots": [str(p) for p in shots],
        "uploadResponse": upload_response,
        "filePath": file_paths,
        "updateResponse": update_response,
    }


def collect_urls(args: argparse.Namespace) -> List[str]:
    urls: List[str] = []
    for item in args.m3u8_url:
        stripped = item.strip()
        if stripped:
            urls.append(stripped)
    if args.input_file:
        for raw_line in Path(args.input_file).read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    if not urls:
        raise RuntimeError("At least one m3u8 URL is required")
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description="Download m3u8 videos, capture screenshots, upload them, and call update API")
    parser.add_argument("--m3u8-url", action="append", default=[], help="Full m3u8 URL, repeatable")
    parser.add_argument("--input-file", help="Text file with one m3u8 URL per line")
    parser.add_argument("--count", type=int, default=10, help="Number of screenshots to capture")
    parser.add_argument("--workdir", default=str(DEFAULT_WORKDIR), help="Working directory for temp files")
    parser.add_argument("--mode", choices=["safe", "fast"], default="safe", help="safe downloads the full video first; fast captures directly from the m3u8 stream")
    parser.add_argument("--workers", type=int, default=4, help="Parallel screenshot worker count")
    parser.add_argument("--env-file", default=str(ROOT / ".env"), help="Fallback env config file path; .env.local in the skill root is loaded first when present")
    args = parser.parse_args()

    require_tool("ffmpeg")
    require_tool("ffprobe")

    env = load_env(Path(args.env_file))
    urls = collect_urls(args)
    base_workdir = Path(args.workdir)

    results: List[Dict] = []
    success_count = 0
    failed_count = 0

    for index, m3u8_url in enumerate(urls, start=1):
        print(json.dumps({"stage": "start", "index": index, "total": len(urls), "mode": args.mode, "workers": args.workers, "m3u8Url": m3u8_url}, ensure_ascii=False))
        try:
            result = process_one(m3u8_url, args.count, base_workdir, env, args.mode, max(1, args.workers))
            results.append(result)
            success_count += 1
        except Exception as exc:
            failed_count += 1
            failure = {
                "ok": False,
                "mode": args.mode,
                "workers": args.workers,
                "m3u8Url": m3u8_url,
                "error": str(exc),
            }
            results.append(failure)
            print(json.dumps({"stage": "failed", "index": index, "total": len(urls), "m3u8Url": m3u8_url, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)

    summary = {
        "total": len(urls),
        "successCount": success_count,
        "failedCount": failed_count,
        "mode": args.mode,
        "workers": args.workers,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise
