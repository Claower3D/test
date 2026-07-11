import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

# We'll redefine THEME to match the modern dashboard CSS.
modern_theme = """THEME = '''<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0f1015;
  --panel: #15161c;
  --border: #23242f;
  --accent: #16c79a;
  --blue: #3d8bd9;
  --red: #ff5d5d;
  --yellow: #e0b341;
  --muted: #8b8b99;
  --text: #ffffff;
}
html, body {
  margin: 0; padding: 0;
  background: var(--bg); color: var(--muted);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
h2 {
  font-family: 'Montserrat', sans-serif;
  color: #fff;
  font-size: 22px;
  text-transform: uppercase;
  margin: 0 0 16px 0;
}
.kpi {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.kpi > div {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.kpi > div > b {
  font-size: 24px;
  color: #fff;
  font-family: 'Montserrat', sans-serif;
}
.rule, .muted { color: var(--muted); margin-bottom: 12px; font-size: 12px; }
.bar {
  display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px;
}
select, input, button {
  background: var(--panel);
  border: 1px solid var(--border);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  outline: none;
}
select:hover, button:hover {
  border-color: var(--accent);
}
button {
  background: var(--accent);
  color: #000;
  font-weight: 600;
  cursor: pointer;
  border: none;
}
button:hover { background: #12a680; }
table {
  width: 100%; border-collapse: separate; border-spacing: 0;
  background: var(--panel);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border);
}
th, td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
th {
  background: rgba(0,0,0,0.2);
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 600;
}
td { color: #fff; }
tr:hover td { background: rgba(255,255,255,0.03); }
tr:last-child td { border-bottom: none; }
.num { text-align: right; }
.nav-links {
  display: flex; gap: 8px; margin-bottom: 24px;
}
.nav-links a {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
}
.nav-links a.active {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}
</style>
<div style="max-width: 1400px; margin: 0 auto; padding: 24px;">
'''"""

# Replace the existing THEME block
content = re.sub(r'THEME = """[\s\S]*?(?="""\n)"*"""', modern_theme, content)

# I should also patch weekly_page header to add navigation tabs
old_header = "\"<h2 style='margin:0'>📅 Еженедельная статистика <span style='font-size:14px;font-weight:400;color:var(--muted)'>&nbsp;<a href='/'>🏠 Главная</a> · <a href='/stats'>📊 Вчерашняя</a></span></h2>\""
new_header = '''"<div class='nav-links'>
    <a href='/'>Главная</a>
    <a href='/stats'>Вчерашняя</a>
    <a href='/weekly' class='active'>Еженедельная</a>
    <a href='/dashboard'>Дашборд</a>
    <a href='/bots'>Боты</a>
</div>
<h2 style='margin:0'>Еженедельная статистика</h2>"'''
content = content.replace(old_header, new_header.replace('\n', ''))

# Patch STATS header
old_stats_header = "\"<h2>Вчерашняя статистика (сохранено) <span style='font-size:14px;font-weight:400'>&nbsp;<a href='/'>🏠 Главная</a> · <a href='/weekly'>📅 Еженедельная</a></span></h2>\""
new_stats_header = '''"<div class='nav-links'>
    <a href='/'>Главная</a>
    <a href='/stats' class='active'>Вчерашняя</a>
    <a href='/weekly'>Еженедельная</a>
    <a href='/dashboard'>Дашборд</a>
    <a href='/bots'>Боты</a>
</div>
<h2 style='margin:0'>Вчерашняя статистика</h2>"'''
content = content.replace(old_stats_header, new_stats_header.replace('\n', ''))


with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated theme!")
