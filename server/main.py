#!/usr/bin/env python3
"""
WebRTC VLM Object Detection Server
Real-time multi-object detection with WebRTC streaming
"""

import sys
from pathlib import Path
import asyncio
import json
import logging
import os
import time
from io import BytesIO
import base64
import socket
import ssl
from dotenv import load_dotenv

import aiohttp
from aiohttp import web, WSMsgType
import qrcode

# Load environment variables from .env file
load_dotenv()

# Add server directory to path to allow relative imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from webrtc_handler import WebRTCHandler
from inferencr_engine import InferenceEngine
from metrics_collector import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG', 'false').lower() == 'true' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DetectionServer:
    def __init__(self):
        self.mode = os.getenv('MODE', 'wasm').lower()
        self.host = '0.0.0.0'
        self.port = 3000
        self.https_port = 3443  # HTTPS port
        self.ws_port = 8765
        self.use_https = os.getenv('HTTPS', 'true').lower() == 'true'
        
        # Initialize components
        self.webrtc_handler = WebRTCHandler()
        self.inference_engine = InferenceEngine(mode=self.mode)
        self.metrics_collector = MetricsCollector()
        
        # Active connections
        self.websockets = set()
        
        logger.info(f"🚀 Initializing DetectionServer in {self.mode.upper()} mode")
        if self.use_https:
            logger.info("🔐 HTTPS enabled for mobile camera support")

    def get_local_ip(self):
        """Get local IP address - for mobile QR codes, we need the host machine IP"""
        try:
            # Method 1: Check environment variable for host IP
            host_ip = os.getenv('HOST_IP')
            if host_ip:
                logger.info(f"Using HOST_IP environment variable: {host_ip}")
                return host_ip
            
            # Method 2: Try to connect to external server to get IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                detected_ip = s.getsockname()[0]
                
                # If running in Docker, this might be the container IP
                # Check if it's a typical Docker internal IP
                if detected_ip.startswith(('172.17.', '172.18.', '172.19.', '172.20.')):
                    logger.warning(f"Detected Docker internal IP: {detected_ip}")
                    logger.warning("For mobile access, set HOST_IP environment variable to your machine's IP")
                    logger.warning("Example: docker-compose up with HOST_IP=192.168.1.100")
                    # Try to guess the host IP based on common patterns
                    if detected_ip.startswith('172.20.'):
                        # For 172.20.x.x networks, try some common host IPs
                        for host_suffix in ['217.125', '0.1', '10.1']:
                            test_ip = f"172.20.{host_suffix}"
                            logger.info(f"Trying host IP: {test_ip}")
                            return test_ip
                
                return detected_ip
                
        except Exception as e:
            logger.warning(f"Could not determine local IP: {e}")
            return "127.0.0.1"

    def generate_qr_code(self, url):
        """Generate QR code for phone access"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()

    async def qr_handler(self, request):
        """Serve a QR PNG for the given `data` or `text` query param (same-origin)."""
        data = request.query.get('data') or request.query.get('text')
        if not data:
            # default to mobile page for better mobile experience
            local_ip = self.get_local_ip()
            protocol = 'https' if self.use_https else 'http'
            port = self.https_port if self.use_https else self.port
            data = f"{protocol}://{local_ip}:{port}/mobile"

        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return web.Response(body=buf.getvalue(), content_type='image/png')
        except Exception as e:
            logger.error(f"QR generation error: {e}")
            return web.Response(status=500, text='QR generation failed')

    async def websocket_handler(self, request):
        """Handle WebSocket connections for signaling and data"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        logger.info(f"📱 New WebSocket connection. Total: {len(self.websockets)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_websocket_message(ws, data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.websockets.discard(ws)
            logger.info(f"📱 WebSocket disconnected. Total: {len(self.websockets)}")
        
        return ws

    async def handle_websocket_message(self, ws, data):
        """Process WebSocket messages"""
        msg_type = data.get('type')
        
        if msg_type == 'offer':
            # Handle WebRTC offer
            answer = await self.webrtc_handler.handle_offer(data['sdp'])
            await ws.send_str(json.dumps({
                'type': 'answer',
                'sdp': answer
            }))
            
        elif msg_type == 'ice-candidate':
            # Handle ICE candidate
            await self.webrtc_handler.add_ice_candidate(data['candidate'])
            
        elif msg_type == 'frame':
            # Handle video frame for inference
            if self.mode == 'server':
                await self.process_frame_server_mode(ws, data)
            # In WASM mode, inference happens client-side
            
        elif msg_type == 'metrics-request':
            # Send current metrics
            metrics = self.metrics_collector.get_current_metrics()
            await ws.send_str(json.dumps({
                'type': 'metrics',
                'data': metrics
            }))

    async def process_frame_server_mode(self, ws, frame_data):
        """Process frame in server mode with inference"""
        try:
            frame_id = frame_data.get('frame_id')
            capture_ts = frame_data.get('capture_ts')
            image_data = frame_data.get('image_data')  # Base64 encoded
            
            recv_ts = int(time.time() * 1000)
            
            # Run inference
            detections = await self.inference_engine.detect_objects(image_data)
            inference_ts = int(time.time() * 1000)
            
            # Prepare response
            response = {
                'type': 'detections',
                'frame_id': frame_id,
                'capture_ts': capture_ts,
                'recv_ts': recv_ts,
                'inference_ts': inference_ts,
                'detections': detections
            }
            
            # Send back to client
            await ws.send_str(json.dumps(response))
            
            # Record metrics
            self.metrics_collector.record_frame(
                capture_ts, recv_ts, inference_ts, len(detections)
            )
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")

    async def index_handler(self, request):
        """Serve the main page"""
        # Generate QR code for current URL - use dynamic local IP
        local_ip = self.get_local_ip()
        
        # Use HTTPS if enabled, otherwise HTTP
        protocol = 'https' if self.use_https else 'http'
        port = self.https_port if self.use_https else self.port
        current_url = f"{protocol}://{local_ip}:{port}/demo"
        
        qr_code = self.generate_qr_code(current_url)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>WebRTC VLM Object Detection</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .mode-badge {{ 
            background: {'#4CAF50' if self.mode == 'wasm' else '#2196F3'}; 
            color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px;
        }}
        .demo-section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .video-container {{ position: relative; margin: 20px 0; }}
        #localVideo, #remoteVideo {{ width: 100%; max-width: 640px; border-radius: 8px; background: #000; }}
        .overlay-canvas {{ position: absolute; top: 0; left: 0; pointer-events: none; }}
        .qr-section {{ text-align: center; }}
        .qr-code {{ max-width: 200px; margin: 10px; }}
        .metrics {{ background: #263238; color: #fff; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 14px; }}
        .controls {{ text-align: center; margin: 20px 0; }}
        .btn {{ 
            background: #1976D2; color: white; border: none; padding: 12px 24px; 
            border-radius: 6px; cursor: pointer; margin: 5px; font-size: 14px;
        }}
        .btn:hover {{ background: #1565C0; }}
        .btn.danger {{ background: #D32F2F; }}
        .btn.danger:hover {{ background: #C62828; }}
        .status {{ padding: 10px; border-radius: 4px; margin: 10px 0; }}
        .status.connected {{ background: #E8F5E8; color: #2E7D32; }}
        .status.connecting {{ background: #FFF3E0; color: #F57C00; }}
        .status.disconnected {{ background: #FFEBEE; color: #C62828; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 WebRTC VLM Object Detection</h1>
            <span class="mode-badge">{self.mode.upper()} MODE</span>
            <div id="connection-status" class="status disconnected">🔴 Disconnected</div>
        </div>
        
        <div class="demo-section">
            <h2>🎥 Live Demo</h2>
            <div class="video-container">
                <video id="localVideo" autoplay muted playsinline></video>
                <canvas id="overlayCanvas" class="overlay-canvas"></canvas>
            </div>
            <div class="controls">
                <button id="startBtn" class="btn">📹 Start Camera</button>
                <button id="stopBtn" class="btn danger" disabled>⏹️ Stop</button>
                <button id="benchBtn" class="btn">📊 Run Benchmark</button>
            </div>
        </div>
        
        <div class="demo-section qr-section">
            <h2>📱 Connect Your Phone</h2>
            <p>Scan this QR code with your phone camera:</p>
            <img src="data:image/png;base64,{qr_code}" alt="QR Code" class="qr-code">
            <p><strong>URL:</strong> <code>{current_url}</code></p>
            <p><small>Make sure your phone and laptop are on the same network</small></p>
        </div>
        
        <div class="demo-section">
            <h2>📊 Real-time Metrics</h2>
            <div id="metrics" class="metrics">
                Connecting to metrics stream...
            </div>
        </div>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
"""
        return web.Response(text=html_content, content_type='text/html')

    async def static_handler(self, request):
        """Serve static files"""
        filename = request.match_info['filename']
        static_dir = Path(__file__).parent.parent / 'static'
        file_path = static_dir / filename
        
        if file_path.exists():
            return web.FileResponse(file_path)
        else:
            return web.Response(status=404, text="File not found")

    async def models_handler(self, request):
        """Serve model files from the ./models directory"""
        filename = request.match_info['filename']
        models_dir = Path(__file__).parent.parent / 'models'
        file_path = models_dir / filename

        if file_path.exists():
            return web.FileResponse(file_path)
        else:
            return web.Response(status=404, text="Model not found")

    async def ip_handler(self, request):
        """Return server's local IP address for mobile QR codes"""
        local_ip = self.get_local_ip()
        return web.json_response({'ip': local_ip})
    
    async def config_handler(self, request):
        """Serve detection configuration from environment variables"""
        config = {
            'engine': os.getenv('DETECTION_ENGINE', 'gemini'),
            'openrouter_api_key': os.getenv('OPENROUTER_API_KEY', ''),
            'detection_interval': int(os.getenv('DETECTION_INTERVAL', '2000')),
            'confidence_threshold': float(os.getenv('CONFIDENCE_THRESHOLD', '0.5')),
            'max_detections': int(os.getenv('MAX_DETECTIONS', '8'))
        }
        return web.json_response(config)
    
    async def metrics_handler(self, request):
        """API endpoint for metrics"""
        metrics = self.metrics_collector.get_current_metrics()
        return web.json_response(metrics)

    def create_ssl_context(self):
        """Create SSL context for HTTPS"""
        try:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            # Path to certificate files
            cert_file = Path(__file__).parent.parent / 'certs' / 'localhost.crt'
            key_file = Path(__file__).parent.parent / 'certs' / 'localhost.key'
            
            if not cert_file.exists() or not key_file.exists():
                logger.error("❌ SSL certificate files not found!")
                logger.info("💡 Run: python generate_cert.py")
                return None
                
            ssl_context.load_cert_chain(str(cert_file), str(key_file))
            logger.info("✅ SSL context created successfully")
            return ssl_context
            
        except Exception as e:
            logger.error(f"❌ Failed to create SSL context: {e}")
            return None

    def create_app(self):
        """Create the web application"""
        app = web.Application()

        # Add security middleware to enable cross-origin isolation (needed for wasm threads / SharedArrayBuffer)
        @web.middleware
        async def security_middleware(request, handler):
            response = await handler(request)
            # These headers enable crossOriginIsolated in supporting browsers when all resources allow it
            response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
            response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
            return response

        app.middlewares.append(security_middleware)

        # Routes
        app.router.add_get('/', self.root_handler)  # Serve main camera UI at root
        app.router.add_get('/landing', self.landing_handler)  # Landing page for protocol selection
        app.router.add_get('/demo', self.index_handler)  # Main demo page
        app.router.add_get('/ws', self.websocket_handler)
        app.router.add_get('/api/metrics', self.metrics_handler)
        app.router.add_get('/api/ip', self.ip_handler)  # Get server IP for mobile QR codes
        app.router.add_get('/api/config', self.config_handler)  # Get detection configuration from .env
        app.router.add_get('/static/{filename}', self.static_handler)
        app.router.add_get('/models/{filename}', self.models_handler)
        app.router.add_get('/qr', self.qr_handler)  # QR code generator endpoint
        app.router.add_get('/test', self.mobile_test_handler)  # Mobile test page
        app.router.add_get('/mobile', self.mobile_handler)  # Mobile optimized page

        return app

    async def landing_handler(self, request):
        """Serve landing page to help users choose HTTP/HTTPS"""
        static_dir = Path(__file__).parent.parent / 'static'
        landing_file = static_dir / 'landing.html'
        
        if landing_file.exists():
            # Read the file and replace placeholders with actual IPs
            with open(landing_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            local_ip = self.get_local_ip()
            content = content.replace('172.20.19.211', local_ip)
            
            return web.Response(text=content, content_type='text/html')
        else:
            return web.Response(status=404, text="Landing page not found")

    async def root_handler(self, request):
        """Serve the main camera UI (index.html) at the root path '/'"""
        static_dir = Path(__file__).parent.parent / 'static'
        index_file = static_dir / 'index.html'

        if index_file.exists():
            return web.FileResponse(index_file)
        else:
            # Fallback to the demo handler if static index is missing
            return await self.index_handler(request)

    async def mobile_test_handler(self, request):
        """Serve mobile camera test page"""
        static_dir = Path(__file__).parent.parent / 'static'
        test_file = static_dir / 'mobile-camera-test.html'
        
        if test_file.exists():
            return web.FileResponse(test_file)
        else:
            return web.Response(status=404, text="Test page not found")
    
    async def mobile_handler(self, request):
        """Serve mobile optimized page"""
        static_dir = Path(__file__).parent.parent / 'static'
        mobile_file = static_dir / 'mobile.html'
        
        if mobile_file.exists():
            return web.FileResponse(mobile_file)
        else:
            return web.Response(status=404, text="Mobile page not found")

    async def run(self):
        """Start the server"""
        app = self.create_app()
        
        runner = web.AppRunner(app)
        await runner.setup()
        # Start HTTP server (for fallback/development)
        try:
            http_site = web.TCPSite(runner, self.host, self.port)
            await http_site.start()
            logger.info(f"🌐 HTTP Server running on http://{self.host}:{self.port}")
        except OSError as e:
            logger.warning(f"⚠️ Could not bind HTTP port {self.port}: {e}")
            # Find a free ephemeral port and retry
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.host, 0))
                free_port = s.getsockname()[1]
            self.port = free_port
            http_site = web.TCPSite(runner, self.host, self.port)
            await http_site.start()
            logger.info(f"🌐 HTTP Server running on http://{self.host}:{self.port} (auto-selected)")

        # Start HTTPS server if enabled
        if self.use_https:
            ssl_context = self.create_ssl_context()
            if ssl_context:
                try:
                    https_site = web.TCPSite(runner, self.host, self.https_port, ssl_context=ssl_context)
                    await https_site.start()
                    logger.info(f"🔐 HTTPS Server running on https://{self.host}:{self.https_port}")
                except OSError as e:
                    logger.warning(f"⚠️ Could not bind HTTPS port {self.https_port}: {e}")
                    # Find a free ephemeral port and retry for HTTPS
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind((self.host, 0))
                        free_https = s.getsockname()[1]
                    self.https_port = free_https
                    https_site = web.TCPSite(runner, self.host, self.https_port, ssl_context=ssl_context)
                    await https_site.start()
                    logger.info(f"🔐 HTTPS Server running on https://{self.host}:{self.https_port} (auto-selected)")
                
                local_ip = self.get_local_ip()
                logger.info(f"📱 Mobile URL (HTTPS): https://{local_ip}:{self.https_port}")
                logger.info(f"� Desktop URL (HTTP): http://{local_ip}:{self.port}")
            else:
                logger.warning("⚠️ HTTPS disabled due to SSL context creation failure")
                self.use_https = False
        
        logger.info(f"📱 Mode: {self.mode.upper()}")
        
        # Keep server running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("🛑 Shutting down server...")
            await runner.cleanup()

if __name__ == "__main__":
    server = DetectionServer()
    
    # Check if models exist for server mode
    if server.mode == 'server':
        model_path = Path("models/yolov5n.onnx")
        if not model_path.exists():
            logger.error("❌ Model file not found. Please ensure yolov5n.onnx is in ./models/")
            logger.info("💡 Run: wget https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5n.onnx -O models/yolov5n.onnx")
            exit(1)
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")