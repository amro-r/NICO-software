#!/usr/bin/env python3
"""
ELMiRA v2 - Unified MLLM Gateway Node

This ROS node provides a unified interface to multiple MLLM providers
(OpenAI, Google) with support for:
- Text and vision chat
- Object grounding/detection
- Visibility checking
- Streaming responses
- Backward compatibility with v1 services
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional

# Add the v2 directory to Python path for imports when run directly by ROS
_v2_dir = Path(__file__).parent.resolve()
if str(_v2_dir) not in sys.path:
    sys.path.insert(0, str(_v2_dir))

import rospy
import numpy as np

from std_srvs.srv import Trigger, TriggerResponse
from elmira.srv import (
    PromptTextLLM, PromptTextLLMResponse,
    PromptVisionLLM, PromptVisionLLMResponse,
    CheckLLMObjectVisibility, CheckLLMObjectVisibilityResponse,
    DetectObjects, DetectObjectsResponse,
    DetectWithMLLM, DetectWithMLLMResponse,
    PromptMLLMWithGrounding, PromptMLLMWithGroundingResponse,
)
from elmira.msg import DetectedObject, DetectedObjectArray

# Import v2 components (absolute imports now that path is set up)
from providers import get_provider, BaseMLLMProvider
from utils.image_cache import CachedImageGrabber
from utils.latency_tracker import (
    LatencyTracker, OperationType,
    init_tracker, get_tracker, shutdown_tracker
)


class MLLMGateway:
    """
    Unified MLLM Gateway for ELMiRA v2.
    
    Provides ROS services for:
    - Chat (text and vision)
    - Object detection with MLLM
    - Object visibility checking
    - Backward compatible v1 services
    """
    
    def __init__(self):
        rospy.init_node("mllm_gateway")
        
        # Load configuration from ROS params
        self.provider_name = rospy.get_param("~provider", "openai")
        self.model = rospy.get_param("~model", None)  # Use provider default
        self.temperature = rospy.get_param("~temperature", 0.7)
        self.max_tokens = rospy.get_param("~max_tokens", 4096)
        self.timeout = rospy.get_param("~timeout", 30.0)
        self.image_topic = rospy.get_param("~image_topic", "/nico/vision/right")
        self.cache_duration = rospy.get_param("~cache_duration", 0.5)
        
        # Latency tracking configuration
        self.track_latency = rospy.get_param("~track_latency", False)
        self.latency_log_dir = rospy.get_param("~latency_log_dir", "")
        
        # Get API key from environment
        self.api_key = self._get_api_key()
        
        # Initialize provider
        self.provider: Optional[BaseMLLMProvider] = None
        self._init_provider()
        
        # Initialize latency tracker (for benchmarking MLLM cognitive core latency)
        self.latency_tracker = init_tracker(
            enabled=self.track_latency,
            log_dir=self.latency_log_dir if self.latency_log_dir else None,
            provider=self.provider_name,
            model=self.provider.model if self.provider else "unknown",
        )
        
        # Initialize image cache
        self.image_cache = CachedImageGrabber(
            topic=self.image_topic,
            cache_duration=self.cache_duration,
        )
        
        # Register v2 services (new names)
        rospy.Service("mllm_chat", PromptTextLLM, self.handle_chat)
        rospy.Service("mllm_vision", PromptVisionLLM, self.handle_vision)
        rospy.Service("mllm_visibility", CheckLLMObjectVisibility, self.handle_visibility)
        rospy.Service("mllm_detect", DetectWithMLLM, self.handle_detect)
        
        # Register backward-compatible v1 services
        # These are the same services but with legacy names
        rospy.Service("llm_chat", PromptTextLLM, self.handle_chat)
        rospy.Service("llm_vision", PromptVisionLLM, self.handle_vision)
        rospy.Service("llm_object_visibility", CheckLLMObjectVisibility, self.handle_visibility)
        
        # Conversation management service
        rospy.Service("mllm_reset_conversation", Trigger, self.handle_reset_conversation)
        
        # Grounded chat service for action planning
        rospy.Service("mllm_grounded_chat", PromptMLLMWithGrounding, self.handle_grounded_chat)
        
        # Publisher for detection visualization
        self.detection_pub = rospy.Publisher("/elmira/detections", DetectedObjectArray, queue_size=1)
        
        rospy.loginfo(f"MLLM Gateway started with provider: {self.provider_name}")
        rospy.loginfo(f"Model: {self.provider.model if self.provider else 'N/A'}")
        rospy.loginfo("Conversation memory enabled (max 10 turns)")
    
    def _get_api_key(self) -> str:
        """Get API key from environment based on provider."""
        if self.provider_name == "openai":
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                rospy.logerr("OPENAI_API_KEY environment variable not set")
                raise ValueError("OPENAI_API_KEY not set")
            return key
        elif self.provider_name == "google":
            key = os.environ.get("GOOGLE_API_KEY")
            if not key:
                rospy.logerr("GOOGLE_API_KEY environment variable not set")
                raise ValueError("GOOGLE_API_KEY not set")
            return key
        else:
            rospy.logerr(f"Unknown provider: {self.provider_name}")
            raise ValueError(f"Unknown provider: {self.provider_name}")
    
    def _init_provider(self):
        """Initialize the MLLM provider."""
        try:
            self.provider = get_provider(
                provider_name=self.provider_name,
                api_key=self.api_key,
                model=self.model,
            )
            rospy.loginfo(f"Initialized {self.provider.provider_name} provider")
        except Exception as e:
            rospy.logerr(f"Failed to initialize provider: {e}")
            raise
    
    def _get_image(self) -> np.ndarray:
        """Get current camera frame."""
        return self.image_cache.get_frame()
    
    def handle_chat(self, request) -> PromptTextLLMResponse:
        """
        Handle chat request (text only, no image).
        
        Service: mllm_chat / llm_chat (v1 compat)
        """
        rospy.loginfo(f"Chat request: {request.prompt[:100]}...")
        
        start_time = time.time()
        
        try:
            response = self.provider.chat(
                prompt=request.prompt,
                image=None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            rospy.loginfo(f"Chat response in {latency_ms:.0f}ms")
            
            if response.success:
                rospy.loginfo(f"LLM output:\n{response.response_json}")
                # Track successful latency (this is the core cognitive latency)
                self.latency_tracker.record(
                    operation_type=OperationType.CHAT,
                    latency_ms=latency_ms,
                    success=True,
                    input_length=len(request.prompt),
                    output_length=len(response.response_json),
                )
                return PromptTextLLMResponse(response=response.response_json)
            else:
                rospy.logerr(f"Chat failed: {response.error_message}")
                # Track failed request
                self.latency_tracker.record(
                    operation_type=OperationType.CHAT,
                    latency_ms=latency_ms,
                    success=False,
                    input_length=len(request.prompt),
                    notes=response.error_message,
                )
                # Return error as JSON for backward compatibility
                error_response = json.dumps({
                    "actions": [
                        {"action": "speak", "text": "Sorry, I encountered an error processing your request."}
                    ],
                    "error": response.error_message
                })
                return PromptTextLLMResponse(response=error_response)
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            rospy.logerr(f"Chat exception: {e}")
            # Track exception
            self.latency_tracker.record(
                operation_type=OperationType.CHAT,
                latency_ms=latency_ms,
                success=False,
                input_length=len(request.prompt),
                notes=f"Exception: {e}",
            )
            error_response = json.dumps({
                "actions": [
                    {"action": "speak", "text": "Sorry, something went wrong."}
                ],
                "error": str(e)
            })
            return PromptTextLLMResponse(response=error_response)
    
    def handle_vision(self, request) -> PromptVisionLLMResponse:
        """
        Handle vision request (chat with current camera image).
        
        Service: mllm_vision / llm_vision (v1 compat)
        """
        rospy.loginfo("Vision request received")
        
        start_time = time.time()
        
        try:
            # Get current camera frame
            image = self._get_image()
            
            response = self.provider.chat(
                prompt="Describe what you see on the table and respond with appropriate actions.",
                image=image,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            rospy.loginfo(f"Vision response in {latency_ms:.0f}ms")
            
            if response.success:
                rospy.loginfo(f"LLM output:\n{response.response_json}")
                # Track successful vision latency
                self.latency_tracker.record(
                    operation_type=OperationType.VISION,
                    latency_ms=latency_ms,
                    success=True,
                    output_length=len(response.response_json),
                )
                return PromptVisionLLMResponse(response=response.response_json)
            else:
                rospy.logerr(f"Vision failed: {response.error_message}")
                # Track failed vision request
                self.latency_tracker.record(
                    operation_type=OperationType.VISION,
                    latency_ms=latency_ms,
                    success=False,
                    notes=response.error_message,
                )
                error_response = json.dumps({
                    "actions": [
                        {"action": "speak", "text": "Sorry, I had trouble seeing the table."}
                    ],
                    "error": response.error_message
                })
                return PromptVisionLLMResponse(response=error_response)
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            rospy.logerr(f"Vision exception: {e}")
            # Track exception
            self.latency_tracker.record(
                operation_type=OperationType.VISION,
                latency_ms=latency_ms,
                success=False,
                notes=f"Exception: {e}",
            )
            error_response = json.dumps({
                "actions": [
                    {"action": "speak", "text": "Sorry, I couldn't process the image."}
                ],
                "error": str(e)
            })
            return PromptVisionLLMResponse(response=error_response)
    
    def handle_visibility(self, request) -> CheckLLMObjectVisibilityResponse:
        """
        Handle object visibility check request.
        
        Service: mllm_visibility / llm_object_visibility (v1 compat)
        """
        rospy.loginfo(f"Visibility check for: {request.prompt}")
        
        start_time = time.time()
        
        try:
            # Get current camera frame
            image = self._get_image()
            
            # Check object visibility
            visible, message = self.provider.check_object_visibility(
                object_name=request.prompt,
                image=image,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            rospy.loginfo(f"Visibility check in {latency_ms:.0f}ms: visible={visible}")
            
            # Track visibility check latency
            self.latency_tracker.record(
                operation_type=OperationType.VISIBILITY,
                latency_ms=latency_ms,
                success=True,
                input_length=len(request.prompt),
                notes=f"visible={visible}",
            )
            
            return CheckLLMObjectVisibilityResponse(
                object_visible=visible,
                system_message=message
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            rospy.logerr(f"Visibility check exception: {e}")
            # Track failed visibility check
            self.latency_tracker.record(
                operation_type=OperationType.VISIBILITY,
                latency_ms=latency_ms,
                success=False,
                input_length=len(request.prompt),
                notes=f"Exception: {e}",
            )
            return CheckLLMObjectVisibilityResponse(
                object_visible=False,
                system_message=f"SYSTEM: Visibility check failed: {e}"
            )
    
    def handle_detect(self, request) -> DetectWithMLLMResponse:
        """
        Handle object detection request using MLLM.
        
        Service: mllm_detect
        
        This provides an alternative to OWLv2 detection using the MLLM's
        visual grounding capabilities.
        """
        rospy.loginfo(f"MLLM detection request for: {request.texts}")
        
        start_time = time.time()
        
        # Get confidence threshold from request or use default
        confidence_threshold = request.confidence_threshold if request.confidence_threshold > 0 else 0.5
        
        try:
            # Get current camera frame
            image = self._get_image()
            
            # Detect objects
            detections = self.provider.detect_objects(
                texts=list(request.texts),
                image=image,
                confidence_threshold=confidence_threshold,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            rospy.loginfo(f"MLLM detection in {latency_ms:.0f}ms: {len(detections)} objects")
            
            # Convert to ROS message format
            ros_detections = []
            for det in detections:
                ros_det = DetectedObject()
                ros_det.label = det.label
                ros_det.score = det.score
                ros_det.center_x = det.center_x
                ros_det.center_y = det.center_y
                ros_det.width = det.width
                ros_det.height = det.height
                ros_detections.append(ros_det)
            
            # Track detection latency
            self.latency_tracker.record(
                operation_type=OperationType.DETECT,
                latency_ms=latency_ms,
                success=True,
                detections_count=len(ros_detections),
            )
            
            return DetectWithMLLMResponse(
                objects=ros_detections,
                success=True,
                error_message="",
                latency_ms=latency_ms
            )
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            rospy.logerr(f"MLLM detection exception: {e}")
            # Track failed detection
            self.latency_tracker.record(
                operation_type=OperationType.DETECT,
                latency_ms=latency_ms,
                success=False,
                notes=f"Exception: {e}",
            )
            return DetectWithMLLMResponse(
                objects=[],
                success=False,
                error_message=str(e),
                latency_ms=latency_ms
            )
    
    def handle_reset_conversation(self, request) -> TriggerResponse:
        """
        Handle conversation reset request.
        
        Service: mllm_reset_conversation
        
        Clears the conversation history to start fresh multi-turn context.
        Call this when starting a new interaction or if context becomes stale.
        """
        try:
            self.provider.reset_conversation()
            rospy.loginfo("Conversation history cleared")
            return TriggerResponse(
                success=True,
                message="Conversation history cleared"
            )
        except Exception as e:
            rospy.logerr(f"Failed to reset conversation: {e}")
            return TriggerResponse(
                success=False,
                message=str(e)
            )
    
    def handle_grounded_chat(self, request) -> PromptMLLMWithGroundingResponse:
        """
        Handle grounded chat request for action planning.
        
        Service: mllm_grounded_chat
        
        Combines chat with object detection in a single MLLM call.
        The MLLM interprets the command AND locates the target object.
        This eliminates the two-stage disconnect between action parsing and detection.
        
        Captures a FRESH frame (not cached) for accurate grounding.
        """
        rospy.loginfo(f"Grounded chat request: {request.prompt[:100]}...")
        rospy.loginfo(f"Objects to detect: {request.detect_objects}")
        
        start_time = time.time()
        
        try:
            # Capture FRESH frame for grounding (not cached)
            # This ensures we're grounding on current scene, not stale image
            image = None
            if request.include_image:
                image = self._get_fresh_image()
            
            # Use temperature from request or default
            temperature = request.temperature if request.temperature > 0 else self.temperature
            
            # Call provider's grounded chat
            response = self.provider.chat_with_grounding(
                prompt=request.prompt,
                detect_objects=list(request.detect_objects),
                image=image,
                temperature=temperature,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            rospy.loginfo(f"Grounded chat response in {latency_ms:.0f}ms")
            
            if response.success:
                rospy.loginfo(f"LLM output:\n{response.response_json}")
                rospy.loginfo(f"Detections: {len(response.detections)} objects")
                
                # Convert detections to ROS message format
                ros_detections = []
                for det in response.detections:
                    ros_det = DetectedObject()
                    ros_det.label = det.label
                    ros_det.score = det.score
                    ros_det.center_x = det.center_x
                    ros_det.center_y = det.center_y
                    ros_det.width = det.width
                    ros_det.height = det.height
                    ros_detections.append(ros_det)
                
                # Publish detections for visualization
                self._publish_detections(ros_detections)
                
                # Track grounded chat latency - THIS IS THE KEY COGNITIVE CORE METRIC
                # Measures: ASR complete → MLLM returns Mode/Action/Target JSON
                self.latency_tracker.record(
                    operation_type=OperationType.GROUNDED_CHAT,
                    latency_ms=latency_ms,
                    success=True,
                    input_length=len(request.prompt),
                    output_length=len(response.response_json),
                    detections_count=len(ros_detections),
                )
                
                return PromptMLLMWithGroundingResponse(
                    response_json=response.response_json,
                    detections=ros_detections,
                    success=True,
                    error_message="",
                    latency_ms=latency_ms
                )
            else:
                rospy.logerr(f"Grounded chat failed: {response.error_message}")
                # Track failed grounded chat
                self.latency_tracker.record(
                    operation_type=OperationType.GROUNDED_CHAT,
                    latency_ms=latency_ms,
                    success=False,
                    input_length=len(request.prompt),
                    notes=response.error_message,
                )
                return PromptMLLMWithGroundingResponse(
                    response_json="",
                    detections=[],
                    success=False,
                    error_message=response.error_message,
                    latency_ms=latency_ms
                )
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            rospy.logerr(f"Grounded chat exception: {e}")
            # Track exception
            self.latency_tracker.record(
                operation_type=OperationType.GROUNDED_CHAT,
                latency_ms=latency_ms,
                success=False,
                input_length=len(request.prompt),
                notes=f"Exception: {e}",
            )
            return PromptMLLMWithGroundingResponse(
                response_json="",
                detections=[],
                success=False,
                error_message=str(e),
                latency_ms=latency_ms
            )
    
    def _publish_detections(self, detections):
        """Publish detections for visualization node."""
        try:
            from std_msgs.msg import Header
            msg = DetectedObjectArray()
            msg.header = Header()
            msg.header.stamp = rospy.Time.now()
            msg.detections = detections
            self.detection_pub.publish(msg)
            rospy.logdebug(f"Published {len(detections)} detections for visualization")
        except Exception as e:
            rospy.logwarn(f"Failed to publish detections: {e}")
    
    def _get_fresh_image(self) -> np.ndarray:
        """
        Capture a fresh frame from the camera.
        
        Uses rospy.wait_for_message to get the latest frame,
        bypassing the image cache for maximum accuracy in grounding.
        """
        import sensor_msgs.msg
        import cv_bridge
        
        bridge = cv_bridge.CvBridge()
        img_msg = rospy.wait_for_message(
            self.image_topic,
            sensor_msgs.msg.Image,
            timeout=5.0
        )
        return bridge.imgmsg_to_cv2(img_msg, "bgr8")
    
    def run(self):
        """Run the gateway node."""
        rospy.loginfo("MLLM Gateway running...")
        
        # Register shutdown hook to print latency summary
        rospy.on_shutdown(self._on_shutdown)
        
        rospy.spin()
    
    def _on_shutdown(self):
        """Cleanup on node shutdown."""
        rospy.loginfo("MLLM Gateway shutting down...")
        
        # Print latency benchmarking summary
        if self.latency_tracker:
            shutdown_tracker()
        
        # Stop image cache
        self.image_cache.stop()
        rospy.loginfo("MLLM Gateway shutdown complete")


def main():
    try:
        gateway = MLLMGateway()
        gateway.run()
    except Exception as e:
        rospy.logerr(f"MLLM Gateway failed to start: {e}")
        raise


if __name__ == "__main__":
    main()
