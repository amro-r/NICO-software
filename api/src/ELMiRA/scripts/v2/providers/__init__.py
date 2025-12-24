#!/usr/bin/env python3
"""
ELMiRA v2 Provider Package

Contains provider adapters for different MLLM backends:
- OpenAI (GPT-4o, GPT-4.5)
- Google (Gemini 2.5 Flash)
"""

import sys
from pathlib import Path

# Add parent directory to path for absolute imports when run by ROS
_providers_dir = Path(__file__).parent.resolve()
_v2_dir = _providers_dir.parent
if str(_v2_dir) not in sys.path:
    sys.path.insert(0, str(_v2_dir))
if str(_providers_dir) not in sys.path:
    sys.path.insert(0, str(_providers_dir))

from base import BaseMLLMProvider, MLLMResponse, DetectionResult, GroundedResponse
from openai_provider import OpenAIProvider

# Conditional import for Google provider
try:
    from google_provider import GoogleProvider
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    GoogleProvider = None


def get_provider(provider_name: str, api_key: str, model: str = None, **kwargs):
    """
    Factory function to get a provider instance.
    
    Args:
        provider_name: Provider name ('openai' or 'google')
        api_key: API key for the provider
        model: Optional model name override
        **kwargs: Additional provider-specific arguments
        
    Returns:
        BaseMLLMProvider instance
        
    Raises:
        ValueError: If provider is not supported
        ImportError: If Google provider is requested but not installed
    """
    provider_name = provider_name.lower()
    
    if provider_name == "openai":
        return OpenAIProvider(api_key=api_key, model=model, **kwargs)
    elif provider_name == "google":
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                "Google provider not available. Install with: pip install google-genai"
            )
        return GoogleProvider(api_key=api_key, model=model, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Supported: openai, google")


__all__ = [
    "BaseMLLMProvider",
    "MLLMResponse", 
    "DetectionResult",
    "GroundedResponse",
    "OpenAIProvider",
    "GoogleProvider",
    "get_provider",
    "GOOGLE_AVAILABLE",
]
