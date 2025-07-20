"""
Reflexion System for Jarvis Multi-Agent AI System.

This module implements self-improvement loops through task analysis,
heuristic extraction, and adaptive behavior learning.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import structlog
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage

from models.database import ReflexionLog, ReflexionLogCreate

logger = structlog.get_logger(__name__)

@dataclass
class TaskAnalysis:
    """Analysis of a completed task."""
    task_id: UUID
    session_id: UUID
    task_description: str
    agent_id: str
    success: bool
    result: str
    processing_time_ms: int
    tokens_used: int
    cost: float
    user_feedback: Optional[str] = None
    context: Dict[str, Any] = None

@dataclass
class ReflexionResult:
    """Result of reflexion analysis."""
    task_id: UUID
    success: bool
    analysis: str
    heuristics: List[Dict[str, Any]]
    improvement_suggestions: List[str]
    confidence_score: float
    patterns_identified: List[str]
    failure_modes: List[str]

class ReflexionAnalyzer:
    """Analyzes task performance and extracts learning insights."""
    
    def __init__(self, model_client: ChatCompletionClient):
        self.model_client = model_client
        self.analysis_prompt_template = """
You are an AI system analyst tasked with analyzing the performance of an AI agent on a specific task.
Your goal is to extract insights, identify patterns, and suggest improvements.

Task Analysis:
- Task ID: {task_id}
- Agent: {agent_id}
- Task Description: {task_description}
- Success: {success}
- Result: {result}
- Processing Time: {processing_time_ms}ms
- Tokens Used: {tokens_used}
- Cost: ${cost:.4f}
- User Feedback: {user_feedback}

Please analyze this task execution and provide:

1. ANALYSIS: A detailed analysis of what happened, why it succeeded or failed
2. HEURISTICS: Specific rules or patterns that can be extracted (format as JSON array)
3. IMPROVEMENTS: Concrete suggestions for improvement
4. CONFIDENCE: Your confidence in this analysis (0.0-1.0)
5. PATTERNS: Any patterns you identify in the approach or execution
6. FAILURE_MODES: If unsuccessful, what failure modes were present

Format your response as JSON:
{{
    "analysis": "detailed analysis text",
    "heuristics": [
        {{"rule": "specific rule", "context": "when to apply", "confidence": 0.8}},
        {{"rule": "another rule", "context": "application context", "confidence": 0.9}}
    ],
    "improvements": ["improvement 1", "improvement 2"],
    "confidence": 0.85,
    "patterns": ["pattern 1", "pattern 2"],
    "failure_modes": ["failure mode 1", "failure mode 2"]
}}
"""
    
    async def analyze_task(self, task_analysis: TaskAnalysis) -> ReflexionResult:
        """Analyze a completed task and extract insights."""
        try:
            # Prepare the analysis prompt
            prompt = self.analysis_prompt_template.format(
                task_id=task_analysis.task_id,
                agent_id=task_analysis.agent_id,
                task_description=task_analysis.task_description,
                success=task_analysis.success,
                result=task_analysis.result[:500],  # Truncate long results
                processing_time_ms=task_analysis.processing_time_ms,
                tokens_used=task_analysis.tokens_used,
                cost=task_analysis.cost,
                user_feedback=task_analysis.user_feedback or "None provided"
            )
            
            # Get analysis from the model
            messages = [
                SystemMessage(content="You are an expert AI system analyst."),
                UserMessage(content=prompt, source="reflexion_system")
            ]
            
            model_result = await self.model_client.create(messages)
            
            # Parse the JSON response
            try:
                analysis_data = json.loads(model_result.content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                analysis_data = {
                    "analysis": model_result.content,
                    "heuristics": [],
                    "improvements": [],
                    "confidence": 0.5,
                    "patterns": [],
                    "failure_modes": []
                }
            
            # Create reflexion result
            result = ReflexionResult(
                task_id=task_analysis.task_id,
                success=task_analysis.success,
                analysis=analysis_data.get("analysis", ""),
                heuristics=analysis_data.get("heuristics", []),
                improvement_suggestions=analysis_data.get("improvements", []),
                confidence_score=analysis_data.get("confidence", 0.5),
                patterns_identified=analysis_data.get("patterns", []),
                failure_modes=analysis_data.get("failure_modes", [])
            )
            
            logger.info("Task analysis completed",
                       task_id=str(task_analysis.task_id),
                       success=task_analysis.success,
                       confidence=result.confidence_score,
                       heuristics_count=len(result.heuristics))
            
            return result
            
        except Exception as e:
            logger.error("Task analysis failed", 
                        task_id=str(task_analysis.task_id), 
                        error=str(e))
            
            # Return a basic result on failure
            return ReflexionResult(
                task_id=task_analysis.task_id,
                success=False,
                analysis=f"Analysis failed: {str(e)}",
                heuristics=[],
                improvement_suggestions=[],
                confidence_score=0.0,
                patterns_identified=[],
                failure_modes=["analysis_failure"]
            )

class HeuristicDatabase:
    """Stores and manages learned heuristics."""
    
    def __init__(self):
        self.heuristics: Dict[str, List[Dict[str, Any]]] = {}
        self.heuristic_usage: Dict[str, int] = {}
        self.heuristic_success_rate: Dict[str, float] = {}
    
    def add_heuristics(self, agent_id: str, heuristics: List[Dict[str, Any]]):
        """Add new heuristics for an agent."""
        if agent_id not in self.heuristics:
            self.heuristics[agent_id] = []
        
        for heuristic in heuristics:
            # Check if similar heuristic already exists
            if not self._is_duplicate_heuristic(agent_id, heuristic):
                heuristic["created_at"] = time.time()
                heuristic["usage_count"] = 0
                heuristic["success_count"] = 0
                self.heuristics[agent_id].append(heuristic)
                
                logger.info("New heuristic added",
                           agent_id=agent_id,
                           rule=heuristic.get("rule", "")[:50])
    
    def get_relevant_heuristics(self, agent_id: str, task_context: str) -> List[Dict[str, Any]]:
        """Get heuristics relevant to a task context."""
        if agent_id not in self.heuristics:
            return []
        
        relevant = []
        for heuristic in self.heuristics[agent_id]:
            # Simple relevance check based on context keywords
            context = heuristic.get("context", "").lower()
            if any(keyword in context for keyword in task_context.lower().split()):
                relevant.append(heuristic)
        
        # Sort by confidence and usage success rate
        relevant.sort(key=lambda h: (
            h.get("confidence", 0.0) * 0.7 + 
            (h.get("success_count", 0) / max(1, h.get("usage_count", 1))) * 0.3
        ), reverse=True)
        
        return relevant[:5]  # Return top 5 most relevant
    
    def update_heuristic_usage(self, agent_id: str, heuristic_rule: str, success: bool):
        """Update usage statistics for a heuristic."""
        if agent_id not in self.heuristics:
            return
        
        for heuristic in self.heuristics[agent_id]:
            if heuristic.get("rule") == heuristic_rule:
                heuristic["usage_count"] = heuristic.get("usage_count", 0) + 1
                if success:
                    heuristic["success_count"] = heuristic.get("success_count", 0) + 1
                break
    
    def _is_duplicate_heuristic(self, agent_id: str, new_heuristic: Dict[str, Any]) -> bool:
        """Check if a similar heuristic already exists."""
        new_rule = new_heuristic.get("rule", "").lower()
        
        for existing in self.heuristics.get(agent_id, []):
            existing_rule = existing.get("rule", "").lower()
            # Simple similarity check
            if self._calculate_similarity(new_rule, existing_rule) > 0.8:
                return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the heuristic database."""
        total_heuristics = sum(len(h) for h in self.heuristics.values())
        total_usage = sum(
            sum(h.get("usage_count", 0) for h in agent_heuristics)
            for agent_heuristics in self.heuristics.values()
        )
        
        return {
            "total_agents": len(self.heuristics),
            "total_heuristics": total_heuristics,
            "total_usage": total_usage,
            "agents": {
                agent_id: {
                    "heuristic_count": len(heuristics),
                    "total_usage": sum(h.get("usage_count", 0) for h in heuristics),
                    "avg_confidence": sum(h.get("confidence", 0.0) for h in heuristics) / max(1, len(heuristics))
                }
                for agent_id, heuristics in self.heuristics.items()
            }
        }

class ReflexionSystem:
    """Main reflexion system that coordinates analysis and learning."""
    
    def __init__(self, model_client: ChatCompletionClient):
        self.analyzer = ReflexionAnalyzer(model_client)
        self.heuristic_db = HeuristicDatabase()
        self.reflexion_history: List[ReflexionResult] = []
        
        # Configuration
        self.min_confidence_threshold = 0.6
        self.max_reflexion_history = 1000
        
        logger.info("ReflexionSystem initialized")
    
    async def process_task_completion(self, task_analysis: TaskAnalysis) -> ReflexionResult:
        """Process a completed task through reflexion analysis."""
        try:
            # Analyze the task
            reflexion_result = await self.analyzer.analyze_task(task_analysis)
            
            # Store high-confidence heuristics
            if reflexion_result.confidence_score >= self.min_confidence_threshold:
                self.heuristic_db.add_heuristics(
                    task_analysis.agent_id,
                    reflexion_result.heuristics
                )
            
            # Store reflexion result
            self.reflexion_history.append(reflexion_result)
            
            # Maintain history size
            if len(self.reflexion_history) > self.max_reflexion_history:
                self.reflexion_history = self.reflexion_history[-self.max_reflexion_history:]
            
            logger.info("Reflexion processing completed",
                       task_id=str(task_analysis.task_id),
                       confidence=reflexion_result.confidence_score,
                       heuristics_added=len(reflexion_result.heuristics))
            
            return reflexion_result
            
        except Exception as e:
            logger.error("Reflexion processing failed",
                        task_id=str(task_analysis.task_id),
                        error=str(e))
            raise
    
    def get_task_guidance(self, agent_id: str, task_description: str) -> Dict[str, Any]:
        """Get guidance for a new task based on learned heuristics."""
        relevant_heuristics = self.heuristic_db.get_relevant_heuristics(agent_id, task_description)
        
        # Extract patterns from successful past tasks
        successful_patterns = []
        for result in self.reflexion_history[-50:]:  # Look at recent history
            if result.success and result.confidence_score >= self.min_confidence_threshold:
                successful_patterns.extend(result.patterns_identified)
        
        # Get common failure modes to avoid
        failure_modes = []
        for result in self.reflexion_history[-50:]:
            if not result.success:
                failure_modes.extend(result.failure_modes)
        
        return {
            "relevant_heuristics": relevant_heuristics,
            "successful_patterns": list(set(successful_patterns)),
            "failure_modes_to_avoid": list(set(failure_modes)),
            "guidance_confidence": min(1.0, len(relevant_heuristics) * 0.2)
        }
    
    def get_system_insights(self) -> Dict[str, Any]:
        """Get insights about the overall system performance."""
        if not self.reflexion_history:
            return {"message": "No reflexion data available"}
        
        recent_results = self.reflexion_history[-100:]  # Last 100 analyses
        
        success_rate = sum(1 for r in recent_results if r.success) / len(recent_results)
        avg_confidence = sum(r.confidence_score for r in recent_results) / len(recent_results)
        
        # Most common patterns and failure modes
        all_patterns = []
        all_failures = []
        
        for result in recent_results:
            all_patterns.extend(result.patterns_identified)
            all_failures.extend(result.failure_modes)
        
        pattern_counts = {}
        for pattern in all_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        failure_counts = {}
        for failure in all_failures:
            failure_counts[failure] = failure_counts.get(failure, 0) + 1
        
        return {
            "total_analyses": len(self.reflexion_history),
            "recent_success_rate": success_rate,
            "average_confidence": avg_confidence,
            "most_common_patterns": sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "most_common_failures": sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "heuristic_stats": self.heuristic_db.get_statistics()
        }
    
    async def generate_improvement_report(self) -> str:
        """Generate a comprehensive improvement report."""
        insights = self.get_system_insights()
        
        report_prompt = f"""
Based on the following system performance data, generate a comprehensive improvement report:

System Insights:
{json.dumps(insights, indent=2)}

Please provide:
1. Overall system performance assessment
2. Key strengths identified
3. Major areas for improvement
4. Specific recommendations
5. Priority actions

Format as a clear, actionable report.
"""
        
        try:
            messages = [
                SystemMessage(content="You are an AI system performance analyst."),
                UserMessage(content=report_prompt, source="reflexion_system")
            ]
            
            model_result = await self.analyzer.model_client.create(messages)
            return model_result.content
            
        except Exception as e:
            logger.error("Failed to generate improvement report", error=str(e))
            return f"Failed to generate report: {str(e)}"
