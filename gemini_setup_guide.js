// 🚀 SETUP INSTRUCTIONS FOR GEMINI DETECTION
// =============================================

// STEP 1: Get your OpenRouter API Key
// ------------------------------------
// 1. Go to https://openrouter.ai/keys
// 2. Sign up or log in
// 3. Create a new API key
// 4. Copy the key (starts with "sk-or-")

// STEP 2: Configure the API Key
// -----------------------------
// Option A: Edit detection_config.js file
DETECTION_CONFIG.OPENROUTER_API_KEY = "sk-or-your-actual-api-key-here";

// Option B: Use the web interface (recommended)
// 1. Open http://localhost:3000 in your browser
// 2. Scroll down to "API Configuration" section
// 3. Enter your OpenRouter API key
// 4. Click "Save Key"
// 5. Click "Test API" to verify

// STEP 3: Use the test page
// -------------------------
// 1. Open http://localhost:3000/static/test.html
// 2. Enter your API key in the configuration section
// 3. Switch to Gemini engine
// 4. Start camera and test detection

// EXAMPLE INTEGRATION:
// --------------------

// For your own implementation, simply:
const apiKey = "sk-or-your-key-here";
const geminiEngine = new GeminiDetectionEngine(apiKey);

// Initialize
await geminiEngine.init();

// Detect objects
const detections = await geminiEngine.detectObjects(null, canvasElement);

// Draw results
geminiEngine.drawDetections(ctx, detections, canvas.width, canvas.height);

// FEATURES:
// ---------
// ✅ Gemini 2.0 Flash vision model via OpenRouter
// ✅ Real-time object detection with confidence scores
// ✅ Colored bounding boxes with object names
// ✅ Rate limiting for API calls (2 second intervals)
// ✅ Fallback to previous detections during cooldown
// ✅ Visual detection container showing object names
// ✅ Compatible with existing WebRTC stream
// ✅ Works on both mobile and desktop

// DETECTION QUALITY:
// ------------------
// Gemini Vision is significantly better than YOLOv5n at:
// - Detecting unusual objects
// - Understanding context
// - Accurate object naming
// - Handling different lighting conditions
// - Detecting text, signs, and complex scenes

console.log("🔥 Gemini Detection Setup Complete!");
console.log("📖 Follow the steps above to configure your API key");
console.log("🧪 Test everything at: http://localhost:3000/static/test.html");
