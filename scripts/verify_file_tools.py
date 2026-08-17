from backend.agents.tools.file_tools import FileTools

tools = FileTools(root="/home/msi/agent-test-repo")

print("list_files() ->", tools.list_files())
print()
print("read_file('calculator.py') ->")
print(tools.read_file("calculator.py"))
print()
print("search_code('def') ->", tools.search_code("def"))
print()

try:
    tools.read_file("../../../etc/passwd")
    print("SECURITY FAILURE: path escape was not blocked!")
except PermissionError as e:
    print(f"Path escape correctly blocked -> {e}")
