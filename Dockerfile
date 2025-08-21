FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable to disable executable stack requirement for ONNX Runtime
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV ONNX_ML=1

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p models static logs metrics

# Download YOLOv5 model if not present
RUN python -c "import os, urllib.request; \
    os.makedirs('./models', exist_ok=True) if not os.path.exists('./models/yolov5n.onnx') else None; \
    urllib.request.urlretrieve('https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5n.onnx', './models/yolov5n.onnx') if not os.path.exists('./models/yolov5n.onnx') else print('Model already exists')"

EXPOSE 3000 3443

CMD ["python", "server/main.py"]