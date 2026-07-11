import web
import re
m = re.search(r'<div class="nav-pills">.*?</div>', web.DASHBOARD_HTML, re.DOTALL)
print(m.group(0))
