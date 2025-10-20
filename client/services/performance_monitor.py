"""
Utility để monitor performance của centralized screen sharing.
"""

import logging
import time
from typing import Dict, List
from dataclasses import dataclass, field
from threading import RLock

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Metrics cho performance monitoring."""

    start_time: float = field(default_factory=time.perf_counter)
    frames_sent: int = 0
    bytes_sent: int = 0
    sessions_count: int = 0

    # Moving averages
    fps_history: List[float] = field(default_factory=list)
    cpu_usage_history: List[float] = field(default_factory=list)

    def add_frame(self, frame_size_bytes: int, current_sessions: int):
        """Thêm thông tin frame mới."""
        self.frames_sent += 1
        self.bytes_sent += frame_size_bytes
        self.sessions_count = current_sessions

        # Tính FPS
        elapsed = time.perf_counter() - self.start_time
        if elapsed > 0:
            current_fps = self.frames_sent / elapsed
            self.fps_history.append(current_fps)

            # Giữ chỉ 100 measurements gần nhất
            if len(self.fps_history) > 100:
                self.fps_history.pop(0)

    def get_average_fps(self) -> float:
        """Lấy FPS trung bình."""
        return (
            sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0.0
        )

    def get_data_rate_mbps(self) -> float:
        """Lấy tốc độ truyền data (Mbps)."""
        elapsed = time.perf_counter() - self.start_time
        if elapsed > 0:
            bits_per_second = (self.bytes_sent * 8) / elapsed
            return bits_per_second / 1_000_000  # Convert to Mbps
        return 0.0

    def get_efficiency_ratio(self) -> float:
        """
        Tỷ lệ hiệu quả: so sánh với multiple individual services.
        Giá trị > 1.0 nghĩa là hiệu quả hơn.
        """
        if self.sessions_count <= 1:
            return 1.0

        # Giả sử mỗi individual service sử dụng tài nguyên tương đương
        # Centralized chỉ capture + encode 1 lần, nhưng gửi N lần
        # Individual services capture + encode + gửi N lần
        theoretical_individual_cost = self.sessions_count  # N times capture+encode+send
        actual_centralized_cost = 1 + (
            self.sessions_count * 0.1
        )  # 1 capture+encode + N*send_overhead

        return theoretical_individual_cost / actual_centralized_cost


class CentralizedPerformanceMonitor:
    """Monitor performance của centralized screen sharing."""

    def __init__(self):
        self._metrics = PerformanceMetrics()
        self._lock = RLock()
        self._last_log_time = time.perf_counter()
        self._log_interval = 10.0  # Log mỗi 10 giây

    def record_frame_sent(self, frame_size_bytes: int, sessions_count: int):
        """Ghi nhận frame được gửi."""
        with self._lock:
            self._metrics.add_frame(frame_size_bytes, sessions_count)
            self._maybe_log_stats()

    def _maybe_log_stats(self):
        """Log statistics định kỳ."""
        current_time = time.perf_counter()
        if current_time - self._last_log_time >= self._log_interval:
            self._log_performance_stats()
            self._last_log_time = current_time

    def _log_performance_stats(self):
        """Log các thống kê performance."""
        with self._lock:
            avg_fps = self._metrics.get_average_fps()
            data_rate = self._metrics.get_data_rate_mbps()
            efficiency = self._metrics.get_efficiency_ratio()

            logger.info(
                f"📊 Centralized Screen Share Performance:\n"
                f"  • Active Sessions: {self._metrics.sessions_count}\n"
                f"  • Frames Sent: {self._metrics.frames_sent}\n"
                f"  • Average FPS: {avg_fps:.1f}\n"
                f"  • Data Rate: {data_rate:.2f} Mbps\n"
                f"  • Efficiency Ratio: {efficiency:.2f}x\n"
                f"  • Total Data: {self._metrics.bytes_sent / 1024 / 1024:.1f} MB"
            )

    def get_current_stats(self) -> Dict[str, float]:
        """Lấy stats hiện tại."""
        with self._lock:
            return {
                "sessions_count": self._metrics.sessions_count,
                "frames_sent": self._metrics.frames_sent,
                "average_fps": self._metrics.get_average_fps(),
                "data_rate_mbps": self._metrics.get_data_rate_mbps(),
                "efficiency_ratio": self._metrics.get_efficiency_ratio(),
                "total_mb": self._metrics.bytes_sent / 1024 / 1024,
            }

    def reset_metrics(self):
        """Reset metrics."""
        with self._lock:
            self._metrics = PerformanceMetrics()
            logger.info("Performance metrics reset")


# Global monitor instance
performance_monitor = CentralizedPerformanceMonitor()
