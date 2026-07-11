import re
with open('web.py', 'r', encoding='utf-8') as f:
    text = f.read()
with open('out2.txt', 'w', encoding='utf-8') as out:
    for i, m in enumerate(re.finditer(r'<div class="nav-pills">.*?</div>', text, re.DOTALL)):
        out.write(f'Block {i}:\n')
        out.write(m.group(0) + '\n\n')
