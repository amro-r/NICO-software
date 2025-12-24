#!/usr/bin/env python3
"""
ELMiRA v2 - Modern Multimodal LLM Integration

This package provides a unified MLLM gateway for the ELMiRA system,
supporting multiple providers (OpenAI, Google) with built-in object
grounding and streaming responses.
"""

__version__ = "2.0.0"
__author__ = "ELMiRA Team"

from .llm_api_v2 import MLLMGateway
