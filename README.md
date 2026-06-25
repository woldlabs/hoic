# HOIC - High Orbital Ion Cannon

**Modern cross-platform network stress testing tool for authorized security research and penetration testing.**

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
  - **Adaptive Saturation Seeker** — auto-discovers the target's breaking point (see below)
- Beautiful, functional **dark-themed GUI** built with CustomTkinter
- Real-time statistics (rate, total sent, errors, elapsed, **p95 latency**, **saturation breakpoint**)
- Configurable workers, duration, and packet size
- **Export Report** button — saves JSON + human-readable summary of the run (ideal for pentest documentation)
- Cross-platform: **Windows** and **Linux**
- Built-in header randomization and modern browser User-Agents
- Explicit authorization checkbox + final confirmation dialog
- Auto-stop timer
- Unit test suite (`test_hoic.py`) for core engine logic

---

## Adaptive Saturation Seeker (New)

Unlike fixed-rate flood modes, **Adaptive Saturation Seeker** intelligently finds where your target starts to fail:

1. **Binary-search probes** — ramps concurrency in short probe windows and measures error rate + p95 latency at each step.
2. **Breakpoint detection** — identifies the maximum sustainable worker count before errors exceed 10% or p95 latency exceeds 2s.
3. **Resonance wave hold** — after discovery, modulates load in a sine envelope around the breakpoint to expose autoscaling oscillation and flash-crowd instability patterns that constant-rate tools miss.

The discovered breakpoint appears live in the stats panel and is included in exported reports with full probe history — invaluable for capacity planning and pentest documentation.

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

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows (PowerShell / CMD)

pip install -r requirements.txt

python hoic.py
```

**Easier cross-platform launchers** (auto setup venv + deps):
- Windows: double-click `run-hoic.bat`
- Linux / macOS: `chmod +x run-hoic.sh && ./run-hoic.sh`

On Windows you can also double-click `hoic.py` after installing dependencies (or create a shortcut).

### Requirements

See [requirements.txt](requirements.txt):

- customtkinter
- aiohttp
- pillow

### Running Tests

```bash
python -m unittest test_hoic -v
```

---

## Usage

1. Launch `python hoic.py`
2. Read and accept the legal warning dialog.
3. Enter the **target host** (domain or IP) and **port**.
4. Select **Attack Mode**.
5. Adjust **Workers** (concurrency) and **Duration**.
6. **Check the authorization checkbox** — you must have explicit permission.
7. Click **START ATTACK**.
8. Monitor live stats and log.
9. Click **STOP** or wait for duration to expire.
10. Use **Export Report** for a JSON + summary file of the run (great for documentation).

### Recommended Starting Points for Research

| Mode                      | Workers | Notes                              |
|---------------------------|---------|------------------------------------|
| HTTP Flood                | 100-300 | Good for web app testing           |
| HTTPS Flood               | 80-200  | TLS adds overhead                  |
| UDP Flood                 | 150-400 | Layer 4 volumetric                 |
| Slowloris                 | 80-200  | Connection exhaustion              |
| Mixed                     | 120-250 | Combined pressure                  |
| Adaptive Saturation Seeker| 200-400 | Max search bound; duration 60s+    |

Start low and increase while monitoring the target and your own network.

---

## Screenshots

The GUI features:
- Clear live stats panel (including p95 latency and saturation breakpoint)
- Scrollable activity log
- Prominent legal warning strip

---

## Modern Methods Explained

- **HTTP/HTTPS Flood**: Uses asynchronous HTTP client with randomized headers, query strings, and optional POST payloads. High concurrency without thread explosion. Tracks per-request latency percentiles.
- **UDP Flood**: Sends large numbers of UDP datagrams to exhaust bandwidth / application processing.
- **TCP Flood**: Opens many connections and sends data bursts.
- **Slowloris**: Holds many connections open by sending incomplete HTTP requests and periodic keep-alive headers.
- **Adaptive Saturation Seeker**: Binary-searches concurrency to find the performance knee, then applies resonance-wave modulation to stress autoscaling systems.
- Header rotation, random referers, and X- headers help bypass naive filters for realistic testing scenarios.

---

## Important Warnings

- **Do not test production systems without permission and a maintenance window.**
- High packet rates can saturate your own uplink or trigger ISP protections.
- Some attack types (especially raw sockets) may require administrator/root privileges on certain platforms.
- This is **not** a stealth tool. Traffic is noisy by design.

---

## Building a Standalone Executable (Optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "assets;assets" hoic.py
```

On Linux use `--add-data "assets:assets"`.

---

## Project Structure

```
hoic/
├── hoic.py            # Main application (GUI + attack engine)
├── test_hoic.py       # Unit tests for core logic
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

## Contributing

Pull requests for improved attack realism, better UX, proxy support, or documentation are welcome — but **only** if they maintain the strict authorized-use focus.

---

## License

MIT License — see [LICENSE](LICENSE).

**Remember**: Having source code access does **not** grant you permission to attack anyone.

---

## Credits

Developed by Wold Labs for legitimate security research tooling.

**Use responsibly. Get permission first. Always.**