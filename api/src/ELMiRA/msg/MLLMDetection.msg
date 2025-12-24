# MLLMDetection.msg
# Extended detection message with MLLM-specific fields

string label                     # Object label
float64 score                    # Confidence score (0-1)
float64 center_x                 # Normalized center x (0-1)
float64 center_y                 # Normalized center y (0-1)
float64 width                    # Normalized width
float64 height                   # Normalized height

# Extended fields for MLLM
string grounding_text            # Natural language grounding description
float64[] bbox_raw               # Raw bounding box [x_min, y_min, x_max, y_max]
string provider                  # Which provider detected this (openai/google)
