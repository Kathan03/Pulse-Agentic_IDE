"""
LLM Client Abstraction for Pulse IDE v2.6 (Phase 1).

Provides unified interface for OpenAI, Anthropic, and Google LLMs with function calling support.

Supported Models:
- OpenAI: gpt-5.x series
- Anthropic: claude-opus-4-5, claude-sonnet-4-5
- Google: gemini-3-pro, gemini-3-flash

Features:
- Function calling / tool use for all providers
- API key loading from settings
- Graceful error handling
- Structured response format
- Token usage tracking with cost estimation
"""

import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import SDKs
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from src.core.settings import get_settings_manager

logger = logging.getLogger(__name__)


# ============================================================================
# RESPONSE MODELS
# ============================================================================

@dataclass
class ToolCall:
    """Represents a tool call request from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class TokenUsage:
    """
    Token usage with cost estimation.
    
    Attributes:
        prompt_tokens: Number of input tokens.
        completion_tokens: Number of output tokens.
        total_tokens: Total tokens (prompt + completion).
        estimated_cost_usd: Estimated cost in USD.
        model: Model name that was used.
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    model: str = ""


@dataclass
class LLMResponse:
    """
    Unified LLM response format.

    Attributes:
        content: Text response from LLM (if any).
        tool_calls: List of tool calls requested by LLM (if any).
        finish_reason: Reason for completion ("stop", "tool_calls", etc.).
        usage: Token usage with cost estimation.
    """
    content: Optional[str]
    tool_calls: List[ToolCall]
    finish_reason: str
    usage: TokenUsage


# ============================================================================
# SESSION COST TRACKER
# ============================================================================

class SessionCostTracker:
    """
    Accumulates token usage and cost across a session, with per-model breakdown.
    
    Example:
        >>> tracker = SessionCostTracker()
        >>> tracker.add(usage)  # TokenUsage from LLMResponse
        >>> print(tracker.summary())
        "3 calls, 5,432 tokens, $0.0156"
    """
    
    def __init__(self):
        """Initialize empty tracker."""
        self.usage_by_model: Dict[str, Dict[str, Any]] = {}
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.call_count: int = 0
    
    def add(self, usage: TokenUsage) -> None:
        """
        Add token usage from an LLM response.
        
        Args:
            usage: TokenUsage object from LLMResponse.
        """
        model = usage.model or "unknown"
        
        # Initialize model entry if needed
        if model not in self.usage_by_model:
            self.usage_by_model[model] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "call_count": 0
            }
        
        # Update per-model stats
        self.usage_by_model[model]["prompt_tokens"] += usage.prompt_tokens
        self.usage_by_model[model]["completion_tokens"] += usage.completion_tokens
        self.usage_by_model[model]["total_tokens"] += usage.total_tokens
        self.usage_by_model[model]["cost_usd"] += usage.estimated_cost_usd
        self.usage_by_model[model]["call_count"] += 1
        
        # Update totals
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_cost_usd += usage.estimated_cost_usd
        self.call_count += 1
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens (prompt + completion)."""
        return self.total_prompt_tokens + self.total_completion_tokens
    
    def get_model_breakdown(self) -> List[Dict[str, Any]]:
        """
        Get usage breakdown by model for settings UI.
        
        Returns:
            List of dicts with model, tokens, and cost.
        """
        breakdown = []
        for model, stats in sorted(self.usage_by_model.items()):
            breakdown.append({
                "model": model,
                "tokens": stats["total_tokens"],
                "prompt_tokens": stats["prompt_tokens"],
                "completion_tokens": stats["completion_tokens"],
                "cost_usd": stats["cost_usd"],
                "call_count": stats["call_count"]
            })
        return breakdown
    
    def reset(self) -> None:
        """Reset all tracking data."""
        self.usage_by_model = {}
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_usd = 0.0
        self.call_count = 0
    
    def summary(self) -> str:
        """Get human-readable summary string."""
        return f"{self.call_count} calls, {self.total_tokens:,} tokens, ${self.total_cost_usd:.4f}"


# Global session tracker instance
_session_tracker = SessionCostTracker()


def get_session_tracker() -> SessionCostTracker:
    """Get the global session cost tracker."""
    return _session_tracker


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """
    Unified LLM client supporting OpenAI and Anthropic.

    Automatically selects provider based on model name.
    Supports function calling / tool use for both providers.

    Example:
        >>> client = LLMClient()
        >>> response = client.generate(
        ...     model="gpt-5-mini",
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     tools=[...],
        ...     system_prompt="You are a helpful assistant."
        ... )
        >>> response.content
        "Hello! How can I help you?"
    """

    # Model provider mapping - ONLY user-specified models
    OPENAI_MODELS = [
        # GPT-5 series
        "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano",
        "gpt-5.2-codex", "gpt-5.1-codex-max", "gpt-5.1-codex",
        "gpt-5.2-pro", "gpt-5-pro"
    ]
    ANTHROPIC_MODELS = [
        # Claude 4.5 series
        "claude-sonnet-4.5", "claude-opus-4.5"
    ]
    GOOGLE_MODELS = [
        # Gemini 3 series
        "gemini-3-pro", "gemini-3-flash"
    ]

    # Models that use max_completion_tokens (newer OpenAI models)
    NEW_OPENAI_MODELS = [
        "gpt-5.2", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano",
        "gpt-5.2-codex", "gpt-5.1-codex-max", "gpt-5.1-codex",
        "gpt-5.2-pro", "gpt-5-pro"
    ]

    # Model parameter compatibility configuration
    MODEL_CONFIGS = {
        # GPT-5.x family: max_completion_tokens, temperature=1 only
        "gpt-5": {
            "max_tokens_param": "max_completion_tokens",
            "supports_custom_temperature": False,
            "default_temperature": 1.0
        },  
        # Claude models: max_tokens, supports custom temperature
        "claude": {
            "max_tokens_param": "max_tokens",
            "supports_custom_temperature": True,
            "default_temperature": 0.7
        },
        # Gemini models
        "gemini": {
            "max_tokens_param": "max_output_tokens",
            "supports_custom_temperature": True,
            "default_temperature": 0.7
        }
    }

    # Pricing per 1M tokens (input_price, output_price) in USD
    # These are approximate prices as of Jan 2026 - update as needed
    MODEL_PRICING = {
        # GPT-5 series
        "gpt-5.2": (1.75, 14.00),
        "gpt-5.1": (1.25, 10.00),
        "gpt-5": (1.25, 10.00),
        "gpt-5-mini": (0.25, 2.00),
        "gpt-5-nano": (0.05, 0.40),
        "gpt-5.2-codex": (1.75, 14.00),
        "gpt-5.1-codex-max": (1.25, 10.00),
        "gpt-5.1-codex": (1.25, 10.00),
        "gpt-5.2-pro": (21.00, 168.00),
        "gpt-5-pro": (15.00, 120.00),
        # Claude 4.5 series
        "claude-opus-4.5": (5.00, 25.00),
        "claude-sonnet-4.5": (3.00, 15.00),
        # Gemini 3 series
        "gemini-3-pro": (3.00, 15.00), #Took everage
        "gemini-3-flash": (0.50, 3.00),
    }

    def __init__(self):
        """
        Initialize LLM client.

        Loads API keys from settings manager.
        """
        self.settings = get_settings_manager()
        self.openai_client: Optional[openai.OpenAI] = None
        self.anthropic_client: Optional[anthropic.Anthropic] = None
        self.google_configured: bool = False

        logger.info("LLMClient initialized")

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate estimated cost in USD for an LLM call.

        Args:
            model: Model identifier.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD (rounded to 6 decimal places).
        """
        # Find matching pricing by model prefix
        for prefix, (input_price, output_price) in self.MODEL_PRICING.items():
            if model.startswith(prefix):
                cost = (prompt_tokens / 1_000_000) * input_price
                cost += (completion_tokens / 1_000_000) * output_price
                return round(cost, 6)
        
        # Unknown model - return 0
        logger.warning(f"No pricing found for model '{model}', returning $0 cost estimate")
        return 0.0

    def _get_provider(self, model: str) -> str:
        """
        Determine provider from model name.

        Args:
            model: Model identifier.

        Returns:
            Provider name ("openai", "anthropic", or "google").

        Raises:
            ValueError: If model not recognized.
        """
        if model in self.OPENAI_MODELS:
            return "openai"
        elif model in self.ANTHROPIC_MODELS:
            return "anthropic"
        elif model in self.GOOGLE_MODELS:
            return "google"
        else:
            # Fallback: guess from prefix
            if model.startswith("gpt"):
                return "openai"
            elif model.startswith("claude"):
                return "anthropic"
            elif model.startswith("gemini"):
                return "google"
            else:
                raise ValueError(f"Unknown model: {model}")

    def _get_model_config(self, model: str) -> Dict[str, Any]:
        """
        Get parameter configuration for a specific model.

        Args:
            model: Model identifier.

        Returns:
            Configuration dict with parameter compatibility info.
        """
        # Match model to config by prefix
        for prefix, config in self.MODEL_CONFIGS.items():
            if model.startswith(prefix):
                return config

        # Default fallback for unknown models (use safe defaults)
        logger.warning(f"Unknown model '{model}', using safe default config")
        return {
            "max_tokens_param": "max_tokens",
            "supports_custom_temperature": True,
            "default_temperature": 0.7
        }

    def _uses_new_token_param(self, model: str) -> bool:
        """
        Check if model uses max_completion_tokens (new) vs max_tokens (legacy).

        Args:
            model: Model identifier.

        Returns:
            True if model uses max_completion_tokens, False if max_tokens.
        """
        config = self._get_model_config(model)
        return config["max_tokens_param"] == "max_completion_tokens"

    def _init_openai_client(self) -> openai.OpenAI:
        """
        Initialize OpenAI client with API key from settings.

        Priority order (respects DEV_MODE):
        - DEV_MODE=true: ONLY use environment variable (skip platformdirs)
        - DEV_MODE=false/unset: Settings UI first, then fallback to .env

        Returns:
            OpenAI client instance.

        Raises:
            ValueError: If API key not configured.
        """
        if self.openai_client is not None:
            return self.openai_client

        # Load API key from config.json (platformdirs) - single source of truth
        api_key = self.settings.get_api_key("openai")
        if api_key:
            logger.info("Using OpenAI API key from config.json")

        if not api_key:
            raise ValueError(
                "OpenAI API key not configured. "
                "Configure your API key in Settings → API Keys."
            )

        if not OPENAI_AVAILABLE:
            raise RuntimeError(
                "OpenAI SDK not installed. "
                "Install with: pip install openai"
            )

        logger.info(f"Initializing OpenAI client with key: {api_key[:20]}...")
        self.openai_client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
        return self.openai_client

    def _init_anthropic_client(self) -> anthropic.Anthropic:
        """
        Initialize Anthropic client with API key from settings.

        Priority order (respects DEV_MODE):
        - DEV_MODE=true: ONLY use environment variable (skip platformdirs)
        - DEV_MODE=false/unset: Settings UI first, then fallback to .env

        Returns:
            Anthropic client instance.

        Raises:
            ValueError: If API key not configured.
        """
        if self.anthropic_client is not None:
            return self.anthropic_client

        # Load API key from config.json (platformdirs) - single source of truth
        api_key = self.settings.get_api_key("anthropic")
        if api_key:
            logger.info("Using Anthropic API key from config.json")

        if not api_key:
            raise ValueError(
                "Anthropic API key not configured. "
                "Configure your API key in Settings → API Keys."
            )

        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError(
                "Anthropic SDK not installed. "
                "Install with: pip install anthropic"
            )

        logger.info(f"Initializing Anthropic client with key: {api_key[:20]}...")
        self.anthropic_client = anthropic.Anthropic(api_key=api_key)
        logger.info("Anthropic client initialized successfully")
        return self.anthropic_client

    def _init_google_client(self) -> None:
        """
        Initialize Google Generative AI client with API key from settings.

        Priority order (respects DEV_MODE):
        - DEV_MODE=true: ONLY use environment variable (skip platformdirs)
        - DEV_MODE=false/unset: Settings UI first, then fallback to .env

        Raises:
            ValueError: If API key not configured.
        """
        if self.google_configured:
            return

        # Load API key from config.json (platformdirs) - single source of truth
        api_key = self.settings.get_api_key("google")
        if api_key:
            logger.info("Using Google API key from config.json")

        if not api_key:
            raise ValueError(
                "Google API key not configured. "
                "Configure your API key in Settings → API Keys."
            )

        if not GOOGLE_AVAILABLE:
            raise RuntimeError(
                "Google Generative AI SDK not installed. "
                "Install with: pip install google-generativeai"
            )

        logger.info(f"Initializing Google Generative AI client with key: {api_key[:20]}...")
        genai.configure(api_key=api_key)
        self.google_configured = True
        logger.info("Google Generative AI client initialized successfully")

    def generate(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Generate LLM response with optional function calling.

        Args:
            model: Model identifier (e.g., "gpt-5-mini", "claude-sonnet-4-5").
            messages: Conversation history (OpenAI format).
            system_prompt: System prompt (optional).
            tools: Function/tool schemas (optional).
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens to generate.

        Returns:
            LLMResponse with content and/or tool calls.

        Raises:
            ValueError: If API key not configured or model unknown.
            RuntimeError: If SDK not installed or API call fails.
        """
        provider = self._get_provider(model)

        if provider == "openai":
            return self._generate_openai(
                model, messages, system_prompt, tools, temperature, max_tokens
            )
        elif provider == "anthropic":
            return self._generate_anthropic(
                model, messages, system_prompt, tools, temperature, max_tokens
            )
        elif provider == "google":
            return self._generate_google(
                model, messages, system_prompt, tools, temperature, max_tokens
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _generate_openai(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """
        Generate response using OpenAI API.

        Args:
            model: OpenAI model name.
            messages: Conversation history.
            system_prompt: System prompt.
            tools: Tool schemas in OpenAI format.
            temperature: Sampling temperature.
            max_tokens: Max tokens.

        Returns:
            LLMResponse.
        """
        try:
            client = self._init_openai_client()

            # Get model-specific parameter configuration
            config = self._get_model_config(model)
            logger.debug(f"Model config for {model}: {config}")

            # Build messages with system prompt
            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            # Prepare API call parameters (base params that all models support)
            params = {
                "model": model,
                "messages": full_messages,
            }

            # Add temperature parameter (only if model supports custom values)
            if config["supports_custom_temperature"]:
                params["temperature"] = temperature
                logger.debug(f"Using custom temperature={temperature} for {model}")
            else:
                # Model requires default temperature
                params["temperature"] = config["default_temperature"]
                logger.debug(f"Using default temperature={config['default_temperature']} for {model} (custom values not supported)")

            # Add max tokens parameter (using correct parameter name for model)
            max_tokens_param = config["max_tokens_param"]
            params[max_tokens_param] = max_tokens
            logger.debug(f"Using {max_tokens_param}={max_tokens} for {model}")

            # Add tools if provided
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"  # Let model decide

            # Make API call
            logger.info(f"OpenAI API call: model={model}, messages={len(full_messages)}, tools={len(tools) if tools else 0}")

            try:
                response = client.chat.completions.create(**params)
            except openai.BadRequestError as e:
                error_message = str(e)
                logger.warning(f"OpenAI API parameter error: {error_message}")

                # Comprehensive fallback handling for parameter errors
                retry_needed = False

                # Handle max_tokens parameter errors
                if "max_tokens" in error_message or "max_completion_tokens" in error_message:
                    logger.warning("Max tokens parameter error, trying alternative")
                    params.pop("max_tokens", None)
                    params.pop("max_completion_tokens", None)

                    # Try opposite parameter
                    if "max_completion_tokens" in error_message:
                        params["max_tokens"] = max_tokens
                        logger.info(f"Retrying with max_tokens={max_tokens}")
                    else:
                        params["max_completion_tokens"] = max_tokens
                        logger.info(f"Retrying with max_completion_tokens={max_tokens}")
                    retry_needed = True

                # Handle temperature parameter errors
                if "temperature" in error_message:
                    logger.warning("Temperature parameter error, using default")
                    # Some models only support default temperature (1.0 for GPT-5)
                    if "gpt-5" in model:
                        params["temperature"] = 1.0
                        logger.info(f"Retrying with default temperature=1.0 for {model}")
                    else:
                        params.pop("temperature", None)
                        logger.info("Retrying without temperature parameter")
                    retry_needed = True

                # Retry API call if we made parameter adjustments
                if retry_needed:
                    logger.info(f"Retrying API call with adjusted parameters: {list(params.keys())}")
                    response = client.chat.completions.create(**params)
                else:
                    # Not a parameter error we can fix, re-raise
                    raise

            # Parse response
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            # Extract content
            content = message.content if message.content else None

            # Extract tool calls
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    import json
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments)
                    ))

            # Extract usage with cost calculation
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            estimated_cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
            
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost,
                model=model
            )

            logger.info(f"OpenAI response: finish_reason={finish_reason}, tool_calls={len(tool_calls)}, tokens={usage.total_tokens}, cost=${usage.estimated_cost_usd:.6f}")

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                usage=usage
            )

        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            raise ValueError(
                "Invalid OpenAI API key. Please check Settings → API Keys."
            )
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise RuntimeError(
                "OpenAI rate limit exceeded. Please try again later."
            )
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"OpenAI unexpected error: {e}", exc_info=True)
            raise RuntimeError(f"OpenAI error: {str(e)}")

    def _generate_anthropic(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """
        Generate response using Anthropic API.

        Args:
            model: Anthropic model name.
            messages: Conversation history (OpenAI format, will be converted).
            system_prompt: System prompt.
            tools: Tool schemas (OpenAI format, will be converted).
            temperature: Sampling temperature.
            max_tokens: Max tokens.

        Returns:
            LLMResponse.
        """
        try:
            client = self._init_anthropic_client()

            # Convert messages from OpenAI to Anthropic format
            anthropic_messages = self._convert_messages_to_anthropic(messages)

            # Prepare API call parameters
            params = {
                "model": model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # Add system prompt if provided
            if system_prompt:
                params["system"] = system_prompt

            # Add tools if provided (convert from OpenAI format)
            if tools:
                params["tools"] = self._convert_tools_to_anthropic(tools)

            # Make API call
            logger.info(f"Anthropic API call: model={model}, messages={len(anthropic_messages)}, tools={len(tools) if tools else 0}")
            response = client.messages.create(**params)

            # Parse response
            content_text = None
            tool_calls = []

            # Anthropic returns content as list of blocks
            for block in response.content:
                if block.type == "text":
                    content_text = block.text
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input
                    ))

            # Extract usage with cost calculation
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens
            estimated_cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
            
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost,
                model=model
            )

            logger.info(f"Anthropic response: stop_reason={response.stop_reason}, tool_calls={len(tool_calls)}, tokens={usage.total_tokens}, cost=${usage.estimated_cost_usd:.6f}")

            return LLMResponse(
                content=content_text,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason,
                usage=usage
            )

        except anthropic.AuthenticationError as e:
            logger.error(f"Anthropic authentication failed: {e}")
            raise ValueError(
                "Invalid Anthropic API key. Please check Settings → API Keys."
            )
        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic rate limit exceeded: {e}")
            raise RuntimeError(
                "Anthropic rate limit exceeded. Please try again later."
            )
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise RuntimeError(f"Anthropic API error: {str(e)}")
        except Exception as e:
            logger.error(f"Anthropic unexpected error: {e}", exc_info=True)
            raise RuntimeError(f"Anthropic error: {str(e)}")

    def _generate_google(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """
        Generate response using Google Generative AI API.

        Args:
            model: Google model name (e.g., "gemini-3-pro").
            messages: Conversation history (OpenAI format, will be converted).
            system_prompt: System prompt.
            tools: Tool schemas (OpenAI format, will be converted).
            temperature: Sampling temperature.
            max_tokens: Max tokens.

        Returns:
            LLMResponse.
        """
        try:
            self._init_google_client()

            # Create generative model with system instruction
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )

            model_kwargs = {
                "model_name": model,
                "generation_config": generation_config
            }

            if system_prompt:
                model_kwargs["system_instruction"] = system_prompt

            # Add tools if provided (convert from OpenAI format)
            if tools:
                google_tools = self._convert_tools_to_google(tools)
                if google_tools:
                    model_kwargs["tools"] = google_tools

            google_model = genai.GenerativeModel(**model_kwargs)

            # Convert messages from OpenAI to Google format
            google_messages = self._convert_messages_to_google(messages)

            # Make API call
            logger.info(f"Google API call: model={model}, messages={len(google_messages)}, tools={len(tools) if tools else 0}")
            response = google_model.generate_content(google_messages)

            # Parse response
            content_text = None
            tool_calls = []

            # Check for valid response
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                # Extract content from parts
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        content_text = part.text
                    elif hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        # Generate a unique ID for the tool call
                        import uuid
                        tool_calls.append(ToolCall(
                            id=f"call_{uuid.uuid4().hex[:8]}",
                            name=fc.name,
                            arguments=dict(fc.args) if fc.args else {}
                        ))

            # Determine finish reason
            finish_reason = "stop"
            if tool_calls:
                finish_reason = "tool_calls"
            elif response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    # Map Google's finish reasons to our format
                    google_reason = str(candidate.finish_reason)
                    if "STOP" in google_reason:
                        finish_reason = "stop"
                    elif "MAX_TOKENS" in google_reason:
                        finish_reason = "length"
                    elif "SAFETY" in google_reason:
                        finish_reason = "content_filter"

            # Extract usage - Google may not always provide this
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
            
            total_tokens = prompt_tokens + completion_tokens
            estimated_cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost,
                model=model
            )

            logger.info(f"Google response: finish_reason={finish_reason}, tool_calls={len(tool_calls)}, tokens={usage.total_tokens}, cost=${usage.estimated_cost_usd:.6f}")

            return LLMResponse(
                content=content_text,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                usage=usage
            )

        except Exception as e:
            error_str = str(e)
            logger.error(f"Google API error: {e}", exc_info=True)
            
            # Check for common error types
            if "API_KEY" in error_str.upper() or "AUTHENTICATION" in error_str.upper():
                raise ValueError(
                    "Invalid Google API key. Please check Settings → API Keys."
                )
            elif "QUOTA" in error_str.upper() or "RATE" in error_str.upper():
                raise RuntimeError(
                    "Google API rate limit or quota exceeded. Please try again later."
                )
            else:
                raise RuntimeError(f"Google API error: {error_str}")

    def _convert_messages_to_google(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert OpenAI message format to Google Generative AI format.

        OpenAI format: {"role": "user"/"assistant"/"system", "content": "..."}
        Google format: {"role": "user"/"model", "parts": ["..."]}
                       (system is handled via system_instruction parameter)

        Args:
            messages: OpenAI format messages.

        Returns:
            Google format messages (excluding system messages).
        """
        google_messages = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            # Skip system messages (handled separately via system_instruction)
            if role == "system":
                continue

            # Map OpenAI roles to Google roles
            google_role = "user" if role == "user" else "model"

            google_messages.append({
                "role": google_role,
                "parts": [content]
            })

        return google_messages

    def _convert_tools_to_google(
        self, tools: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Convert OpenAI tool format to Google Generative AI format.

        OpenAI format:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        }

        Google format uses genai.protos.FunctionDeclaration

        Args:
            tools: OpenAI format tools.

        Returns:
            Google format tools (list of FunctionDeclaration).
        """
        google_functions = []

        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                # Use the declarative dict format which Google SDK accepts
                google_functions.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {"type": "object", "properties": {}})
                })

        if google_functions:
            # Wrap in a Tool object
            return [genai.protos.Tool(function_declarations=[
                genai.protos.FunctionDeclaration(**f) for f in google_functions
            ])]
        return []

    def _convert_messages_to_anthropic(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert OpenAI message format to Anthropic format.

        OpenAI format: {"role": "user"/"assistant"/"system", "content": "..."}
        Anthropic format: {"role": "user"/"assistant", "content": "..."}
                         (system is separate parameter, not in messages)

        Args:
            messages: OpenAI format messages.

        Returns:
            Anthropic format messages (excluding system messages).
        """
        anthropic_messages = []

        for msg in messages:
            # Skip system messages (handled separately)
            if msg.get("role") == "system":
                continue

            # Keep user and assistant messages
            anthropic_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        return anthropic_messages

    def _convert_tools_to_anthropic(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert OpenAI tool format to Anthropic format.

        OpenAI format:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        }

        Anthropic format:
        {
            "name": "...",
            "description": "...",
            "input_schema": {...}
        }

        Args:
            tools: OpenAI format tools.

        Returns:
            Anthropic format tools.
        """
        anthropic_tools = []

        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func["description"],
                    "input_schema": func["parameters"]
                })

        return anthropic_tools


__all__ = ["LLMClient", "LLMResponse", "ToolCall", "TokenUsage", "SessionCostTracker", "get_session_tracker"]
