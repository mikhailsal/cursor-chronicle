# Cursor Chronicle

A powerful tool for extracting and displaying dialogs from Cursor IDE database with comprehensive support for attached files, tool calls, and conversation metadata.

## Features

- 📊 **Complete Conversation History**: Extract full chat sessions with AI assistants
- 🛠️ **Tool Call Analysis**: Detailed view of tool executions and results
- 📎 **File Attachment Support**: See all attached files and context
- 🧠 **AI Thinking Process**: View AI reasoning and thinking duration
- 📈 **Token Usage Tracking**: Monitor token consumption and infer models
- 🔍 **Advanced Search**: Find specific projects and conversations
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
# Run directly without installation
python cursor_chronicle.py --help
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

# Format code
make format

# Clean build artifacts
make clean

# Show all available commands
make help
```

### Project Structure

```
cursor-chronicle/
├── cursor_chronicle.py          # Main application
├── cursor_chronicle.md          # Detailed documentation
├── pyproject.toml              # Modern Python project config
├── tests/                      # Test suite
├── Makefile                    # Development commands
├── README.md                   # This file
└── LICENSE                     # License file
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

### Version 1.0.0
- Initial release with full conversation extraction
- Tool call analysis and rich metadata support
- Modern Python packaging with pyproject.toml
- Comprehensive database structure understanding
- Message ordering using `fullConversationHeadersOnly`
- Model inference capabilities
- 100+ metadata fields support