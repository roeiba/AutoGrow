#!/usr/bin/env python3
"""
Run Specialized Issue Agents

This script demonstrates how to use the specialized agents (Marketing, Product, Sales)
to generate domain-specific issues.

Usage:
    # Run all agents
    python scripts/run_specialized_agents.py

    # Run specific agent
    python scripts/run_specialized_agents.py --agent marketing

    # Dry mode (no actual issues created)
    python scripts/run_specialized_agents.py --dry-mode

    # Custom minimum issues
    python scripts/run_specialized_agents.py --agent product --min-issues 5
"""

import os
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from github import Github
from agents import MarketingAgent, ProductAgent, SalesAgent, AgentConfig
from logging_config import get_logger

logger = get_logger(__name__)


def get_env_var(name: str, required: bool = True) -> str:
    """Get environment variable with error handling"""
    value = os.getenv(name)
    if required and not value:
        print("\n" + "="*80)
        print("⏭️  SKIPPING: Specialized Agents")
        print("="*80)
        print(f"\n📋 This workflow requires the environment variable: {name}")
        print("\n💡 These are typically not available in forked repositories.")
        print("   This is expected behavior and not an error.")
        print("\n🔒 Repository owners can configure these secrets in:")
        print("   Settings → Secrets and variables → Actions")
        print("="*80 + "\n")
        logger.info(f"Skipping execution due to missing environment variable: {name} (expected in forks)")
        sys.exit(0)
    return value


def run_marketing_agent(repo, api_key: str, dry_mode: bool = False, min_issues: int = 2):
    """Run the marketing agent"""
    logger.info("=" * 60)
    logger.info("Running Marketing Agent")
    logger.info("=" * 60)
    
    config = AgentConfig(
        domain="marketing",
        default_labels=["marketing", "growth"],
        min_issues=min_issues
    )
    
    agent = MarketingAgent(
        repo=repo,
        anthropic_api_key=api_key,
        dry_mode=dry_mode,
        custom_config=config
    )
    
    result = agent.check_and_generate()
    
    if result:
        logger.info("✅ Marketing agent completed successfully")
    else:
        logger.info("ℹ️  Marketing agent: No action needed")
    
    return result


def run_product_agent(repo, api_key: str, dry_mode: bool = False, min_issues: int = 2):
    """Run the product agent"""
    logger.info("=" * 60)
    logger.info("Running Product Agent")
    logger.info("=" * 60)
    
    config = AgentConfig(
        domain="product",
        default_labels=["product", "feature"],
        min_issues=min_issues
    )
    
    agent = ProductAgent(
        repo=repo,
        anthropic_api_key=api_key,
        dry_mode=dry_mode,
        custom_config=config
    )
    
    result = agent.check_and_generate()
    
    if result:
        logger.info("✅ Product agent completed successfully")
    else:
        logger.info("ℹ️  Product agent: No action needed")
    
    return result


def run_sales_agent(repo, api_key: str, dry_mode: bool = False, min_issues: int = 2):
    """Run the sales agent"""
    logger.info("=" * 60)
    logger.info("Running Sales Agent")
    logger.info("=" * 60)
    
    config = AgentConfig(
        domain="sales",
        default_labels=["sales", "revenue"],
        min_issues=min_issues
    )
    
    agent = SalesAgent(
        repo=repo,
        anthropic_api_key=api_key,
        dry_mode=dry_mode,
        custom_config=config
    )
    
    result = agent.check_and_generate()
    
    if result:
        logger.info("✅ Sales agent completed successfully")
    else:
        logger.info("ℹ️  Sales agent: No action needed")
    
    return result


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run specialized issue generation agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all agents
  python scripts/run_specialized_agents.py

  # Run specific agent
  python scripts/run_specialized_agents.py --agent marketing

  # Dry mode (testing)
  python scripts/run_specialized_agents.py --dry-mode

  # Custom configuration
  python scripts/run_specialized_agents.py --agent product --min-issues 5
        """
    )
    
    parser.add_argument(
        "--agent",
        choices=["marketing", "product", "sales", "all"],
        default="all",
        help="Which agent to run (default: all)"
    )
    
    parser.add_argument(
        "--dry-mode",
        action="store_true",
        help="Run in dry mode (no actual issues created)"
    )
    
    parser.add_argument(
        "--min-issues",
        type=int,
        default=2,
        help="Minimum number of issues to maintain per domain (default: 2)"
    )
    
    parser.add_argument(
        "--repo",
        help="Repository in format 'owner/repo' (default: from GITHUB_REPOSITORY env)"
    )
    
    args = parser.parse_args()
    
    # Get environment variables
    github_token = get_env_var("GITHUB_TOKEN")
    anthropic_api_key = get_env_var("ANTHROPIC_API_KEY")
    repo_name = args.repo or get_env_var("GITHUB_REPOSITORY")
    
    logger.info(f"Repository: {repo_name}")
    logger.info(f"Dry Mode: {args.dry_mode}")
    logger.info(f"Min Issues: {args.min_issues}")
    
    # Initialize GitHub
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_name)
        logger.info(f"Connected to repository: {repo.full_name}")
    except Exception as e:
        logger.error(f"Failed to connect to GitHub: {e}")
        sys.exit(1)
    
    # Run selected agent(s)
    results = {}
    
    if args.agent in ["marketing", "all"]:
        results["marketing"] = run_marketing_agent(
            repo, anthropic_api_key, args.dry_mode, args.min_issues
        )
    
    if args.agent in ["product", "all"]:
        results["product"] = run_product_agent(
            repo, anthropic_api_key, args.dry_mode, args.min_issues
        )
    
    if args.agent in ["sales", "all"]:
        results["sales"] = run_sales_agent(
            repo, anthropic_api_key, args.dry_mode, args.min_issues
        )
    
    # Summary
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    
    for agent_name, result in results.items():
        status = "✅ Generated issues" if result else "ℹ️  No action needed"
        logger.info(f"{agent_name.capitalize()}: {status}")
    
    logger.info("=" * 60)
    logger.info("All agents completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
