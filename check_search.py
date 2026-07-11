with open('olx_search.html', 'r', encoding='utf-8') as f:
    html = f.read()
import re
links = re.findall(r'href="([^"]*)"', html)
for link in links:
    if '/d/obyavlenie/' in link:
        print(link)
