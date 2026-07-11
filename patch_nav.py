import re

with open('web.py', 'r', encoding='utf-8') as f:
    text = f.read()

# For nav-pills blocks
text = re.sub(r'(<a href="/bots2?"[^>]*>.*?</a>\s*)</div>\s*</div>', r'\1  <a href="/logs">📜 Логи</a>\n  </div>\n</div>', text)

with open('web.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Patched nav-pills!')
