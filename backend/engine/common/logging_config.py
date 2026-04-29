"""Structured (JSON) logging + optional OpenTelemetry init for the engine.

Engine logs are still human-readable by default — when ``STRUCTURED_LOGS=1``
they switch to JSON lines so the ELK stack / Loki / Datadog can parse them
without log-line regex maintenance. The ``trace_id`` and ``span_id`` fields
are populated from the active OTel context when ``OTEL_ENABLED=1``.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """One JSON object per log record. Keys are stable so log shipping
    pipelines can index them without sniffing."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts":        time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level":     record.levelname,
            "logger":    record.name,
            "msg":       record.getMessage(),
            "module":    record.module,
            "line":      record.lineno,
        }
        # Inject OTel context if present
        trace_id = getattr(record, "trace_id", None) or _current_trace_id()
        if trace_id:
            payload["trace_id"] = trace_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_TRACER = None


def _current_trace_id() -> str:
    """Return current OTel trace_id as hex, or '' when no span is active."""
    try:
        from opentelemetry import trace  # type: ignore
        span = trace.get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx and ctx.is_valid:
            return f"{ctx.trace_id:032x}"
    except Exception:
        pass
    return ""


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if os.getenv("STRUCTURED_LOGS", "0") == "1":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))
    root.addHandler(handler)
    root.setLevel(level.upper())


def setup_otel(service_name: str = "securisphere-engine") -> None:
    """Initialise OpenTelemetry tracing if the SDK is installed AND
    ``OTEL_ENABLED=1``. No-op otherwise — keeps engine startup fast."""
    if os.getenv("OTEL_ENABLED", "0") != "1":
        return
    try:
        from opentelemetry import trace  # type: ignore
        from opentelemetry.sdk.resources import Resource  # type: ignore
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore
        from opentelemetry.sdk.trace.export import (  # type: ignore
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
    except Exception as exc:
        logging.getLogger("otel").info("OTel SDK not installed: %s", exc)
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    exporter = None
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(endpoint=endpoint + "/v1/traces")
        except Exception as exc:
            logging.getLogger("otel").info("OTLP exporter unavailable: %s", exc)
    if exporter is None:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    global _TRACER
    _TRACER = trace.get_tracer(service_name)
    logging.getLogger("otel").info("OTel tracer initialised for %s", service_name)


def tracer():
    return _TRACER
