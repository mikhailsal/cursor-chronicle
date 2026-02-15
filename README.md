# Cursor Chronicle

A powerful tool for extracting, searching, and displaying dialogs from Cursor IDE database with comprehensive support for attached files, tool calls, and conversation metadata.

## Features

- 📊 **Complete Conversation History**: Extract full chat sessions with AI assistants
- 🔍 **Full-Text Search**: Search across all chat history for any keyword
- 📅 **Time-Based Filtering**: List dialogs by date range across all projects
- 📈 **Usage Statistics**: Analyze activity by project, messages, tools, and tokens
- 📤 **Markdown Export**: Export dialogs to `.md` files organized by project and date
- 🛠️ **Tool Call Analysis**: Detailed view of tool executions and results
- 📎 **File Attachment Support**: See all attached files and context
- 🧠 **AI Thinking Process**: View AI reasoning and thinking duration
- 📈 **Token Usage Tracking**: Monitor token consumption and infer models
- 📋 **Rich Metadata**: Access 100+ fields of conversation data

## Installation

### Using pip (Recommended)

```bash
# Install from local directory
pip install .

# For development installation
pip install -e ".[dev]"
```

### Direct Usage

```bash
# Run as module without installation
python -m cursor_chronicle --help
python -m search_history --help
```

## Quick Start

### List all projects
```bash
cursor-chronicle --list-projects
```

### List dialogs in a project
```bash
cursor-chronicle --list-dialogs "my-project"
```

### View latest conversation
```bash
cursor-chronicle
```

### View specific conversation
```bash
cursor-chronicle --project "my-project" --dialog "bug-fix"
```

### View with detailed tool outputs
```bash
cursor-chronicle --project "my-project" --max-output-lines 10
```

### List all dialogs across all projects
```bash
cursor-chronicle --list-all
```

### List dialogs with time filtering
```bash
# Dialogs created after a specific date (oldest first by default)
cursor-chronicle --list-all --from 2024-01-01

# Dialogs in a date range
cursor-chronicle --list-all --from 2024-01-01 --before 2025-01-01

# Filter/sort by last updated date instead of creation date
cursor-chronicle --list-all --from 2024-01-01 --updated

# Newest first
cursor-chronicle --list-all --desc
```

### Sort dialogs
```bash
# Sort by dialog name (A-Z)
cursor-chronicle --list-all --sort name

# Sort by project name (A-Z)
cursor-chronicle --list-all --sort project

# Sort by date descending (newest first)
cursor-chronicle --list-all --sort date --desc
```

## Usage Examples

### Basic Operations

```bash
# Show all available projects
cursor-chronicle --list-projects

# Show dialogs in a specific project (partial name matching)
cursor-chronicle --list-dialogs "cursor-chronicle"

# Show the most recent conversation
cursor-chronicle

# Show conversation with more detail
cursor-chronicle --max-output-lines 5
```

### Advanced Usage

```bash
# Find and display specific conversation
cursor-chronicle --project "web-app" --dialog "authentication"

# View conversation with full tool outputs
cursor-chronicle --project "api" --dialog "refactor" --max-output-lines 20
```

### List All Dialogs

```bash
# List all dialogs across all projects (oldest first)
cursor-chronicle --list-all

# Filter by project
cursor-chronicle --list-all --project "my-project"

# Filter by date range
cursor-chronicle --list-all --from 2024-06-01 --before 2025-01-01

# Sort by name alphabetically
cursor-chronicle --list-all --sort name

# Sort by project, then by name
cursor-chronicle --list-all --sort project

# Show more results (default: 50)
cursor-chronicle --list-all --limit 100

# Newest dialogs first
cursor-chronicle --list-all --desc
```

### List All Options

| Option | Short | Description |
|--------|-------|-------------|
| `--list-all` | | List all dialogs across all projects |
| `--from` | | Filter dialogs after date (YYYY-MM-DD) |
| `--before` | | Filter dialogs before date (YYYY-MM-DD, exclusive) |
| `--sort` | | Sort by: date, name, or project (default: date) |
| `--desc` | | Sort descending (newest/Z first) |
| `--updated` | | Use last updated date instead of creation date |
| `--limit` | | Maximum dialogs to display (default: 50) |
| `--project` | `-p` | Filter by project name (partial match) |

## Usage Statistics

Get comprehensive statistics about your Cursor IDE usage.

### Statistics Commands

```bash
# Statistics for last 30 days (default)
cursor-chronicle --stats

# Statistics for last 7 days
cursor-chronicle --stats --days 7

# Statistics for specific date range
cursor-chronicle --stats --from 2024-01-01 --before 2024-02-01

# Statistics for specific project
cursor-chronicle --stats -p "my-project"

# Show more top items in rankings
cursor-chronicle --stats --top 20
```

### Statistics Output

The statistics command displays:

- **Summary**: Total dialogs, messages, user/AI message counts, tool calls
- **Token Usage**: Input/output token consumption
- **AI Thinking**: Thinking bubble count and total time
- **Project Activity**: Ranking of most active projects by message count
- **Tool Usage**: Most frequently used tools
- **Longest Dialogs**: Dialogs with most messages
- **Daily Activity**: Activity distribution over the period

### Statistics Options

| Option | Short | Description |
|--------|-------|-------------|
| `--stats` | | Show usage statistics |
| `--days` | | Number of days to analyze (default: 30) |
| `--from` | | Start date for statistics (YYYY-MM-DD) |
| `--before` | | End date for statistics (YYYY-MM-DD, exclusive) |
| `--project` | `-p` | Filter by project name (partial match) |
| `--top` | | Number of top items to show (default: 10) |

## Export to Markdown

Export your dialog history to Markdown files for easy browsing, searching, and integration with tools like Obsidian.

### Export Commands

```bash
# Export all dialogs to Markdown files
cursor-chronicle --export

# Export dialogs from a specific project
cursor-chronicle --export -p "my-project"

# Export with date filtering
cursor-chronicle --export --from 2024-01-01 --before 2024-07-01

# Export with custom verbosity level
cursor-chronicle --export --verbosity 3

# Export to a custom directory
cursor-chronicle --export --export-path /path/to/my/obsidian/vault

# Show current configuration
cursor-chronicle --show-config
```

### Folder Structure

Exported files are organized by project and month:

```
<export_path>/
├── my-project/
│   ├── 2024-06/
│   │   ├── 2024-06-12_14-31_How_to_implement_logging.md
│   │   └── 2024-06-15_09-22_Bug_fix_discussion.md
│   └── 2024-07/
│       └── 2024-07-01_10-00_New_feature_planning.md
├── another-project/
│   └── 2024-06/
│       └── 2024-06-20_16-45_API_refactoring.md
└── ...
```

**Note**: Dialogs are placed in folders based on their **creation date**, not last updated date. If you continue an old dialog months later, it stays in its original month folder.

### Verbosity Levels

Control how much detail is included in exported files:

| Level | Name | Description |
|-------|------|-------------|
| 1 | compact | User/AI text only, tool names as one-line summaries |
| 2 | standard | Includes tool parameters, attached files, token counts (default) |
| 3 | full | Complete output: tool results, full thinking content, file contents |

### Configuration

Export settings are stored in `~/.cursor-chronicle/config.json`:

```json
{
  "export_path": "/tmp/cursor-chronicle-export",
  "verbosity": 2
}
```

- **export_path**: Default directory for exported files (default: `/tmp/cursor-chronicle-export`)
- **verbosity**: Default verbosity level 1-3 (default: 2)

You can override these settings via command-line arguments (`--export-path`, `--verbosity`).

### Export Options

| Option | Description |
|--------|-------------|
| `--export` | Export dialogs to Markdown files |
| `--export-path` | Override export directory |
| `--verbosity` | Verbosity level: 1=compact, 2=standard, 3=full |
| `--project` / `-p` | Filter by project name (partial match) |
| `--from` | Export dialogs created after date (YYYY-MM-DD) |
| `--before` | Export dialogs created before date (YYYY-MM-DD) |
| `--show-config` | Display current configuration |

## Search History

The `search-history` command provides full-text search across all Cursor IDE chat history.

### Search Commands

```bash
# Search for a keyword across all history
search-history "KiloCode"

# Search with progress output
search-history "API" --verbose

# Search in specific project only
search-history "bug" --project "my-project"

# Case-sensitive search
search-history "Error" --case-sensitive
```

### List Matching Dialogs

```bash
# Show all dialogs containing the keyword with match counts
search-history "KiloCode" --list-dialogs
```

Output example:
```
🔍 Dialogs containing 'KiloCode':
============================================================
📁 ai-proxy / CI comparison dialog
   Matches: 9 | Date: 2025-09-30
   ID: a001bbfc-219f-4d0d-bd6d-f16af617c994

📁 MyJune24 / Reduce system prompt
   Matches: 37 | Date: 2025-09-05
   ID: 25f0e5ec-7490-41b0-8beb-1fc57e02984b
```

### View Full Dialog

```bash
# Show complete dialog by composer ID (from --list-dialogs output)
search-history --show-dialog "a001bbfc-219f-4d0d-bd6d-f16af617c994"
```

### Search with Context

```bash
# Show surrounding messages for each match
search-history "error" --show-context

# Customize context size (default: 3 messages)
search-history "bug" --show-context --context-size 5
```

### Search Options

| Option | Short | Description |
|--------|-------|-------------|
| `--project` | `-p` | Filter by project name (partial match) |
| `--case-sensitive` | `-c` | Case-sensitive search |
| `--limit` | `-l` | Maximum results (default: 50) |
| `--show-context` | `-x` | Show surrounding messages |
| `--context-size` | | Context messages count (default: 3) |
| `--show-dialog` | `-d` | Show full dialog by composer ID |
| `--list-dialogs` | | List dialogs with match counts |
| `--verbose` | `-v` | Show search progress |

## Output Format

Cursor Chronicle provides rich, formatted output including:

- **👤 USER**: User messages with attached files
- **🤖 AI**: AI responses with token usage and model inference
- **🛠️ TOOL**: Detailed tool executions with parameters and results
- **🧠 AI THINKING**: AI reasoning process and duration
- **📎 ATTACHED FILES**: Complete file context and selections

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/cursor-chronicle/cursor-chronicle.git
cd cursor-chronicle

# Install in development mode with dev dependencies
make install
```

### Development Commands

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Format code
make format

# Check file sizes (max 400 lines)
make check-size

# Check test coverage (min 85%)
make check-coverage

# Install pre-commit hooks
make pre-commit-install

# Clean build artifacts
make clean

# Show all available commands
make help
```

### Code Quality Standards

- **File size limit**: 400 lines per Python file (enforced by pre-commit)
- **Test coverage**: 85% minimum (enforced on pre-push)
- **Code formatting**: Black + isort (auto-fixed on commit)
- **Modular architecture**: Split into focused, maintainable modules

### Project Structure

```
cursor-chronicle/
├── cursor_chronicle/            # Main package (modular)
│   ├── __init__.py             # Package exports
│   ├── __main__.py             # Module entry point
│   ├── viewer.py               # Core viewer logic
│   ├── messages.py             # Message processing
│   ├── formatters.py           # Output formatting
│   ├── statistics.py           # Usage statistics
│   ├── exporter.py             # Markdown export engine
│   ├── config.py               # Configuration management
│   ├── cli.py                  # Command-line interface
│   └── utils.py                # Shared utilities
├── search_history/              # Search package (modular)
│   ├── __init__.py             # Package exports
│   ├── __main__.py             # Module entry point
│   ├── searcher.py             # Core search logic
│   ├── formatters.py           # Search output formatting
│   └── cli.py                  # Search CLI
├── scripts/                     # Development scripts
│   ├── check_file_size.py      # Pre-commit: file size check
│   └── check_coverage.py       # Pre-push: coverage check
├── tests/                       # Test suite (modular)
│   ├── conftest.py             # Shared fixtures
│   ├── test_viewer.py          # Viewer tests
│   ├── test_messages.py        # Message tests
│   ├── test_formatters.py      # Formatter tests
│   ├── test_statistics.py      # Statistics tests
│   ├── test_exporter.py        # Export tests
│   ├── test_config.py          # Config tests
│   ├── test_cli.py             # CLI tests
│   ├── test_search_*.py        # Search tests
│   └── test_integration.py     # Integration tests
├── .pre-commit-config.yaml      # Pre-commit hooks config
├── pyproject.toml               # Project config
├── Makefile                     # Development commands
└── README.md                    # This file
```

## Database Structure

Cursor Chronicle understands the complex internal structure of Cursor IDE's SQLite databases. This section provides detailed information about how Cursor stores conversation data.

### Database Location

Cursor IDE uses SQLite databases to store chat history:

- **Global Storage**: `~/.config/Cursor/User/globalStorage/state.vscdb`
  - Contains actual message `bubbles` (individual chat messages and tool outputs)
  - Bubbles stored under keys: `bubbleId:<composerId>:<bubbleId>`
  - Over 100 different fields per bubble with comprehensive metadata

- **Workspace Storage**: `~/.config/Cursor/User/workspaceStorage/<workspace_id>/state.vscdb`
  - Each workspace has its own database
  - Contains high-level `composerData` (chat sessions metadata)
  - Stores individual composer details under `composerData:<composerId>`

### Key Data Structures

#### Composer Data (Chat Sessions)
- `composerId`: Unique identifier for the chat session
- `name`: User-defined name of the session
- `createdAt`: Unix timestamp (milliseconds) when session was created
- `lastUpdatedAt`: Unix timestamp (milliseconds) of last update
- **`fullConversationHeadersOnly`**: Ordered array defining correct chronological order of messages

#### Bubble Data (Individual Messages)
**Core Fields:**
- `bubbleId`: Unique ID for each message bubble
- `type`: Speaker type (`1` for user, `2` for assistant)
- `text`: The actual message content
- `_v`: Version field (typically `2` for current format)

**Tool and Capability Fields:**
- `toolFormerData`: Details of tool calls (name, status, rawArgs, result)
- `capabilities`: Array of available capabilities
- `capabilitiesRan`: Object with capability execution data
- `supportedTools`: List of tools available for the message

**AI Processing Fields:**
- `thinking`: AI's thinking process data
- `thinkingDurationMs`: Duration of AI's thinking in milliseconds
- `isThought`: Boolean indicating if this is a thinking bubble
- `isAgentic`: Boolean indicating if agentic mode was used

**Context and File Fields:**
- `currentFileLocationData`: Information about active file in editor
- `projectLayouts`: Structured data about relevant project files
- `codebaseContextChunks`: Code snippets from codebase search results
- `attachedCodeChunks`: Code chunks attached to the message
- `relevantFiles`: Other files identified as relevant

**Metadata Fields:**
- `tokenCount`: Object with `inputTokens` and `outputTokens` counts
- `usageUuid`: Unique identifier for usage tracking
- `serverBubbleId`: Server-side bubble identifier
- `unifiedMode`: Numeric indicator of unified mode (e.g., 2, 4)
- `useWeb`: Boolean indicating if web search was used

### Message Ordering

**Critical Insight**: Message ordering is NOT determined by database `rowid` alone. For Cursor conversations, the definitive order is provided by the `fullConversationHeadersOnly` array within the `composerData` object. This array contains `bubbleId`s in the correct chronological order.

### Model Information

**Important**: Cursor IDE does not store explicit model information (like "GPT-4", "Claude-3.5-Sonnet") directly in the database. Models can be inferred using:

1. **Agentic Mode**: `isAgentic` flag suggests Claude for agentic capabilities
2. **Token Patterns**: High token counts may suggest more advanced models
3. **Capability Usage**: Complex capability patterns may indicate model tier
4. **Context Clues**: Model names mentioned in message text
5. **Unified Mode**: Different unified mode numbers may correlate with model types

### Database Query Patterns

```sql
-- Get composer data for message ordering
SELECT value FROM cursorDiskKV 
WHERE key = 'composerData:<composerId>';

-- Get bubble data in correct order
SELECT value FROM cursorDiskKV 
WHERE key = 'bubbleId:<composerId>:<bubbleId>' 
AND LENGTH(value) > 100;

-- Find recent conversations
SELECT key, value FROM cursorDiskKV 
WHERE key LIKE 'bubbleId:%' 
ORDER BY rowid DESC LIMIT 10;
```

## Requirements

- **Python**: 3.8 or higher
- **Dependencies**: None (uses only Python standard library)
- **OS**: Linux, macOS, Windows (wherever Cursor IDE runs)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Format code: `make format`
6. Submit a pull request

## Troubleshooting

### Common Issues

**Database not found**: Ensure Cursor IDE is installed and has been used to create conversations.

**Permission errors**: The tool reads databases in read-only mode, but ensure your user has access to the Cursor config directory.

**Empty output**: Check that you have actual conversations in Cursor IDE and try `--list-projects` first.

### Debug Mode

For troubleshooting, examine the database structure directly:

```bash
# Check if databases exist
ls -la ~/.config/Cursor/User/globalStorage/
ls -la ~/.config/Cursor/User/workspaceStorage/
```

## Changelog

### Version 1.5.0
- **New**: Export dialogs to Markdown files with `--export` command
- **New**: Configurable export path and verbosity via `~/.cursor-chronicle/config.json`
- **New**: Organized folder structure: `<project>/<YYYY-MM>/<date_time_title>.md`
- **New**: Three verbosity levels for export: compact (1), standard (2), full (3)
- **New**: `--show-config` command to display current configuration
- **New**: `config.py` module for configuration management
- **New**: `exporter.py` module for Markdown export engine
- **Improved**: Test coverage with 65 new tests for export functionality

### Version 1.4.0
- **Refactor**: Split monolithic files into modular packages (cursor_chronicle/, search_history/)
- **Refactor**: Rename `--to` parameter to `--before` for clarity
- **New**: Pre-commit hooks for file size (400 lines max) and coverage (85% min) checks
- **New**: `python -m cursor_chronicle` and `python -m search_history` module execution
- **New**: Development scripts in scripts/ directory
- **New**: Makefile targets: check-size, check-coverage, pre-commit-install
- **Improved**: Test suite split into focused modules (test_viewer, test_messages, etc.)
- **Improved**: Test coverage increased to 87%
- **Fix**: Coding days now correctly calculates month boundaries (--before is exclusive)

### Version 1.3.2
- **New**: "Coding days" statistic showing active days vs total period days with percentage

### Version 1.3.1
- **Fix**: Daily activity now shows all days in the specified period
- **Fix**: `--days` parameter properly controls daily activity display count

### Version 1.3.0
- **New**: Usage statistics with `--stats` command
- **New**: Analyze activity by project, messages, tools, and tokens
- **New**: Daily activity visualization
- **New**: Top tools and longest dialogs rankings
- **New**: Configurable analysis period with `--days` option

### Version 1.2.1
- **Fix**: Sort by creation date by default, add `--updated` option
- **Fix**: Bug where dialogs with `last_updated=0` sorted incorrectly

### Version 1.2.0
- **New**: List all dialogs across all projects with `--list-all`
- **New**: Filter dialogs by time interval with `--from` and `--to`
- **New**: Customizable sorting: by date, name, or project (`--sort`)
- **New**: Ascending/descending sort order (`--desc`)
- **New**: Sort/filter by creation date (default) or last updated (`--updated`)
- **New**: Limit results count (`--limit`)

### Version 1.1.0
- **New**: Full-text search across all chat history (`search_history.py`)
- **New**: List dialogs containing search term with `--list-dialogs`
- **New**: Show full dialog by composer ID with `--show-dialog`
- **New**: Context display around matches with `--show-context`
- **New**: Project filtering for search with `--project`

### Version 1.0.0
- Initial release with full conversation extraction
- Tool call analysis and rich metadata support
- Modern Python packaging with pyproject.toml
- Comprehensive database structure understanding
- Message ordering using `fullConversationHeadersOnly`
- Model inference capabilities
- 100+ metadata fields support