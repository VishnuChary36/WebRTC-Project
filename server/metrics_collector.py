"""
Metrics Collector for WebRTC VLM Object Detection
Collects and analyzes performance metrics including latency, FPS, and bandwidth
"""

import json
import logging
import time
import threading
from collections import deque
from pathlib import Path
import psutil
import statistics

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self, max_samples=1000):
        self.max_samples = max_samples
        self.start_time = time.time()
        
        # Metrics storage
        self.frame_metrics = deque(maxlen=max_samples)
        self.system_metrics = deque(maxlen=100)  # Store last 100 system snapshots
        
        # Counters
        self.total_frames = 0
        self.total_detections = 0
        self.frames_processed = 0
        
        # System monitoring
        self.process = psutil.Process()
        self.initial_cpu_times = self.process.cpu_times()
        
        # Threading for periodic system metrics
        self.system_monitor_active = True
        self.system_monitor_thread = threading.Thread(target=self._monitor_system)
        self.system_monitor_thread.daemon = True
        self.system_monitor_thread.start()
        
        logger.info("📊 Metrics collector initialized")

    def record_frame(self, capture_ts, recv_ts, inference_ts, num_detections=0, display_ts=None):
        """Record metrics for a processed frame"""
        current_ts = int(time.time() * 1000)
        if display_ts is None:
            display_ts = current_ts
        
        # Calculate latencies
        network_latency = recv_ts - capture_ts
        server_latency = inference_ts - recv_ts
        end_to_end_latency = display_ts - capture_ts
        
        frame_metric = {
            'timestamp': current_ts,
            'capture_ts': capture_ts,
            'recv_ts': recv_ts,
            'inference_ts': inference_ts,
            'display_ts': display_ts,
            'network_latency': network_latency,
            'server_latency': server_latency,
            'end_to_end_latency': end_to_end_latency,
            'num_detections': num_detections
        }
        
        self.frame_metrics.append(frame_metric)
        self.total_frames += 1
        self.total_detections += num_detections
        self.frames_processed += 1
        
        logger.debug(f"📈 Frame {self.total_frames}: E2E={end_to_end_latency}ms, Objects={num_detections}")

    def _monitor_system(self):
        """Background thread to monitor system metrics"""
        while self.system_monitor_active:
            try:
                # CPU and memory usage
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                system_cpu = psutil.cpu_percent(interval=1)
                
                # Network I/O (if available)
                net_io = psutil.net_io_counters()
                
                system_metric = {
                    'timestamp': int(time.time() * 1000),
                    'process_cpu_percent': cpu_percent,
                    'system_cpu_percent': system_cpu,
                    'memory_rss': memory_info.rss,
                    'memory_vms': memory_info.vms,
                    'bytes_sent': net_io.bytes_sent if net_io else 0,
                    'bytes_recv': net_io.bytes_recv if net_io else 0
                }
                
                self.system_metrics.append(system_metric)
                
            except Exception as e:
                logger.error(f"❌ Error collecting system metrics: {e}")
            
            time.sleep(5)  # Collect every 5 seconds

    def get_current_metrics(self):
        """Get current performance metrics"""
        current_time = time.time()
        runtime_seconds = current_time - self.start_time
        
        metrics = {
            'runtime_seconds': runtime_seconds,
            'total_frames': self.total_frames,
            'total_detections': self.total_detections,
            'frames_processed': self.frames_processed,
            'processed_fps': self.frames_processed / runtime_seconds if runtime_seconds > 0 else 0,
            'avg_detections_per_frame': self.total_detections / self.total_frames if self.total_frames > 0 else 0
        }
        
        # Latency statistics
        if self.frame_metrics:
            e2e_latencies = [m['end_to_end_latency'] for m in self.frame_metrics]
            network_latencies = [m['network_latency'] for m in self.frame_metrics]
            server_latencies = [m['server_latency'] for m in self.frame_metrics]
            
            metrics.update({
                'latency': {
                    'end_to_end': {
                        'median': statistics.median(e2e_latencies),
                        'p95': self._percentile(e2e_latencies, 95),
                        'p99': self._percentile(e2e_latencies, 99),
                        'mean': statistics.mean(e2e_latencies),
                        'min': min(e2e_latencies),
                        'max': max(e2e_latencies)
                    },
                    'network': {
                        'median': statistics.median(network_latencies),
                        'p95': self._percentile(network_latencies, 95),
                        'mean': statistics.mean(network_latencies)
                    },
                    'server': {
                        'median': statistics.median(server_latencies),
                        'p95': self._percentile(server_latencies, 95),
                        'mean': statistics.mean(server_latencies)
                    }
                }
            })
        
        # System metrics
        if self.system_metrics:
            latest_system = self.system_metrics[-1]
            
            # Calculate bandwidth (rough estimate)
            if len(self.system_metrics) >= 2:
                prev_system = self.system_metrics[-2]
                time_diff = (latest_system['timestamp'] - prev_system['timestamp']) / 1000.0
                
                bytes_sent_rate = (latest_system['bytes_sent'] - prev_system['bytes_sent']) / time_diff
                bytes_recv_rate = (latest_system['bytes_recv'] - prev_system['bytes_recv']) / time_diff
                
                # Convert to kbps
                uplink_kbps = (bytes_sent_rate * 8) / 1000
                downlink_kbps = (bytes_recv_rate * 8) / 1000
            else:
                uplink_kbps = 0
                downlink_kbps = 0
            
            metrics.update({
                'system': {
                    'process_cpu_percent': latest_system['process_cpu_percent'],
                    'system_cpu_percent': latest_system['system_cpu_percent'],
                    'memory_mb': latest_system['memory_rss'] / (1024 * 1024),
                    'uplink_kbps': uplink_kbps,
                    'downlink_kbps': downlink_kbps
                }
            })
        
        return metrics

    def _percentile(self, data, p):
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (p / 100.0) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def export_metrics(self, filename="metrics.json", duration_filter=None):
        """Export metrics to JSON file"""
        metrics = self.get_current_metrics()
        
        # Add raw frame data if requested
        frame_data = []
        for frame in self.frame_metrics:
            if duration_filter is None or frame['timestamp'] >= duration_filter:
                frame_data.append(frame)
        
        export_data = {
            'summary': metrics,
            'export_timestamp': int(time.time() * 1000),
            'frame_count': len(frame_data),
            'frames': frame_data[-100:] if len(frame_data) > 100 else frame_data  # Last 100 frames
        }
        
        # Save to file
        output_path = Path("metrics") / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"📊 Metrics exported to {output_path}")
        return output_path

    def get_benchmark_summary(self, duration_seconds=30):
        """Get a benchmark summary for the specified duration"""
        if not self.frame_metrics:
            return {"error": "No metrics available"}
        
        # Filter frames from the last duration_seconds
        cutoff_time = int(time.time() * 1000) - (duration_seconds * 1000)
        recent_frames = [f for f in self.frame_metrics if f['timestamp'] >= cutoff_time]
        
        if not recent_frames:
            return {"error": f"No metrics in last {duration_seconds} seconds"}
        
        # Calculate key metrics
        e2e_latencies = [f['end_to_end_latency'] for f in recent_frames]
        total_detections = sum(f['num_detections'] for f in recent_frames)
        
        fps = len(recent_frames) / duration_seconds
        
        summary = {
            'duration_seconds': duration_seconds,
            'frames_processed': len(recent_frames),
            'processed_fps': fps,
            'total_detections': total_detections,
            'median_e2e_latency_ms': statistics.median(e2e_latencies),
            'p95_e2e_latency_ms': self._percentile(e2e_latencies, 95),
            'mean_e2e_latency_ms': statistics.mean(e2e_latencies)
        }
        
        # Add bandwidth if available
        if self.system_metrics:
            latest = self.system_metrics[-1]
            if len(self.system_metrics) >= 2:
                prev = self.system_metrics[-2]
                time_diff = (latest['timestamp'] - prev['timestamp']) / 1000.0
                
                uplink_kbps = ((latest['bytes_sent'] - prev['bytes_sent']) * 8) / (time_diff * 1000)
                downlink_kbps = ((latest['bytes_recv'] - prev['bytes_recv']) * 8) / (time_diff * 1000)
                
                summary.update({
                    'uplink_kbps': uplink_kbps,
                    'downlink_kbps': downlink_kbps
                })
        
        return summary

    def reset_metrics(self):
        """Reset all metrics counters"""
        self.frame_metrics.clear()
        self.system_metrics.clear()
        self.total_frames = 0
        self.total_detections = 0
        self.frames_processed = 0
        self.start_time = time.time()
        
        logger.info("🔄 Metrics reset")

    def stop(self):
        """Stop the metrics collector"""
        self.system_monitor_active = False
        if self.system_monitor_thread.is_alive():
            self.system_monitor_thread.join(timeout=2)
        
        logger.info("🛑 Metrics collector stopped")