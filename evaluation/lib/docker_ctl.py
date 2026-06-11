"""Docker helpers for churn experiments (service restart, correlation mode)."""

from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Literal

from evaluation.lib.paths import project_root

logger = logging.getLogger(__name__)

# Compose service name → container_name in docker-compose.yml
SERVICE_CONTAINER_MAP: dict[str, str] = {
    "auth-service": "securisphere-auth",
    "api-server": "securisphere-api",
    "database": "securisphere-db",
}

CORRELATION_ENGINE_SERVICE = "correlation-engine"
CORRELATION_ENGINE_CONTAINER = "securisphere-correlator"


def restart_service(service_name: str, *, timeout_sec: int = 60) -> None:
    """Restart a target microservice container mid-attack.

    Args:
        service_name: Docker Compose service name (e.g. ``auth-service``).
        timeout_sec: Max seconds to wait for container health after restart.

    Raises:
        RuntimeError: If the container cannot be found or restarted.
    """
    container = SERVICE_CONTAINER_MAP.get(service_name, service_name)
    try:
        import docker  # type: ignore

        client = docker.from_env()
        ctr = client.containers.get(container)
        ctr.restart(timeout=timeout_sec)
        logger.info("Restarted container %s (service %s)", container, service_name)
        return
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("Docker SDK restart failed (%s); falling back to CLI", exc)

    result = subprocess.run(
        ["docker", "restart", container],
        capture_output=True,
        text=True,
        timeout=timeout_sec + 10,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to restart {container}: {result.stderr or result.stdout}"
        )
    logger.info("Restarted container %s via docker CLI", container)


def set_correlation_mode(
    mode: Literal["service", "legacy"],
    *,
    recreate_engine: bool = True,
    warmup_sec: float = 12.0,
) -> None:
    """Switch CORRELATION_MODE on the correlation-engine container.

    Args:
        mode: ``service`` (identity keys) or ``legacy`` (IP keys).
        recreate_engine: If True, force-recreate the engine container.
        warmup_sec: Seconds to wait after recreate for health.
    """
    if mode not in ("service", "legacy"):
        raise ValueError(f"Invalid correlation mode: {mode}")

    env = os.environ.copy()
    env["CORRELATION_MODE"] = mode
    root = project_root()
    cmd = ["docker", "compose", "up", "-d"]
    if recreate_engine:
        cmd.extend(["--force-recreate", CORRELATION_ENGINE_SERVICE])
    else:
        cmd.append(CORRELATION_ENGINE_SERVICE)

    result = subprocess.run(
        cmd,
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"docker compose failed setting CORRELATION_MODE={mode}: "
            f"{result.stderr or result.stdout}"
        )
    logger.info("Set CORRELATION_MODE=%s; waiting %.0fs for engine", mode, warmup_sec)
    time.sleep(warmup_sec)
