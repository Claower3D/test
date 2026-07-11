import ast
with open("web.py", "r", encoding="utf-8") as f:
    source = f.read()

tree = ast.parse(source)
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in ["weekly_page"]:
        with open("weekly_page.py", "w", encoding="utf-8") as out:
            out.write(ast.get_source_segment(source, node))
