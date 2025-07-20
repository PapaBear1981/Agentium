"""
Cost Tracking and Budget Management for Jarvis Multi-Agent AI System.

This module provides comprehensive cost tracking for LLM usage,
budget controls, and financial reporting across all agents and sessions.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog

from models.database import CostHistory, CostHistoryCreate

logger = structlog.get_logger(__name__)

@dataclass
class ModelPricing:
    """Pricing information for a model."""
    model_name: str
    provider: str
    input_cost_per_1k_tokens: Decimal
    output_cost_per_1k_tokens: Decimal
    context_window: int
    notes: str = ""

@dataclass
class UsageRecord:
    """Record of model usage."""
    session_id: UUID
    agent_id: str
    model_name: str
    operation_type: str
    tokens_input: int
    tokens_output: int
    cost: Decimal
    timestamp: float
    metadata: Dict[str, Any]

@dataclass
class BudgetAlert:
    """Budget alert information."""
    session_id: UUID
    alert_type: str  # 'warning', 'limit_reached', 'exceeded'
    current_cost: Decimal
    budget_limit: Decimal
    percentage_used: float
    message: str
    timestamp: float

class ModelPricingManager:
    """Manages pricing information for different models."""
    
    def __init__(self):
        self.pricing_data: Dict[str, ModelPricing] = {}
        self._initialize_default_pricing()
    
    def _initialize_default_pricing(self):
        """Initialize with default pricing for common models."""
        # OpenRouter pricing (approximate)
        self.pricing_data.update({
            "gpt-4o": ModelPricing(
                model_name="gpt-4o",
                provider="openrouter",
                input_cost_per_1k_tokens=Decimal("0.005"),
                output_cost_per_1k_tokens=Decimal("0.015"),
                context_window=128000,
                notes="GPT-4o via OpenRouter"
            ),
            "gpt-4o-mini": ModelPricing(
                model_name="gpt-4o-mini",
                provider="openrouter",
                input_cost_per_1k_tokens=Decimal("0.00015"),
                output_cost_per_1k_tokens=Decimal("0.0006"),
                context_window=128000,
                notes="GPT-4o Mini via OpenRouter"
            ),
            "gemini-2.5-flash": ModelPricing(
                model_name="gemini-2.5-flash",
                provider="openrouter",
                input_cost_per_1k_tokens=Decimal("0.00075"),
                output_cost_per_1k_tokens=Decimal("0.003"),
                context_window=1000000,
                notes="Gemini 2.5 Flash via OpenRouter"
            ),
            "claude-3.5-sonnet": ModelPricing(
                model_name="claude-3.5-sonnet",
                provider="openrouter",
                input_cost_per_1k_tokens=Decimal("0.003"),
                output_cost_per_1k_tokens=Decimal("0.015"),
                context_window=200000,
                notes="Claude 3.5 Sonnet via OpenRouter"
            ),
            # Ollama models (free but we track compute cost estimates)
            "gemma2:7b": ModelPricing(
                model_name="gemma2:7b",
                provider="ollama",
                input_cost_per_1k_tokens=Decimal("0.0001"),  # Estimated compute cost
                output_cost_per_1k_tokens=Decimal("0.0001"),
                context_window=8192,
                notes="Gemma2 7B local model (estimated compute cost)"
            ),
            "llama3.2:8b": ModelPricing(
                model_name="llama3.2:8b",
                provider="ollama",
                input_cost_per_1k_tokens=Decimal("0.0001"),
                output_cost_per_1k_tokens=Decimal("0.0001"),
                context_window=128000,
                notes="Llama 3.2 8B local model (estimated compute cost)"
            )
        })
        
        logger.info("Model pricing initialized", models=list(self.pricing_data.keys()))
    
    def get_pricing(self, model_name: str) -> Optional[ModelPricing]:
        """Get pricing information for a model."""
        return self.pricing_data.get(model_name)
    
    def calculate_cost(self, model_name: str, tokens_input: int, tokens_output: int) -> Decimal:
        """Calculate cost for model usage."""
        pricing = self.get_pricing(model_name)
        if not pricing:
            logger.warning("No pricing data for model", model=model_name)
            return Decimal("0.001")  # Default minimal cost
        
        input_cost = (Decimal(tokens_input) / 1000) * pricing.input_cost_per_1k_tokens
        output_cost = (Decimal(tokens_output) / 1000) * pricing.output_cost_per_1k_tokens
        
        total_cost = input_cost + output_cost
        return total_cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    def add_custom_pricing(self, pricing: ModelPricing):
        """Add custom pricing for a model."""
        self.pricing_data[pricing.model_name] = pricing
        logger.info("Custom pricing added", model=pricing.model_name)
    
    def get_all_pricing(self) -> Dict[str, ModelPricing]:
        """Get all pricing information."""
        return self.pricing_data.copy()

class BudgetManager:
    """Manages budget limits and alerts."""
    
    def __init__(self):
        self.session_budgets: Dict[UUID, Decimal] = {}
        self.global_budget: Optional[Decimal] = None
        self.alert_thresholds = [0.5, 0.8, 0.9, 1.0]  # 50%, 80%, 90%, 100%
        self.session_alerts: Dict[UUID, List[BudgetAlert]] = {}
    
    def set_session_budget(self, session_id: UUID, budget_limit: Decimal):
        """Set budget limit for a session."""
        self.session_budgets[session_id] = budget_limit
        logger.info("Session budget set", session_id=str(session_id), budget=float(budget_limit))
    
    def set_global_budget(self, budget_limit: Decimal):
        """Set global budget limit."""
        self.global_budget = budget_limit
        logger.info("Global budget set", budget=float(budget_limit))
    
    def check_budget_status(self, session_id: UUID, current_cost: Decimal) -> List[BudgetAlert]:
        """Check budget status and generate alerts if needed."""
        alerts = []
        
        # Check session budget
        if session_id in self.session_budgets:
            session_budget = self.session_budgets[session_id]
            percentage_used = float(current_cost / session_budget) if session_budget > 0 else 0.0
            
            # Check each threshold
            for threshold in self.alert_thresholds:
                if percentage_used >= threshold:
                    alert_type = self._get_alert_type(threshold)
                    
                    # Check if we've already sent this alert
                    existing_alerts = self.session_alerts.get(session_id, [])
                    if not any(alert.alert_type == alert_type for alert in existing_alerts):
                        alert = BudgetAlert(
                            session_id=session_id,
                            alert_type=alert_type,
                            current_cost=current_cost,
                            budget_limit=session_budget,
                            percentage_used=percentage_used,
                            message=self._get_alert_message(alert_type, current_cost, session_budget, percentage_used),
                            timestamp=time.time()
                        )
                        alerts.append(alert)
                        
                        # Store alert to avoid duplicates
                        if session_id not in self.session_alerts:
                            self.session_alerts[session_id] = []
                        self.session_alerts[session_id].append(alert)
        
        return alerts
    
    def _get_alert_type(self, threshold: float) -> str:
        """Get alert type based on threshold."""
        if threshold >= 1.0:
            return "exceeded"
        elif threshold >= 0.9:
            return "limit_reached"
        else:
            return "warning"
    
    def _get_alert_message(self, alert_type: str, current_cost: Decimal, budget_limit: Decimal, percentage_used: float) -> str:
        """Generate alert message."""
        if alert_type == "exceeded":
            return f"Budget exceeded! Used ${current_cost:.4f} of ${budget_limit:.4f} budget ({percentage_used:.1%})"
        elif alert_type == "limit_reached":
            return f"Budget limit reached! Used ${current_cost:.4f} of ${budget_limit:.4f} budget ({percentage_used:.1%})"
        else:
            return f"Budget warning: Used ${current_cost:.4f} of ${budget_limit:.4f} budget ({percentage_used:.1%})"
    
    def is_budget_exceeded(self, session_id: UUID, current_cost: Decimal) -> bool:
        """Check if budget is exceeded."""
        if session_id in self.session_budgets:
            return current_cost >= self.session_budgets[session_id]
        return False
    
    def get_remaining_budget(self, session_id: UUID, current_cost: Decimal) -> Optional[Decimal]:
        """Get remaining budget for a session."""
        if session_id in self.session_budgets:
            return max(Decimal("0"), self.session_budgets[session_id] - current_cost)
        return None

class CostTracker:
    """Main cost tracking system."""
    
    def __init__(self):
        self.pricing_manager = ModelPricingManager()
        self.budget_manager = BudgetManager()
        self.usage_records: List[UsageRecord] = []
        self.session_totals: Dict[UUID, Decimal] = {}
        
        # Configuration
        self.max_records = 10000  # Keep last 10k records in memory
        
        logger.info("CostTracker initialized")
    
    async def record_usage(
        self,
        session_id: UUID,
        agent_id: str,
        model_name: str,
        operation_type: str,
        tokens_input: int,
        tokens_output: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Decimal, List[BudgetAlert]]:
        """Record model usage and return cost and any budget alerts."""
        
        # Calculate cost
        cost = self.pricing_manager.calculate_cost(model_name, tokens_input, tokens_output)
        
        # Create usage record
        record = UsageRecord(
            session_id=session_id,
            agent_id=agent_id,
            model_name=model_name,
            operation_type=operation_type,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=cost,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        # Store record
        self.usage_records.append(record)
        
        # Maintain record limit
        if len(self.usage_records) > self.max_records:
            self.usage_records = self.usage_records[-self.max_records:]
        
        # Update session total
        if session_id not in self.session_totals:
            self.session_totals[session_id] = Decimal("0")
        self.session_totals[session_id] += cost
        
        # Check budget status
        alerts = self.budget_manager.check_budget_status(session_id, self.session_totals[session_id])
        
        logger.info("Usage recorded",
                   session_id=str(session_id),
                   agent_id=agent_id,
                   model=model_name,
                   cost=float(cost),
                   total_session_cost=float(self.session_totals[session_id]))
        
        return cost, alerts
    
    def get_session_summary(self, session_id: UUID) -> Dict[str, Any]:
        """Get cost summary for a session."""
        session_records = [r for r in self.usage_records if r.session_id == session_id]
        
        if not session_records:
            return {
                "session_id": str(session_id),
                "total_cost": 0.0,
                "total_tokens": 0,
                "operation_count": 0,
                "agents_used": [],
                "models_used": [],
                "breakdown": {}
            }
        
        total_cost = sum(r.cost for r in session_records)
        total_tokens = sum(r.tokens_input + r.tokens_output for r in session_records)
        
        # Breakdown by agent
        agent_breakdown = {}
        for record in session_records:
            if record.agent_id not in agent_breakdown:
                agent_breakdown[record.agent_id] = {
                    "cost": Decimal("0"),
                    "tokens": 0,
                    "operations": 0,
                    "models": set()
                }
            
            agent_breakdown[record.agent_id]["cost"] += record.cost
            agent_breakdown[record.agent_id]["tokens"] += record.tokens_input + record.tokens_output
            agent_breakdown[record.agent_id]["operations"] += 1
            agent_breakdown[record.agent_id]["models"].add(record.model_name)
        
        # Convert sets to lists for JSON serialization
        for agent_data in agent_breakdown.values():
            agent_data["models"] = list(agent_data["models"])
            agent_data["cost"] = float(agent_data["cost"])
        
        return {
            "session_id": str(session_id),
            "total_cost": float(total_cost),
            "total_tokens": total_tokens,
            "operation_count": len(session_records),
            "agents_used": list(set(r.agent_id for r in session_records)),
            "models_used": list(set(r.model_name for r in session_records)),
            "breakdown": agent_breakdown,
            "budget_limit": float(self.budget_manager.session_budgets.get(session_id, 0)),
            "budget_remaining": float(self.budget_manager.get_remaining_budget(session_id, total_cost) or 0)
        }
    
    def get_global_summary(self) -> Dict[str, Any]:
        """Get global cost summary."""
        if not self.usage_records:
            return {
                "total_cost": 0.0,
                "total_tokens": 0,
                "total_operations": 0,
                "active_sessions": 0,
                "models_used": [],
                "agents_used": []
            }
        
        total_cost = sum(r.cost for r in self.usage_records)
        total_tokens = sum(r.tokens_input + r.tokens_output for r in self.usage_records)
        
        # Model usage statistics
        model_stats = {}
        for record in self.usage_records:
            if record.model_name not in model_stats:
                model_stats[record.model_name] = {
                    "cost": Decimal("0"),
                    "tokens": 0,
                    "operations": 0
                }
            
            model_stats[record.model_name]["cost"] += record.cost
            model_stats[record.model_name]["tokens"] += record.tokens_input + record.tokens_output
            model_stats[record.model_name]["operations"] += 1
        
        # Convert to serializable format
        for model_data in model_stats.values():
            model_data["cost"] = float(model_data["cost"])
        
        return {
            "total_cost": float(total_cost),
            "total_tokens": total_tokens,
            "total_operations": len(self.usage_records),
            "active_sessions": len(self.session_totals),
            "models_used": list(set(r.model_name for r in self.usage_records)),
            "agents_used": list(set(r.agent_id for r in self.usage_records)),
            "model_statistics": model_stats,
            "time_range": {
                "start": min(r.timestamp for r in self.usage_records),
                "end": max(r.timestamp for r in self.usage_records)
            }
        }
    
    def get_cost_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get cost trends over the specified time period."""
        cutoff_time = time.time() - (hours * 3600)
        recent_records = [r for r in self.usage_records if r.timestamp >= cutoff_time]
        
        if not recent_records:
            return {"message": "No recent usage data"}
        
        # Group by hour
        hourly_costs = {}
        for record in recent_records:
            hour = int(record.timestamp // 3600) * 3600  # Round to hour
            if hour not in hourly_costs:
                hourly_costs[hour] = Decimal("0")
            hourly_costs[hour] += record.cost
        
        # Convert to list of tuples for easier plotting
        trend_data = [(hour, float(cost)) for hour, cost in sorted(hourly_costs.items())]
        
        return {
            "time_period_hours": hours,
            "total_cost": float(sum(r.cost for r in recent_records)),
            "total_operations": len(recent_records),
            "hourly_trend": trend_data,
            "average_cost_per_hour": float(sum(hourly_costs.values()) / max(1, len(hourly_costs)))
        }
    
    def export_usage_data(self, session_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
        """Export usage data for analysis."""
        records = self.usage_records
        if session_id:
            records = [r for r in records if r.session_id == session_id]
        
        return [
            {
                "session_id": str(r.session_id),
                "agent_id": r.agent_id,
                "model_name": r.model_name,
                "operation_type": r.operation_type,
                "tokens_input": r.tokens_input,
                "tokens_output": r.tokens_output,
                "tokens_total": r.tokens_input + r.tokens_output,
                "cost": float(r.cost),
                "timestamp": r.timestamp,
                "metadata": r.metadata
            }
            for r in records
        ]
