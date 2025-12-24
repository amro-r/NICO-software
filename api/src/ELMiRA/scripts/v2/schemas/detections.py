#!/usr/bin/env python3
"""
Detection schema definitions for ELMiRA v2.
For visual grounding and object detection responses.
"""

from typing import List, Optional, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class BoundingBox:
    """Bounding box in normalized coordinates [0.0-1.0]."""
    x_min: float = 0.0
    y_min: float = 0.0
    x_max: float = 1.0
    y_max: float = 1.0
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of bounding box."""
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)
    
    @property
    def width(self) -> float:
        return self.x_max - self.x_min
    
    @property
    def height(self) -> float:
        return self.y_max - self.y_min
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    def to_pixel_coords(self, img_width: int, img_height: int) -> Tuple[int, int, int, int]:
        """Convert to pixel coordinates (x_min, y_min, x_max, y_max)."""
        return (
            int(self.x_min * img_width),
            int(self.y_min * img_height),
            int(self.x_max * img_width),
            int(self.y_max * img_height)
        )
    
    def center_pixel(self, img_width: int, img_height: int) -> Tuple[int, int]:
        """Get center in pixel coordinates."""
        cx, cy = self.center
        return (int(cx * img_width), int(cy * img_height))
    
    @classmethod
    def from_google_format(cls, coords: List[int]) -> "BoundingBox":
        """
        Parse Google's native bounding box format.
        Google returns [y_min, x_min, y_max, x_max] in 0-1000 scale.
        """
        if len(coords) >= 4:
            return cls(
                x_min=coords[1] / 1000.0,
                y_min=coords[0] / 1000.0,
                x_max=coords[3] / 1000.0,
                y_max=coords[2] / 1000.0
            )
        return cls()
    
    @classmethod  
    def from_openai_format(cls, box: dict) -> "BoundingBox":
        """
        Parse OpenAI format bounding box.
        Expected format: {"x_min": 0.1, "y_min": 0.2, "x_max": 0.5, "y_max": 0.6}
        or pixel format that needs normalization.
        """
        return cls(
            x_min=float(box.get("x_min", box.get("xmin", 0.0))),
            y_min=float(box.get("y_min", box.get("ymin", 0.0))),
            x_max=float(box.get("x_max", box.get("xmax", 1.0))),
            y_max=float(box.get("y_max", box.get("ymax", 1.0)))
        )


@dataclass
class Detection:
    """Single object detection result."""
    label: str = ""
    confidence: float = 1.0
    bounding_box: BoundingBox = field(default_factory=BoundingBox)
    description: str = ""  # Optional description from MLLM
    
    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "bounding_box": {
                "x_min": self.bounding_box.x_min,
                "y_min": self.bounding_box.y_min,
                "x_max": self.bounding_box.x_max,
                "y_max": self.bounding_box.y_max
            },
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Detection":
        bbox_data = data.get("bounding_box", data.get("bbox", {}))
        if isinstance(bbox_data, list):
            # Google format
            bbox = BoundingBox.from_google_format(bbox_data)
        else:
            bbox = BoundingBox.from_openai_format(bbox_data)
        
        return cls(
            label=data.get("label", data.get("object", "")),
            confidence=float(data.get("confidence", data.get("score", 1.0))),
            bounding_box=bbox,
            description=data.get("description", "")
        )


@dataclass
class DetectionResponse:
    """Response containing multiple object detections."""
    detections: List[Detection] = field(default_factory=list)
    raw_response: str = ""
    latency_ms: float = 0.0
    provider: str = ""
    model: str = ""
    image_width: int = 640
    image_height: int = 480
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "detections": [d.to_dict() for d in self.detections],
            "count": len(self.detections)
        }, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str, **kwargs) -> "DetectionResponse":
        """Parse JSON response into DetectionResponse."""
        try:
            data = json.loads(json_str)
            detections_data = data.get("detections", data.get("objects", []))
            
            detections = [Detection.from_dict(d) for d in detections_data]
            
            return cls(detections=detections, raw_response=json_str, **kwargs)
        except json.JSONDecodeError:
            return cls(raw_response=json_str, **kwargs)
    
    def get_by_label(self, label: str) -> Optional[Detection]:
        """Find detection by label (case-insensitive partial match)."""
        label_lower = label.lower()
        for det in self.detections:
            if label_lower in det.label.lower():
                return det
        return None
    
    def get_highest_confidence(self) -> Optional[Detection]:
        """Get detection with highest confidence."""
        if not self.detections:
            return None
        return max(self.detections, key=lambda d: d.confidence)


@dataclass
class GroundingResponse:
    """
    Combined action + grounding response.
    Used when MLLM provides both action decision and object localization.
    """
    action_response: Optional["ActionResponse"] = None  # Forward reference
    detection: Optional[Detection] = None  # Primary grounded object
    all_detections: List[Detection] = field(default_factory=list)
    raw_response: str = ""
    latency_ms: float = 0.0
    provider: str = ""
    model: str = ""
    
    @property
    def has_grounding(self) -> bool:
        """Check if response includes valid grounding."""
        return self.detection is not None and self.detection.bounding_box.area > 0
    
    def to_json(self) -> str:
        """Convert to JSON."""
        result = {
            "grounding": self.detection.to_dict() if self.detection else None,
            "all_detections": [d.to_dict() for d in self.all_detections]
        }
        if self.action_response:
            result["actions"] = [a.to_dict() for a in self.action_response.actions]
        return json.dumps(result, ensure_ascii=False)


# Import ActionResponse here to avoid circular import
from .actions import ActionResponse
