"""
Inference Engine for Object Detection
Supports both server-side ONNX inference and WASM client-side mode
"""

import asyncio
import base64
import io
import logging
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Try to import ONNX Runtime with fallback handling
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ONNX Runtime not available: {e}")
    ONNX_AVAILABLE = False
    ort = None

class InferenceEngine:
    def __init__(self, mode="wasm"):
        self.mode = mode.lower()
        self.session = None
        self.input_size = (320, 240)  # Low-resource default
        self.confidence_threshold = 0.5
        self.nms_threshold = 0.4
        
        # COCO class names (YOLOv5 default)
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
        
        if self.mode == "server":
            self._initialize_onnx_session()
        
        logger.info(f"🧠 Inference engine initialized in {mode.upper()} mode")

    def _initialize_onnx_session(self):
        """Initialize ONNX Runtime session for server mode"""
        if not ONNX_AVAILABLE:
            logger.warning("⚠️ ONNX Runtime not available, server mode will be limited")
            return
            
        try:
            model_path = Path("models/yolov5n.onnx")
            if not model_path.exists():
                raise FileNotFoundError(f"Model not found: {model_path}")
            
            # Configure ONNX Runtime for CPU optimization
            providers = ['CPUExecutionProvider']
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_options.intra_op_num_threads = 4
            
            self.session = ort.InferenceSession(
                str(model_path), 
                sess_options=sess_options,
                providers=providers
            )
            
            # Get model input details
            input_details = self.session.get_inputs()[0]
            input_shape = input_details.shape
            
            if len(input_shape) == 4:  # [batch, channels, height, width]
                self.input_size = (input_shape[3], input_shape[2])  # (width, height)
            
            logger.info(f"✅ ONNX model loaded: {model_path}")
            logger.info(f"📐 Input size: {self.input_size}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ONNX session: {e}")
            logger.warning("🔄 Falling back to WASM mode")
            self.mode = "wasm"

    async def detect_objects(self, image_data):
        """
        Detect objects in image
        Args:
            image_data: Base64 encoded image or numpy array
        Returns:
            List of detection dictionaries
        """
        if self.mode == "wasm" or not ONNX_AVAILABLE or self.session is None:
            # In WASM mode or when ONNX is not available, detection happens client-side
            return []
        
        try:
            # Decode image
            if isinstance(image_data, str):
                # Base64 encoded image
                image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
                image = Image.open(io.BytesIO(image_bytes))
                img_array = np.array(image)
            elif isinstance(image_data, np.ndarray):
                img_array = image_data
            else:
                raise ValueError("Unsupported image format")
            
            # Preprocess image
            processed_img = self._preprocess_image(img_array)
            
            # Run inference
            start_time = time.time()
            outputs = self.session.run(None, {self.session.get_inputs()[0].name: processed_img})
            inference_time = time.time() - start_time
            
            # Post-process detections
            detections = self._postprocess_detections(outputs[0], img_array.shape)
            
            logger.debug(f"🔍 Detected {len(detections)} objects in {inference_time:.3f}s")
            
            return detections
            
        except Exception as e:
            logger.error(f"❌ Detection error: {e}")
            return []

    def _preprocess_image(self, img_array):
        """Preprocess image for YOLO model"""
        # Convert BGR to RGB if needed
        if img_array.shape[2] == 3:
            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
        else:
            img_rgb = img_array
        
        # Resize to model input size
        img_resized = cv2.resize(img_rgb, self.input_size)
        
        # Normalize to [0, 1] and convert to float32
        img_normalized = img_resized.astype(np.float32) / 255.0
        
        # Convert HWC to CHW format
        img_transposed = np.transpose(img_normalized, (2, 0, 1))
        
        # Add batch dimension
        img_batch = np.expand_dims(img_transposed, axis=0)
        
        return img_batch

    def _postprocess_detections(self, outputs, original_shape):
        """Post-process YOLO outputs to get bounding boxes"""
        detections = []
        
        # YOLO output format: [batch, num_detections, 85] 
        # 85 = 4 bbox coords + 1 confidence + 80 class scores
        if len(outputs.shape) == 3:
            outputs = outputs[0]  # Remove batch dimension
        
        orig_h, orig_w = original_shape[:2]
        input_h, input_w = self.input_size[1], self.input_size[0]
        
        # Scale factors
        scale_x = orig_w / input_w
        scale_y = orig_h / input_h
        
        for detection in outputs:
            # Extract confidence and class scores
            confidence = detection[4]
            if confidence < self.confidence_threshold:
                continue
            
            # Get class with highest score
            class_scores = detection[5:]
            class_id = np.argmax(class_scores)
            class_confidence = class_scores[class_id]
            
            # Final confidence
            final_confidence = confidence * class_confidence
            if final_confidence < self.confidence_threshold:
                continue
            
            # Extract and scale bounding box
            x_center, y_center, width, height = detection[:4]
            
            # Convert from center format to corner format
            x1 = (x_center - width / 2) * scale_x
            y1 = (y_center - height / 2) * scale_y
            x2 = (x_center + width / 2) * scale_x
            y2 = (y_center + height / 2) * scale_y
            
            # Normalize coordinates to [0, 1]
            xmin = max(0, x1 / orig_w)
            ymin = max(0, y1 / orig_h)
            xmax = min(1, x2 / orig_w)
            ymax = min(1, y2 / orig_h)
            
            # Skip invalid boxes
            if xmax <= xmin or ymax <= ymin:
                continue
            
            detections.append({
                'label': self.class_names[class_id],
                'score': float(final_confidence),
                'xmin': float(xmin),
                'ymin': float(ymin),
                'xmax': float(xmax),
                'ymax': float(ymax)
            })
        
        # Apply NMS
        detections = self._apply_nms(detections)
        
        return detections

    def _apply_nms(self, detections):
        """Apply Non-Maximum Suppression to remove overlapping boxes"""
        if not detections:
            return detections
        
        # Sort by confidence
        detections.sort(key=lambda x: x['score'], reverse=True)
        
        kept_detections = []
        
        while detections:
            # Take the detection with highest confidence
            best = detections.pop(0)
            kept_detections.append(best)
            
            # Remove overlapping detections
            detections = [
                det for det in detections 
                if self._calculate_iou(best, det) < self.nms_threshold
            ]
        
        return kept_detections

    def _calculate_iou(self, box1, box2):
        """Calculate Intersection over Union (IoU) between two boxes"""
        # Calculate intersection area
        x1 = max(box1['xmin'], box2['xmin'])
        y1 = max(box1['ymin'], box2['ymin'])
        x2 = min(box1['xmax'], box2['xmax'])
        y2 = min(box1['ymax'], box2['ymax'])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        # Calculate union area
        area1 = (box1['xmax'] - box1['xmin']) * (box1['ymax'] - box1['ymin'])
        area2 = (box2['xmax'] - box2['xmin']) * (box2['ymax'] - box2['ymin'])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0

    def get_model_info(self):
        """Get information about the loaded model"""
        if self.mode == "wasm":
            return {
                "mode": "wasm",
                "inference_location": "client-side",
                "model": "Loaded dynamically in browser"
            }
        
        if self.session is None:
            return {"mode": "server", "status": "not_initialized"}
        
        return {
            "mode": "server",
            "input_size": self.input_size,
            "confidence_threshold": self.confidence_threshold,
            "nms_threshold": self.nms_threshold,
            "num_classes": len(self.class_names),
            "providers": self.session.get_providers()
        }