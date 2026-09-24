"""Reporta el estado del monitor SIEDCO al Centro de fuentes del SISC.

Este modulo usa solamente la biblioteca estandar y nunca interrumpe el monitor
principal si el API central no esta disponible.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_API_URL = "https://sisc-backend.onrender.com/api"


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _iso_datetime(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _data_changed(current: Dict[str, Any], previous_path: Path) -> bool:
    previous = _load_json(previous_path)
    return previous is None or previous != current


def build_payload(
    summary_path: Path = BASE_DIR / "resumen_actual.json",
    previous_path: Path = BASE_DIR / "resumen_anterior.json",
    *,
    outcome: str = "success",
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    checked_at = _utc_now(now)
    normalized_outcome = (outcome or "success").strip().lower()
    workflow_ok = normalized_outcome == "success"
    summary = _load_json(Path(summary_path)) or {}

    successful = []
    failed = []
    cutoff_dates = []
    missing_cutoff = []

    for name, raw_info in summary.items():
        info = raw_info if isinstance(raw_info, dict) else {}
        state = str(info.get("estado") or "SIN ESTADO").strip()
        metric_ok = state.upper() == "OK" and info.get("2026") is not None
        if metric_ok:
            successful.append(name)
            cutoff = _parse_date(info.get("fecha_corte_2026"))
            if cutoff:
                cutoff_dates.append(cutoff)
            else:
                missing_cutoff.append(name)
        else:
            failed.append(f"{name}: {state}"[:500])

    warnings = []
    if not workflow_ok:
        warnings.append("La ejecucion del monitor SIEDCO termino con error.")
    if not summary:
        warnings.append("No se encontro un resumen estructurado de la ejecucion.")
    if failed:
        warnings.append(
            f"Fallaron {len(failed)} indicadores: " + "; ".join(failed[:6])
        )
    if missing_cutoff:
        warnings.append(
            f"{len(missing_cutoff)} indicadores no informaron fecha de corte 2026: "
            + ", ".join(missing_cutoff[:8])
        )
    distinct_cutoffs = sorted(set(cutoff_dates))
    if len(distinct_cutoffs) > 1:
        warnings.append(
            "La fuente publica cortes independientes entre "
            f"{distinct_cutoffs[0].isoformat()} y {distinct_cutoffs[-1].isoformat()}."
        )

    if not workflow_ok:
        status, quality = "ERROR", "ERROR"
    elif not successful:
        status, quality = "ERROR", "INCOMPLETE"
    elif failed or missing_cutoff:
        status, quality = "CURRENT", "WARNING"
    else:
        status, quality = "CURRENT", "VALIDATED"

    source_cutoff = max(cutoff_dates) if cutoff_dates else None
    changed = bool(summary) and workflow_ok and _data_changed(summary, Path(previous_path))

    if distinct_cutoffs:
        if len(distinct_cutoffs) == 1:
            period_label = f"Corte al {distinct_cutoffs[0].isoformat()} - {len(successful)} indicadores"
        else:
            period_label = (
                f"Cortes {distinct_cutoffs[0].isoformat()} a "
                f"{distinct_cutoffs[-1].isoformat()} - {len(successful)} indicadores"
            )
    else:
        period_label = f"{len(successful)} indicadores revisados" if successful else None

    payload: Dict[str, Any] = {
        "connector_code": "SIEDCO_PUBLICO",
        "status": status,
        "quality_status": quality,
        "last_checked_at": _iso_datetime(checked_at),
        "indicator_count": len(successful),
        "warnings": [warning[:500] for warning in warnings[:30]],
        "details": {
            "workflow": os.getenv("GITHUB_WORKFLOW", "monitor-siedco"),
            "run_id": os.getenv("GITHUB_RUN_ID"),
            "outcome": normalized_outcome,
            "successful_indicators": len(successful),
            "failed_indicators": len(failed),
            "data_changed": changed,
        },
    }
    if period_label:
        payload["period_label"] = period_label
    if source_cutoff:
        payload["source_cutoff_date"] = source_cutoff.isoformat()
    if workflow_ok and successful:
        payload["last_success_at"] = _iso_datetime(checked_at)
    if changed:
        payload["last_change_detected_at"] = _iso_datetime(checked_at)
    return payload


def _heartbeat_url(api_url: str) -> str:
    base = api_url.strip().rstrip("/")
    if base.endswith("/source-center/heartbeat"):
        return base
    return f"{base}/source-center/heartbeat"


def _request_github_oidc_token(audience: str = "sisc-source-center") -> Optional[str]:
    request_url = os.getenv("ACTIONS_ID_TOKEN_REQUEST_URL", "").strip()
    request_token = os.getenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "").strip()
    if not request_url or not request_token:
        return None
    separator = "&" if "?" in request_url else "?"
    oidc_request = Request(
        f"{request_url}{separator}{urlencode({'audience': audience})}",
        headers={"Authorization": f"Bearer {request_token}"},
    )
    try:
        with urlopen(oidc_request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        token = result.get("value") if isinstance(result, dict) else None
        return str(token) if token else None
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        print(f"[AVISO] No se pudo obtener la identidad OIDC de GitHub: {error}.")
        return None


def send_heartbeat(
    payload: Dict[str, Any],
    *,
    api_url: Optional[str] = None,
    service_key: Optional[str] = None,
    oidc_token: Optional[str] = None,
    timeout: int = 60,
) -> bool:
    token = _request_github_oidc_token() if oidc_token is None else oidc_token.strip()
    key = (service_key if service_key is not None else os.getenv("SISC_SOURCE_MONITOR_KEY", "")).strip()
    if not token and not key:
        print("[AVISO] Heartbeat SISC omitido: no hay identidad OIDC ni clave de servicio.")
        return False

    endpoint = _heartbeat_url(api_url or os.getenv("SISC_API_URL", DEFAULT_API_URL))
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "monitor-siedco/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["X-SISC-SOURCE-KEY"] = key
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                accepted = 200 <= response.status < 300
            print(f"[INFO] Heartbeat SISC enviado ({payload['status']}).")
            return accepted
        except HTTPError as error:
            print(f"[AVISO] El API SISC rechazo el heartbeat (HTTP {error.code}).")
            if error.code not in {408, 429, 500, 502, 503, 504}:
                return False
        except (URLError, TimeoutError, OSError):
            print(f"[AVISO] Fallo temporal de entrega SISC; intento {attempt + 1}/3.")
        if attempt < 2:
            time.sleep(2 ** (attempt + 1))
    return False


def main() -> int:
    payload = build_payload(outcome=os.getenv("SISC_MONITOR_OUTCOME", "success"))
    Path("sisc-heartbeat.json").write_text(
        json.dumps(payload, ensure_ascii=True), encoding="utf-8"
    )
    print(
        "[INFO] Estado para Centro de fuentes: "
        f"{payload['status']} / {payload['quality_status']} / "
        f"{payload['indicator_count']} indicadores."
    )
    return 0 if send_heartbeat(payload) else 1


if __name__ == "__main__":
    raise SystemExit(main())
