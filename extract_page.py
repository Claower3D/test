import ast
with open("web.py", "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'PAGE':
        with open("PAGE.txt", "w", encoding="utf-8") as out:
            # Need to get value, it's a constant
            out.write(node.value.value)
