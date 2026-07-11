import re
with open('web.py', 'r', encoding='utf-8') as f:
    text = f.read()

matches = re.findall(r'<div class="nav-pills">.*?</div>\s*</div>', text, re.DOTALL)
for i, m in enumerate(matches):
    print(f'--- Block {i} ---')
    print(m)
