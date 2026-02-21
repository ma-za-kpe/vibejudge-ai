"""Bedrock Converse API wrapper with token tracking and retry logic."""

import json
from datetime import datetime
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.constants import MODEL_RATES, BEDROCK_RETRY_ATTEMPTS
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BedrockClient:
    """Wrapper for Amazon Bedrock Converse API with token tracking."""
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize Bedrock client.
        
        Args:
            region_name: AWS region for Bedrock
        """
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.region = region_name
    
    @retry(
        stop=stop_after_attempt(BEDROCK_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type((ClientError,)),
        reraise=True,
    )
    def converse(
        self,
        model_id: str,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        top_p: float = 0.9,
    ) -> dict[str, Any]:
        """Call Bedrock Converse API with retry logic.
        
        Args:
            model_id: Bedrock model ID
            system_prompt: System prompt text
            user_message: User message text
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            
        Returns:
            Response dict with:
                - content: Generated text
                - usage: Token usage dict
                - stop_reason: Why generation stopped
                - latency_ms: Response latency
                
        Raises:
            ClientError: If Bedrock API call fails after retries
        """
        start_time = datetime.utcnow()
        
        try:
            response = self.client.converse(
                modelId=model_id,
                system=[{"text": system_prompt}],
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_message}],
                    }
                ],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": top_p,
                },
            )
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Extract response content
            output = response.get("output", {})
            message = output.get("message", {})
            content_blocks = message.get("content", [])
            content_text = content_blocks[0].get("text", "") if content_blocks else ""
            
            # Extract usage
            usage = response.get("usage", {})
            
            result = {
                "content": content_text,
                "usage": {
                    "input_tokens": usage.get("inputTokens", 0),
                    "output_tokens": usage.get("outputTokens", 0),
                    "total_tokens": usage.get("totalTokens", 0),
                },
                "stop_reason": response.get("stopReason", "unknown"),
                "latency_ms": latency_ms,
                "model_id": model_id,
            }
            
            logger.info(
                "bedrock_converse_success",
                model_id=model_id,
                input_tokens=result["usage"]["input_tokens"],
                output_tokens=result["usage"]["output_tokens"],
                latency_ms=latency_ms,
            )
            
            return result
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "bedrock_converse_failed",
                model_id=model_id,
                error_code=error_code,
                error=str(e),
            )
            raise
    
    def calculate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> dict[str, float]:
        """Calculate cost for a Bedrock API call.
        
        Args:
            model_id: Bedrock model ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Dict with input_cost_usd, output_cost_usd, total_cost_usd
        """
        rates = MODEL_RATES.get(model_id)
        if not rates:
            logger.warning("model_rates_not_found", model_id=model_id)
            return {
                "input_cost_usd": 0.0,
                "output_cost_usd": 0.0,
                "total_cost_usd": 0.0,
            }
        
        input_cost = input_tokens * rates["input"]
        output_cost = output_tokens * rates["output"]
        total_cost = input_cost + output_cost
        
        return {
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6),
        }
    
    def parse_json_response(self, content: str) -> Optional[dict]:
        """Parse JSON from LLM response.
        
        Handles common issues:
        - Markdown code blocks
        - Leading/trailing whitespace
        - Text before/after JSON
        
        Args:
            content: Raw LLM response text
            
        Returns:
            Parsed JSON dict or None if parsing fails
        """
        # Remove markdown code blocks
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        # Try to find JSON object boundaries
        start = content.find("{")
        end = content.rfind("}") + 1
        
        if start == -1 or end == 0:
            logger.error("json_parse_no_braces", content_preview=content[:200])
            return None
        
        json_str = content[start:end]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_failed",
                error=str(e),
                content_preview=json_str[:200],
            )
            return None
    
    def retry_with_correction(
        self,
        model_id: str,
        system_prompt: str,
        original_message: str,
        failed_response: str,
        parse_error: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Retry API call with correction prompt.
        
        Args:
            model_id: Bedrock model ID
            system_prompt: Original system prompt
            original_message: Original user message
            failed_response: Previous failed response
            parse_error: Error message from parsing
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Response dict from converse()
        """
        correction_prompt = f"""Your previous response was not valid JSON.

Previous response snippet:
{failed_response[:500]}

Parse error: {parse_error}

Please respond with ONLY a valid JSON object matching your system prompt schema.
No markdown code blocks, no text outside the JSON object.

Original request:
{original_message[:1000]}
"""
        
        logger.info("bedrock_retry_with_correction", model_id=model_id)
        
        return self.converse(
            model_id=model_id,
            system_prompt=system_prompt,
            user_message=correction_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
