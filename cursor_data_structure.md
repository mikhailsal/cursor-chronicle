# Cursor IDE Data Structure Documentation

This document outlines the key aspects of Cursor IDE's internal data storage, particularly focusing on chat sessions and message ordering, based on the `specstory` extension source code (`tmp/extension.pretty.js`) and provided documentation (`cursor_database_interaction.md`). Understanding this structure is crucial for accurate data retrieval and manipulation.

## 1. Database Location and Access

Cursor IDE primarily uses SQLite databases to store its internal state and chat history. The main database files are:

-   **Global Storage**: `~/.config/Cursor/User/globalStorage/state.vscdb`
    -   This database contains the actual message `bubbles` (individual chat messages and tool outputs).
    -   Bubbles are typically stored under keys formatted as `bubbleId:<composerId>:<bubbleId>`.
    -   Contains over 100 different fields per bubble (comprehensive metadata).

-   **Workspace Storage**: `~/.config/Cursor/User/workspaceStorage/<workspace_id>/state.vscdb`
    -   Each workspace has its own `state.vscdb`.
    -   This database contains high-level `composerData` (chat sessions metadata) under the key `composer.composerData`.
    -   It also stores individual composer details under `composerData:<composerId>`.

Access to these databases often involves opening them in read-only mode, with a temporary switch to `WAL` (Write-Ahead Logging) mode if needed for concurrent access.

## 2. Key Data Structures

### 2.1. Composer Data (Chat Sessions Metadata)

Composer data, typically found in the workspace-specific `state.vscdb` under `composerData:<composerId>`, provides metadata for each chat session. Key fields include:

-   `composerId`: A unique identifier for the chat session.
-   `name`: The user-defined name of the session.
-   `createdAt`: Unix timestamp (milliseconds) when the session was created.
-   `lastUpdatedAt`: Unix timestamp (milliseconds) of the last update.
-   **`fullConversationHeadersOnly`**: **Crucially, for Cursor composers, this field contains an ordered array of objects, where each object has a `bubbleId`. This array defines the *correct chronological order* of messages within the conversation.** This is the definitive source for message sequencing.

### 2.2. Bubble Data (Individual Messages/Tool Outputs)

Bubble data, stored in the global `state.vscdb` under keys like `bubbleId:<composerId>:<bubbleId>`, represents individual turns in a conversation. Our investigation revealed **106 unique fields** across bubble data structures.

#### Core Message Fields:
-   `bubbleId`: Unique ID for each message bubble.
-   `type`: Denotes the speaker (`1` for user, `2` for assistant, others for internal).
-   `text`: The actual message content.
-   `_v`: Version field (typically `2` for current format).

#### Tool and Capability Fields:
-   `toolFormerData`: Contains details of tool calls (e.g., `name`, `status`, `rawArgs`, `result`).
-   `capabilities`: Array of available capabilities.
-   `capabilitiesRan`: Object with capability names as keys, containing execution data.
-   `capabilityStatuses`: Status information for each capability.
-   `capabilityContexts`: Additional context for capabilities.
-   `supportedTools`: List of tools available for the message.
-   `toolResults`: Results from tool executions.

#### AI Thinking and Processing:
-   `thinking`: Indicates AI's thinking process data.
-   `thinkingDurationMs`: Duration of AI's thinking in milliseconds.
-   `allThinkingBlocks`: Array of thinking blocks.
-   `isThought`: Boolean indicating if this is a thinking bubble.

#### Context and File Information:
-   `currentFileLocationData`: Information about the active file in the editor.
-   `projectLayouts`: Structured data about relevant project files.
-   `codebaseContextChunks`: Contains snippets of code from codebase search results, with `relativeWorkspacePath` and `contents`.
-   `attachedFileCodeChunksUris`: URIs of explicitly attached files.
-   `attachedCodeChunks`: Code chunks attached to the message.
-   `relevantFiles`: Other files identified as relevant.
-   `context.fileSelections`: Details about selected file regions.
-   `recentlyViewedFiles`: Files recently viewed by user.
-   `recentLocationsHistory`: History of recent code locations.

#### Metadata and Tracking:
-   `tokenCount`: Object with `inputTokens` and `outputTokens` counts.
-   `usageUuid`: Unique identifier for usage tracking.
-   `serverBubbleId`: Server-side bubble identifier.
-   `isAgentic`: Boolean indicating if agentic mode was used.
-   `unifiedMode`: Numeric indicator of unified mode (e.g., 2, 4).
-   `useWeb`: Boolean indicating if web search was used.
-   `isRefunded`: Boolean indicating if the request was refunded.

#### Additional Rich Metadata (100+ fields total):
-   `approximateLintErrors`: Linting errors in context.
-   `assistantSuggestedDiffs`: AI-suggested code changes.
-   `attachedFolders`: Folders attached to context.
-   `attachedHumanChanges`: Human-made changes in context.
-   `commits`: Git commits related to the message.
-   `consoleLogs`: Console output logs.
-   `contextPieces`: Additional context pieces.
-   `cursorRules`: Cursor rules applied to the session.
-   `deletedFiles`: Files deleted in context.
-   `diffHistories`: History of code diffs.
-   `docsReferences`: Documentation references.
-   `documentationSelections`: Selected documentation.
-   `editTrailContexts`: Context from edit trails.
-   `existedPreviousTerminalCommand`: Boolean for terminal command history.
-   `existedSubsequentTerminalCommand`: Boolean for subsequent commands.
-   `externalLinks`: External links referenced.
-   `fileDiffTrajectories`: File change trajectories.
-   `gitDiffs`: Git diff information.
-   `humanChanges`: Human-made changes.
-   `images`: Images attached to the message.
-   `interpreterResults`: Results from code interpreters.
-   `knowledgeItems`: Knowledge base items.
-   `lints`: Linting information.
-   `multiFileLinterErrors`: Multi-file linting errors.
-   `notepads`: Notepad content.
-   `pullRequests`: Pull request information.
-   `suggestedCodeBlocks`: AI-suggested code blocks.
-   `summarizedComposers`: Summarized composer information.
-   `uiElementPicked`: UI elements selected by user.
-   `userResponsesToSuggestedCodeBlocks`: User responses to suggestions.
-   `webReferences`: Web references used.

## 3. Message Ordering Logic (Key Insight)

The most important insight gained from the `specstory` extension source code is that **message ordering is NOT determined by the `rowid` of the `cursorDiskKV` table alone**. Instead, for Cursor-originated conversations, the definitive order is provided by the `fullConversationHeadersOnly` array within the `composerData` object for a given `composerId`. Each element in this array corresponds to a `bubbleId`, and processing these `bubbleId`s in the order they appear in `fullConversationHeadersOnly` ensures the correct chronological display of the conversation.

If `fullConversationHeadersOnly` is not present (e.g., for older or VS Code-originated sessions), falling back to ordering by `rowid` is a reasonable heuristic, but it may not always perfectly reflect the user's view in the Cursor IDE.

## 4. Model Information Storage

**Critical Finding**: Cursor IDE **does not store explicit model information** (such as "GPT-4", "Claude-3.5-Sonnet", "o1-preview") directly in the database records. Our comprehensive investigation of the database structure revealed:

### What is NOT stored:
- Direct model names or identifiers
- Model configuration per message
- Explicit model selection data

### What CAN be inferred:
- **Agentic Mode Usage**: `isAgentic` field indicates advanced model capabilities
- **Token Patterns**: High token counts may suggest more advanced models
- **Capability Usage**: Complex capability patterns may indicate model tier
- **Context Clues**: Model names mentioned in message text or cursor rules
- **Unified Mode**: Different unified mode numbers may correlate with model types

### Model Inference Strategies:
1. Check `isAgentic` flag (suggests Claude for agentic capabilities)
2. Analyze token usage patterns (`tokenCount` field)
3. Examine capability complexity (`capabilitiesRan` field)
4. Look for model mentions in `text` content
5. Check cursor rules filenames for model hints

## 5. Relationship between Composer and Bubble Data

-   `composerData` provides the metadata and the *ordered list of `bubbleId`s* for a conversation.
-   Individual `bubbleData` entries, identified by their `bubbleId`, contain the actual content of each message or tool interaction.

Therefore, to reconstruct a full, accurately ordered conversation, one must first retrieve the `composerData` to get the `fullConversationHeadersOnly` list, and then fetch each `bubbleData` using the `bubbleId`s in that specific order.

## 6. Database Query Patterns

### Efficient Data Retrieval:
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

### Field Analysis:
- Most bubbles contain 50-100 populated fields
- Empty arrays/objects are common for unused features
- Critical fields for conversation reconstruction: `type`, `text`, `toolFormerData`, `tokenCount`
- Metadata fields provide rich context about AI processing

## 7. Practical Implications

This structured understanding of Cursor's data storage is vital for:

1. **Conversation Reconstruction**: Proper message ordering using `fullConversationHeadersOnly`
2. **Metadata Analysis**: Rich context about AI processing and capabilities
3. **Usage Tracking**: Token counts, usage UUIDs, and server correlation
4. **Model Inference**: Heuristic approaches to determine likely models used
5. **Tool Development**: Building tools that accurately reflect Cursor's internal state

The database structure is highly sophisticated, storing comprehensive metadata about every aspect of the AI interaction, even though direct model identification is not preserved. 