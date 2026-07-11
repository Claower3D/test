import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("return BOTS_HTML.format(ads_html=ads_html)", "return BOTS_HTML.replace('{ads_html}', ads_html)")

with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Format fixed")
