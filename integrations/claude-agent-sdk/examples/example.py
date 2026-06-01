import asyncio
import os
import webbrowser

import cognee
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    SystemMessage,
    TextBlock,
    UserMessage,
    create_sdk_mcp_server,
)
from cognee_integration_claude import add_tool, search_tool


def display_message(msg):
    """Standardized message display function.

    - UserMessage: "User: <content>"
    - AssistantMessage: "Claude: <content>"
    - SystemMessage: ignored
    - ResultMessage: "Result ended" + cost if available
    """
    if isinstance(msg, UserMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"User: {block.text}")
    elif isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"Claude: {block.text}")
    elif isinstance(msg, SystemMessage):
        # Ignore system messages
        pass
    elif isinstance(msg, ResultMessage):
        print("Result ended")


async def visualize_graph(open_browser=True):
    destination_file_path = os.path.join(os.getcwd(), "graph_visualization.html")

    await cognee.visualize_graph(destination_file_path)

    if open_browser:
        url = "file://" + os.path.abspath(destination_file_path)
        webbrowser.open(url)


server = create_sdk_mcp_server(name="my-tools", version="1.0.0", tools=[add_tool, search_tool])

options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__add_tool", "mcp__tools__search_tool"],
    disallowed_tools=[
        "Task",
        "Bash",
        "Glob",
        "Grep",
        "ExitPlanMode",
        "Read",
        "Edit",
        "Write",
        "NotebookEdit",
        "WebFetch",
        "TodoWrite",
        "WebSearch",
        "BashOutput",
        "KillShell",
        "SlashCommand",
    ],
)


async def main():
    from cognee.api.v1.config import config

    config.data_root_directory(os.path.join(os.path.dirname(__file__), "../.cognee/data_storage"))

    config.system_root_directory(os.path.join(os.path.dirname(__file__), "../.cognee/system"))

    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            'We have signed a contract with the following company: "Meditech Solutions". '
            "Company is in the healthcare industry. Start date is Jan 2023 and "
            "end date is Dec 2025. Contract value is £1.2M.\n"
            'We have signed a contract with the following company: "QuantumSoft". '
            "Company is in the technology industry. Start date is Aug 2024 and "
            "end date is Aug 2028. Contract value is £5.5M.\n"
            'We have signed a contract with the following company: "Orion Retail Group". '
            "Company is in the retail industry. Start date is Mar 2024 and "
            "end date is Mar 2026. Contract value is £850K.\n"
        )

        await client.query(
            "I need to research our contract portfolio. Can you search for any contracts we "
            "have with companies in the healthcare industry? Use any tools you have."
        )

        async for msg in client.receive_response():
            display_message(msg)

    await visualize_graph()


if __name__ == "__main__":
    asyncio.run(main())
