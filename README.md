# HOIC - High Orbital Ion Cannon

**Modern cross-platform network stress testing tool for authorized security research and penetration testing.**

<p align="center">
  <img src="assets/hoic-logo.svg" alt="HOIC Logo" width="220"/>
</p>

![HOIC Banner](assets/hoic-banner.jpg)

> **CRITICAL LEGAL NOTICE**  
> This tool is provided **strictly for authorized security research, load testing, and penetration testing** where you have **explicit written permission** from the system owner.  
> Unauthorized use against any computer system, network, website, or service is **illegal** in virtually every country and can result in serious criminal prosecution.  
> Wold Labs and contributors accept **zero liability** for misuse.

---

## Features

- **Modern attack vectors**:
  - High-concurrency **HTTP/HTTPS Flood** using `aiohttp` (async)
  - **UDP Flood**
  - **TCP Flood**
  - **Slowloris** (slow HTTP connection exhaustion)
  - **Mixed** mode (HTTP + UDP)
  - **Adaptive Saturation Seeker** — auto-discovers the target's breaking point
  - **Superposition Storm** — self-adapting multi-vector assault (see below)
- **Attack Message** field — embed custom text in HTTP bodies/headers or UDP/TCP payloads (visible in Wireshark)
- Beautiful, functional **dark-themed GUI** built with CustomTkinter
- Real-time statistics (rate, errors, p95 latency, saturation breakpoint, **dominant attack vector**)
- **Export Report** — JSON + human-readable summary for pentest documentation
- Cross-platform: **Windows** and **Linux**
- Unit test suite (`test_hoic.py`)

---

## Superposition Storm

HOIC's most advanced mode. Five attack vectors run in **quantum superposition** simultaneously:

| Vector | What it does |
|--------|----------------|
| `http_get` | Async HTTP flood with randomized headers |
| `http_post` | Large binary POST bursts |
| `udp_burst` | Volumetric UDP datagrams |
| `tcp_connect` | TCP connection + payload storms |
| `slowloris_micro` | Short-lived incomplete HTTP connections |

Every **5 seconds**, a **pain-bandit controller** measures which vector is causing the most errors and latency on the target, then **shifts worker probability** toward that vector — automatically finding and exploiting the target's **weakest layer** (application, connection pool, UDP handler, etc.).

The live stats panel shows the **dominant vector** and its weight. Full vector weight history is included in exported reports.

**Recommended settings:** workers 150–300, duration ≥ 60s.

---

## Adaptive Saturation Seeker

Unlike fixed-rate flood modes, **Adaptive Saturation Seeker** intelligently finds where your target starts to fail:

1. **Binary-search probes** — ramps concurrency in short probe windows and measures error rate + p95 latency at each step.
2. **Breakpoint detection** — identifies the maximum sustainable worker count before errors exceed 10% or p95 latency exceeds 2s.
3. **Resonance wave hold** — after discovery, modulates load in a sine envelope around the breakpoint to expose autoscaling oscillation.

**Recommended settings:** workers slider = max search bound (e.g. 200–400), duration ≥ 60s.

---

## Installation (Windows & Linux)

### Prerequisites

- Python 3.10 or newer
- On Linux: `sudo apt install python3-tk` (or equivalent for your distro)

### Quick Start

```bash
git clone https://github.com/woldlabs/hoic.git
cd hoic

python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
python hoic.py
```

**Easier launchers:**
- Windows: `run-hoic.bat`
- Linux / macOS: `chmod +x run-hoic.sh && ./run-hoic.sh`

### Running Tests

```bash
python -m unittest test_hoic -v
```

---

## Usage

1. Launch `python hoic.py`
2. Accept the legal warning dialog.
3. Enter **target host** and **port**.
4. Select **Attack Mode**.
5. Adjust **Workers** and **Duration**.
6. Optionally set an **Attack Message** (embedded in traffic for packet capture tagging).
7. Check the **authorization checkbox**.
8. Click **START ATTACK**.
9. Monitor live stats and log.
10. **Export Report** when done.

### Recommended Starting Points

| Mode                      | Workers | Notes                              |
|---------------------------|---------|------------------------------------|
| HTTP Flood                | 100-300 | Web app testing                    |
| HTTPS Flood               | 80-200  | TLS overhead                       |
| UDP Flood                 | 150-400 | Layer 4 volumetric                 |
| Slowloris                 | 80-200  | Connection exhaustion              |
| Mixed                     | 120-250 | Combined pressure                  |
| Adaptive Saturation Seeker| 200-400 | Max search bound; duration 60s+    |
| Superposition Storm       | 150-300 | Auto-finds weakest layer; 60s+     |

---

## Modern Methods Explained

- **HTTP/HTTPS Flood**: Async HTTP with randomized headers, POST bodies, latency tracking.
- **UDP/TCP Flood**: High-volume datagrams and connection storms; optional `HOICMSG:` payload prefix.
- **Slowloris**: Incomplete HTTP requests holding connections open.
- **Adaptive Saturation Seeker**: Binary-search concurrency knee + resonance-wave hold.
- **Superposition Storm**: Five vectors in parallel with pain-bandit adaptation toward the weakest target layer.
- **Attack Message**: Cleartext tagging via HTTP POST body, headers, User-Agent suffix, or UDP/TCP payload prefix.

---

## Important Warnings

- **Do not test production systems without permission and a maintenance window.**
- High packet rates can saturate your own uplink or trigger ISP protections.
- HTTPS modes encrypt traffic — use HTTP Flood for cleartext packet inspection.
- This is **not** a stealth tool. Traffic is noisy by design.

---

## Project Structure

```
hoic/
├── hoic.py            # Main application (GUI + attack engine)
├── test_hoic.py       # Unit tests
├── requirements.txt
├── README.md
├── LICENSE
├── run-hoic.bat
├── run-hoic.sh
└── assets/
    ├── hoic-logo.svg
    ├── hoic-logo-1.jpg
    ├── hoic-logo-2.jpg
    └── hoic-banner.jpg
```

---

## License

MIT License — see [LICENSE](LICENSE).

**Use responsibly. Get permission first. Always.**

Developed by [Wold Labs](https://github.com/woldlabs) for legitimate security research tooling.