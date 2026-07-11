import re

# 1. Update bots/interaction.py to track statistics
with open("bots/interaction.py", "r", encoding="utf-8") as f:
    bot_code = f.read()

if "def get_today_stats()" not in bot_code:
    stats_logic = """
import json, datetime

def record_stat(status):
    today = datetime.date.today().isoformat()
    try:
        if os.path.exists("static/live/stats.json"):
            with open("static/live/stats.json", "r") as f:
                st = json.load(f)
        else:
            st = {}
    except:
        st = {}
    
    if today not in st:
        st[today] = {"runs": 0, "success": 0, "errors": 0}
        
    st[today]["runs"] += 1
    if status == "success":
        st[today]["success"] += 1
    else:
        st[today]["errors"] += 1
        
    try:
        with open("static/live/stats.json", "w") as f:
            json.dump(st, f)
    except:
        pass

def get_today_stats():
    today = datetime.date.today().isoformat()
    try:
        if os.path.exists("static/live/stats.json"):
            with open("static/live/stats.json", "r") as f:
                st = json.load(f)
                return st.get(today, {"runs": 0, "success": 0, "errors": 0})
    except:
        pass
    return {"runs": 0, "success": 0, "errors": 0}
"""
    bot_code = stats_logic + bot_code
    
    # Record success/error
    bot_code = bot_code.replace('active_tasks[task_id]["status"] = "завершено успешно"', 'active_tasks[task_id]["status"] = "завершено успешно"\n            record_stat("success")')
    bot_code = bot_code.replace('active_tasks[task_id]["status"] = f"ошибка: {str(e)}"', 'active_tasks[task_id]["status"] = f"ошибка: {str(e)}"\n        record_stat("error")')

    with open("bots/interaction.py", "w", encoding="utf-8") as f:
        f.write(bot_code)

# 2. Update web.py to show stats in Dashboard
with open("web.py", "r", encoding="utf-8") as f:
    web_code = f.read()

# I will find DASHBOARD_HTML by looking for '<div class="grid-4">' and adding a 5th card or just changing grid-4 to grid-4 with 5 items (it will wrap naturally).
# Actually grid-4 uses auto-fit so it will wrap nicely to the next row.
if "{bot_stats_html}" not in web_code:
    # Insert the placeholder into DASHBOARD_HTML
    web_code = web_code.replace(
        '<div class="grid-4">',
        '<div class="grid-4">\n  {bot_stats_html}'
    )
    
    # Update custom_dashboard to generate bot_stats_html
    # Look for: replacements = {
    new_python = """
    try:
        import bots.interaction as bot
        bst = bot.get_today_stats()
        bot_runs = bst["runs"]
        bot_succ = bst["success"]
        bot_err = bst["errors"]
    except:
        bot_runs = bot_succ = bot_err = 0
        
    bot_stats_html = f'''<div class="card" style="border-color:var(--accent);">
    <div class="kpi-head"><span style="color:var(--accent);">Работа ботов (Сегодня)</span><div class="kpi-icon" style="background:var(--accent);color:#000">🤖</div></div>
    <div class="kpi-val">{bot_runs}</div>
    <div class="kpi-trend" style="color:var(--muted)">Успешных: {bot_succ} | Ошибок: {bot_err}</div>
  </div>'''
  
    replacements = {"""
    
    web_code = web_code.replace('    replacements = {', new_python)
    web_code = web_code.replace('"{total_views}": total_views,', '"{bot_stats_html}": bot_stats_html,\n        "{total_views}": total_views,')

    with open("web.py", "w", encoding="utf-8") as f:
        f.write(web_code)

print("Added Bot Stats to Dashboard")
