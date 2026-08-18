import json
import re

from backend.models.provider import ModelProvider, ChatMessage
from backend.agents.tools.file_tools import FileTools


SYSTEM_PROMPT = """You are a coding agent. You have these tools:

- list_files(subdir=".") -> list of file paths
- read_file(path) -> file contents
- search_code(pattern) -> matching lines
- write_file(path, content) -> creates/overwrites a file
- edit_file(path, old_text, new_text) -> replaces old_text with new_text in a file

CRITICAL RULES:
1. Base every conclusion strictly on the ACTUAL CONTENT returned by tool results.
   Never guess or assume what a file contains — only trust what a tool result showed you.
2. If a tool result already contains the answer to the task, use it directly. Do not
   run additional tool calls "just to be sure" if you already have the information.
3. Before answering "done", re-read the most recent tool results in this conversation
   and confirm your summary directly matches what they showed.

Respond with EXACTLY ONE JSON object per turn, nothing else, no markdown fences:

To call a tool:
{"action": "tool_call", "tool": "<tool_name>", "args": {...}}

When the task is fully done:
{"action": "done", "summary": "<what you did, referencing the exact evidence from tool results>"}

Always respond with valid JSON only."""


class AgentStep:
    def __init__(self, kind: str, detail: str):
        self.kind = kind  # "tool_call" | "tool_result" | "done" | "error"
        self.detail = detail

    def __repr__(self):
        return f"[{self.kind}] {self.detail}"


class CodingAgent:
    def __init__(self, model: ModelProvider, tools: FileTools, max_iterations: int = 8):
        self.model = model
        self.tools = tools
        self.max_iterations = max_iterations

    def _extract_json(self, text: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        return json.loads(cleaned)

    def _call_tool(self, tool: str, args: dict) -> str:
        fn = getattr(self.tools, tool, None)
        if fn is None:
            raise ValueError(f"Unknown tool: {tool}")
        result = fn(**args)
        return json.dumps(result) if not isinstance(result, str) else result

    async def run(self, task: str) -> list[AgentStep]:
        history = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=task),
        ]
        steps: list[AgentStep] = []

        for i in range(self.max_iterations):
            result = await self.model.generate(history)
            raw = result.text

            try:
                parsed = self._extract_json(raw)
            except (json.JSONDecodeError, ValueError) as e:
                steps.append(AgentStep("error", f"Model did not return valid JSON: {e} | raw: {raw[:200]}"))
                break

            if parsed.get("action") == "done":
                steps.append(AgentStep("done", parsed.get("summary", "")))
                break

            elif parsed.get("action") == "tool_call":
                tool = parsed.get("tool")
                args = parsed.get("args", {})
                steps.append(AgentStep("tool_call", f"{tool}({args})"))

                try:
                    tool_result = self._call_tool(tool, args)
                except Exception as e:
                    tool_result = f"ERROR: {e}"

                steps.append(AgentStep("tool_result", tool_result[:500]))

                history.append(ChatMessage(role="assistant", content=raw))
                history.append(ChatMessage(role="user", content=f"Tool result: {tool_result}\n\nRemember: base your next step strictly on this actual content."))

            else:
                steps.append(AgentStep("error", f"Unrecognized action in model response: {raw[:200]}"))
                break
        else:
            steps.append(AgentStep("error", f"Max iterations ({self.max_iterations}) reached without completion"))

        return steps
