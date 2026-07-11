#!/usr/bin/env python3
"""CLI-оркестратор пайплайна OLX. Запускай: python run.py <команда>"""
import sys, json
import config
import auth, collector, cpl, rules, storage

def cmd_auth(account="default"):
    if not config.CLIENT_ID:
        print("Сначала впиши OLX_CLIENT_ID/SECRET в .env"); return
    url = auth.build_authorize_url()
    print("\n1) Открой ссылку в браузере и подтверди доступ (это ТВОЁ действие):\n")
    print("   ", url)
    print("\n2) После редиректа скопируй параметр ?code=... из адресной строки.")
    code = input("\nВставь сюда code: ").strip()
    tok = auth.exchange_code(code, account)
    print("OK, токен получен. Скоупы:", tok.get("scope"))

def cmd_collect(account="default"):
    collector.collect(account)

def cmd_cpl(account="default"):
    print(json.dumps(cpl.cpl_report(account), ensure_ascii=False, indent=2))

def cmd_rules(account="default"):
    print("Кандидаты на оптимизацию:")
    print(json.dumps(rules.optimization_candidates(account), ensure_ascii=False, indent=2))
    print("\nПлан автоподнятия (DRY-RUN, ничего не списывается):")
    print(json.dumps(rules.promote(account, apply=False), ensure_ascii=False, indent=2))

def cmd_daily(account="default"):
    storage.init()
    collector.collect(account)
    print(json.dumps(cpl.cpl_report(account), ensure_ascii=False, indent=2))
    print(json.dumps(rules.promote(account, apply=False), ensure_ascii=False, indent=2))

CMDS = {"auth": cmd_auth, "collect": cmd_collect, "cpl": cmd_cpl,
        "rules": cmd_rules, "daily": cmd_daily}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print("Команды:", ", ".join(CMDS)); sys.exit(1)
    acc = sys.argv[2] if len(sys.argv) > 2 else "default"
    CMDS[sys.argv[1]](acc)
