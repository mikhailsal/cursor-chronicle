# Cursor Chronicle

Python script for extracting and displaying dialogs from Cursor IDE database with support for tools and attached files.

## Description

This script allows viewing complete AI chat history from Cursor IDE, including:
- 💬 User messages and AI responses
- 🛠️ Tool calls
- ⚡ Terminal command execution
- ✏️ File editing
- 🔍 Codebase search
- 🌐 Web search and other MCP tools
- 📎 **NEW**: Attached files and context

The script extracts data from SQLite databases where Cursor stores all dialog history and tool execution.

## Features

- 📋 View list of all projects with dialogs
- 💬 View dialog list for specific project
- 🔍 Search and display specific dialog
- 🕒 Shows most recent dialog from most recent project by default
- 🎯 Supports partial search by project and dialog names
- 🛠️ **NEW**: Display tool calls with parameters and results
- ⚡ **NEW**: Show executed terminal commands with output
- ✏️ **NEW**: File editing information with diffs
- 📎 **NEW**: Display attached files with context

## Usage

### Show most recent dialog (default)
```bash
python3 cursor_chronicle.py
```

### Show list of all projects
```bash
python3 cursor_chronicle.py --list-projects
```

### Show dialogs for specific project
```bash
python3 cursor_chronicle.py --list-dialogs ai-chatting
```

### Show specific dialog
```bash
python3 cursor_chronicle.py --project ai-chatting --dialog "database"
```

### Show dialog from specific project (most recent)
```bash
python3 cursor_chronicle.py --project tts-python-ai
```

## Parameters

- `--project`, `-p` - Project name (supports partial matching)
- `--dialog`, `-d` - Dialog name (supports partial matching)
- `--list-projects` - Show list of all projects
- `--list-dialogs PROJECT` - Show dialog list for specified project

## Output Format

Dialogs are displayed in readable format with tools and attached files:

```
============================================================
PROJECT: ai-chatting
DIALOG: Where is Cursor IDE database stored
============================================================

👤 USER:
You need to find out where Cursor IDE stores the database...

📎 ATTACHED FILES:
   📍 Active file: anime/Kill la Kill 01-04 summary.txt
      Line: 5
      Preview: The third episode shows Satsuki herself in a new light...
   🔗 Relevant file: cursor_chronicle.py
   🔗 Relevant file: README.md
   📁 Project files (9 files):
      - anime/[HorribleSubs] Kill la Kill - 01 [720p].ass
      - anime/[HorribleSubs] Kill la Kill - 01 [720p].txt
      - anime/[HorribleSubs] Kill la Kill - 02 [720p].ass
      - backup/all software without years.txt
      - backup/all software.txt
      ... and 4 more files
----------------------------------------

🛠️ TOOL: ⚡ Terminal Command
   Name: run_terminal_cmd
   Status: completed
   Decision: ✅ accepted
   Parameters:
     command: find ~/.config/Cursor -name "*.db" -o -name "*.sqlite"
     explanation: Searching for database files in Cursor config directory
   Result:
     Exit code: 0
     Output: /home/user/.config/Cursor/User/globalStorage/state.vscdb...
----------------------------------------

🤖 AI:
Hello! I'm Claude Sonnet 4. I found the Cursor database location...
----------------------------------------
```

## Supported Tools

The script recognizes and beautifully displays the following tool types:

- 🔍 **Codebase Search** - codebase search
- 🔎 **Grep Search** - regex search
- 📖 **Read File** - file reading
- 📁 **List Directory** - directory listing
- ✏️ **Edit File** - file editing (with diff display)
- 🔍 **File Search** - file search
- 🗑️ **Delete File** - file deletion
- 🔄 **Reapply** - reapplying changes
- ⚡ **Terminal Command** - terminal command execution
- 📋 **Fetch Rules** - rules fetching
- 🌐 **Web Search** - web search
- 🔧 **MCP Tool** - various MCP tools (browser, puppeteer, etc.)

## Attached File Types

The script recognizes and displays the following attached file types:

- 📍 **Active file** - file open in editor when message was created
  - Shows file path, line number, and text preview
- ✅ **Selected files** - files explicitly attached by user to message (@ symbol)
  - These are the main attached files visible in Cursor interface
- 📎 **Context files** - files from codebase with code fragments
  - Shows line ranges and content preview
- 🔗 **Relevant files** - files automatically determined as relevant to context
- 📁 **Project files** - complete project file structure (limited to first 10 for readability)
- 🎯 **Selected in context** - files with specific selections or fragments

## How It Works

The script reads data from the following locations:

1. **Project metadata**: `~/.config/Cursor/User/workspaceStorage/*/workspace.json`
2. **Dialog information**: `~/.config/Cursor/User/workspaceStorage/*/state.vscdb` (table `ItemTable`, key `composer.composerData`)
3. **Messages and tools**: `~/.config/Cursor/User/globalStorage/state.vscdb` (table `cursorDiskKV`, keys `bubbleId:*`)

### Data Structure

- `type: 1` - user message 👤
- `type: 2` - AI response 🤖
- `toolFormerData` - tool call data 🛠️
  - `tool` - tool type (numeric code)
  - `name` - tool name
  - `status` - execution status
  - `userDecision` - user decision (accepted/rejected)
  - `rawArgs` - call parameters
  - `result` - execution result

## Requirements

- Python 3.6+
- Installed Cursor IDE with dialog history
- Read permissions for files in `~/.config/Cursor/`

## Usage Examples

```bash
# View all projects
./cursor_chronicle.py --list-projects

# Find project with "python" in name
./cursor_chronicle.py --project python

# Find dialog about tests in ai-chatting project
./cursor_chronicle.py --project ai-chatting --dialog test

# Show all dialogs for project
./cursor_chronicle.py --list-dialogs starcraft7x
```

## What's New in Version 2.0

- ✨ **Tool support**: display of all tool calls with parameters and results
- 🎨 **Beautiful formatting**: icons for different tool types
- 📊 **Detailed information**: showing command exit codes, file diffs, execution statuses
- 🔧 **MCP tools**: support for browser, puppeteer and other MCP tools
- 📈 **Extended diagnostics**: more information about each action in dialog

## What's New in Version 3.0

- 📎 **Attached files support**: display of all types of files attached to dialog
- 📍 **Active files**: showing file open in editor with line number and preview
- 🔗 **Relevant files**: automatically determined Cursor context files
- 📁 **Project structure**: complete project file hierarchy from metadata
- 🎨 **Improved formatting**: grouping files by types with icons
- 🔧 **Extended parsing**: analysis of `currentFileLocationData`, `projectLayouts`, `context` and `relevantFiles` fields

## Author

Created with Claude Sonnet 4 as part of research on Cursor IDE data structure. 