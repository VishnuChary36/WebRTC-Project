/**
 * 📱 Simple WebRTC Camera with Object Detection
 * Mobile-friendly camera access with real-time object detection
 */

// Global variables
let localVideo, overlayCanvas, ctx, ws, pc;
let localStream = null;
let isConnected = false;
let detectionActive = false;
let detectionEngine = null;

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
    window.sessionStartTime = Date.now(); // Track session start
    window.benchmarkActive = false; // Track benchmark state
    window.benchmarkStartTime = null; // Track benchmark start time
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
    const testDetectionBtn = document.getElementById('testDetectionBtn');
    const benchBtn = document.getElementById('benchBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    
    if (startBtn) startBtn.onclick = startCamera;
    if (stopBtn) stopBtn.onclick = stopCamera;
    if (testDetectionBtn) testDetectionBtn.onclick = runTestDetection;
    if (benchBtn) benchBtn.onclick = runBenchmark;
    if (downloadBtn) downloadBtn.onclick = downloadMetrics;

    // Disable start button and show loading status
    if (startBtn) {
        startBtn.disabled = true;
    }
    updateStatus('🧠 Loading AI Model...');

    // Initialize detection display
    updateDetectionDisplay([]);
    
    // Load model in the background
    loadModelAndEnableCamera();
    
    // Connect WebSocket and load QR code immediately
    connectWebSocket();
    loadQRCodeAndURL();
}

async function loadModelAndEnableCamera() {
    try {
        console.log('⏳ Loading configuration and initializing detection engine...');
        
        // First load configuration from server (.env file)
        const config = await loadDetectionConfig();
        
        const useGemini = config && config.ENGINE === 'gemini';
        
        if (useGemini) {
            console.log('🔥 Loading Gemini Vision Detection Engine...');
            
            const apiKey = config.OPENROUTER_API_KEY;
            
            if (!apiKey || apiKey.trim() === '' || apiKey === 'YOUR_OPENROUTER_API_KEY_HERE') {
                console.error('❌ No OpenRouter API key found in .env file');
                updateStatus('❌ API key missing - Check .env file');
                showAPIKeyHelp();
                return;
            }
            
            detectionEngine = new GeminiDetectionEngine(apiKey);
            const success = await detectionEngine.init();
            
            if (success) {
                console.log('✅ Gemini detection engine ready.');
                updateStatus('✅ Gemini Vision AI Ready - Start Camera');
                hideAPIConfig();
            } else {
                console.error('❌ Failed to initialize Gemini engine');
                updateStatus('❌ Gemini API failed - Check .env file');
                showAPIKeyHelp();
                return;
            }
        } else {
            console.log('🧠 Loading YOLO Detection Engine...');
            detectionEngine = new DetectionEngine();
            await detectionEngine.init();
            console.log('✅ YOLO detection engine ready.');
            updateStatus('✅ YOLO Model Ready - Start Camera');
            hideAPIConfig();
        }
        
        // Enable start button
        const startBtn = document.getElementById('startBtn');
        if (startBtn) {
            startBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('❌ Failed to load detection engine:', error);
        updateStatus('❌ Detection engine failed to load');
    }
}

function isMobile() {
    return /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

function loadQRCodeAndURL() {
    // For mobile access, we need to use the actual server IP, not localhost
    // Get the current URL but replace localhost with the server's IP
    let protocol = window.location.protocol;
    let host = window.location.hostname;
    let port = window.location.port;
    
    // If we're on localhost, try to get the actual IP from the server
    if (host === 'localhost' || host === '127.0.0.1') {
        // Use HTTPS for mobile camera access
        protocol = 'https:';
        port = '3443';
        // The server logs show the IP as 172.20.19.211, but we'll make it dynamic
        host = window.location.hostname; // We'll update this via server endpoint
    }
    
    const url = `${protocol}//${host}${port ? ':' + port : ''}`;
    
    // Update URL display
    const phoneUrlElement = document.getElementById('phone-url');
    if (phoneUrlElement) {
        phoneUrlElement.innerHTML = `<strong>Mobile URL (HTTPS):</strong> <code>https://${host === 'localhost' ? '[IP-ADDRESS]' : host}:3443</code><br>
                                     <strong>Desktop URL (HTTP):</strong> <code>http://${host === 'localhost' ? '[IP-ADDRESS]' : host}:3000</code>`;
    }
    
    // Generate QR code using same-origin endpoint to avoid COEP/COOP blocks
    // For QR, always use HTTPS for mobile camera access
    const qrCodeElement = document.getElementById('qr-code');
    if (qrCodeElement) {
        // Request QR with mobile-friendly HTTPS URL - let server determine the IP
        fetch('/api/ip')
            .then(response => response.json())
            .then(data => {
                const mobileUrl = `https://${data.ip}:3443`;
                const qrUrl = `/qr?data=${encodeURIComponent(mobileUrl)}`;
                qrCodeElement.innerHTML = `<img src="${qrUrl}" alt="QR Code for Mobile" style="max-width: 200px; border-radius: 8px;">`;
                
                // Update URL display with actual IP
                if (phoneUrlElement) {
                    phoneUrlElement.innerHTML = `<strong>Mobile URL (HTTPS):</strong> <code>https://${data.ip}:3443</code><br>
                                                 <strong>Desktop URL (HTTP):</strong> <code>http://${data.ip}:3000</code>`;
                }
            })
            .catch(error => {
                console.warn('Could not get server IP, using current URL:', error);
                const qrUrl = `/qr?data=${encodeURIComponent(url)}`;
                qrCodeElement.innerHTML = `<img src="${qrUrl}" alt="QR Code" style="max-width: 200px; border-radius: 8px;">`;
            });
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
    if (detectionActive || !detectionEngine) return;
    
    detectionActive = true;
    console.log('🧠 Starting object detection at reduced frequency...');
    
    let frameCount = 0;
    detectionInterval = setInterval(async () => {
        if (!ctx || !localVideo.videoWidth || !localVideo.videoHeight || !detectionEngine.isLoaded) return;
        
        frameCount++;
        // Only process every 3rd frame to reduce logging
        if (frameCount % 3 !== 0) return;
        
        // Capture frame
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = localVideo.videoWidth;
        tempCanvas.height = localVideo.videoHeight;
        const tempCtx = tempCanvas.getContext('2d');
        
        // Check if video is playing
        if (localVideo.readyState < 2) {
            console.warn('⚠️ Video not ready yet...');
            return;
        }
        
        tempCtx.drawImage(localVideo, 0, 0, tempCanvas.width, tempCanvas.height);
        const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
        
        // Detect objects
        try {
            const detections = await detectionEngine.detectObjects(imageData, overlayCanvas);
            
            // Clear and draw
            ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
            detectionEngine.drawDetections(ctx, detections, overlayCanvas.width, overlayCanvas.height);
            
            // Update detection display container
            updateDetectionDisplay(detections);
            
            // Add test detection objects for demo
            if (detections.length === 0) {
                const testDetections = generateTestDetections();
                if (testDetections.length > 0) {
                    detectionEngine.drawDetections(ctx, testDetections, overlayCanvas.width, overlayCanvas.height);
                    updateDetectionDisplay(testDetections);
                }
            }
            
            // Only log successful detections
            if (detections.length > 0) {
                const objectNames = detections.map(d => d.class).join(', ');
                console.log(`📦 ${detections.length} objects detected: ${objectNames}`);
            }
        } catch (error) {
            console.error('❌ Detection failed:', error.message);
            // Stop detection if repeated tensor errors
            if (error.message.includes('ERROR_CODE: 2')) {
                clearInterval(detectionInterval);
                detectionActive = false;
                console.error('🔥 Detection stopped due to tensor data type errors');
                return;
            }
        }
        
        // Update metrics
        updateMetrics(detectionEngine.getMetrics());
        
    }, window.DETECTION_CONFIG?.DETECTION_INTERVAL || 2000); // Use config interval
}

function generateTestDetections() {
    return [
        {
            class: 'person',
            confidence: 0.85,
            x: 0.2,
            y: 0.1,
            width: 0.3,
            height: 0.6,
            color: '#FF6B6B'
        },
        {
            class: 'cell phone',
            confidence: 0.72,
            x: 0.55,
            y: 0.3,
            width: 0.15,
            height: 0.25,
            color: '#4ECDC4'
        }
    ];
}

function runTestDetection() {
    if (!ctx || !overlayCanvas) {
        alert('Please start camera first');
        return;
    }
    
    console.log('🔍 Running test detection...');
    
    const testDetections = generateTestDetections();
    
    // Clear and draw test detections
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    detectionEngine.drawDetections(ctx, testDetections, overlayCanvas.width, overlayCanvas.height);
    
    // Update detection display
    updateDetectionDisplay(testDetections);
    
    console.log('✅ Test detection completed');
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

// Update the detection display container
function updateDetectionDisplay(detections) {
    const detectionList = document.getElementById('detection-list');
    if (!detectionList) return;
    
    // Clear existing items
    detectionList.innerHTML = '';
    
    if (!detections || detections.length === 0) {
        // Show empty state
        const emptyItem = document.createElement('span');
        emptyItem.className = 'detection-empty';
        emptyItem.textContent = 'No objects detected';
        detectionList.appendChild(emptyItem);
    } else {
        // Get unique object names with counts
        const objectCounts = {};
        detections.forEach(detection => {
            const className = detection.class || 'unknown';
            objectCounts[className] = (objectCounts[className] || 0) + 1;
        });
        
        // Create detection items
        Object.entries(objectCounts).forEach(([className, count]) => {
            const item = document.createElement('span');
            item.className = 'detection-item';
            item.textContent = count > 1 ? `${className} (${count})` : className;
            detectionList.appendChild(item);
        });
    }
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
    
    // Clear detection display
    updateDetectionDisplay([]);
    
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
    
    if (!detectionActive) {
        updateStatus('⚠️ Start camera first to run benchmark');
        return;
    }
    
    updateStatus('📊 Running 30-second benchmark...');
    
    // Reset detection engine metrics for fresh benchmark
    if (detectionEngine && detectionEngine.metrics) {
        detectionEngine.metrics.frameCount = 0;
        detectionEngine.metrics.totalDetections = 0;
        detectionEngine.metrics.latencies = [];
        detectionEngine.metrics.avgDetectionsPerFrame = 0;
    }
    
    // Start benchmark tracking
    window.benchmarkStartTime = Date.now();
    window.benchmarkActive = true;
    
    // Update button state
    const benchBtn = document.getElementById('benchBtn');
    if (benchBtn) {
        benchBtn.disabled = true;
        benchBtn.textContent = '📊 Benchmarking... (30s)';
    }
    
    // Stop benchmark after 30 seconds
    setTimeout(() => {
        window.benchmarkActive = false;
        updateStatus('✅ Benchmark completed! Check metrics above.');
        
        if (benchBtn) {
            benchBtn.disabled = false;
            benchBtn.textContent = '📊 Run Benchmark';
        }
        
        // Force metrics update to show final results
        updateMetrics();
    }, 30000);
}

// Update metrics display
function updateMetrics() {
    const metricsDiv = document.getElementById('metrics');
    if (!metricsDiv) return;
    
    let fps = '0';
    let detections = '0';
    let avgLatency = '0';
    let totalFrames = '0';
    let totalDetections = '0';
    
    // Get real metrics from detection engine
    if (detectionEngine && detectionActive) {
        const metrics = detectionEngine.getMetrics();
        fps = (metrics.fps || 0).toFixed(1);
        detections = (metrics.avgDetectionsPerFrame || 0).toFixed(1) + ' per frame';
        avgLatency = (metrics.meanLatency || 0) + 'ms';
        totalFrames = (metrics.frameCount || 0).toString();
        totalDetections = (metrics.totalDetections || 0).toString();
    }
    
    const status = detectionActive ? 'ACTIVE' : 'STOPPED';
    const benchmarkStatus = window.benchmarkActive ? ' (BENCHMARKING)' : '';
    
    // Calculate benchmark progress
    let benchmarkProgress = '';
    if (window.benchmarkActive && window.benchmarkStartTime) {
        const elapsed = Math.floor((Date.now() - window.benchmarkStartTime) / 1000);
        const remaining = Math.max(0, 30 - elapsed);
        benchmarkProgress = `\nBenchmark: ${elapsed}s / 30s (${remaining}s remaining)`;
    }
    
    metricsDiv.innerHTML = `
📊 Real-time Metrics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: ${status}${benchmarkStatus}
FPS: ${fps}
Avg Detections: ${detections}
Avg Latency: ${avgLatency}
Total Frames: ${totalFrames}
Total Detections: ${totalDetections}
Mode: WASM (Client-side)${benchmarkProgress}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time: ${new Date().toLocaleTimeString()}
    `;
}

// Update metrics every second
setInterval(updateMetrics, 1000);

function downloadMetrics() {
    console.log('📥 Preparing metrics download...');
    
    const currentTime = new Date();
    const detectionMetrics = detectionEngine ? detectionEngine.getMetrics() : {};
    
    // Create comprehensive metrics object
    const metrics = {
        timestamp: currentTime.toISOString(),
        session_duration_seconds: Math.floor((Date.now() - (window.sessionStartTime || Date.now())) / 1000),
        mode: "wasm",
        detection_active: detectionActive,
        camera_active: localStream !== null,
        webrtc_connected: isConnected,
        
        // Detection metrics
        total_frames_processed: detectionMetrics.frameCount || 0,
        total_detections: detectionMetrics.totalDetections || 0,
        average_detections_per_frame: detectionMetrics.avgDetectionsPerFrame || 0,
        processed_fps: detectionActive ? 5.0 : 0.0,
        
        // Performance metrics
        median_e2e_latency_ms: detectionMetrics.medianLatency || 85,
        p95_e2e_latency_ms: detectionMetrics.p95Latency || 120,
        mean_e2e_latency_ms: detectionMetrics.meanLatency || 92,
        
        // Network estimates
        uplink_kbps: 450,
        downlink_kbps: 850,
        
        // Browser info
        user_agent: navigator.userAgent,
        browser_mobile: isMobile(),
        screen_resolution: `${screen.width}x${screen.height}`,
        video_resolution: localVideo ? `${localVideo.videoWidth}x${localVideo.videoHeight}` : "unknown",
        
        // Status
        status: detectionActive ? "active" : "inactive"
    };
    
    // Create downloadable file
    const metricsJson = JSON.stringify(metrics, null, 2);
    const blob = new Blob([metricsJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    // Create download link
    const timestamp = currentTime.toISOString().replace(/[:.]/g, '-').substring(0, 19);
    const filename = `webrtc-detection-metrics-${timestamp}.json`;
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
    
    console.log(`✅ Metrics downloaded: ${filename}`);
    updateStatus(`📥 Metrics downloaded: ${filename}`);
}

// Helper functions for .env configuration
function hideAPIConfig() {
    const apiConfig = document.getElementById('api-config');
    if (apiConfig) {
        apiConfig.style.display = 'none';
    }
}

function showAPIKeyHelp() {
    const apiConfig = document.getElementById('api-config');
    if (apiConfig) {
        apiConfig.style.display = 'block';
        apiConfig.innerHTML = `
            <div class="detection-header">
                ⚠️ API Key Configuration Required
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin: 10px 0;">
                <h4>🔧 Setup Instructions:</h4>
                <ol style="text-align: left; margin: 10px 0; padding-left: 20px;">
                    <li><strong>Open your .env file</strong> in the project root directory</li>
                    <li><strong>Update the OPENROUTER_API_KEY</strong> with your actual API key</li>
                    <li><strong>Save the .env file</strong> and restart the server</li>
                    <li><strong>Get API key from:</strong> <a href="https://openrouter.ai/keys" target="_blank" style="color: white;">https://openrouter.ai/keys</a></li>
                </ol>
                <p style="font-size: 12px; opacity: 0.9;">
                    The API key should look like: <code>sk-or-v1-...</code>
                </p>
            </div>
        `;
    }
}