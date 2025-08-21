# WebRTC VLM Multi-Object Detection Demo

Real-time multi-object detection system that streams live video from a phone via WebRTC, performs inference (client-side WASM or server-side), and overlays detection results in near real-time.

## 🚀 Quick Start (One Command)

### Windows Users

```cmd
# Clone and start demo
git clone <repo-url>
cd webrtc-vlm-detection
start.bat
```

### Linux/macOS Users

```bash
# Clone and start demo
git clone <repo-url>
cd webrtc-vlm-detection
chmod +x start.sh
./start.sh
```

Then:

1. Open http://localhost:3000 on your laptop
2. Click "Start Camera" to test locally, OR
3. For mobile: visit https://localhost:3443 and accept the security certificate
4. Allow camera access → see live object detection!

## 📱 Phone Connection Methods

### Method 1: Local Network (Recommended)

**Windows:**

```cmd
start.bat  # Default mode
```

**Linux/macOS:**

```bash
./start.sh  # Default mode
```

- Phone and laptop must be on same WiFi network
- Open displayed URL on phone: `http://192.168.x.x:3000`

### Method 2: Local Development (No Phone Required)

- Open http://localhost:3000 directly in your browser
- Click "Start Camera" to use your laptop's webcam
- Perfect for testing without mobile device

### Method 3: External Access (if local doesn't work)

**Windows:**

```cmd
# Note: Ngrok support may require additional setup
start.bat --help  # Check available options
```

**Linux/macOS:**

```bash
./start.sh --ngrok
```

- Uses ngrok tunnel for external access
- Works from any network
- Displays public URL for phone access

## 🧠 Inference Modes

### WASM Mode (Low-Resource, Default)

**Windows:**

```cmd
start.bat --mode wasm
```

**Linux/macOS:**

```bash
./start.sh --mode wasm
```

- Client-side inference in browser
- Works on modest laptops (Intel i5, 8GB RAM)
- ~10-15 FPS processing at 320×240 resolution
- CPU usage: 15-25%

### Server Mode (Higher Performance)

**Windows:**

```cmd
start.bat --mode server
```

**Linux/macOS:**

```bash
./start.sh --mode server
```

- Server-side ONNX inference
- Better accuracy and performance
- Requires model download (automatic)
- CPU usage: 30-50%

## 📊 Benchmarking

**Linux/macOS:**

```bash
# Run 30-second benchmark
./bench/run_bench.sh --duration 30 --mode wasm

# Server mode benchmark
./bench/run_bench.sh --duration 60 --mode server

# Custom output file
./bench/run_bench.sh --duration 30 --output my_results.json
```

**Windows:**

```cmd
# Note: Benchmarking scripts are primarily for Linux/macOS
# For Windows, monitor performance via browser dev tools
# or Task Manager while running the demo
```

Generates `metrics.json` with:

- Median & P95 end-to-end latency
- Processed FPS
- Uplink/downlink bandwidth
- System resource usage

## 🛠️ Installation & Setup

### Prerequisites

- **Docker & Docker Compose** (Recommended - works on all platforms)
- **Git**
- **Modern browser** (Chrome/Safari/Edge)

### Windows Quick Setup

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/install/)
2. Clone this repository
3. Open Command Prompt or PowerShell in the project directory
4. Run: `start.bat`
5. Open http://localhost:3000 in your browser

### Alternative: Local Development Mode (Windows)

If you prefer not to use Docker:

1. Install [Python 3.9+](https://python.org)
2. Run: `start_local.bat`
3. This will set up a virtual environment and start the server

### Manual Setup (if Docker unavailable)

```bash
# Backend
pip install -r requirements.txt
```

**Frontend (if running separately):**
```bash
cd frontend
npm install
npm start
```

## Windows Users Notes

### Available Batch Files

- **`start.bat`** - Main starter script (uses Docker)
  - `start.bat` - Default WASM mode
  - `start.bat --mode server` - Server-side inference
  - `start.bat --debug` - Enable debug logging
  - `start.bat --help` - Show all options

- **`start_local.bat`** - Local development without Docker
  - Automatically creates Python virtual environment
  - Installs dependencies and starts the server
  - Good for development or if Docker is not available

### Commands Reference for Windows

```cmd
# Start with Docker (recommended)
start.bat

# Start with server-side inference
start.bat --mode server

# Local development mode (no Docker)
start_local.bat

# View help and options
start.bat --help
```

### Troubleshooting Windows

1. **Docker not found**: Install Docker Desktop from the official website
2. **Python not found**: Install Python 3.9+ and add to PATH
3. **Port conflicts**: Close other applications using ports 3000 or 3443
4. **Certificate errors**: Accept the self-signed certificate warning in your browser

## Platform Support

- **Windows** - Full support with `.bat` files
- **Linux** - Full support with `.sh` scripts
- **macOS** - Full support with `.sh` scripts
- **Docker** - Cross-platform containerized deployment

## Quick Windows Setup Summary

1. **Clone the repository**
2. **For Docker users**: Run `start.bat`
3. **For local development**: Run `start_local.bat`
4. **Open browser**: Navigate to http://localhost:3000
5. **Start detecting**: Use your webcam or mobile device
