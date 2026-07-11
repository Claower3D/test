import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

# I will find the custom_dashboard function and replace the formatting logic
# The easiest way is to rewrite the return statement of custom_dashboard.

def replacer(match):
    return """
    replacements = {
        "{total_views}": total_views,
        "{trend_views_class}": trend_views_class,
        "{trend_views_str}": trend_views_str,
        "{conv_pct}": f"{conv_pct:.1f}",
        "{total_leads}": total_leads,
        "{active_ads}": active_ads,
        "{strong_ads}": strong_ads,
        "{phones}": total_phones,
        "{phones_pct}": f"{phones_pct:.1f}",
        "{chats}": total_chats,
        "{chats_pct}": f"{chats_pct:.1f}",
        "{top_ads_html}": top_ads_html,
        "{chart_labels}": json.dumps(chart_labels),
        "{chart_data}": json.dumps(chart_data)
    }
    out = DASHBOARD_HTML
    for k, v in replacements.items():
        out = out.replace(k, str(v))
    return out
"""

# Let's just find the custom_dashboard definition and replace its return statement entirely.
# The original script I made replaced `return DASHBOARD_HTML.format(` ... with `replacements = dict(...`
# Since it probably made a mess, let me just reconstruct the end of custom_dashboard.

import ast

# Better to just use regex to find the end of custom_dashboard
content = re.sub(
    r"return DASHBOARD_HTML\.format\([\s\S]*?chart_data=json\.dumps\(chart_data\)\s*\)",
    replacer(None).strip(),
    content
)
content = re.sub(
    r"replacements = dict\([\s\S]*?return out",
    replacer(None).strip(),
    content
)

with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fix applied")
