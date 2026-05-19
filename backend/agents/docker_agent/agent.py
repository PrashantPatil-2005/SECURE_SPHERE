"""
docker_agent/agent.py — SecuriSphere Docker Host Agent

Connects to Docker daemon via /var/run/docker.sock, monitors container lifecycle
events in real-time, runs Trivy vulnerability scans, tails container logs,
and sends events to the Agent Manager.
"""

import os
import sys
import json
import time
import socket
import hashlib
import threading
import logging
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import docker
import requests


# ── Configuration ──────────────────────────────────────────────────────────────

AGENT_ID: str = os.getenv("AGENT_ID", "docker-host-agent")
MANAGER_URL: str = os.getenv("MANAGER_URL", "http://securisphere-agent-manager:8514")
SCAN_INTERVAL: int = int(os.getenv("SCAN_INTERVAL", "300"))
ENABLE_LOG_TAILING: bool = os.getenv("ENABLE_LOG_TAILING", "false").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "5.0"))
HEARTBEAT_INTERVAL: int = int(os.getenv("HEARTBEAT_INTERVAL", "60"))
EVENT_BATCH_SIZE: int = int(os.getenv("EVENT_BATCH_SIZE", "50"))


# ── Severity levels ────────────────────────────────────────────────────────────

class Severity(Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── Structured logging ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='{"time":"%(asctime)s","service":"docker-agent","level":"%(levelname)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("DockerAgent")


# ── Event schema ───────────────────────────────────────────────────────────────

def create_event(
    event_type: str,
    docker_action: str,
    container_id: str,
    container_name: str,
    image: str,
    severity: str,
    correlation_tags: List[str],
    raw_data: Dict,
    agent_id: str = AGENT_ID
) -> Dict[str, Any]:
    """Create normalized event for Agent Manager."""
    return {
        "event_type": event_type,
        "source_layer": "docker_host",
        "agent_id": agent_id,
        "severity": severity,
        "docker_action": docker_action,
        "container_id": container_id,
        "container_name": container_name,
        "image": image,
        "correlation_tags": correlation_tags,
        "timestamp": time.time(),
        "raw_data": raw_data,
    }


# ── Docker Host Agent ──────────────────────────────────────────────────────────

class DockerHostAgent:
    """Docker Host Agent for SecuriSphere."""

    def __init__(self) -> None:
        self.agent_id = AGENT_ID
        self.manager_url = MANAGER_URL
        self.scan_interval = SCAN_INTERVAL
        self.enable_log_tailing = ENABLE_LOG_TAILING
        self.heartbeat_interval = HEARTBEAT_INTERVAL
        self.max_retries = MAX_RETRIES
        self.retry_delay = RETRY_DELAY
        self.event_batch_size = EVENT_BATCH_SIZE

        self.docker_client: Optional[docker.DockerClient] = None
        self.manager_session: Optional[requests.Session] = None
        self.event_buffer: List[Dict] = []
        self.running = False
        self.hostname = socket.gethostname()
        self.ip_address = self._get_ip_address()
        self.container_cache: Dict[str, Dict] = {}
        self.scan_timer: Optional[threading.Timer] = None
        self.heartbeat_timer: Optional[threading.Timer] = None
        self.log_tail_threads: List[threading.Thread] = []

        logger.info(f"Initializing DockerHostAgent: {self.agent_id} on {self.hostname}")

    def _get_ip_address(self) -> str:
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _connect_docker(self) -> bool:
        """Connect to Docker daemon."""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            logger.info("Successfully connected to Docker daemon")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Docker daemon: {str(e)}")
            return False

    def _connect_manager(self) -> bool:
        """Initialize connection to Agent Manager."""
        self.manager_session = requests.Session()
        try:
            response = requests.get(f"{self.manager_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info(f"Connected to Agent Manager at {self.manager_url}")
                return True
        except Exception as e:
            logger.error(f"Failed to connect to Agent Manager: {str(e)}")
        return False

    def register(self) -> bool:
        """Register with Agent Manager."""
        try:
            payload = {
                "agent_id": self.agent_id,
                "name": f"Docker Host Agent ({self.hostname})",
                "type": "docker_host",
                "ip_address": self.ip_address,
                "hostname": self.hostname,
                "os": os.uname().sysname if hasattr(os, 'uname') else "unknown",
                "platform": sys.platform,
                "status": "active",
                "labels": {
                    "scan_interval": self.scan_interval,
                    "log_tailing": self.enable_log_tailing,
                    "modules": ["container_events", "image_events", "network_events", "volume_events", "vulnerability_scan"],
                }
            }

            response = requests.post(
                f"{self.manager_url}/api/agents/register",
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                logger.info(f"Registered with Agent Manager: {self.agent_id}")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return False

    def send_heartbeat(self) -> bool:
        """Send heartbeat to Agent Manager."""
        try:
            payload = {
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "active",
                "event_count": len(self.event_buffer),
            }
            response = requests.post(
                f"{self.manager_url}/api/agents/{self.agent_id}/heartbeat",
                json=payload,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Heartbeat error: {str(e)}")
            return False

    def send_events(self, events: List[Dict]) -> bool:
        """Send events to Agent Manager."""
        if not events:
            return True

        try:
            payload = {
                "agent_id": self.agent_id,
                "events": events,
                "batch_timestamp": datetime.utcnow().isoformat() + "Z",
            }
            response = requests.post(
                f"{self.manager_url}/api/agents/{self.agent_id}/events",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Sent {len(events)} events to Manager")
                return True
            else:
                logger.error(f"Failed to send events: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending events: {str(e)}")
            return False

    def classify_severity(self, action: str) -> str:
        """Classify event severity based on Docker action."""
        high_severity_actions = [
            "exec_create", "exec_start", "exec_die", "container_killed",
            "container_die", "pause", "unpause"
        ]
        medium_severity_actions = [
            "start", "stop", "die", "oom_killed",
        ]
        critical_actions = [
            "container_killed", "exec_create"  # Potential container compromise
        ]

        if action in critical_actions:
            return "CRITICAL"
        elif action in high_severity_actions:
            return "HIGH"
        elif action in medium_severity_actions:
            return "MEDIUM"
        else:
            return "INFO"

    def get_correlation_tags(self, action: str) -> List[str]:
        """Get correlation tags for event."""
        tags = []
        if action in ["exec_create", "exec_start"]:
            tags.append("container_exec")
        if action in ["container_killed", "container_die"]:
            tags.append("container_terminated")
        if action == "exec_create":
            tags.append("potential_compromise")
        if action in ["start", "create"]:
            tags.append("container_spawn")
        return tags

    def _process_docker_event(self, event: Dict) -> Optional[Dict]:
        """Process a Docker event and create normalized event."""
        action = event.get("Action", "unknown")
        actor = event.get("Actor", {})
        scope = event.get("Scope", "")

        # Extract container info
        container_id = ""
        container_name = ""
        image = ""

        if scope == "container":
            container_id = event.get("id", "")[:12] if event.get("id") else ""
            attrs = event.get("Actor", {}).get("Attributes", {})
            container_name = attrs.get("name", "")
            image = attrs.get("image", "")

        elif scope == "image":
            image = event.get("Actor", {}).get("Attributes", {}).get("reference", "")

        # Determine event type
        if scope == "container":
            event_type = "docker_container_event"
        elif scope == "image":
            event_type = "docker_image_event"
        elif scope == "network":
            event_type = "docker_network_event"
        elif scope == "volume":
            event_type = "docker_volume_event"
        else:
            event_type = f"docker_{scope}_event"

        severity = self.classify_severity(action)
        correlation_tags = self.get_correlation_tags(action)

        return create_event(
            event_type=event_type,
            docker_action=action,
            container_id=container_id,
            container_name=container_name,
            image=image,
            severity=severity,
            correlation_tags=correlation_tags,
            raw_data=event,
        )

    def _watch_docker_events(self):
        """Watch Docker events in real-time."""
        logger.info("Starting Docker event watcher")
        try:
            for event in self.docker_client.events(filters={"type": ["container", "image", "network", "volume"]}):
                if not self.running:
                    break

                try:
                    event_data = json.loads(event)
                    normalized = self._process_docker_event(event_data)

                    if normalized:
                        self.event_buffer.append(normalized)

                        # Flush buffer if exceeds batch size
                        if len(self.event_buffer) >= self.event_batch_size:
                            self._flush_events()

                except Exception as e:
                    logger.error(f"Error processing Docker event: {str(e)}")

        except Exception as e:
            logger.error(f"Docker event watcher error: {str(e)}")

    def _scan_container_vulnerabilities(self, container_id: str, image: str) -> Optional[Dict]:
        """Scan container for vulnerabilities using Trivy."""
        if not image:
            return None

        try:
            # Check if Trivy is installed
            result = subprocess.run(["which", "trivy"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("Trivy not installed, skipping vulnerability scan")
                return None

            # Run Trivy scan
            scan_cmd = ["trivy", "image", "--format", "json", "--quiet", image]
            result = subprocess.run(scan_cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0 and "No vulnerabilities found" not in result.stderr:
                logger.warning(f"Trivy scan failed: {result.stderr}")
                return None

            vulnerabilities = json.loads(result.stdout) if result.stdout else []

            if not vulnerabilities:
                return None

            # Count severity levels
            critical_count = sum(1 for v in vulnerabilities if v.get("Severity") == "CRITICAL")
            high_count = sum(1 for v in vulnerabilities if v.get("Severity") == "HIGH")
            medium_count = sum(1 for v in vulnerabilities if v.get("Severity") == "MEDIUM")

            if critical_count == 0 and high_count == 0:
                return None

            event = create_event(
                event_type="vulnerability_scan",
                docker_action="trivy_scan",
                container_id=container_id[:12] if container_id else "",
                container_name="",
                image=image,
                severity="HIGH" if critical_count > 0 else "MEDIUM",
                correlation_tags=["vulnerability", f"cve_count:{len(vulnerabilities)}"],
                raw_data={
                    "vulnerabilities": vulnerabilities,
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                }
            )
            return event

        except subprocess.TimeoutExpired:
            logger.error(f"Trivy scan timeout for {image}")
        except Exception as e:
            logger.error(f"Vulnerability scan error: {str(e)}")

        return None

    def _scan_all_containers(self):
        """Scan all running containers for vulnerabilities."""
        try:
            containers = self.docker_client.containers.list()
            logger.info(f"Scanning {len(containers)} running containers")

            for container in containers:
                if not self.running:
                    break

                image = container.image.tags[0] if container.image.tags else str(container.image.id)
                event = self._scan_container_vulnerabilities(container.id, image)

                if event:
                    self.event_buffer.append(event)

            # Flush events
            self._flush_events()

        except Exception as e:
            logger.error(f"Container scan error: {str(e)}")

    def _tail_container_logs(self):
        """Tail container logs for ERROR/WARN level entries."""
        try:
            containers = self.docker_client.containers.list()

            for container in containers:
                if not self.running:
                    break

                try:
                    # Stream logs
                    for line in container.logs(stream=True, tail=100):
                        log_line = line.decode('utf-8', errors='ignore').strip()

                        if any(level in log_line.upper() for level in ["ERROR", "WARN", "CRITICAL"]):
                            event = create_event(
                                event_type="container_log",
                                docker_action="log_error",
                                container_id=container.id[:12],
                                container_name=container.name,
                                image=container.image.tags[0] if container.image.tags else "",
                                severity="HIGH" if "ERROR" in log_line.upper() else "MEDIUM",
                                correlation_tags=["log_error"],
                                raw_data={"log": log_line}
                            )
                            self.event_buffer.append(event)

                except Exception as e:
                    logger.debug(f"Log tailing error for {container.name}: {str(e)}")

        except Exception as e:
            logger.error(f"Log tailing error: {str(e)}")

    def _flush_events(self):
        """Flush event buffer to Manager."""
        if not self.event_buffer:
            return

        events_to_send = self.event_buffer[:self.event_batch_size]
        self.event_buffer = self.event_buffer[self.event_batch_size:]

        success = self.send_events(events_to_send)

        if not success and self.event_buffer:
            # Retry logic
            for attempt in range(self.max_retries):
                time.sleep(self.retry_delay * (2 ** attempt))
                if self.send_events(events_to_send):
                    break

    def _heartbeat_loop(self):
        """Send heartbeat at regular intervals."""
        while self.running:
            try:
                self.send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {str(e)}")
            time.sleep(self.heartbeat_interval)

    def _scan_loop(self):
        """Run vulnerability scans at regular intervals."""
        while self.running:
            try:
                self._scan_all_containers()
            except Exception as e:
                logger.error(f"Scan loop error: {str(e)}")
            time.sleep(self.scan_interval)

    def _log_tail_loop(self):
        """Tail container logs at regular intervals."""
        while self.running:
            try:
                self._tail_container_logs()
            except Exception as e:
                logger.error(f"Log tail loop error: {str(e)}")
            time.sleep(30)  # Check logs every 30 seconds

    def start(self) -> bool:
        """Start the Docker Host Agent."""
        logger.info(f"Starting DockerHostAgent: {self.agent_id}")

        # Connect to Docker
        if not self._connect_docker():
            logger.error("Failed to connect to Docker daemon")
            return False

        # Connect to Manager
        if not self._connect_manager():
            logger.error("Failed to connect to Agent Manager")
            return False

        # Register with Manager
        if not self.register():
            logger.error("Failed to register with Agent Manager")
            return False

        self.running = True

        # Start event watcher thread
        event_thread = threading.Thread(target=self._watch_docker_events, daemon=True)
        event_thread.start()

        # Start heartbeat thread
        self.heartbeat_timer = threading.Timer(self.heartbeat_interval, self._heartbeat_loop)
        self.heartbeat_timer.daemon = True
        self.heartbeat_timer.start()

        # Start scan thread
        self.scan_timer = threading.Timer(self.scan_interval, self._scan_loop)
        self.scan_timer.daemon = True
        self.scan_timer.start()

        # Start log tailing if enabled
        if self.enable_log_tailing:
            log_thread = threading.Thread(target=self._log_tail_loop, daemon=True)
            log_thread.start()
            self.log_tail_threads.append(log_thread)

        logger.info("DockerHostAgent started successfully")
        return True

    def stop(self):
        """Stop the Docker Host Agent."""
        logger.info("Stopping DockerHostAgent")
        self.running = False

        # Flush remaining events
        self._flush_events()

        # Cancel timers
        if self.scan_timer:
            self.scan_timer.cancel()
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()

        # Stop threads
        for thread in self.log_tail_threads:
            thread.join(timeout=5)

        logger.info("DockerHostAgent stopped")


# ── Main entry point ───────────────────────────────────────────────────────────

def main() -> int:
    """Main entry point for Docker Host Agent."""
    agent = DockerHostAgent()

    try:
        if not agent.start():
            logger.error("Failed to start agent")
            return 1

        # Keep running
        while agent.running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        agent.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
