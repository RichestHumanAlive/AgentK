from typing import Literal
from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

import utils

system_prompt = """You are tool_maker, a ReAct agent that develops LangChain tools for other agents.

Your responses must be either an inner monologue or a message to the user.
If you are intending to call tools, then your response must be a succinct summary of your inner thoughts.
Else, your response is a message the user.  

You approach your given task this way:
1. Write the tool implementation and tests to disk.
2. Verify the tests pass.
3. Confirm the tool is complete with its name and a succinct description of its purpose.

Further guidance:

Tools go in the `tools` directory.
You have access to all the tools.
The name of the tool file and the function must be the same.
When writing a tool, make sure to include a docstring on the function that succintly describes what the tool does.
Always include a test file that verifies the intended behaviour of the tool.
Use write_to_file tool to write the tool and test to disk.
Verify the tests pass by running the shell command `python -m unittest path_to_test_file`.
The test must pass before the tool is considered complete.

Example:
tools/add_smiley_face.py
```
from langchain_core.tools import tool

@tool
def add_smiley_face(text: str) -> str:
    \"\"\"Generates an asccii face.\"\"\"
    return text + " :)"
```

tests/tools/test_add_smiley_face.py
```
import unittest

from tools import add_smiley_face

class TestAddSmileyFace(unittest.TestCase):
    def test_that_it_adds_a_smiley_to_text(self):
        self.assertEqual(add_smiley_face.add_smiley_face.invoke({ "text": "hello" }), "hello :)")

if __name__ == '__main__':
    unittest.main()
```

Another example:
tools/get_smiley.py
```
from langchain_core.tools import tool

@tool
def get_smiley() -> str:
    \"\"\"Get a smiley.\"\"\"
    return ":)"
```

tests/tools/test_get_smiley.py
```
import unittest

from tools import get_smiley

class TestGetSmiley(unittest.TestCase):
    def test_that_it_returns_smiley(self):
        self.assertEqual(get_smiley.get_smiley.invoke({}), ":)")

if __name__ == '__main__':
    unittest.main()
```
"""
    
tools = utils.all_tool_functions()

def reasoning(state: MessagesState):
    print()
    print("tool_maker is thinking...")
    messages = state['messages']
    tooled_up_model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools)
    response = tooled_up_model.invoke(messages)
    return {"messages": [response]}

def check_for_tool_calls(state: MessagesState) -> Literal["tools", END]:
    messages = state['messages']
    last_message = messages[-1]
    
    if last_message.tool_calls:
        print("tool_maker thought this:")
        print(last_message.content)
        print()
        print("tool_maker is acting by invoking these tools:")
        print([tool_call["name"] for tool_call in last_message.tool_calls])
        return "tools"
    
    return END

acting = ToolNode(tools)

workflow = StateGraph(MessagesState)
workflow.add_node("reasoning", reasoning)
workflow.add_node("tools", acting)
workflow.set_entry_point("reasoning")
workflow.add_conditional_edges(
    "reasoning",
    check_for_tool_calls,
)
workflow.add_edge("tools", 'reasoning')
graph = workflow.compile()


def tool_maker(task: str) -> str:
    """Creates a new tool that langchain agents can use."""
    return graph.invoke(
        {"messages": [SystemMessage(system_prompt), HumanMessage(task)]}
    )