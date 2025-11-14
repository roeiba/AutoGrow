#!/usr/bin/env python3
"""
View Feedback Metrics - CLI tool to view outcome tracking data

Usage:
    python view_feedback_metrics.py             # Show overall report
    python view_feedback_metrics.py --recent    # Show recent outcomes only
    python view_feedback_metrics.py --export    # Export as JSON
"""

import sys
import argparse
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.outcome_tracker import OutcomeTracker
from utils.feedback_analyzer import FeedbackAnalyzer
from logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="View AutoGrow feedback loop metrics"
    )
    parser.add_argument(
        "--recent",
        action="store_true",
        help="Show only recent outcomes"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export metrics as JSON"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze (default: 30)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of recent items to show (default: 10)"
    )

    args = parser.parse_args()

    # Initialize tracker and analyzer
    tracker = OutcomeTracker()
    analyzer = FeedbackAnalyzer(tracker)

    if args.export:
        # Export as JSON
        logger.info("Exporting metrics as JSON")
        print(tracker.export_metrics_json())
    elif args.recent:
        # Show recent outcomes only
        logger.info(f"Displaying recent outcomes (limit: {args.limit})")
        print("="*80)
        print(f"📊 RECENT OUTCOMES (Last {args.limit})")
        print("="*80)
        print()

        recent = tracker.get_recent_outcomes(limit=args.limit)

        if not recent:
            logger.warning("No outcome data available")
            print("No outcome data available yet.")
            return

        for record in recent:
            status_icon = {
                'merged': '✅',
                'resolved': '🔄',
                'failed': '❌',
                'pending': '⏳',
                'closed': '🚫'
            }.get(record['status'], '❓')

            print(f"{status_icon} Issue #{record['issue_number']}: {record['issue_title']}")
            print(f"   Type: {record['issue_type']}")
            print(f"   Labels: {', '.join(record['labels'])}")
            print(f"   Status: {record['status']}")

            if record['pr_number']:
                print(f"   PR: #{record['pr_number']}")

            if record['files_changed']:
                print(f"   Files changed: {record['files_changed']}")

            if record['time_to_resolve_minutes']:
                print(f"   Time to resolve: {record['time_to_resolve_minutes']} minutes")

            if record['error_message']:
                print(f"   Error: {record['error_message']}")

            print(f"   Created: {record['created_at']}")
            print()
    else:
        # Show comprehensive report
        logger.info(f"Generating comprehensive report for last {args.days} days")
        report = analyzer.format_metrics_report(days=args.days)
        print(report)

        # Show generation guidance
        print()
        print("="*80)
        print("🎯 ADAPTIVE GENERATION GUIDANCE")
        print("="*80)
        print()

        guidance = analyzer.get_generation_guidance(days=args.days)

        print("HIGH PRIORITY TYPES:")
        if guidance.high_priority_types:
            for issue_type in guidance.high_priority_types:
                print(f"  ✅ {issue_type}")
        else:
            print("  (No data available yet)")

        print()
        print("LOW PRIORITY TYPES:")
        if guidance.low_priority_types:
            for issue_type in guidance.low_priority_types:
                print(f"  ⚠️  {issue_type}")
        else:
            print("  (None)")

        print()
        print("RECOMMENDED DISTRIBUTION:")
        if guidance.recommended_distribution:
            for issue_type, weight in sorted(
                guidance.recommended_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                bar = "█" * int(weight * 30)
                print(f"  {issue_type:15} {bar:30} {weight:.1%}")
        else:
            print("  (No data available yet)")

        print()
        print("="*80)


if __name__ == "__main__":
    main()
