"""Прогон по всем авторизованным аккаунтам."""
import collector, cpl
from auth import _load

def accounts():
    return list(_load().keys())

def run_all():
    result = {}
    for acc in accounts():
        try:
            collector.collect(acc)
            result[acc] = cpl.cpl_report(acc)
        except Exception as e:
            result[acc] = {"error": str(e)}
    return result
