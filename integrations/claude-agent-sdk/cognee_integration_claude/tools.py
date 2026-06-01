import asyncio
import functools
import logging
from typing import List, Optional

import cognee
from claude_agent_sdk import tool
from cognee.modules.engine.models.node_set import NodeSet

from . import bootstrap  # noqa: F401

logger = logging.getLogger(__name__)

_add_lock = asyncio.Lock()
_add_queue = asyncio.Queue()


async def _enqueue_add(*args, **kwargs):
    global _add_lock
    if _add_lock.locked():
        await _add_queue.put((args, kwargs))
        return
    async with _add_lock:
        await _add_queue.put((args, kwargs))
        while True:
            try:
                next_args, next_kwargs = await asyncio.wait_for(_add_queue.get(), timeout=2)
                _add_queue.task_done()
            except asyncio.TimeoutError:
                break
            await cognee.add(*next_args, **next_kwargs)
        await cognee.cognify()


async def add_tool_impl(data: str, node_set: Optional[List[str]] = None):
    """
    Store information in the knowledge base for later retrieval.

    Use this tool whenever you need to remember, store, or save information
    that the user provides. This is essential for building up a knowledge base
    that can be searched later. Always use this tool when the user says things
    like "remember", "store", "save", or gives you information to keep track of.

    Args:
        data (str): The text or information you want to store and remember.
        node_set (Optional[List[str]]): Additional node set identifiers for session isolation.

    Returns:
        str: A confirmation message indicating that the item was added.
    """
    logger.info(f"Adding data to cognee: {data}")

    # Use lock to prevent race conditions during database initialization
    await _enqueue_add(data, node_set=node_set)
    return "Item added to cognee and processed"


async def search_tool_impl(query_text: str, node_set: Optional[List[str]] = None):
    """
    Search and retrieve previously stored information from the knowledge base.

    Use this tool to find and recall information that was previously stored.
    Always use this tool when you need to answer questions about information
    that should be in the knowledge base, or when the user asks questions
    about previously discussed topics.

    Args:
        query_text (str): What you're looking for, written as a natural language search query.
        node_set (Optional[List[str]]): Additional node set identifiers for scoping the search.

    Returns:
        list: A list of search results matching the query.
    """
    logger.info(f"Searching cognee for: {query_text} with node_set: {node_set}")
    await _add_queue.join()

    if node_set:
        # Use NodeSet filtering when a node_set is provided
        result = await cognee.search(
            query_text=query_text, node_type=NodeSet, node_name=node_set, top_k=100
        )
    else:
        # Default search without node filtering
        result = await cognee.search(query_text, top_k=100)

    logger.info(f"Search results: {result}")
    return result


@tool(
    "add_tool",
    "Store information in the knowledge base for later retrieval",
    {"data": str},
)
async def add_tool(args):
    data = args["data"]
    logger.info(f'add_tool called with: "{data}"')
    result = await add_tool_impl(data)
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "search_tool",
    "Search and retrieve previously stored information from the knowledge base",
    {"query_text": str},
)
async def search_tool(args):
    query_text = args["query_text"]
    logger.info(f'search_tool called with: "{query_text}"')
    search_result = await search_tool_impl(query_text)
    return {"content": [{"type": "text", "text": f"Result: {search_result}"}]}


def sessionised_tool(user_id: str):
    """
    Decorator factory that creates a decorator to add user_id to tool calls.

    Args:
        user_id (str): The user session ID to bind to the tool

    Returns:
        A decorator that modifies tools to use the specific user's session
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"Using tool {func.__name__} with user_id: {user_id}")
            # Inject user_id for tools that support it
            if func.__name__ in ["add_tool_impl", "search_tool_impl"]:
                kwargs["node_set"] = [user_id]
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _create_sessionized_add_tool(session_decorator):
    """Create a sessionized add_tool with the @tool decorator."""
    sessionized_impl = session_decorator(add_tool_impl)

    @tool(
        "add_tool",
        "Store information in the knowledge base for later retrieval",
        {"data": str},
    )
    async def sessionized_add_tool(args):
        data = args["data"]
        logger.info(f'sessionized add_tool called with: "{data}"')
        result = await sessionized_impl(data)
        return {"content": [{"type": "text", "text": result}]}

    return sessionized_add_tool


def _create_sessionized_search_tool(session_decorator):
    """Create a sessionized search_tool with the @tool decorator."""
    sessionized_impl = session_decorator(search_tool_impl)

    @tool(
        "search_tool",
        "Search and retrieve previously stored information from the knowledge base",
        {"query_text": str},
    )
    async def sessionized_search_tool(args):
        query_text = args["query_text"]
        logger.info(f'sessionized search_tool called with: "{query_text}"')
        search_result = await sessionized_impl(query_text)
        return {"content": [{"type": "text", "text": f"Result: {search_result}"}]}

    return sessionized_search_tool


def get_sessionized_cognee_tools(session_id: Optional[str] = None) -> list:
    """
    Returns a list of cognee tools sessionized for a specific user.

    This function creates tools that are bound to a specific session ID,
    enabling session isolation where different users' data is kept separate.

    Args:
        session_id (str, optional): The session ID to bind to all tools.
                                    If None, a UUID-based ID is auto-generated.

    Returns:
        list: List of sessionized cognee tools [add_tool, search_tool]

    Example:
        >>> add_tool, search_tool = get_sessionized_cognee_tools("user-123")
        >>> # These tools will only access data from the "user-123" session
    """
    if session_id is None:
        import uuid

        uid = str(uuid.uuid4())
        session_id = f"cognee-test-user-{uid}"

    session_decorator = sessionised_tool(session_id)

    sessionized_add_tool = _create_sessionized_add_tool(session_decorator)
    sessionized_search_tool = _create_sessionized_search_tool(session_decorator)

    logger.info(f"Initialized session with session_id = {session_id}")

    return [
        sessionized_add_tool,
        sessionized_search_tool,
    ]
