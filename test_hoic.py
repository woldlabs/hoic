#!/usr/bin/env python3
"""Unit tests for HOIC core logic (no GUI, minimal network)."""

import asyncio
import socket
import threading
import time
import unittest
from unittest.mock import MagicMock

from aiohttp import web

import hoic


class TestPureHelpers(unittest.TestCase):
    def test_make_payload_size(self):
        payload = hoic.make_payload(512)
        self.assertEqual(len(payload), 512)
        self.assertIsInstance(payload, bytes)

    def test_make_payload_minimum_one_byte(self):
        self.assertEqual(len(hoic.make_payload(0)), 1)

    def test_build_random_headers_has_host(self):
        headers = hoic.build_random_headers("test.example")
        self.assertEqual(headers["Host"], "test.example")
        self.assertIn("User-Agent", headers)

    def test_compute_error_rate(self):
        self.assertEqual(hoic.compute_error_rate(90, 10), 0.1)
        self.assertEqual(hoic.compute_error_rate(0, 0), 0.0)
        self.assertEqual(hoic.compute_error_rate(0, 5), 1.0)

    def test_compute_percentile(self):
        samples = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        self.assertEqual(hoic.compute_percentile(samples, 50), 50.0)
        self.assertEqual(hoic.compute_percentile([], 95), 0.0)

    def test_is_target_saturated_by_error_rate(self):
        self.assertTrue(hoic.is_target_saturated(0.15, 100.0, 0.10, 2000.0))

    def test_is_target_saturated_by_latency(self):
        self.assertTrue(hoic.is_target_saturated(0.01, 2500.0, 0.10, 2000.0))

    def test_is_target_saturated_healthy(self):
        self.assertFalse(hoic.is_target_saturated(0.02, 150.0, 0.10, 2000.0))

    def test_saturation_search_bounds_saturated(self):
        low, high = hoic.saturation_search_bounds(5, 100, 50, saturated=True)
        self.assertEqual(low, 5)
        self.assertEqual(high, 49)

    def test_saturation_search_bounds_ok(self):
        low, high = hoic.saturation_search_bounds(5, 100, 50, saturated=False)
        self.assertEqual(low, 51)
        self.assertEqual(high, 100)

    def test_resonance_wave_factor_range(self):
        values = [hoic.resonance_wave_factor(t, period=12.0) for t in range(0, 120)]
        self.assertTrue(all(0.35 <= v <= 1.15 for v in values))

    def test_active_resonance_workers(self):
        workers = hoic.active_resonance_workers(100, elapsed=3.0, period=12.0)
        self.assertGreaterEqual(workers, 1)
        self.assertLessEqual(workers, 115)


class TestStats(unittest.TestCase):
    def test_reset_and_record(self):
        stats = hoic.Stats()
        stats.start()
        stats.record_sent(10)
        stats.record_error(2)
        stats.record_latency(50.0)
        stats.record_latency(150.0)
        result = stats.get_stats()
        self.assertEqual(result["sent"], 10)
        self.assertEqual(result["errors"], 2)
        self.assertGreater(result["latency"]["p50"], 0)

    def test_saturation_point(self):
        stats = hoic.Stats()
        stats.set_saturation_point(42)
        self.assertEqual(stats.get_stats()["saturation_point"], 42)

    def test_probe_history(self):
        stats = hoic.Stats()
        stats.record_probe(50, 100, 5, 120.0, False)
        probes = stats.get_stats()["probe_history"]
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0]["workers"], 50)


class TestAttackController(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.stat_updates = []
        self.controller = hoic.AttackController(
            log_callback=lambda m: self.logs.append(m),
            stats_callback=lambda s: self.stat_updates.append(s),
        )

    def test_stop_when_not_running(self):
        self.controller.stop()
        self.assertFalse(self.controller.running)

    def test_unknown_mode_fails(self):
        cfg = hoic.AttackConfig(
            target_host="127.0.0.1",
            target_port=9,
            mode="Invalid Mode",
            workers=5,
            duration=1,
        )
        ok = self.controller.start(cfg)
        self.assertFalse(ok)
        self.assertFalse(self.controller.running)

    def test_udp_flood_localhost(self):
        cfg = hoic.AttackConfig(
            target_host="127.0.0.1",
            target_port=59999,
            mode="UDP Flood",
            workers=3,
            duration=1,
            packet_size=64,
        )
        ok = self.controller.start(cfg)
        self.assertTrue(ok)
        time.sleep(1.5)
        self.controller.stop()
        final = self.controller.stats.get_stats()
        self.assertGreater(final["sent"], 0)

    def test_tcp_flood_attempt(self):
        cfg = hoic.AttackConfig(
            target_host="127.0.0.1",
            target_port=59998,
            mode="TCP Flood",
            workers=30,
            duration=2,
            packet_size=128,
        )
        ok = self.controller.start(cfg)
        self.assertTrue(ok)
        time.sleep(2.5)
        self.controller.stop()
        stats = self.controller.stats.get_stats()
        # Closed port should produce connection errors or occasional sends
        self.assertGreaterEqual(stats["sent"] + stats["errors"], 1)
        self.assertFalse(self.controller.running)


class TestHttpProbeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)

        async def handler(request):
            await asyncio.sleep(0.01)
            return web.Response(text="ok")

        cls.app = web.Application()
        cls.app.router.add_get("/", handler)
        cls.runner = web.AppRunner(cls.app)
        cls.loop.run_until_complete(cls.runner.setup())
        cls.site = web.TCPSite(cls.runner, "127.0.0.1", 0)
        cls.loop.run_until_complete(cls.site.start())
        sockets = cls.site._server.sockets
        cls.port = sockets[0].getsockname()[1]

    @classmethod
    def tearDownClass(cls):
        cls.loop.run_until_complete(cls.runner.cleanup())
        cls.loop.close()

    def test_http_probe_against_local_server(self):
        logs = []
        controller = hoic.AttackController(
            log_callback=lambda m: logs.append(m),
            stats_callback=lambda s: None,
        )
        cfg = hoic.AttackConfig(
            target_host="127.0.0.1",
            target_port=self.port,
            mode="HTTP Flood",
            workers=5,
            duration=5,
            timeout=3.0,
        )
        url = f"http://127.0.0.1:{self.port}/"
        probe = self.loop.run_until_complete(
            controller._run_http_probe(url, cfg, worker_count=4, duration=2.0, use_ssl=False)
        )
        self.assertGreater(probe["sent"], 0)
        self.assertGreaterEqual(probe["p95_ms"], 0)


class TestAttackConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = hoic.AttackConfig(target_host="localhost", target_port=80, mode="HTTP Flood")
        self.assertEqual(cfg.workers, 150)
        self.assertEqual(cfg.probe_duration, 5)
        self.assertEqual(cfg.saturation_error_threshold, 0.10)


class TestAttackModes(unittest.TestCase):
    def test_saturation_seeker_in_modes(self):
        self.assertIn("Adaptive Saturation Seeker", hoic.ATTACK_MODES)


if __name__ == "__main__":
    unittest.main(verbosity=2)