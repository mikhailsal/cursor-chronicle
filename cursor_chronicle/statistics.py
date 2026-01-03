"""
Statistics collection and formatting for Cursor Chronicle.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .messages import get_dialog_messages
from .viewer import CursorChatViewer


def get_dialog_statistics(
    viewer: CursorChatViewer,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    project_filter: Optional[str] = None,
) -> Dict:
    """
    Collect comprehensive statistics for dialogs in the given period.
    
    Args:
        viewer: CursorChatViewer instance
        start_date: Start of period (inclusive)
        end_date: End of period (inclusive)
        project_filter: Filter by project name (partial match)
    
    Returns:
        Dict with all statistics data
    """
    dialogs = viewer.get_all_dialogs(
        start_date=start_date,
        end_date=end_date,
        project_filter=project_filter,
        use_updated=True,
    )

    if not dialogs:
        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_dialogs": 0,
            "projects": {},
        }

    stats = {
        "period_start": start_date,
        "period_end": end_date,
        "total_dialogs": len(dialogs),
        "total_messages": 0,
        "user_messages": 0,
        "ai_messages": 0,
        "tool_calls": 0,
        "thinking_bubbles": 0,
        "total_tokens_in": 0,
        "total_tokens_out": 0,
        "total_thinking_time_ms": 0,
        "projects": defaultdict(lambda: {
            "dialogs": 0, "messages": 0, "user_messages": 0,
            "ai_messages": 0, "tool_calls": 0, "tokens_in": 0,
            "tokens_out": 0, "dialog_names": [],
        }),
        "tool_usage": Counter(),
        "daily_activity": defaultdict(lambda: {"dialogs": 0, "messages": 0}),
        "dialogs_by_length": [],
    }

    for dialog in dialogs:
        composer_id = dialog.get("composer_id")
        project_name = dialog.get("project_name", "Unknown")
        dialog_name = dialog.get("name", "Untitled")
        last_updated = dialog.get("last_updated", 0)

        stats["projects"][project_name]["dialogs"] += 1
        stats["projects"][project_name]["dialog_names"].append(dialog_name)

        if last_updated:
            day_key = datetime.fromtimestamp(last_updated / 1000).strftime("%Y-%m-%d")
            stats["daily_activity"][day_key]["dialogs"] += 1

        try:
            messages = get_dialog_messages(composer_id)
        except Exception:
            continue

        dialog_message_count = 0

        for msg in messages:
            msg_type = msg.get("type")
            tool_data = msg.get("tool_data")
            is_thought = msg.get("is_thought", False)
            token_count = msg.get("token_count", {})
            thinking_duration = msg.get("thinking_duration", 0)

            if msg_type == 1:
                stats["user_messages"] += 1
                stats["projects"][project_name]["user_messages"] += 1
                dialog_message_count += 1
            elif msg_type == 2:
                if is_thought:
                    stats["thinking_bubbles"] += 1
                    stats["total_thinking_time_ms"] += thinking_duration
                elif msg.get("text"):
                    stats["ai_messages"] += 1
                    stats["projects"][project_name]["ai_messages"] += 1
                    dialog_message_count += 1

            if tool_data and tool_data.get("name"):
                stats["tool_calls"] += 1
                stats["projects"][project_name]["tool_calls"] += 1
                tool_name = tool_data.get("name", "unknown")
                stats["tool_usage"][tool_name] += 1

            input_tokens = token_count.get("inputTokens", 0)
            output_tokens = token_count.get("outputTokens", 0)
            stats["total_tokens_in"] += input_tokens
            stats["total_tokens_out"] += output_tokens
            stats["projects"][project_name]["tokens_in"] += input_tokens
            stats["projects"][project_name]["tokens_out"] += output_tokens

        stats["total_messages"] += dialog_message_count
        stats["projects"][project_name]["messages"] += dialog_message_count

        if last_updated:
            day_key = datetime.fromtimestamp(last_updated / 1000).strftime("%Y-%m-%d")
            stats["daily_activity"][day_key]["messages"] += dialog_message_count

        stats["dialogs_by_length"].append((dialog_name, project_name, dialog_message_count))

    stats["dialogs_by_length"].sort(key=lambda x: x[2], reverse=True)
    stats["projects"] = dict(stats["projects"])
    stats["daily_activity"] = dict(stats["daily_activity"])

    return stats


def format_statistics(stats: Dict, top_n: int = 10, max_days: int = 30) -> str:
    """Format statistics for display."""
    if stats["total_dialogs"] == 0:
        return "No dialogs found in the specified period."

    output = []
    output.append("=" * 70)
    output.append("📊 CURSOR CHRONICLE - USAGE STATISTICS")
    output.append("=" * 70)

    period_parts = []
    if stats["period_start"]:
        period_parts.append(f"From: {stats['period_start'].strftime('%Y-%m-%d')}")
    if stats["period_end"]:
        period_parts.append(f"To: {stats['period_end'].strftime('%Y-%m-%d')}")
    output.append(" | ".join(period_parts) if period_parts else "Period: All time")
    output.append("")

    output.append("📈 SUMMARY")
    output.append("-" * 40)
    output.append(f"  Total dialogs:      {stats['total_dialogs']}")
    output.append(f"  Total messages:     {stats['total_messages']}")
    output.append(f"    👤 User messages: {stats['user_messages']}")
    output.append(f"    🤖 AI responses:  {stats['ai_messages']}")
    output.append(f"    🛠️  Tool calls:    {stats['tool_calls']}")

    if stats['total_dialogs'] > 0:
        avg_messages = stats['total_messages'] / stats['total_dialogs']
        output.append(f"  Avg messages/dialog: {avg_messages:.1f}")

    active_days = len(stats.get("daily_activity", {}))
    if stats["period_start"] and stats["period_end"]:
        total_period_days = (stats["period_end"] - stats["period_start"]).days
        if total_period_days > 0:
            coding_percent = (active_days / total_period_days) * 100
            output.append(f"  📆 Coding days:      {active_days}/{total_period_days} ({coding_percent:.0f}%)")
    elif active_days > 0:
        output.append(f"  📆 Coding days:      {active_days}")
    output.append("")

    total_tokens = stats["total_tokens_in"] + stats["total_tokens_out"]
    if total_tokens > 0:
        output.append("🔢 TOKEN USAGE")
        output.append("-" * 40)
        output.append(f"  Input tokens:  {stats['total_tokens_in']:,}")
        output.append(f"  Output tokens: {stats['total_tokens_out']:,}")
        output.append(f"  Total tokens:  {total_tokens:,}")
        output.append("")

    if stats["thinking_bubbles"] > 0:
        total_thinking_sec = stats["total_thinking_time_ms"] / 1000
        avg_thinking = total_thinking_sec / stats["thinking_bubbles"]
        output.append("🧠 AI THINKING")
        output.append("-" * 40)
        output.append(f"  Thinking bubbles: {stats['thinking_bubbles']}")
        output.append(f"  Total time:       {total_thinking_sec:.1f}s")
        output.append(f"  Average time:     {avg_thinking:.1f}s")
        output.append("")

    if stats["projects"]:
        output.append("📁 PROJECT ACTIVITY (by messages)")
        output.append("-" * 40)
        sorted_projects = sorted(stats["projects"].items(), key=lambda x: x[1]["messages"], reverse=True)

        for i, (project_name, proj_stats) in enumerate(sorted_projects[:top_n], 1):
            output.append(f"  {i}. {project_name}")
            output.append(f"     💬 {proj_stats['dialogs']} dialogs | 📝 {proj_stats['messages']} messages | 🛠️ {proj_stats['tool_calls']} tools")
            proj_tokens = proj_stats['tokens_in'] + proj_stats['tokens_out']
            if proj_tokens > 0:
                output.append(f"     🔢 {proj_tokens:,} tokens")

        if len(sorted_projects) > top_n:
            output.append(f"  ... and {len(sorted_projects) - top_n} more projects")
        output.append("")

    if stats["tool_usage"]:
        output.append("🛠️ MOST USED TOOLS")
        output.append("-" * 40)
        for tool_name, count in stats["tool_usage"].most_common(top_n):
            output.append(f"  {tool_name}: {count}")
        output.append("")

    if stats["dialogs_by_length"]:
        output.append("📏 LONGEST DIALOGS")
        output.append("-" * 40)
        for dialog_name, project_name, msg_count in stats["dialogs_by_length"][:5]:
            display_name = dialog_name[:40] + "..." if len(dialog_name) > 40 else dialog_name
            output.append(f"  {display_name}")
            output.append(f"     📁 {project_name} | 📝 {msg_count} messages")
        output.append("")

    if stats["daily_activity"]:
        output.append("📅 DAILY ACTIVITY")
        output.append("-" * 40)
        sorted_days = sorted(stats["daily_activity"].items(), reverse=True)
        days_to_show = sorted_days[:max_days] if len(sorted_days) > max_days else sorted_days

        for day, day_stats in days_to_show:
            bar_len = min(day_stats["messages"] // 2, 30)
            bar = "█" * bar_len
            output.append(f"  {day}: {bar} {day_stats['dialogs']}d/{day_stats['messages']}m")

        if len(sorted_days) > max_days:
            output.append(f"  ... {len(sorted_days) - max_days} more days")
        output.append("")

    output.append("=" * 70)
    return "\n".join(output)


def show_statistics(
    viewer: CursorChatViewer,
    days: int = 30,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    project_filter: Optional[str] = None,
    top_n: int = 10,
):
    """Display usage statistics for the specified period."""
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
    elif not end_date:
        end_date = datetime.now()
    elif not start_date:
        start_date = end_date - timedelta(days=days)

    max_days = days

    print("Collecting statistics... (this may take a moment)")

    stats = get_dialog_statistics(
        viewer,
        start_date=start_date,
        end_date=end_date,
        project_filter=project_filter,
    )

    output = format_statistics(stats, top_n=top_n, max_days=max_days)
    print(output)
