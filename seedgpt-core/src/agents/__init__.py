"""
AI Agents Package

Core agent implementations for GitHub automation:
- IssueGenerator: Generates new issues using AI
- IssueResolver: Resolves issues and creates PRs
- PRFailureResolver: Fixes failing PR checks and updates PRs
- QAAgent: Monitors repository health

Specialized Issue Agents:
- BaseIssueAgent: Abstract base class for domain-specific agents
- MarketingAgent: Generates marketing and growth-related issues
- ProductAgent: Generates product and feature-related issues
- SalesAgent: Generates sales and revenue-related issues
"""

from .issue_generator import IssueGenerator
from .issue_resolver import IssueResolver
from .pr_failure_resolver import PRFailureResolver
from .qa_agent import QAAgent
from .base_issue_agent import BaseIssueAgent, AgentConfig
from .marketing_agent import MarketingAgent
from .product_agent import ProductAgent
from .sales_agent import SalesAgent

__all__ = [
    "IssueGenerator",
    "IssueResolver",
    "PRFailureResolver",
    "QAAgent",
    "BaseIssueAgent",
    "AgentConfig",
    "MarketingAgent",
    "ProductAgent",
    "SalesAgent",
]
