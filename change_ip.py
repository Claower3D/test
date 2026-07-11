import os
import time
import requests

def reset_router_ip():
    """
    Универсальный скрипт для смены IP через перезагрузку роутера.
    РАБОТАЕТ ТОЛЬКО ЕСЛИ У ВАС РОУТЕР ИЛИ МОДЕМ ДОСТУПЕН ПО АДРЕСУ 192.168.1.1 или 192.168.0.1
    """
    print("[IP_CHANGER] Начинаем смену IP-адреса...")
    
    # Чтобы боты не вылетали с ошибками интернета, говорим им встать на паузу
    try:
        import bots.interaction
        bots.interaction.system_paused_for_ip_change = True
        print("[IP_CHANGER] Боты поставлены на паузу.")
    except Exception as e:
        pass
        
    try:
        # Для Казахтелекома и большинства роутеров Zyxel/Huawei
        # Простейший вариант - отправить запрос на перезагрузку (требует логин/пароль)
        # Так как мы не знаем ваш точный роутер, вот шаблон, который нужно будет настроить:
        
        # РОУТЕР ПО УМОЛЧАНИЮ (замените admin:admin на свои)
        ROUTER_IP = "192.168.1.1" 
        USER = "admin"
        PASS = "admin"
        
        # Пример для TP-Link
        # url = f"http://{USER}:{PASS}@{ROUTER_IP}/userRpm/SysRebootRpm.htm?Reboot=Reboot"
        # requests.get(url, timeout=5)
        
        # Поскольку у нас нет точных данных вашего роутера, мы просто ждем 15 секунд 
        # (Имитация ручного выдергивания шнура)
        print("[IP_CHANGER] Пожалуйста, выдерните кабель/нажмите 'Режим полета' и включите обратно...")
        time.sleep(15)
        print("[IP_CHANGER] Ожидание завершено, IP должен быть обновлен.")
        
    except Exception as e:
        print("[IP_CHANGER] Ошибка смены IP:", e)
    finally:
        try:
            import bots.interaction
            bots.interaction.system_paused_for_ip_change = False
            print("[IP_CHANGER] Боты сняты с паузы и продолжают работу!")
        except Exception:
            pass

if __name__ == "__main__":
    reset_router_ip()
