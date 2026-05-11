from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from json_repair import repair_json

from app.config.settings import Settings
from app.rag.catalog_models import ProcessedAssessment
from app.rag.key_codes import keys_to_test_type

log = logging.getLogger(__name__)


def _sanitize_text(val: object) -> str:
    if val is None:
        return ""
    s = str(val)
    # Catalog occasionally contains stray control characters inside strings.
    s = "".join(ch if ord(ch) >= 32 or ch in "\t\n\r" else " " for ch in s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _as_list(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [_sanitize_text(x) for x in raw if _sanitize_text(x)]
    return []


def _is_individual_solution_url(link: str) -> bool:
    try:
        p = urlparse(link)
        if p.netloc not in {"www.shl.com", "shl.com"}:
            # Allow subdomain matches
            if not p.netloc.endswith("shl.com"):
                return False
        path_lower = (p.path or "").lower()
        # Assignment scope: Individual Test Solution pages in catalog.
        return "/products/product-catalog/view/" in path_lower
    except Exception:
        return False


def normalize_catalog_records(raw_records: list[dict]) -> list[ProcessedAssessment]:
    normalized: list[ProcessedAssessment] = []
    dedupe: set[str] = set()

    for item in raw_records:
        entity_id = _sanitize_text(item.get("entity_id"))
        name = _sanitize_text(item.get("name"))
        link = _sanitize_text(item.get("link"))
        description = _sanitize_text(item.get("description"))
        duration = _sanitize_text(item.get("duration"))

        keys = list(dict.fromkeys(_as_list(item.get("keys"))))
        languages = list(dict.fromkeys(_as_list(item.get("languages"))))
        job_levels = list(dict.fromkeys(_as_list(item.get("job_levels"))))

        if not entity_id or not name or not link or not _is_individual_solution_url(link):
            continue

        uniq = f"{entity_id}|{link}"
        if uniq in dedupe:
            continue

        test_type = keys_to_test_type(keys)
        searchable = " \n ".join(
            [
                name,
                description,
                " ".join(keys),
                " ".join(languages),
                " ".join(job_levels),
                duration,
                _sanitize_text(item.get("languages_raw")),
                _sanitize_text(item.get("job_levels_raw")),
                _sanitize_text(item.get("remote")),
                _sanitize_text(item.get("adaptive")),
            ]
        )
        searchable = re.sub(r"\s+", " ", searchable).strip()

        normalized.append(
            ProcessedAssessment(
                entity_id=entity_id,
                name=name,
                url=link,
                description=description,
                duration=duration,
                languages=languages,
                job_levels=job_levels,
                keys=keys,
                remote=_sanitize_text(item.get("remote")),
                adaptive=_sanitize_text(item.get("adaptive")),
                searchable_text=searchable,
                test_type=test_type,
            )
        )
        dedupe.add(uniq)

    log.info("normalized_catalog count=%s", len(normalized))
    return normalized


def load_catalog_json_bytes(data: bytes) -> list[dict]:
    decoded = data.decode("utf-8", errors="replace")
    repaired_text = repair_json(decoded)
    repaired = json.loads(repaired_text)
    if not isinstance(repaired, list):
        raise ValueError("Catalog JSON must decode to an array.")
    cleaned: list[dict] = []
    for obj in repaired:
        if isinstance(obj, dict):
            cleaned.append(obj)
    return cleaned


async def fetch_catalog_remote(settings: Settings) -> bytes:
    timeout = httpx.Timeout(180.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(settings.catalog_url)
        resp.raise_for_status()
        return resp.content


async def ensure_raw_catalog_present(settings: Settings, raw_path: Path) -> Path:
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists() and raw_path.stat().st_size > 10_000:
        return raw_path
    log.info("Downloading catalog to %s", raw_path.as_posix())
    data = await fetch_catalog_remote(settings)
    raw_path.write_bytes(data)
    return raw_path


def ensure_processed_catalog(
    *,
    raw_path: Path,
    processed_path: Path,
) -> list[ProcessedAssessment]:
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    rebuild = False
    if processed_path.exists() and raw_path.exists():
        if raw_path.stat().st_mtime > processed_path.stat().st_mtime:
            rebuild = True
    else:
        rebuild = True

    if rebuild:
        log.info(
            "Building processed catalog from raw=%s out=%s",
            raw_path.as_posix(),
            processed_path.as_posix(),
        )
        raw_records = load_catalog_json_bytes(raw_path.read_bytes())
        normalized = normalize_catalog_records(raw_records)
        processed_path.write_text(
            json.dumps([x.model_dump() for x in normalized], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return normalized

    payloads = json.loads(processed_path.read_text(encoding="utf-8"))
    return [ProcessedAssessment.model_validate(x) for x in payloads]
