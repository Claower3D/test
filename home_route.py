def home():
    accs = auth._load()
    rows = "".join(
        f"<div class=acc>✓ {a}"
        f"<span style='float:right'>"
        f"<button type=button onclick=\"renameAcc('{a}')\" style='padding:3px 11px;font-size:12px'>переименовать</button> "
        f"<form style='display:inline' method=post action=/delete>"
        f"<input type=hidden name=account value='{a}'>"
        f"<button style='padding:3px 11px;font-size:12px;background:#ff5d5d;border-color:#ff5d5d'>удалить</button>"
        f"</form></span></div>" for a in accs) or "<i>пока нет</i>"
    return PAGE.format(n=len(accs), accs=rows, theme=THEME) + SCRIPT