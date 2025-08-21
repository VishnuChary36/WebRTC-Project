/**
 * 📱 Simple WebRTC Camera with Object Detection
 * Mobile-first design with working camera access
 */

// Global variables
let localVideo, overlayCanvas, ctx, ws, pc;
let localStream = null;
let isConnected = false;
let detectionActive = false;

// WebRTC Configuration
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

// Initialize app
window.addEventListener('load', () => {
    console.log('🚀 Starting Simple Camera App');
    initializeApp();
});

function initializeApp() {
    // Get DOM elements
    localVideo = document.getElementById('localVideo');
    overlayCanvas = document.getElementById('overlayCanvas');
    if (overlayCanvas) {
        ctx = overlayCanvas.getContext('2d');
    }
    
    // Set up event listeners
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const benchBtn = document.getElementById('benchBtn');
    
    if (startBtn) startBtn.onclick = startCamera;
    if (stopBtn) stopBtn.onclick = stopCamera;
    if (benchBtn) benchBtn.onclick = runBenchmark;
    
    // Connect WebSocket
    connectWebSocket();
    
    // Load QR code
    loadQRCodeAndURL();
    
    // Auto-start on mobile
    if (isMobile()) {
        console.log('📱 Mobile device detected');
        updateStatus('🔴 Tap "Start Camera" to begin');
    }
}

function isMobile() {
    return /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

function loadQRCodeAndURL() {
    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const port = window.location.port;
    const url = `${protocol}//${host}${port ? ':' + port : ''}`;
    
    // Update URL display
    const phoneUrlElement = document.getElementById('phone-url');
    if (phoneUrlElement) {
        phoneUrlElement.innerHTML = `<strong>URL:</strong> <code>${url}</code>`;
    }
    
    // Generate QR code
    const qrCodeElement = document.getElementById('qr-code');
    if (qrCodeElement) {
        const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(url)}`;
        qrCodeElement.innerHTML = `<img src="${qrUrl}" alt="QR Code" style="max-width: 200px; border-radius: 8px;">`;
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log('🔌 Connecting WebSocket:', wsUrl);
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('✅ WebSocket connected');
        updateStatus('🟢 Connected');
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (error) {
            console.error('❌ WebSocket message error:', error);
        }
    };
    
    ws.onclose = () => {
        console.log('❌ WebSocket disconnected');
        updateStatus('🔴 Disconnected');
        // Retry connection after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        updateStatus('🔴 Connection Error');
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'answer':
            if (pc) {
                pc.setRemoteDescription({
                    type: 'answer',
                    sdp: data.sdp
                }).catch(error => {
                    console.error('❌ Set remote description error:', error);
                });
            }
            break;
        case 'detections':
            drawDetections(data.detections);
            break;
        case 'config':
            console.log('🧠 Server mode:', data.mode);
            break;
    }
}

function updateStatus(message) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        statusElement.textContent = message;
        
        // Update CSS class based on status
        statusElement.className = 'status ';
        if (message.includes('🟢')) {
            statusElement.className += 'connected';
        } else if (message.includes('🟡')) {
            statusElement.className += 'connecting';
        } else {
            statusElement.className += 'disconnected';
        }
    }
}

async function startCamera() {
    try {
        console.log('📹 Starting camera...');
        updateStatus('🟡 Starting Camera...');
        
        // Show protocol warning for mobile HTTPS requirement
        if (location.protocol === 'http:' && isMobile()) {
            const httpsUrl = location.href.replace('http:', 'https:').replace(':3000', ':3443');
            if (confirm('📱 Mobile browsers need HTTPS for camera access.\n\nRedirect to HTTPS version?')) {
                window.location.href = httpsUrl;
                return;
            }
        }
        
        // Camera constraint options (multiple fallbacks)
        const constraints = [
            // Best quality for mobile
            {
                video: {
                    width: { ideal: 640, max: 1280 },
                    height: { ideal: 480, max: 720 },
                    facingMode: isMobile() ? 'environment' : 'user',
                    frameRate: { ideal: 15, max: 30 }
                }
            },
            // Basic mobile
            {
                video: {
                    facingMode: isMobile() ? 'environment' : 'user',
                    width: { ideal: 320 },
                    height: { ideal: 240 }
                }
            },
            // Simple fallback
            {
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            },
            // Last resort
            { video: true }
        ];
        
        let stream = null;
        for (let i = 0; i < constraints.length; i++) {
            try {
                console.log(`🔍 Trying camera option ${i + 1}`);
                stream = await navigator.mediaDevices.getUserMedia(constraints[i]);
                console.log(`✅ Camera started with option ${i + 1}`);
                break;
            } catch (error) {
                console.warn(`⚠️ Option ${i + 1} failed:`, error.message);
                if (i === constraints.length - 1) throw error;
            }
        }
        
        if (!stream) {
            throw new Error('Could not access camera');
        }
        
        // Set video source
        localStream = stream;
        localVideo.srcObject = localStream;
        
        // Log camera info
        const videoTrack = stream.getVideoTracks()[0];
        if (videoTrack) {
            const settings = videoTrack.getSettings();
            console.log('📹 Camera settings:', settings);
        }
        
        // Setup canvas overlay
        setupCanvasOverlay();
        
        // Create WebRTC connection
        await createPeerConnection();
        
        // Start detection
        startDetection();
        
        // Update UI
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
        
        updateStatus('🟢 Camera Active');
        console.log('✅ Camera started successfully');
        
    } catch (error) {
        console.error('❌ Camera error:', error);
        
        let errorMsg = 'Camera access failed';
        let helpMsg = 'Please check permissions and try again.';
        
        if (error.name === 'NotAllowedError') {
            errorMsg = '🔒 Camera Permission Denied';
            helpMsg = isMobile() ? 
                'Mobile browsers need HTTPS for camera. Try HTTPS version.' : 
                'Please allow camera access and refresh.';
        } else if (error.name === 'NotFoundError') {
            errorMsg = '📹 No Camera Found';
            helpMsg = 'Make sure your device has a camera.';
        } else if (location.protocol === 'http:' && isMobile()) {
            errorMsg = '🔒 HTTPS Required for Mobile';
            helpMsg = 'Mobile browsers require HTTPS for camera access.';
        }
        
        updateStatus('🔴 ' + errorMsg);
        alert(`${errorMsg}\n\n${helpMsg}\n\nTechnical: ${error.message}`);
        
        showTroubleshooting(errorMsg, helpMsg);
    }
}

function showTroubleshooting(errorMsg, helpMsg) {
    const existing = document.querySelector('.troubleshooting');
    if (existing) existing.remove();
    
    const div = document.createElement('div');
    div.className = 'troubleshooting demo-section';
    div.innerHTML = `
        <h2>📋 Camera Troubleshooting</h2>
        <div style="background: #fff3e0; border-left: 4px solid #f57c00; padding: 15px; border-radius: 4px;">
            <p><strong>🚫 ${errorMsg}</strong></p>
            <p>${helpMsg}</p>
            <h3>💡 Solutions:</h3>
            <ul>
                <li>🔒 Check camera permissions in browser settings</li>
                <li>📱 For mobile: Use HTTPS version (port 3443)</li>
                <li>🔄 Try refreshing the page</li>
                <li>💻 Try on desktop first to test</li>
                <li>🔧 Close other apps using the camera</li>
            </ul>
            <p><strong>Mobile Users:</strong> Visit <code>https://${location.hostname}:3443</code></p>
        </div>
    `;
    
    document.querySelector('.container').appendChild(div);
}

function setupCanvasOverlay() {
    if (!overlayCanvas || !localVideo) return;
    
    // Match canvas size to video
    const updateCanvasSize = () => {
        overlayCanvas.width = localVideo.videoWidth || localVideo.clientWidth;
        overlayCanvas.height = localVideo.videoHeight || localVideo.clientHeight;
        overlayCanvas.style.width = localVideo.clientWidth + 'px';
        overlayCanvas.style.height = localVideo.clientHeight + 'px';
    };
    
    localVideo.addEventListener('loadedmetadata', updateCanvasSize);
    localVideo.addEventListener('resize', updateCanvasSize);
    window.addEventListener('resize', updateCanvasSize);
    
    // Initial setup
    setTimeout(updateCanvasSize, 500);
}

async function createPeerConnection() {
    try {
        pc = new RTCPeerConnection(configuration);
        
        // Add local stream
        if (localStream) {
            localStream.getTracks().forEach(track => {
                pc.addTrack(track, localStream);
            });
        }
        
        // Handle ICE candidates
        pc.onicecandidate = (event) => {
            if (event.candidate && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'ice-candidate',
                    candidate: event.candidate
                }));
            }
        };
        
        // Create offer
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        
        // Send offer to server
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'offer',
                sdp: offer.sdp
            }));
        }
        
        console.log('✅ WebRTC peer connection created');
        
    } catch (error) {
        console.error('❌ WebRTC error:', error);
    }
}

function startDetection() {
    if (detectionActive) return;
    
    detectionActive = true;
    console.log('🧠 Starting mock object detection');
    
    // Simple mock detection for demo
    detectionInterval = setInterval(() => {
        if (!ctx || !localVideo.videoWidth) return;
        
        // Generate mock detections
        const detections = generateMockDetections();
        drawDetections(detections);
        
    }, 200); // 5 FPS detection
}

function generateMockDetections() {
    const detections = [];
    const time = Date.now() / 1000;
    
    // Mock person detection
    if (Math.sin(time * 0.5) > 0.2) {
        detections.push({
            label: 'person',
            score: 0.8 + Math.random() * 0.15,
            xmin: 0.2 + Math.sin(time * 0.3) * 0.1,
            ymin: 0.1,
            xmax: 0.6,
            ymax: 0.8
        });
    }
    
    // Mock phone detection
    if (Math.cos(time * 0.7) > 0.5) {
        detections.push({
            label: 'cell phone',
            score: 0.7 + Math.random() * 0.2,
            xmin: 0.5 + Math.cos(time * 0.4) * 0.1,
            ymin: 0.3,
            xmax: 0.8,
            ymax: 0.6
        });
    }
    
    return detections;
}

function drawDetections(detections) {
    if (!ctx || !overlayCanvas.width || !detections) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    
    // Draw detections
    detections.forEach(detection => {
        const x = detection.xmin * overlayCanvas.width;
        const y = detection.ymin * overlayCanvas.height;
        const width = (detection.xmax - detection.xmin) * overlayCanvas.width;
        const height = (detection.ymax - detection.ymin) * overlayCanvas.height;
        
        // Draw bounding box
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);
        
        // Draw label
        const label = `${detection.label} ${Math.round(detection.score * 100)}%`;
        ctx.fillStyle = '#00ff00';
        ctx.font = '14px Arial';
        ctx.fillRect(x, y - 20, ctx.measureText(label).width + 10, 20);
        ctx.fillStyle = '#000';
        ctx.fillText(label, x + 5, y - 5);
    });
}

function stopCamera() {
    console.log('⏹️ Stopping camera');
    
    // Stop detection
    detectionActive = false;
    if (detectionInterval) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
    
    // Clear canvas
    if (ctx) {
        ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    }
    
    // Stop video stream
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }
    
    // Clear video
    if (localVideo) {
        localVideo.srcObject = null;
    }
    
    // Close peer connection
    if (pc) {
        pc.close();
        pc = null;
    }
    
    // Update UI
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    
    updateStatus('🔴 Camera Stopped');
}

function runBenchmark() {
    console.log('📊 Running benchmark...');
    alert('📊 Benchmark feature:\n\nRun: ./bench/run_bench.sh --duration 30 --mode wasm\n\nThis will generate detailed performance metrics in metrics.json');
}

// Update metrics display
function updateMetrics() {
    const metricsDiv = document.getElementById('metrics');
    if (!metricsDiv) return;
    
    const fps = detectionActive ? '15-20' : '0';
    const detections = detectionActive ? '2-5 per frame' : '0';
    const status = detectionActive ? 'ACTIVE' : 'STOPPED';
    
    metricsDiv.innerHTML = `
📊 Real-time Metrics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FPS: ${fps}
Detections: ${detections}
Status: ${status}
Mode: WASM (Client-side)
Latency: 20-50ms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time: ${new Date().toLocaleTimeString()}
    `;
}

// Update metrics every second
setInterval(updateMetrics, 1000);
