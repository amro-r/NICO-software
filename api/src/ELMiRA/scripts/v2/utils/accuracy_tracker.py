#!/usr/bin/env python3
"""
ELMiRA v2 - Accuracy Tracking Module

This module provides accuracy benchmarking for validating the unified MLLM
architecture against the baseline ELMiRA v1 (GPT-4 + GPT-4V) system.

Research Context:
    - Baseline (ELMiRA v1): 46.67% accuracy
    - Target (ELMiRA v2): 67% accuracy (20% improvement)

Measurement Modes:
    - "describe": Scene description accuracy (MLLM correctly describes visible objects)
    - "act": Action + localization accuracy (MLLM correctly identifies target object with bbox)
    - "speak": Knowledge/conversation accuracy (MLLM responds appropriately)

Log Format (CSV):
    timestamp, session_id, interaction_id, asr_transcript, mode_selected,
    action_type, target_object, image_path, detections_json, robot_output,
    success, failure_reason, manual_verdict, notes

Usage:
    Enable via launch file: roslaunch elmira init_nodes_v2.launch track_accuracy:=true

Manual Review Process:
    1. Run robot interaction session
    2. Open generated CSV file
    3. Review 'image_path' (raw or with bounding boxes)
    4. Fill in 'manual_verdict' column with: correct, incorrect, partial
    5. Compute accuracy: correct_count / total_count * 100
"""

import os
import csv
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

import cv2
import numpy as np
import rospy


class ModeType(Enum):
    """Types of MLLM interaction modes."""
    SPEAK = "speak"
    DESCRIBE = "describe"
    ACT = "act"
    QUIT = "quit"
    UNKNOWN = "unknown"


@dataclass
class AccuracyRecord:
    """
    Single accuracy measurement record for manual review.
    
    Captures all relevant data for post-hoc accuracy evaluation.
    """
    # Core identity
    timestamp: str
    session_id: str
    interaction_id: int
    
    # ASR input (user prompt)
    asr_transcript: str
    
    # Mode/Action info
    mode_selected: str          # speak, describe, act, quit
    action_type: str            # touch, push, grasp, etc. (for act mode)
    target_object: str          # Object name from LLM parsing
    
    # Image data
    image_path: str             # Path to saved image file
    has_bounding_boxes: bool    # True if image has bbox overlay (act mode)
    
    # Detection data (for act mode)
    detections_json: str        # JSON string of all detections
    detection_count: int        # Number of objects detected
    selected_bbox_x: float      # Selected object center_x (0-1)
    selected_bbox_y: float      # Selected object center_y (0-1)
    selected_bbox_w: float      # Selected object width (0-1)
    selected_bbox_h: float      # Selected object height (0-1)
    
    # Robot output
    robot_output: str           # TTS text or scene description
    response_json: str          # Full LLM JSON response
    
    # Status
    success: bool               # Did the operation complete?
    failure_reason: str         # object_not_found, out_of_reach, etc.
    
    # Manual review (empty columns for human annotation)
    manual_verdict: str = ""    # correct, incorrect, partial
    notes: str = ""             # Human reviewer notes
    
    def to_csv_row(self) -> List[Any]:
        """Convert to CSV row values."""
        return [
            self.timestamp,
            self.session_id,
            self.interaction_id,
            self.asr_transcript,
            self.mode_selected,
            self.action_type,
            self.target_object,
            self.image_path,
            str(self.has_bounding_boxes).lower(),
            self.detections_json,
            self.detection_count,
            f"{self.selected_bbox_x:.4f}" if self.selected_bbox_x else "",
            f"{self.selected_bbox_y:.4f}" if self.selected_bbox_y else "",
            f"{self.selected_bbox_w:.4f}" if self.selected_bbox_w else "",
            f"{self.selected_bbox_h:.4f}" if self.selected_bbox_h else "",
            self.robot_output,
            self.response_json,
            str(self.success).lower(),
            self.failure_reason,
            self.manual_verdict,
            self.notes,
        ]
    
    @staticmethod
    def csv_header() -> List[str]:
        """Return CSV header row."""
        return [
            "timestamp",
            "session_id",
            "interaction_id",
            "asr_transcript",
            "mode_selected",
            "action_type",
            "target_object",
            "image_path",
            "has_bounding_boxes",
            "detections_json",
            "detection_count",
            "selected_bbox_x",
            "selected_bbox_y",
            "selected_bbox_w",
            "selected_bbox_h",
            "robot_output",
            "response_json",
            "success",
            "failure_reason",
            "manual_verdict",
            "notes",
        ]


class AccuracyTracker:
    """
    Thread-safe accuracy tracker for MLLM interactions.
    
    Records interaction data including images for manual accuracy review.
    Generates CSV logs with image paths for post-hoc evaluation.
    """
    
    # Benchmarking constants
    BASELINE_ACCURACY = 46.67       # ELMiRA v1 accuracy (%)
    TARGET_ACCURACY = 67.0          # 20% improvement target (%)
    
    def __init__(
        self,
        enabled: bool = False,
        log_dir: Optional[str] = None,
        provider: str = "unknown",
        model: str = "unknown",
    ):
        """
        Initialize the accuracy tracker.
        
        Args:
            enabled: Whether tracking is active
            log_dir: Directory for log files (default: ~/.elmira/accuracy_logs)
            provider: MLLM provider name
            model: MLLM model name
        """
        self.enabled = enabled
        self.provider = provider
        self.model = model
        
        # Session tracking
        self.session_id = str(uuid.uuid4())[:8]
        self.interaction_counter = 0
        
        # Thread safety
        self._lock = threading.Lock()
        
        # In-memory records for session statistics
        self._records: List[AccuracyRecord] = []
        
        # Log file setup
        if log_dir:
            self._log_dir = Path(log_dir)
        else:
            self._log_dir = Path.home() / ".elmira" / "accuracy_logs"
        
        self._images_dir: Optional[Path] = None
        self._log_file: Optional[Path] = None
        self._csv_writer = None
        self._file_handle = None
        
        if self.enabled:
            self._setup_log_file()
            rospy.loginfo(f"[AccuracyTracker] ENABLED - Logging to: {self._log_file}")
            rospy.loginfo(f"[AccuracyTracker] Images saved to: {self._images_dir}")
            rospy.loginfo(f"[AccuracyTracker] Baseline: {self.BASELINE_ACCURACY:.1f}% | Target: >{self.TARGET_ACCURACY:.1f}%")
        else:
            rospy.loginfo("[AccuracyTracker] Disabled (use track_accuracy:=true to enable)")
    
    def _setup_log_file(self):
        """Create log directory, images subdirectory, and CSV file with headers."""
        try:
            # Create main log directory
            self._log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped session directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir = self._log_dir / f"session_{timestamp}"
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Create images subdirectory
            self._images_dir = session_dir / "images"
            self._images_dir.mkdir(parents=True, exist_ok=True)
            
            # Create CSV log file
            self._log_file = session_dir / f"accuracy_{timestamp}.csv"
            
            self._file_handle = open(self._log_file, 'w', newline='', encoding='utf-8')
            self._csv_writer = csv.writer(self._file_handle)
            
            # Write header
            self._csv_writer.writerow(AccuracyRecord.csv_header())
            self._file_handle.flush()
            
        except Exception as e:
            rospy.logerr(f"[AccuracyTracker] Failed to setup log file: {e}")
            self.enabled = False
    
    def save_image(
        self,
        image: np.ndarray,
        prefix: str = "frame",
        detections: Optional[List[Any]] = None,
    ) -> str:
        """
        Save image to disk, optionally with bounding box overlay.
        
        Args:
            image: OpenCV image (BGR format)
            prefix: Filename prefix (e.g., "describe", "act")
            detections: List of detection objects with center_x, center_y, width, height, label
            
        Returns:
            Absolute path to saved image file
        """
        if not self.enabled or self._images_dir is None:
            return ""
        
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            
            # Draw bounding boxes if detections provided
            if detections:
                image = self._draw_detections(image.copy(), detections)
                filename = f"{prefix}_bbox_{timestamp}.jpg"
            else:
                filename = f"{prefix}_{timestamp}.jpg"
            
            filepath = self._images_dir / filename
            cv2.imwrite(str(filepath), image)
            
            rospy.logdebug(f"[AccuracyTracker] Saved image: {filepath}")
            return str(filepath)
            
        except Exception as e:
            rospy.logwarn(f"[AccuracyTracker] Failed to save image: {e}")
            return ""
    
    def _draw_detections(
        self,
        image: np.ndarray,
        detections: List[Any],
    ) -> np.ndarray:
        """
        Draw bounding boxes and labels on image.
        
        Args:
            image: OpenCV image (BGR format)
            detections: List of detection objects
            
        Returns:
            Annotated image
        """
        h, w = image.shape[:2]
        
        # Color palette for multiple detections
        colors = [
            (0, 255, 0),    # Green
            (255, 0, 0),    # Blue
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]
        
        for i, det in enumerate(detections):
            color = colors[i % len(colors)]
            
            # Get bbox coordinates (normalized 0-1)
            cx = getattr(det, 'center_x', 0)
            cy = getattr(det, 'center_y', 0)
            bw = getattr(det, 'width', 0)
            bh = getattr(det, 'height', 0)
            label = getattr(det, 'label', 'object')
            score = getattr(det, 'score', 0.0)
            
            # Convert to pixel coordinates
            x1 = int((cx - bw / 2) * w)
            y1 = int((cy - bh / 2) * h)
            x2 = int((cx + bw / 2) * w)
            y2 = int((cy + bh / 2) * h)
            
            # Clamp to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            # Draw rectangle
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            label_text = f"{label}: {score:.2f}" if score > 0 else label
            (text_w, text_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(image, (x1, y1 - text_h - 10), (x1 + text_w + 4, y1), color, -1)
            
            # Draw label text
            cv2.putText(
                image, label_text,
                (x1 + 2, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 0, 0), 2
            )
            
            # Draw center point
            cx_px, cy_px = int(cx * w), int(cy * h)
            cv2.circle(image, (cx_px, cy_px), 5, color, -1)
        
        # Add timestamp watermark
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            image, timestamp,
            (10, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            (255, 255, 255), 1
        )
        
        return image
    
    def record(
        self,
        asr_transcript: str,
        mode_selected: str,
        image_path: str,
        robot_output: str,
        response_json: str,
        success: bool,
        action_type: str = "",
        target_object: str = "",
        detections: Optional[List[Any]] = None,
        selected_detection: Optional[Any] = None,
        failure_reason: str = "",
        has_bounding_boxes: bool = False,
    ) -> None:
        """
        Record an accuracy measurement.
        
        Args:
            asr_transcript: User's spoken input (from ASR)
            mode_selected: Mode chosen by MLLM (speak, describe, act)
            image_path: Path to saved image file
            robot_output: Robot's spoken response or description
            response_json: Full JSON response from MLLM
            success: Whether the operation completed successfully
            action_type: Type of action (for act mode)
            target_object: Target object name (for act mode)
            detections: List of all detections (for act mode)
            selected_detection: The selected target detection (for act mode)
            failure_reason: Reason for failure if not success
            has_bounding_boxes: Whether image has bbox overlay
        """
        if not self.enabled:
            return
        
        with self._lock:
            self.interaction_counter += 1
            interaction_id = self.interaction_counter
        
        # Convert detections to JSON string
        detections_json = ""
        detection_count = 0
        if detections:
            detection_count = len(detections)
            det_list = []
            for det in detections:
                det_list.append({
                    "label": getattr(det, 'label', ''),
                    "score": getattr(det, 'score', 0.0),
                    "center_x": getattr(det, 'center_x', 0.0),
                    "center_y": getattr(det, 'center_y', 0.0),
                    "width": getattr(det, 'width', 0.0),
                    "height": getattr(det, 'height', 0.0),
                })
            detections_json = json.dumps(det_list, ensure_ascii=False)
        
        # Extract selected detection bbox
        selected_bbox_x = 0.0
        selected_bbox_y = 0.0
        selected_bbox_w = 0.0
        selected_bbox_h = 0.0
        if selected_detection:
            selected_bbox_x = getattr(selected_detection, 'center_x', 0.0)
            selected_bbox_y = getattr(selected_detection, 'center_y', 0.0)
            selected_bbox_w = getattr(selected_detection, 'width', 0.0)
            selected_bbox_h = getattr(selected_detection, 'height', 0.0)
        
        record = AccuracyRecord(
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            interaction_id=interaction_id,
            asr_transcript=asr_transcript,
            mode_selected=mode_selected,
            action_type=action_type,
            target_object=target_object,
            image_path=image_path,
            has_bounding_boxes=has_bounding_boxes,
            detections_json=detections_json,
            detection_count=detection_count,
            selected_bbox_x=selected_bbox_x,
            selected_bbox_y=selected_bbox_y,
            selected_bbox_w=selected_bbox_w,
            selected_bbox_h=selected_bbox_h,
            robot_output=robot_output,
            response_json=response_json,
            success=success,
            failure_reason=failure_reason,
            manual_verdict="",
            notes="",
        )
        
        with self._lock:
            # Store in memory
            self._records.append(record)
            
            # Write to file
            if self._csv_writer:
                self._csv_writer.writerow(record.to_csv_row())
                self._file_handle.flush()
        
        # Log interaction
        status_icon = "✓" if success else "✗"
        rospy.loginfo(
            f"[AccuracyTracker] {status_icon} #{interaction_id} "
            f"mode={mode_selected} | target={target_object or 'N/A'} | "
            f"detections={detection_count}"
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Compute statistics from recorded measurements.
        
        Note: This only counts success/failure rates, NOT accuracy.
        True accuracy requires manual review of the 'manual_verdict' column.
        
        Returns:
            Dictionary with counts and success rates by mode
        """
        with self._lock:
            if not self._records:
                return {"error": "No records available"}
            
            total = len(self._records)
            successful = sum(1 for r in self._records if r.success)
            
            # By mode
            by_mode = {}
            for record in self._records:
                mode = record.mode_selected
                if mode not in by_mode:
                    by_mode[mode] = {"total": 0, "successful": 0}
                by_mode[mode]["total"] += 1
                if record.success:
                    by_mode[mode]["successful"] += 1
            
            mode_stats = {}
            for mode, counts in by_mode.items():
                mode_stats[mode] = {
                    "total": counts["total"],
                    "successful": counts["successful"],
                    "success_rate": counts["successful"] / counts["total"] * 100,
                }
            
            return {
                "session_id": self.session_id,
                "total_interactions": total,
                "successful_interactions": successful,
                "system_success_rate": successful / total * 100,
                "by_mode": mode_stats,
                "note": "True accuracy requires manual review of manual_verdict column",
            }
    
    def print_summary(self) -> None:
        """Print a summary of the session."""
        stats = self.get_statistics()
        
        if "error" in stats:
            rospy.logwarn(f"[AccuracyTracker] Summary: {stats['error']}")
            return
        
        rospy.loginfo("=" * 70)
        rospy.loginfo("[AccuracyTracker] SESSION SUMMARY")
        rospy.loginfo("=" * 70)
        rospy.loginfo(f"Session ID: {stats['session_id']}")
        rospy.loginfo(f"Total Interactions: {stats['total_interactions']}")
        rospy.loginfo(f"System Success Rate: {stats['system_success_rate']:.1f}%")
        rospy.loginfo("-" * 70)
        
        rospy.loginfo("By Mode:")
        for mode, mode_stats in stats.get("by_mode", {}).items():
            rospy.loginfo(
                f"  {mode}: {mode_stats['successful']}/{mode_stats['total']} "
                f"({mode_stats['success_rate']:.1f}% success)"
            )
        rospy.loginfo("-" * 70)
        
        rospy.loginfo("ACCURACY BENCHMARKING:")
        rospy.loginfo(f"  Baseline (ELMiRA v1): {self.BASELINE_ACCURACY:.1f}%")
        rospy.loginfo(f"  Target (20% improvement): >{self.TARGET_ACCURACY:.1f}%")
        rospy.loginfo("-" * 70)
        rospy.loginfo("NEXT STEPS:")
        rospy.loginfo(f"  1. Open CSV: {self._log_file}")
        rospy.loginfo(f"  2. Review images in: {self._images_dir}")
        rospy.loginfo("  3. Fill 'manual_verdict' column: correct/incorrect/partial")
        rospy.loginfo("  4. Calculate accuracy: correct_count / total * 100")
        rospy.loginfo("=" * 70)
    
    def close(self) -> None:
        """Close log file and print summary."""
        if self.enabled:
            self.print_summary()
            
            if self._file_handle:
                self._file_handle.close()
                self._file_handle = None
                self._csv_writer = None


# Global tracker instance (initialized by MLLM gateway)
_accuracy_tracker: Optional[AccuracyTracker] = None


def get_accuracy_tracker() -> Optional[AccuracyTracker]:
    """Get the global accuracy tracker instance."""
    return _accuracy_tracker


def init_accuracy_tracker(
    enabled: bool,
    log_dir: Optional[str] = None,
    provider: str = "unknown",
    model: str = "unknown",
) -> AccuracyTracker:
    """
    Initialize the global accuracy tracker.
    
    Should be called once during MLLM gateway startup.
    """
    global _accuracy_tracker
    _accuracy_tracker = AccuracyTracker(
        enabled=enabled,
        log_dir=log_dir,
        provider=provider,
        model=model,
    )
    return _accuracy_tracker


def shutdown_accuracy_tracker() -> None:
    """Shutdown and cleanup the global tracker."""
    global _accuracy_tracker
    if _accuracy_tracker:
        _accuracy_tracker.close()
        _accuracy_tracker = None
