#!/usr/bin/env python3
"""
Base Agent Class
Foundation for all agents in the agent-based architecture
"""

import json
import logging
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from agents.agent_prompts import (
    CHAMPIONS_AND_BOSSES,
    CHARACTER_BASE_T3RN,
    CHARACTER_BASE_T4RN,
    CONTENT_RESTRICTIONS,
    GAME_CONTEXT,
    MOBILE_FORMAT,
    QUESTION_ANALYZER_INITIAL_TASK,
    QUESTION_ANALYZER_RULES,
    T3RN_INTRODUCTION,
    TOOL_RESULTS_ANALYSIS,
)
from channel_logger import ChannelLogger
from session import Session


def chat_completion_to_content_str(content: ChatCompletionMessageParam) -> str:
    content_str = content.get("content", None)

    if content_str is None:
        return ""

    if isinstance(content_str, str):
        return content_str

    return str("".join([str(x) for x in content_str]))


def format_toolcall(tool_call: Function):
    """Format a tool call for logging."""
    return f"{tool_call.name}({tool_call.arguments})"


def chat_response_toolcalls(
    response: "ChatCompletion",
) -> List[ChatCompletionMessageToolCall]:
    if not response.choices:
        return []

    message = response.choices[0].message

    if not message.tool_calls:
        return []

    return message.tool_calls


def chat_response_to_str(response: "ChatCompletion", content_only=False) -> str:
    choices = response.choices

    if not choices:
        return ""

    message = choices[0].message

    if message.content is not None:
        return message.content

    if message.refusal is not None:
        return message.refusal

    if content_only:
        return ""

    if message.tool_calls:
        output = []

        for tool_call in message.tool_calls:
            output.append(format_toolcall(tool_call.function))

        return "\n".join(output)

    return ""


logger = logging.getLogger("Base Agent")


@dataclass
class AgentResult:
    messages: List[ChatCompletionMessageParam]
    error_content: str = ""

    @property
    def final_answer(self) -> Optional[str]:
        """Return content of the last assistant message, if any."""
        if self.messages[-1]["role"] == "assistant":
            return chat_completion_to_content_str(self.messages[-1])

        return None

    @property
    def user_message(self) -> str:
        """Return content of the last user message, if any."""
        for msg in reversed(self.messages):
            if msg["role"] == "user":
                return chat_completion_to_content_str(msg)
        return ""


class Agent(ABC):
    def __init__(self, session: "Session", channel_logger: "ChannelLogger"):
        self.session_data: "Session" = session
        self.channel_logger: "ChannelLogger" = channel_logger

        if self.session_data.memory_manager is None:
            raise ValueError("Session must have a memory manager initialized")

        self.memory_manager = self.session_data.memory_manager

    @abstractmethod
    def get_system_prompt(
        self,
    ) -> str:
        """Get system prompt for this agent"""
        pass

    @abstractmethod
    def execute(self, context: str) -> AgentResult:
        """Execute the agent with given context"""
        pass

    def _log_state(
        self,
        messages: List["ChatCompletionMessageParam"] | List[Any],
        response: str | None = None,
    ):
        try:
            agent_name = self.__class__.__name__

            session = self.session_data
            mm = session.memory_manager

            short_messages = [
                {
                    **message,
                    "content": textwrap.shorten(chat_completion_to_content_str(message), width=500),
                }
                for message in messages
            ]

            state_log = {
                "agent": agent_name,
                "session_id": session.session_id,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "channel": session.channel,
                "message_id": session.message_id,
                "action_id": session.action_id,
                "text_snippet": (session.user_message[:100] + "...")
                if session.user_message and len(session.user_message) > 100
                else session.user_message,
                "memory_summary": {"llm_summarization_count": mm.llm_summarization_count} if mm else "No memory manager",
                "messages": messages,
                "json_data_keys": None,  # TODO GAME STATE PARSER
                "response": response,
            }

            pretty_log = f"""
=== AGENT STATE DUMP ===
Agent: {agent_name}
Session ID: {state_log["session_id"]}
Created At: {state_log["created_at"]}
Last Activity: {state_log["last_activity"]}
Action ID: {state_log["action_id"]}
Channel: {state_log["channel"]} | Msg ID: {state_log["message_id"]}
Text Snippet: {state_log["text_snippet"]}

=== Messages ===
{json.dumps(short_messages, indent=2)}
=== LLM Response ===
{state_log["response"] if state_log["response"] else "No response generated"}
=== JSON DATA ===
""".strip()

            self.channel_logger.log_to_prompts(pretty_log)

        except Exception as e:
            self.channel_logger.log_to_logs(f"❌ Failed to log state: {str(e)}")

    def build_prompt(self, *fragments) -> str:
        fragment_map = {
            "CHARACTER_BASE_T3RN": CHARACTER_BASE_T3RN,
            "CHARACTER_BASE_T4RN": CHARACTER_BASE_T4RN,
            "GAME_CONTEXT": GAME_CONTEXT,
            "CONTENT_RESTRICTIONS": CONTENT_RESTRICTIONS,
            "T3RN_INTRODUCTION": T3RN_INTRODUCTION,
            "MOBILE_FORMAT": MOBILE_FORMAT,
            "QUESTION_ANALYZER_INITIAL_TASK": QUESTION_ANALYZER_INITIAL_TASK,
            "CHAMPIONS_AND_BOSSES": CHAMPIONS_AND_BOSSES,
            "QUESTION_ANALYZER_RULES": QUESTION_ANALYZER_RULES,
            # "QUESTION_ANALYZER_TOOLS": QUESTION_ANALYZER_TOOLS,
            "TOOL_RESULTS_ANALYSIS": TOOL_RESULTS_ANALYSIS,
        }

        prompt_parts = []
        for fragment in fragments:
            if isinstance(fragment, str):
                if fragment in fragment_map:
                    prompt_parts.append(fragment_map[fragment])
                else:
                    prompt_parts.append(fragment)
            else:
                # Convert to string
                prompt_parts.append(str(fragment))

        return "\n\n".join(prompt_parts)

    def get_config(self) -> Dict[str, Any]:
        return {"class_name": self.__class__.__name__}
