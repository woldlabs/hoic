# HOIC - High Orbital Ion Cannon

**Modern cross-platform network stress testing tool for authorized security research and penetration testing.**

![HOIC Logo](assets/hoic-logo.svg)

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
- Beautiful, functional **dark-themed GUI** built with CustomTkinter
- Real-time statistics (rate, total sent, errors, elapsed)
- Configurable workers, duration, and packet size
- Cross-platform: **Windows** and **Linux**
- Built-in header randomization and modern browser User-Agents
- Explicit authorization checkbox + final confirmation dialog
- Auto-stop timer

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

On Windows you can also double-click `hoic.py` after installing dependencies (or create a shortcut).

### Requirements

See [requirements.txt](requirements.txt):

- customtkinter
- aiohttp

---

## Unique Logo

The HOIC logo is a custom-designed stylized high-orbit satellite firing a piercing ion/laser beam. The primary asset is a clean vector SVG for perfect rendering at any size:

![Logo](assets/hoic-logo.svg)

Raster versions of the generated satellite laser artwork are also available in the `assets/` folder (or generate new ones for your fork).

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

### Recommended Starting Points for Research

| Mode            | Workers | Notes                              |
|-----------------|---------|------------------------------------|
| HTTP Flood      | 100-300 | Good for web app testing           |
| HTTPS Flood     | 80-200  | TLS adds overhead                  |
| UDP Flood       | 150-400 | Layer 4 volumetric                 |
| Slowloris       | 80-200  | Connection exhaustion              |
| Mixed           | 120-250 | Combined pressure                  |

Start low and increase while monitoring the target and your own network.

---

## Modern Methods Explained

- **HTTP/HTTPS Flood**: Uses asynchronous HTTP client with randomized headers, query strings, and optional POST payloads. High concurrency without thread explosion.
- **UDP Flood**: Sends large numbers of UDP datagrams to exhaust bandwidth / application processing.
- **TCP Flood**: Opens many connections and sends data bursts.
- **Slowloris**: Holds many connections open by sending incomplete HTTP requests and periodic keep-alive headers.
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
├── requirements.txt
├── README.md
├── LICENSE
├── run-hoic.bat
├── run-hoic.sh
└── assets/
    └── hoic-logo.svg   # Unique satellite laser vector logo
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

Unique satellite laser logo designed for this project.

**Use responsibly. Get permission first. Always.**
