#!/usr/bin/env python3
"""
ELMiRA v2 - Latency Tracking Module

This module provides latency benchmarking for the unified MLLM architecture.
It measures the "cognitive core latency" - the time from when ASR completes
(transcript available) to when the MLLM returns the structured action response.

Usage:
    Enable via launch file: roslaunch elmira init_nodes_v2.launch track_latency:=true
    
Benchmarking Context:
    - Baseline (ELMiRA v1 with GPT-4 + GPT-4V): 8.98 seconds average
    - Target (ELMiRA v2 unified MLLM): <8.08 seconds (10% reduction)

Measurement Window:
    - Start: Immediately after MLLM receives the text transcript
    - Stop: When MLLM returns JSON/structured output (Mode/Action/Target)
    
Exclusions (per research methodology):
    - Robot physical movement time (IK/Motion Planning)
    - Text-to-Speech (TTS) generation time
    - ASR/Whisper transcription time (measured separately)

Log Format (CSV):
    timestamp,operation_type,latency_ms,provider,model,success,notes
"""

import os
import time
import csv
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

import rospy


class OperationType(Enum):
    """Types of MLLM operations to track."""
    CHAT = "chat"                       # Text-only chat
    VISION = "vision"                   # Vision + text (scene description)
    GROUNDED_CHAT = "grounded_chat"     # Combined action + detection
    DETECT = "detect"                   # Object detection only
    VISIBILITY = "visibility"           # Object visibility check


@dataclass
class LatencyRecord:
    """Single latency measurement record."""
    timestamp: str
    operation_type: str
    latency_ms: float
    provider: str
    model: str
    success: bool
    input_length: int = 0           # Character count of input prompt
    output_length: int = 0          # Character count of output JSON
    detections_count: int = 0       # Number of objects detected (for grounded ops)
    notes: str = ""
    
    def to_csv_row(self) -> List[Any]:
        """Convert to CSV row values."""
        return [
            self.timestamp,
            self.operation_type,
            f"{self.latency_ms:.2f}",
            self.provider,
            self.model,
            str(self.success).lower(),
            self.input_length,
            self.output_length,
            self.detections_count,
            self.notes
        ]
    
    @staticmethod
    def csv_header() -> List[str]:
        """Return CSV header row."""
        return [
            "timestamp",
            "operation_type", 
            "latency_ms",
            "provider",
            "model",
            "success",
            "input_length",
            "output_length",
            "detections_count",
            "notes"
        ]


class LatencyTracker:
    """
    Thread-safe latency tracker for MLLM operations.
    
    Tracks individual operation latencies and computes statistics.
    Writes records to a CSV log file for later analysis.
    """
    
    # Benchmarking constants
    BASELINE_LATENCY_MS = 8980.0    # ELMiRA v1 average (8.98 seconds)
    TARGET_LATENCY_MS = 8080.0      # 10% reduction target (8.08 seconds)
    
    def __init__(
        self,
        enabled: bool = False,
        log_dir: Optional[str] = None,
        provider: str = "unknown",
        model: str = "unknown",
    ):
        """
        Initialize the latency tracker.
        
        Args:
            enabled: Whether tracking is active
            log_dir: Directory for log files (default: ~/.elmira/latency_logs)
            provider: MLLM provider name
            model: MLLM model name
        """
        self.enabled = enabled
        self.provider = provider
        self.model = model
        
        # Thread safety
        self._lock = threading.Lock()
        
        # In-memory records for session statistics
        self._records: List[LatencyRecord] = []
        
        # Log file setup
        if log_dir:
            self._log_dir = Path(log_dir)
        else:
            self._log_dir = Path.home() / ".elmira" / "latency_logs"
        
        self._log_file: Optional[Path] = None
        self._csv_writer = None
        self._file_handle = None
        
        if self.enabled:
            self._setup_log_file()
            rospy.loginfo(f"[LatencyTracker] ENABLED - Logging to: {self._log_file}")
            rospy.loginfo(f"[LatencyTracker] Baseline: {self.BASELINE_LATENCY_MS:.0f}ms | Target: <{self.TARGET_LATENCY_MS:.0f}ms")
        else:
            rospy.loginfo("[LatencyTracker] Disabled (use track_latency:=true to enable)")
    
    def _setup_log_file(self):
        """Create log directory and file with headers."""
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._log_file = self._log_dir / f"latency_{timestamp}.csv"
            
            self._file_handle = open(self._log_file, 'w', newline='')
            self._csv_writer = csv.writer(self._file_handle)
            
            # Write header
            self._csv_writer.writerow(LatencyRecord.csv_header())
            self._file_handle.flush()
            
        except Exception as e:
            rospy.logerr(f"[LatencyTracker] Failed to setup log file: {e}")
            self.enabled = False
    
    def record(
        self,
        operation_type: OperationType,
        latency_ms: float,
        success: bool,
        input_length: int = 0,
        output_length: int = 0,
        detections_count: int = 0,
        notes: str = "",
    ) -> None:
        """
        Record a latency measurement.
        
        Args:
            operation_type: Type of MLLM operation
            latency_ms: Measured latency in milliseconds
            success: Whether the operation succeeded
            input_length: Character count of input
            output_length: Character count of output
            detections_count: Number of detections (for grounded ops)
            notes: Optional notes or error details
        """
        if not self.enabled:
            return
        
        record = LatencyRecord(
            timestamp=datetime.now().isoformat(),
            operation_type=operation_type.value,
            latency_ms=latency_ms,
            provider=self.provider,
            model=self.model,
            success=success,
            input_length=input_length,
            output_length=output_length,
            detections_count=detections_count,
            notes=notes,
        )
        
        with self._lock:
            # Store in memory
            self._records.append(record)
            
            # Write to file
            if self._csv_writer:
                self._csv_writer.writerow(record.to_csv_row())
                self._file_handle.flush()
        
        # Log with benchmark comparison
        status_icon = "✓" if success else "✗"
        vs_baseline = latency_ms - self.BASELINE_LATENCY_MS
        vs_target = latency_ms - self.TARGET_LATENCY_MS
        
        if latency_ms < self.TARGET_LATENCY_MS:
            benchmark_status = f"✓ MEETS TARGET ({-vs_target:.0f}ms under)"
        elif latency_ms < self.BASELINE_LATENCY_MS:
            benchmark_status = f"~ IMPROVED ({-vs_baseline:.0f}ms faster, {vs_target:.0f}ms over target)"
        else:
            benchmark_status = f"✗ REGRESSION ({vs_baseline:.0f}ms slower)"
        
        rospy.loginfo(
            f"[LatencyTracker] {status_icon} {operation_type.value}: "
            f"{latency_ms:.0f}ms | {benchmark_status}"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Compute statistics from recorded measurements.
        
        Returns:
            Dictionary with min, max, mean, median, success rate, etc.
        """
        with self._lock:
            if not self._records:
                return {"error": "No records available"}
            
            # Filter successful records for latency stats
            successful = [r for r in self._records if r.success]
            latencies = [r.latency_ms for r in successful]
            
            if not latencies:
                return {
                    "total_records": len(self._records),
                    "successful_records": 0,
                    "success_rate": 0.0,
                    "error": "No successful records for latency stats"
                }
            
            # Sort for percentiles
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            
            # Compute statistics
            mean_latency = sum(latencies) / n
            median_latency = sorted_latencies[n // 2]
            p95_latency = sorted_latencies[int(n * 0.95)] if n >= 20 else sorted_latencies[-1]
            p99_latency = sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1]
            
            # By operation type
            by_type = {}
            for record in successful:
                op_type = record.operation_type
                if op_type not in by_type:
                    by_type[op_type] = []
                by_type[op_type].append(record.latency_ms)
            
            type_stats = {}
            for op_type, lats in by_type.items():
                type_stats[op_type] = {
                    "count": len(lats),
                    "mean_ms": sum(lats) / len(lats),
                    "min_ms": min(lats),
                    "max_ms": max(lats),
                }
            
            return {
                "total_records": len(self._records),
                "successful_records": len(successful),
                "success_rate": len(successful) / len(self._records) * 100,
                "latency_stats": {
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                    "mean_ms": mean_latency,
                    "median_ms": median_latency,
                    "p95_ms": p95_latency,
                    "p99_ms": p99_latency,
                    "std_ms": self._std_dev(latencies, mean_latency),
                },
                "by_operation_type": type_stats,
                "benchmark_assessment": self._assess_benchmark(mean_latency),
            }
    
    def _std_dev(self, values: List[float], mean: float) -> float:
        """Compute standard deviation."""
        if len(values) < 2:
            return 0.0
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _assess_benchmark(self, mean_latency_ms: float) -> Dict[str, Any]:
        """
        Assess performance against benchmark targets.
        
        Returns:
            Assessment with pass/fail status and improvement percentage
        """
        improvement_vs_baseline = (
            (self.BASELINE_LATENCY_MS - mean_latency_ms) / self.BASELINE_LATENCY_MS * 100
        )
        
        meets_target = mean_latency_ms < self.TARGET_LATENCY_MS
        
        return {
            "baseline_ms": self.BASELINE_LATENCY_MS,
            "target_ms": self.TARGET_LATENCY_MS,
            "mean_latency_ms": mean_latency_ms,
            "improvement_percent": improvement_vs_baseline,
            "meets_10_percent_target": meets_target,
            "verdict": "PASS ✓" if meets_target else "FAIL ✗",
        }
    
    def print_summary(self) -> None:
        """Print a summary of benchmarking results."""
        stats = self.get_statistics()
        
        if "error" in stats and "latency_stats" not in stats:
            rospy.logwarn(f"[LatencyTracker] Summary: {stats['error']}")
            return
        
        rospy.loginfo("=" * 60)
        rospy.loginfo("[LatencyTracker] BENCHMARKING SUMMARY")
        rospy.loginfo("=" * 60)
        rospy.loginfo(f"Total Records: {stats['total_records']}")
        rospy.loginfo(f"Success Rate: {stats['success_rate']:.1f}%")
        rospy.loginfo("-" * 60)
        
        ls = stats.get("latency_stats", {})
        rospy.loginfo("Latency Statistics:")
        rospy.loginfo(f"  Mean:   {ls.get('mean_ms', 0):.0f} ms")
        rospy.loginfo(f"  Median: {ls.get('median_ms', 0):.0f} ms")
        rospy.loginfo(f"  Min:    {ls.get('min_ms', 0):.0f} ms")
        rospy.loginfo(f"  Max:    {ls.get('max_ms', 0):.0f} ms")
        rospy.loginfo(f"  StdDev: {ls.get('std_ms', 0):.0f} ms")
        rospy.loginfo(f"  P95:    {ls.get('p95_ms', 0):.0f} ms")
        rospy.loginfo("-" * 60)
        
        by_type = stats.get("by_operation_type", {})
        if by_type:
            rospy.loginfo("By Operation Type:")
            for op_type, ts in by_type.items():
                rospy.loginfo(f"  {op_type}: n={ts['count']}, mean={ts['mean_ms']:.0f}ms")
        rospy.loginfo("-" * 60)
        
        ba = stats.get("benchmark_assessment", {})
        rospy.loginfo("BENCHMARK ASSESSMENT:")
        rospy.loginfo(f"  Baseline (v1): {ba.get('baseline_ms', 0):.0f} ms")
        rospy.loginfo(f"  Target (<10% reduction): {ba.get('target_ms', 0):.0f} ms")
        rospy.loginfo(f"  Your Mean: {ba.get('mean_latency_ms', 0):.0f} ms")
        rospy.loginfo(f"  Improvement: {ba.get('improvement_percent', 0):.1f}%")
        rospy.loginfo(f"  Verdict: {ba.get('verdict', 'N/A')}")
        rospy.loginfo("=" * 60)
        
        if self._log_file:
            rospy.loginfo(f"Log file: {self._log_file}")
    
    def close(self) -> None:
        """Close log file and print summary."""
        if self.enabled:
            self.print_summary()
            
            if self._file_handle:
                self._file_handle.close()
                self._file_handle = None
                self._csv_writer = None


# Global tracker instance (initialized by MLLM gateway)
_tracker: Optional[LatencyTracker] = None


def get_tracker() -> Optional[LatencyTracker]:
    """Get the global latency tracker instance."""
    return _tracker


def init_tracker(
    enabled: bool,
    log_dir: Optional[str] = None,
    provider: str = "unknown",
    model: str = "unknown",
) -> LatencyTracker:
    """
    Initialize the global latency tracker.
    
    Should be called once during MLLM gateway startup.
    """
    global _tracker
    _tracker = LatencyTracker(
        enabled=enabled,
        log_dir=log_dir,
        provider=provider,
        model=model,
    )
    return _tracker


def shutdown_tracker() -> None:
    """Shutdown and cleanup the global tracker."""
    global _tracker
    if _tracker:
        _tracker.close()
        _tracker = None
