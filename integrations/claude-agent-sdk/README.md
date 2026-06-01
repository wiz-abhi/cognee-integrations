# Cognee-Integration-Claude

A powerful integration between Cognee and Claude Agent SDK that provides intelligent memory management and retrieval capabilities for AI agents.

## Overview

`cognee-integration-claude` combines [Cognee's advanced memory layer](https://github.com/topoteretes/cognee) with Anthropic's [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). This integration allows you to build AI agents that can efficiently store, search, and retrieve information from a persistent knowledge base.

## Features

- **Smart Knowledge Storage**: Add and persist information using Cognee's advanced indexing
- **Semantic Search**: Retrieve relevant information using natural language queries
- **Session Management**: Support for user-specific data isolation
- **Claude Agent SDK Integration**: Seamless integration with Claude's agent framework
- **Async Support**: Built with async/await for high-performance applications
- **Thread-Safe**: Queue-based processing for concurrent operations
- **Cross-Session Persistence**: Memory survives between agent instances

## Installation

```bash
pip install cognee-integration-claude
```

Or using uv:

```bash
uv add cognee-integration-claude
```

## Quick Start

```python
import asyncio
import os
from dotenv import load_dotenv
import cognee
from claude_agent_sdk import (
    create_sdk_mcp_server,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
)
from cognee_integration_claude import add_tool, search_tool

load_dotenv()

async def main():
    # Clean up memory to start fresh (Optional)
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    
    # Create an MCP server with Cognee tools
    server = create_sdk_mcp_server(
        name="cognee-tools",
        version="1.0.0",
        tools=[add_tool, search_tool]
    )
    
    # Configure the agent
    options = ClaudeAgentOptions(
        mcp_servers={"tools": server},
        allowed_tools=["mcp__tools__add_tool", "mcp__tools__search_tool"],
    )
    
    # Use the agent to store information
    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Remember that our company signed a contract with HealthBridge Systems "
            "in the healthcare industry, starting Feb 2023, ending Jan 2026, worth £2.4M"
        )
        
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")
    
    # Query the stored information (new agent instance)
    async with ClaudeSDKClient(options=options) as client:
        await client.query("What contracts do we have in the healthcare industry?")
        
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Available Tools

### Basic Tools

```python
from cognee_integration_claude import add_tool, search_tool

# add_tool: Store information in the knowledge base
# search_tool: Search and retrieve previously stored information
```

### Sessionized Tools

For multi-user applications, use sessionized tools to isolate data between users:

```python
from cognee_integration_claude import get_sessionized_cognee_tools

# Get tools for a specific user session
add_tool, search_tool = get_sessionized_cognee_tools("user-123")

# Auto-generate a session ID
add_tool, search_tool = get_sessionized_cognee_tools()
```

## Session Management

`cognee-integration-claude` supports user-specific sessions to tag data and isolate retrieval between different users or contexts:

```python
import asyncio
from claude_agent_sdk import (
    create_sdk_mcp_server,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
)
from cognee_integration_claude import get_sessionized_cognee_tools

async def main():
    # Each user gets their own isolated session
    user1_add, user1_search = get_sessionized_cognee_tools("user-123")
    user2_add, user2_search = get_sessionized_cognee_tools("user-456")
    
    # Create separate agent configurations for each user
    user1_server = create_sdk_mcp_server(
        name="user1-tools",
        version="1.0.0",
        tools=[user1_add, user1_search]
    )
    
    user2_server = create_sdk_mcp_server(
        name="user2-tools",
        version="1.0.0",
        tools=[user2_add, user2_search]
    )
    
    user1_options = ClaudeAgentOptions(
        mcp_servers={"tools": user1_server},
        allowed_tools=["mcp__tools__add_tool", "mcp__tools__search_tool"],
    )
    
    user2_options = ClaudeAgentOptions(
        mcp_servers={"tools": user2_server},
        allowed_tools=["mcp__tools__add_tool", "mcp__tools__search_tool"],
    )
    
    # Each agent works with isolated data
    async with ClaudeSDKClient(options=user1_options) as client:
        await client.query("Remember: I like pizza")
        async for msg in client.receive_response():
            pass
    
    async with ClaudeSDKClient(options=user2_options) as client:
        await client.query("Remember: I like sushi")
        async for msg in client.receive_response():
            pass
    
    # User 1 can only see their own data
    async with ClaudeSDKClient(options=user1_options) as client:
        await client.query("What food do I like?")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"User 1's agent: {block.text}")  # Will mention pizza, not sushi

if __name__ == "__main__":
    asyncio.run(main())
```

## Tool Reference

### `add_tool(data: str)`

Store information in the memory for later retrieval.

**Parameters:**
- `data` (str): The text or information you want to store

**Returns:** Confirmation message

**Example:**
```python
server = create_sdk_mcp_server(
    name="memory-tools",
    version="1.0.0",
    tools=[add_tool]
)

options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__add_tool"],
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Store this: Our Q4 revenue was $2.5M with 15% growth")
    async for msg in client.receive_response():
        pass
```

### `search_tool(query_text: str)`

Search and retrieve previously stored information from the memory.

**Parameters:**
- `query_text` (str): Natural language search query

**Returns:** List of relevant search results

**Example:**
```python
server = create_sdk_mcp_server(
    name="memory-tools",
    version="1.0.0",
    tools=[search_tool]
)

options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__search_tool"],
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("What was our Q4 revenue?")
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    print(block.text)
```

### `get_sessionized_cognee_tools(session_id: Optional[str] = None)`

Returns cognee tools with optional user-specific sessionization.

**Parameters:**
- `session_id` (Optional[str]): User identifier for data isolation. If not provided, a random session ID is auto-generated.

**Returns:** `[add_tool, search_tool]` - A list of sessionized tools

**Example:**
```python
# With explicit session ID
add_tool, search_tool = get_sessionized_cognee_tools("user-123")

# Auto-generate session ID
add_tool, search_tool = get_sessionized_cognee_tools()
```

## Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# OpenAI API key (used by Cognee for LLM operations)
LLM_API_KEY=your-openai-api-key-here
```

You can also use other LLM providers with Cognee. Check the [Cognee documentation](https://docs.cognee.ai/setup-configuration/llm-providers) for more details.

The Claude Agent SDK uses a bundled Claude Code CLI that handles authentication automatically. 

1. **If you're using Cursor**: You're likely already authenticated through your Cursor/Claude session. The bundled CLI will use your existing credentials.

2. **If you're running standalone**: The first time you run the SDK, it will guide you through authentication via OAuth or API key through the bundled CLI.

3. **For CI/CD or automated environments**: You may need to authenticate the CLI separately. See the [Claude Agent SDK documentation](https://github.com/anthropics/claude-agent-sdk-python) for details.

### Cognee Configuration (Optional)

You can customize Cognee's data and system directories:

```python
from cognee.api.v1.config import config
import os

config.data_root_directory(
    os.path.join(os.path.dirname(__file__), ".cognee/data_storage")
)

config.system_root_directory(
    os.path.join(os.path.dirname(__file__), ".cognee/system")
)
```

## Examples

Check out the `examples/` directory for simple examples:

- **`examples/example.py`**: Basic usage with add and search tools

And the interactive guide:

- **`cognee_integration_claude/guide.ipynb`**: Step-by-step Jupyter notebook tutorial

## Advanced Usage

### Pre-loading Data

You can pre-load data into Cognee before creating agents:

```python
import asyncio
import cognee
from claude_agent_sdk import (
    create_sdk_mcp_server,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
)
from cognee_integration_claude import search_tool

async def main():
    # Pre-load data directly into Cognee
    await cognee.add("Important company information here...")
    await cognee.add("More data to remember...")
    await cognee.cognify()  # Process and index the data
    
    # Now create an agent that can search this data
    server = create_sdk_mcp_server(
        name="search-tools",
        version="1.0.0",
        tools=[search_tool]
    )
    
    options = ClaudeAgentOptions(
        mcp_servers={"tools": server},
        allowed_tools=["mcp__tools__search_tool"],
    )
    
    async with ClaudeSDKClient(options=options) as client:
        await client.query("What information do we have?")
        
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(block.text)

if __name__ == "__main__":
    asyncio.run(main())
```

### Data Management

```python
import asyncio
import cognee

async def reset_knowledge_base():
    """Clear all data and reset the knowledge base"""
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

async def visualize_knowledge_graph():
    """Generate a visualization of the knowledge graph"""
    await cognee.visualize_graph("graph.html")
```

### Disabling Default Cursor Tools

When using Claude Agent SDK in environments like Cursor, you may want to disable default tools:

```python
options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__add_tool", "mcp__tools__search_tool"],
    disallowed_tools=[
        "Task", "Bash", "Glob", "Grep", "ExitPlanMode",
        "Read", "Edit", "Write", "NotebookEdit", "WebFetch",
        "TodoWrite", "WebSearch", "BashOutput", "KillShell", "SlashCommand",
    ],
)
```

## Requirements

- Python 3.13+
- OpenAI API key (or other LLM provider supported by Cognee)

## Related Projects

- [cognee](https://github.com/topoteretes/cognee) - The core Cognee memory layer
- [claude-agent-sdk](https://github.com/anthropics/claude-agent-sdk-python) - Claude Agent SDK

## License

MIT License

## Contributing

Contributions are welcome! Please feel free fork to submit a PR.

