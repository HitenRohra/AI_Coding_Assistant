import json
import requests
from dotenv import load_dotenv
from openai import OpenAI
import os
import subprocess


load_dotenv()
client = OpenAI()

def run_command(command):
    if isinstance(command, dict) and "command" in command:
        command = command["command"]
    return os.system(command)

def write_file(input):
    filepath = input.get("filepath")
    content = input.get("content")
    with open(filepath, "w") as f:
        f.write(content)
    return f"File {filepath} created/updated."

def read_file(input):
    filepath = input.get("filepath")
    with open(filepath, "r") as f:
        return f.read()

def append_file(input):
    filepath = input.get("filepath")
    content = input.get("content")
    with open(filepath, "a") as f:
        f.write(content)
    return f"Content appended to {filepath}."

def list_dir(input):
    path = input.get("path", ".")
    return os.listdir(path)

def make_dir(input):
    path = input.get("path")
    os.makedirs(path, exist_ok=True)
    return f"Directory '{path}' created."

def install_package(input):
    command = input.get("command")
    return os.system(command)

def git_command(params):
    command = params.get("command")

    # ❌ Dangerous command blacklist
    blocked_keywords = ["reset", "clean", "rebase", "push --force", "checkout --", "rm -rf", "cherry-pick", "reflog", "stash drop"]
    if any(bad in command.lower() for bad in blocked_keywords):
        return f"[❌] Unsafe git command blocked: '{command}'"

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"[ERROR] {str(e)}"

avaiable_tools = {
    "run_command": {
        "fn": run_command,
        "description": "Executes a shell command on the system."
    },
    "write_file": {
        "fn": write_file,
        "description": "Create or overwrite a file with content."
    },
    "read_file": {
        "fn": read_file,
        "description": "Reads content from a file."
    },
    "append_file": {
        "fn": append_file,
        "description": "Appends content to a file."
    },
    "list_dir": {
        "fn": list_dir,
        "description": "List contents of a directory."
    },
    "make_dir": {
        "fn": make_dir,
        "description": "Create a directory at the given path."
    },
    "install_package": {
        "fn": install_package,
        "description": "Install packages using system package manager."
    },
    "git_command" : {
    "fn": git_command,
    "description": "Runs safe git commands like init, clone, add, commit, status, etc."
    },
}

system_prompt = f"""
    You are a helpful AI coding Assistant who is specialized in resolving user queries and coding.
    You work in start, plan, action, observe mode.
    For the given user query and available tools, plan the step-by-step execution. Based on the planning,
    select the relevant tool from the available tools, and based on the tool selection, you perform an action to call the tool.
    Wait for the observation and based on the observation from the tool call, resolve the user query.

    You also support `git` commands using the `git_command` tool.

    Examples of allowed commands:
    - git init
    - git status
    - git add .
    - git commit -m "initial commit"
    - git clone https://github.com/user/repo.git
    - git branch

    Rules:
    - Follow the Output JSON Format.
    - Always perform one step at a time and wait for the next input.
    - Carefully analyze the user query.

    Output JSON Format:
    {{
        "step": "string",
        "content": "string",
        "function": "The name of function if the step is action",
        "input": "The input parameter for the function",
    }}

    Available Tools:
    - run_command: Executes a shell command on the system.
    - write_file: Create or overwrite a file with content.
    - read_file: Reads content from a file.
    - append_file: Appends content to a file.
    - list_dir: List contents of a directory.
    - make_dir: Create a directory at the given path.
    - install_package: Install packages using system package manager.

    Example:
    User Query: Write a python script to add two numbers.
    Output: {{ "step": "plan", "content": "The user wants to create a python file to add two numbers" }}
    Output: {{ "step": "plan", "content": "First, I will create the file using write_file" }}
    Output: {{ "step": "action", "function": "write_file", "input": {{ "filepath": "add.py", "content": "a = int(input('Enter first number: '))\\nb = int(input('Enter second number: '))\\nprint('Sum is:', a + b)" }} }}
    Output: {{ "step": "output", "output": "File add.py created/updated." }}
"""

messages = [
    { "role": "system", "content": system_prompt }
]

while True:
    user_query = input('> ')
    messages.append({ "role": "user", "content": user_query })

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=messages
        )

        parsed_output = json.loads(response.choices[0].message.content)
        messages.append({ "role": "assistant", "content": json.dumps(parsed_output) })

        if parsed_output.get("step") == "plan":
            print(f"🧠: {parsed_output.get("content")}")
            continue

        if parsed_output.get("step") == "action":
            tool_name = parsed_output.get("function")
            tool_input = parsed_output.get("input")

            if avaiable_tools.get(tool_name, False) != False:
                output = avaiable_tools[tool_name].get("fn")(tool_input)
                messages.append({ "role": "assistant", "content": json.dumps({ "step": "observe", "output": output }) })
                continue

        if parsed_output.get("step") == "output":
            print(f"🤖: {parsed_output.get("content")}")
            break
