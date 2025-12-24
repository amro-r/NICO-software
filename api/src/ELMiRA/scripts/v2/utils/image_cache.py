#!/usr/bin/env python3
"""
Cached image grabber for efficient camera frame sharing.
Avoids multiple ROS wait_for_message calls.
"""

import time
import threading
from typing import Tuple, Optional
import numpy as np

import rospy
import cv_bridge
from sensor_msgs.msg import Image


class CachedImageGrabber:
    """
    Caches the latest camera frame for efficient multi-consumer access.
    """
    
    def __init__(
        self,
        topic: str = "/nico/vision/right",
        cache_duration: float = 0.5,
        auto_subscribe: bool = True,
    ):
        self.topic = topic
        self.cache_duration = cache_duration
        
        self._bridge = cv_bridge.CvBridge()
        self._frame: Optional[np.ndarray] = None
        self._timestamp: float = 0
        self._lock = threading.Lock()
        self._subscriber = None
        
        if auto_subscribe:
            self.start()
    
    def start(self):
        """Start background subscription."""
        if self._subscriber is None:
            self._subscriber = rospy.Subscriber(
                self.topic,
                Image,
                self._callback,
                queue_size=1,
                buff_size=2**24  # 16MB buffer for images
            )
            rospy.loginfo(f"CachedImageGrabber: Subscribed to {self.topic}")
    
    def stop(self):
        """Stop background subscription."""
        if self._subscriber is not None:
            self._subscriber.unregister()
            self._subscriber = None
    
    def _callback(self, msg: Image):
        """Store latest frame."""
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, "bgr8")
            with self._lock:
                self._frame = frame
                self._timestamp = time.time()
        except Exception as e:
            rospy.logwarn(f"CachedImageGrabber: Failed to convert image: {e}")
    
    def get_frame(self, max_age: float = None) -> np.ndarray:
        """
        Get the latest cached frame.
        
        Args:
            max_age: Maximum acceptable frame age in seconds.
                     If None, uses cache_duration.
                     If cached frame is older, waits for new one.
        
        Returns:
            BGR image as numpy array
        """
        max_age = max_age or self.cache_duration
        
        with self._lock:
            age = time.time() - self._timestamp
            if self._frame is not None and age < max_age:
                return self._frame.copy()
        
        # Cache miss - wait for new frame
        try:
            msg = rospy.wait_for_message(self.topic, Image, timeout=2.0)
            frame = self._bridge.imgmsg_to_cv2(msg, "bgr8")
            with self._lock:
                self._frame = frame
                self._timestamp = time.time()
            return frame
        except Exception as e:
            rospy.logerr(f"CachedImageGrabber: Failed to get frame: {e}")
            # Return stale frame if available
            with self._lock:
                if self._frame is not None:
                    return self._frame.copy()
            raise
    
    def get_frame_with_timestamp(self) -> Tuple[np.ndarray, float]:
        """Get frame and its capture timestamp."""
        frame = self.get_frame()
        with self._lock:
            return frame, self._timestamp
    
    def has_recent_frame(self, max_age: float = None) -> bool:
        """Check if a recent frame is available without blocking."""
        max_age = max_age or self.cache_duration
        with self._lock:
            if self._frame is None:
                return False
            age = time.time() - self._timestamp
            return age < max_age


# Global instance for shared access
_global_grabber: Optional[CachedImageGrabber] = None


def get_cached_grabber(topic: str = "/nico/vision/right") -> CachedImageGrabber:
    """Get or create global cached image grabber."""
    global _global_grabber
    if _global_grabber is None:
        _global_grabber = CachedImageGrabber(topic)
    return _global_grabber
