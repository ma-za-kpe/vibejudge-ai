"""Base agent class with shared logic for all AI agents."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from src.constants import AGENT_CONFIGS
from src.models.analysis import RepoData
from src.models.scores import BaseAgentResponse
from src.utils.bedrock import BedrockClient
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, agent_name: str, bedrock_client: Optional[BedrockClient] = None):
        """Initialize base agent.
        
        Args:
            agent_name: Name of the agent (bug_hunter, performance, etc.)
            bedrock_client: Optional Bedrock client (creates new if None)
        """
        self.agent_name = agent_name
        self.bedrock = bedrock_client or BedrockClient()
        
        # Get agent configuration
        config = AGENT_CONFIGS.get(agent_name, {})
        self.model_id = config.get("model_id", "amazon.nova-lite-v1:0")
        self.temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 2048)
        self.top_p = config.get("top_p", 0.9)
        self.timeout_seconds = config.get("timeout_seconds", 120)
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent.
        
        Returns:
            System prompt text
        """
        pass
    
    @abstractmethod
    def build_user_message(
        self,
        repo_data: RepoData,
        hackathon_name: str,
        team_name: str,
        **kwargs
    ) -> str:
        """Build the user message for this agent.
        
        Args:
            repo_data: Extracted repository data
            hackathon_name: Name of the hackathon
            team_name: Name of the team
            **kwargs: Additional agent-specific parameters
            
        Returns:
            User message text
        """
        pass
    
    @abstractmethod
    def parse_response(self, response_dict: dict) -> BaseAgentResponse:
        """Parse and validate agent response.
        
        Args:
            response_dict: Parsed JSON response from LLM
            
        Returns:
            Validated agent response model
        """
        pass
    
    def analyze(
        self,
        repo_data: RepoData,
        hackathon_name: str,
        team_name: str,
        **kwargs
    ) -> tuple[BaseAgentResponse, dict]:
        """Run agent analysis on repository data.
        
        Args:
            repo_data: Extracted repository data
            hackathon_name: Name of the hackathon
            team_name: Name of the team
            **kwargs: Additional agent-specific parameters
            
        Returns:
            Tuple of (agent_response, usage_dict)
            
        Raises:
            Exception: If analysis fails after retries
        """
        logger.info(
            "agent_analysis_started",
            agent=self.agent_name,
            team=team_name,
            repo=repo_data.repo_url,
        )
        
        # Build messages
        system_prompt = self.get_system_prompt()
        user_message = self.build_user_message(
            repo_data, hackathon_name, team_name, **kwargs
        )
        
        # Call Bedrock
        try:
            response = self.bedrock.converse(
                model_id=self.model_id,
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
            )
            
            # Parse JSON response
            content = response["content"]
            parsed = self.bedrock.parse_json_response(content)
            
            if not parsed:
                # Retry with correction
                logger.warning("agent_json_parse_failed_retrying", agent=self.agent_name)
                response = self.bedrock.retry_with_correction(
                    model_id=self.model_id,
                    system_prompt=system_prompt,
                    original_message=user_message,
                    failed_response=content,
                    parse_error="Failed to parse JSON",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                parsed = self.bedrock.parse_json_response(response["content"])
                
                if not parsed:
                    raise ValueError(f"Failed to parse JSON after retry: {response['content'][:200]}")
            
            # Validate and parse into Pydantic model
            agent_response = self.parse_response(parsed)
            
            # Validate evidence
            agent_response = self.validate_evidence(agent_response, repo_data)
            
            # Calculate cost
            usage = response["usage"]
            cost_info = self.bedrock.calculate_cost(
                model_id=self.model_id,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
            )
            
            usage_dict = {
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
                "latency_ms": response["latency_ms"],
                **cost_info,
            }
            
            logger.info(
                "agent_analysis_completed",
                agent=self.agent_name,
                overall_score=agent_response.overall_score,
                confidence=agent_response.confidence,
                cost_usd=cost_info["total_cost_usd"],
            )
            
            return agent_response, usage_dict
            
        except Exception as e:
            logger.error(
                "agent_analysis_failed",
                agent=self.agent_name,
                error=str(e),
            )
            raise
    
    def validate_evidence(
        self,
        response: BaseAgentResponse,
        repo_data: RepoData,
    ) -> BaseAgentResponse:
        """Validate evidence citations against actual repo data.
        
        This is the anti-hallucination safeguard. Marks evidence as
        unverified if it references files/commits that don't exist.
        
        Args:
            response: Agent response with evidence
            repo_data: Actual repository data
            
        Returns:
            Response with verified evidence flags
        """
        # Build sets of valid files and commits
        valid_files = {sf.path for sf in repo_data.source_files}
        valid_commits = {c.hash for c in repo_data.commit_history}
        valid_commits.update({c.short_hash for c in repo_data.commit_history})
        
        # Validate each evidence item
        for evidence in response.evidence:
            verified = True
            verification_notes = []
            
            # Check file exists
            if hasattr(evidence, 'file') and evidence.file:
                if evidence.file not in valid_files:
                    verified = False
                    verification_notes.append(f"File '{evidence.file}' not found in repo")
            
            # Check commit exists
            if hasattr(evidence, 'commit') and evidence.commit:
                if evidence.commit not in valid_commits:
                    verified = False
                    verification_notes.append(f"Commit '{evidence.commit}' not in history")
            
            # Add verification metadata
            if hasattr(evidence, '__dict__'):
                evidence.__dict__['verified'] = verified
                if verification_notes:
                    evidence.__dict__['verification_notes'] = verification_notes
        
        # Lower confidence if many unverified evidence items
        if response.evidence:
            unverified_count = sum(
                1 for e in response.evidence
                if hasattr(e, '__dict__') and not e.__dict__.get('verified', True)
            )
            unverified_ratio = unverified_count / len(response.evidence)
            
            if unverified_ratio > 0.3:
                # More than 30% unverified - significantly lower confidence
                response.confidence = min(response.confidence, 0.5)
                logger.warning(
                    "high_unverified_evidence_ratio",
                    agent=self.agent_name,
                    unverified_count=unverified_count,
                    total=len(response.evidence),
                    unverified_ratio=unverified_ratio,
                )
        
        return response
