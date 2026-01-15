#!/usr/bin/env python3
"""
Detection Visualizer Node

Subscribes to camera images and detection results, draws bounding boxes
with labels and coordinates, and publishes annotated images for debugging.

View with: rqt_image_view /elmira/debug/detections
"""

import rospy
import cv2
import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from elmira.msg import DetectedObject, DetectedObjectArray


class DetectionVisualizer:
    """Visualizes object detections on camera images."""
    
    # Workspace polygon (normalized image coordinates)
    # Workspace polygon (normalized image coordinates)
    WORKSPACE = np.array([
        [0.0396, 0.5600],
        [0.2021, 0.2000],
        [0.7646, 0.1800],
        [0.9448, 0.5800],
        [0.8162, 0.6500],
        [0.6391, 0.7200],
        [0.4380, 0.7500],
        [0.2599, 0.7000],
        [0.1328, 0.6200],
    ])
    
    # Colors (BGR format for OpenCV)
    COLOR_IN_REACH = (0, 255, 0)      # Green
    COLOR_OUT_OF_REACH = (0, 0, 255)  # Red
    COLOR_SELECTED = (255, 150, 0)    # Blue
    COLOR_WORKSPACE = (255, 255, 0)   # Cyan
    
    def __init__(self):
        rospy.init_node("detection_visualizer")
        
        self.bridge = CvBridge()
        self.latest_image = None
        self.detections = []
        self.selected_label = None
        
        # Get parameters
        image_topic = rospy.get_param("~image_topic", "/nico/vision/right")
        self.show_workspace = rospy.get_param("~show_workspace", True)
        
        # Subscribers
        rospy.Subscriber(image_topic, Image, self.image_callback)
        rospy.Subscriber("/elmira/detections", DetectedObjectArray, self.detection_callback)
        
        # Publisher for annotated images
        self.pub = rospy.Publisher("/elmira/debug/detections", Image, queue_size=1)
        
        rospy.loginfo("Detection visualizer started")
        rospy.loginfo(f"  Image topic: {image_topic}")
        rospy.loginfo(f"  Output topic: /elmira/debug/detections")
        
        self.run()
    
    def image_callback(self, msg):
        """Store latest camera image."""
        try:
            self.latest_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            rospy.logerr(f"Failed to convert image: {e}")
    
    def detection_callback(self, msg):
        """Store latest detections."""
        self.detections = msg.detections
        rospy.loginfo(f"Received {len(self.detections)} detections")
    
    def within_workspace(self, x, y):
        """Check if point is within workspace polygon."""
        cross_products = np.array([
            (x - self.WORKSPACE[i - 1][0])
            * (self.WORKSPACE[i][1] - self.WORKSPACE[i - 1][1])
            - (self.WORKSPACE[i][0] - self.WORKSPACE[i - 1][0])
            * (y - self.WORKSPACE[i - 1][1])
            for i in range(len(self.WORKSPACE))
        ])
        return np.logical_or(np.all(cross_products <= 0), np.all(cross_products >= 0))
    
    def draw_detections(self, img):
        """Draw bounding boxes and labels on image."""
        h, w = img.shape[:2]
        annotated = img.copy()
        
        # Draw workspace polygon
        if self.show_workspace:
            workspace_pts = (self.WORKSPACE * np.array([w, h])).astype(np.int32)
            cv2.polylines(annotated, [workspace_pts], True, self.COLOR_WORKSPACE, 2)
        
        # Draw each detection
        for det in self.detections:
            # Calculate bounding box corners from center + dimensions
            cx, cy = det.center_x, det.center_y
            bw, bh = det.width, det.height
            
            x1 = int((cx - bw/2) * w)
            y1 = int((cy - bh/2) * h)
            x2 = int((cx + bw/2) * w)
            y2 = int((cy + bh/2) * h)
            
            # Determine color based on reach
            in_reach = self.within_workspace(cx, cy)
            if det.label == self.selected_label:
                color = self.COLOR_SELECTED
                thickness = 3
            elif in_reach:
                color = self.COLOR_IN_REACH
                thickness = 2
            else:
                color = self.COLOR_OUT_OF_REACH
                thickness = 2
            
            # Draw bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
            
            # Create label with confidence
            label = f"{det.label} ({det.score:.2f})"
            
            # Create coordinate text
            coord_text = f"img: ({cx:.3f}, {cy:.3f})"
            
            # Get text sizes for background rectangles
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_thickness = 1
            
            (label_w, label_h), _ = cv2.getTextSize(label, font, font_scale, font_thickness)
            (coord_w, coord_h), _ = cv2.getTextSize(coord_text, font, font_scale, font_thickness)
            
            # Draw label background and text (above box)
            label_y = max(y1 - 5, label_h + 5)
            cv2.rectangle(annotated, (x1, label_y - label_h - 5), 
                         (x1 + label_w + 5, label_y + 2), color, -1)
            cv2.putText(annotated, label, (x1 + 2, label_y - 2), 
                       font, font_scale, (0, 0, 0), font_thickness)
            
            # Draw coordinates at center of box
            center_x_px = int(cx * w)
            center_y_px = int(cy * h)
            
            # Draw center marker
            cv2.circle(annotated, (center_x_px, center_y_px), 5, color, -1)
            
            # Draw coordinate text below center
            coord_y = min(center_y_px + 20, h - 10)
            cv2.rectangle(annotated, 
                         (center_x_px - coord_w//2 - 2, coord_y - coord_h - 2),
                         (center_x_px + coord_w//2 + 2, coord_y + 2), 
                         (0, 0, 0), -1)
            cv2.putText(annotated, coord_text, 
                       (center_x_px - coord_w//2, coord_y), 
                       font, font_scale, (255, 255, 255), font_thickness)
            
            # Show reach status
            status = "IN REACH" if in_reach else "OUT OF REACH"
            status_color = self.COLOR_IN_REACH if in_reach else self.COLOR_OUT_OF_REACH
            (status_w, status_h), _ = cv2.getTextSize(status, font, 0.4, 1)
            status_y = y2 + status_h + 5
            if status_y < h:
                cv2.putText(annotated, status, (x1, status_y), 
                           font, 0.4, status_color, 1)
        
        # Draw detection count
        count_text = f"Detections: {len(self.detections)}"
        cv2.putText(annotated, count_text, (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return annotated
    
    def run(self):
        """Main loop - publish annotated images at 10Hz."""
        rate = rospy.Rate(10)
        
        while not rospy.is_shutdown():
            if self.latest_image is not None:
                # Draw detections on image
                annotated = self.draw_detections(self.latest_image)
                
                # Publish
                try:
                    msg = self.bridge.cv2_to_imgmsg(annotated, "bgr8")
                    self.pub.publish(msg)
                except Exception as e:
                    rospy.logerr(f"Failed to publish image: {e}")
            
            rate.sleep()


if __name__ == "__main__":
    try:
        DetectionVisualizer()
    except rospy.ROSInterruptException:
        pass
