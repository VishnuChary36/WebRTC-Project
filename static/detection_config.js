/**
 * 🔧 Detection Configuration
 * Configuration loaded from server's .env file
 */

// This will be loaded from the server at runtime
let DETECTION_CONFIG = {
    // Default fallback values
    ENGINE: 'yolo',
    OPENROUTER_API_KEY: '',
    DETECTION_INTERVAL: 2000,
    YOLO_INTERVAL: 200,
    MAX_DETECTIONS: 8,
    CONFIDENCE_THRESHOLD: 0.5
};

// Load configuration from server
async function loadDetectionConfig() {
    try {
        console.log('🔧 Loading detection configuration from server...');
        const response = await fetch('/api/config');
        if (response.ok) {
            const serverConfig = await response.json();
            
            DETECTION_CONFIG = {
                ENGINE: serverConfig.engine || 'yolo',
                OPENROUTER_API_KEY: serverConfig.openrouter_api_key || '',
                DETECTION_INTERVAL: serverConfig.detection_interval || 2000,
                YOLO_INTERVAL: 200,
                MAX_DETECTIONS: serverConfig.max_detections || 8,
                CONFIDENCE_THRESHOLD: serverConfig.confidence_threshold || 0.5
            };
            
            console.log('✅ Configuration loaded from server:', DETECTION_CONFIG);
            
            // Show API key status (partially masked)
            if (DETECTION_CONFIG.OPENROUTER_API_KEY) {
                const key = DETECTION_CONFIG.OPENROUTER_API_KEY;
                const maskedKey = key.substring(0, 8) + '...' + key.substring(key.length - 4);
                console.log(`🔑 API Key loaded: ${maskedKey}`);
            }
            
            return DETECTION_CONFIG;
        } else {
            console.warn('⚠️ Failed to load server config, using defaults');
            return DETECTION_CONFIG;
        }
    } catch (error) {
        console.error('❌ Error loading configuration:', error);
        return DETECTION_CONFIG;
    }
}

// Export configuration and loader function
window.DETECTION_CONFIG = DETECTION_CONFIG;
window.loadDetectionConfig = loadDetectionConfig;
