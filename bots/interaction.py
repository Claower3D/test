
import json, datetime, threading

stats_lock = threading.Lock()

def encode_olx_id(num_str):
    try:
        base62 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        num = int(num_str)
        if num == 0: return '0'
        res = ''
        while num > 0:
            res = base62[num % 62] + res
            num //= 62
        return "ID" + res
    except:
        return num_str

def record_stat(status, url=None, ip=None, actions_completed=None, traffic_mb=0.0):
    today = datetime.date.today().isoformat()
    
    with stats_lock:
        try:
            if os.path.exists("static/live/stats.json"):
                with open("static/live/stats.json", "r") as f:
                    st = json.load(f)
            else:
                st = {}
        except:
            st = {}
        
        if today not in st:
            st[today] = {"runs": 0, "success": 0, "errors": 0, "warnings": 0, "urls": {}, "traffic_mb": 0.0}
            
        if "traffic_mb" not in st[today]:
            st[today]["traffic_mb"] = 0.0
            
        if "urls" not in st[today]:
            st[today]["urls"] = {}
            
        st[today]["runs"] += 1
        st[today]["traffic_mb"] += traffic_mb
        
        if status == "success":
            st[today]["success"] += 1
        elif status == "warning":
            st[today]["warnings"] = st[today].get("warnings", 0) + 1
        else:
            st[today]["errors"] += 1
            
        if url:
            if url not in st[today]["urls"]:
                st[today]["urls"][url] = {"runs": 0, "success": 0, "errors": 0, "warnings": 0, "ips": [], "actions": {"scroll": 0, "phone": 0, "chat": 0}}
            
            # Ensure ips list exists for backwards compatibility
            if "ips" not in st[today]["urls"][url]:
                st[today]["urls"][url]["ips"] = []
                
            # Ensure actions exists for backwards compatibility
            if "actions" not in st[today]["urls"][url]:
                st[today]["urls"][url]["actions"] = {"scroll": 0, "phone": 0, "chat": 0}
                
            st[today]["urls"][url]["runs"] += 1
            if status == "success":
                st[today]["urls"][url]["success"] += 1
            elif status == "warning":
                st[today]["urls"][url]["warnings"] = st[today]["urls"][url].get("warnings", 0) + 1
            else:
                st[today]["urls"][url]["errors"] += 1
                
            if ip and ip not in st[today]["urls"][url]["ips"]:
                st[today]["urls"][url]["ips"].append(ip)
                
            if actions_completed:
                for k, v in actions_completed.items():
                    if k in st[today]["urls"][url]["actions"]:
                        st[today]["urls"][url]["actions"][k] += v
                
        try:
            with open("static/live/stats.json", "w") as f:
                json.dump(st, f)
        except:
            pass

def get_stats_for_date(date_str=None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    with stats_lock:
        try:
            if os.path.exists("static/live/stats.json"):
                with open("static/live/stats.json", "r") as f:
                    st = json.load(f)
                    return st.get(date_str, {"runs": 0, "success": 0, "errors": 0, "warnings": 0})
        except:
            pass
    return {"runs": 0, "success": 0, "errors": 0, "warnings": 0}

def get_all_stat_dates():
    with stats_lock:
        try:
            if os.path.exists("static/live/stats.json"):
                with open("static/live/stats.json", "r") as f:
                    st = json.load(f)
                    return sorted(list(st.keys()), reverse=True)
        except:
            pass
    return [datetime.date.today().isoformat()]
import time
import random
import threading
import asyncio
import os
from playwright.async_api import async_playwright

def parse_proxy_string(proxy_str):
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None
        
    protocol = "http"
    if proxy_str.startswith("socks5://"):
        protocol = "socks5"
        proxy_str = proxy_str[9:]
    elif proxy_str.startswith("socks4://"):
        protocol = "socks4"
        proxy_str = proxy_str[9:]
    elif proxy_str.startswith("http://"):
        protocol = "http"
        proxy_str = proxy_str[7:]
    elif proxy_str.startswith("https://"):
        protocol = "http"
        proxy_str = proxy_str[8:]
        
    server = ""
    username = ""
    password = ""
    
    if "@" in proxy_str:
        auth_part, ip_part = proxy_str.split("@", 1)
        server = f"{protocol}://{ip_part}"
        if ":" in auth_part:
            username, password = auth_part.split(":", 1)
        else:
            username = auth_part
    elif proxy_str.count(":") == 3:
        parts = proxy_str.split(":")
        server = f"{protocol}://{parts[0]}:{parts[1]}"
        username = parts[2]
        password = parts[3]
    else:
        server = f"{protocol}://{proxy_str}"
        
    res = {"server": server}
    if username:
        res["username"] = username
    if password:
        res["password"] = password
    return res

_proxy_history = []

def get_random_kz_proxy(exclude_servers=None, use_free=True, strict=False):
    import urllib.request
    import random
    import os
    import time
    
    global _proxy_history
    if exclude_servers is None:
        exclude_servers = set()
        
    proxies = []
    
    # 1. Проверяем наличие файла пользовательских прокси proxies.txt
    user_proxy_file = "proxies.txt"
    if os.path.exists(user_proxy_file):
        try:
            with open(user_proxy_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parsed = parse_proxy_string(line)
                        if parsed:
                            proxies.append(parsed)
            # Добавляем прямой IP в конец списка, чтобы он чередовался с остальными 3 прокси
            if proxies:
                proxies.append({"server": "direct"})
        except Exception as e:
            print("Ошибка чтения proxies.txt:", e)

    # 2. Если файл пустой или отсутствует, берем бесплатные прокси KZ (только если разрешено use_free)
    if not proxies and use_free:
        cache_file = "kz_proxies.txt"
        raw_proxies = []
        if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < 3600:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    raw_proxies = [line.strip() for line in f if line.strip()]
            except Exception:
                pass
                
        if not raw_proxies:
            try:
                raw_proxies = []
                
                # Загружаем гигантские списки HTTP, SOCKS4 и SOCKS5 прокси (мировые)
                
                # Функция-помощник для загрузки
                def fetch_list(url, prefix):
                    try:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            content = resp.read().decode('utf-8')
                            for line in content.split('\n'):
                                line = line.strip()
                                if line:
                                    raw_proxies.append(f"{prefix}://{line}")
                    except Exception as e:
                        print(f"Ошибка загрузки {url}:", e)

                # Source 1: TheSpeedX (HTTP, SOCKS4, SOCKS5)
                fetch_list("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", "http")
                fetch_list("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt", "socks4")
                fetch_list("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt", "socks5")
                
                # Source 2: monosans (HTTP, SOCKS4, SOCKS5)
                fetch_list("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt", "http")
                fetch_list("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt", "socks4")
                fetch_list("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt", "socks5")
                
                # Source 3: ShiftyTR (HTTP, SOCKS4, SOCKS5)
                fetch_list("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt", "http")
                fetch_list("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt", "socks4")
                fetch_list("https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt", "socks5")
                
                # Source 4: prxchecker & hookzof
                fetch_list("https://raw.githubusercontent.com/prxchecker/proxy-list/main/http.txt", "http")
                fetch_list("https://raw.githubusercontent.com/prxchecker/proxy-list/main/socks4.txt", "socks4")
                fetch_list("https://raw.githubusercontent.com/prxchecker/proxy-list/main/socks5.txt", "socks5")
                fetch_list("https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt", "socks5")
                
                # Source 5: API ProxyScrape
                fetch_list("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text", "http")
                
                # Убираем дубликаты
                raw_proxies = list(set(raw_proxies))
                random.shuffle(raw_proxies) # Перемешиваем
                    
                if raw_proxies:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        f.write('\n'.join(raw_proxies))
            except Exception as e:
                print("Ошибка при загрузке глобального списка прокси:", e)
                
        for rp in raw_proxies:
            parsed = parse_proxy_string(rp)
            if parsed:
                proxies.append(parsed)
                
    # Отфильтровываем уже используемые прямо сейчас (опционально)
    available = [p for p in proxies if p["server"] not in exclude_servers]
    
    # Если мы отфильтровали всё, то разрешаем использовать занятые прокси повторно (только если strict=False)
    if not available and proxies and not strict:
        available = proxies
        
    if not available:
        return None
        
    # Строгий последовательный перебор по кругу
    if not hasattr(get_random_kz_proxy, "proxy_index"):
        get_random_kz_proxy.proxy_index = 0
        
    if get_random_kz_proxy.proxy_index >= len(available):
        get_random_kz_proxy.proxy_index = 0
        
    choice = available[get_random_kz_proxy.proxy_index]
    get_random_kz_proxy.proxy_index += 1
    
    return choice

active_tasks = {}

os.makedirs("static/live", exist_ok=True)

async def auto_screenshot(page, task_id):
    """Фоновая корутина для регулярного обновления скриншота."""
    path = f"static/live/{task_id}.jpg"
    while task_id in active_tasks and active_tasks[task_id]["progress"] < 100:
        try:
            if not page.is_closed():
                await page.screenshot(path=path, type="jpeg", quality=60)
        except Exception:
            pass
        await asyncio.sleep(1)

async def run_playwright_bot(task_id, url, actions):
    screenshot_task = None
    actions_completed = {"scroll": 0, "phone": 0, "chat": 0}
    start_time = time.time()
    
    try:
        async with async_playwright() as p:
            active_tasks[task_id]["status"] = "запуск браузера..."
            
            browser_args = {
                "headless": True,
                "channel": "msedge",
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--window-position=-32000,-32000",
                    "--headless=new"
                ]
            }
            try:
                browser = await p.chromium.launch(**browser_args)
            except:
                browser_args["channel"] = "chrome"
                browser = await p.chromium.launch(**browser_args)
            
            desktop_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 720}
            }
            
            context_args = desktop_args
            active_tasks[task_id]["status"] = "эмуляция: Desktop..."
            
            bot_acc = actions.get("bot_account")
            if bot_acc and bot_acc != "none":
                state_path = f"bot_accounts/{bot_acc}.json"
                if os.path.exists(state_path):
                    context_args["storage_state"] = state_path
                    active_tasks[task_id]["status"] = f"используем аккаунт {bot_acc}..."
                
                # Загружаем настройки прокси, если они есть
                proxy_meta_path = f"bot_accounts/{bot_acc}_meta.json"
                if os.path.exists(proxy_meta_path):
                    try:
                        with open(proxy_meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                            proxy = meta.get("proxy", {})
                            if proxy.get("server"):
                                context_args["proxy"] = proxy
                    except Exception as e:
                        print("Ошибка загрузки прокси:", e)
            else:
                # Читаем файл конфигурации, чтобы понять, нужно ли использовать бесплатные прокси вообще
                # (так как публичные прокси часто блокируются CloudFront 403)
                use_free = True
                if os.path.exists("config_proxy.json"):
                    try:
                        with open("config_proxy.json", "r", encoding="utf-8") as cf:
                            import json
                            cfg = json.load(cf)
                            use_free = cfg.get("use_free_kz_proxies", True)
                    except:
                        pass
                
                kz_proxy = None
                while True:
                    if active_tasks.get(task_id, {}).get("cancel"):
                        raise Exception("Task cancelled during proxy wait")
                        
                    # Собираем прокси, которые сейчас используются другими активными задачами
                    used_servers = {task.get("proxy_server") for tid, task in active_tasks.items() if tid != task_id and task.get("proxy_server")}
                    
                    if actions.get("force_proxy"):
                        kz_proxy = parse_proxy_string(actions["force_proxy"])
                        break
                    elif actions.get("force_direct_ip"):
                        if "direct" not in used_servers:
                            kz_proxy = {"server": "direct"}
                            break
                    else:
                        kz_proxy = get_random_kz_proxy(exclude_servers=used_servers, use_free=use_free, strict=True)
                        if kz_proxy:
                            break
                            
                    active_tasks[task_id]["status"] = "ожидание свободного IP..."
                    await asyncio.sleep(5)
                
                if kz_proxy and kz_proxy.get("server") != "direct":
                    context_args["proxy"] = kz_proxy
                    active_tasks[task_id]["proxy_server"] = kz_proxy["server"] # Сохраняем для исключения
                    display_server = kz_proxy["server"].replace("http://", "").replace("https://", "").replace("socks5://", "").replace("socks4://", "")
                    active_tasks[task_id]["status"] = f"используем прокси iProxy: {display_server}..."
                    print(f"Гостевой бот {task_id} запущен через прокси: {kz_proxy['server']}")
                else:
                    active_tasks[task_id]["proxy_server"] = "direct"
                    active_tasks[task_id]["status"] = "запуск с прямого IP..."
                    print(f"Гостевой бот {task_id} запущен с прямым IP")
            
            context = await browser.new_context(**context_args)
            
            # Блокируем рекламные трекеры, попапы и шрифты (картинки теперь грузятся)
            async def route_interceptor(route):
                block_types = ["media", "font"]
                
                # Блокируем тяжелые медиафайлы
                if route.request.resource_type in block_types:
                    await route.abort()
                # Блокируем только откровенные рекламные сети и тяжелые плееры,
                # НО пропускаем всю внутреннюю аналитику OLX (ninja, laquesis, google-analytics), 
                # иначе OLX не засчитает наш просмотр в счетчик!
                elif any(domain in route.request.url for domain in [
                    "criteo.com", "adtraff", "doubleclick.net", "googlesyndication.com", 
                    "facebook.net", "imasdk.googleapis.com", "2mdn.net"
                ]):
                    await route.abort()
                else:
                    await route.continue_()
            
            await context.route("**/*", route_interceptor)
            
            page = await context.new_page()
            
            total_bytes_used = 0
            async def on_response(response):
                nonlocal total_bytes_used
                try:
                    # Прибавляем 2000 байт на каждый запрос как накладные расходы прокси (заголовки, TCP, TLS)
                    val = int(response.headers.get("content-length", "0"))
                    total_bytes_used += val + 2000
                except:
                    total_bytes_used += 2000
            page.on("response", on_response)
            
            # Автоматически отклоняем все диалоги (например, запуск звонилки tel:), чтобы избежать зависаний
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))
            
            from playwright_stealth import Stealth
            await Stealth().apply_stealth_async(page)
            
            # Запускаем фоновый процесс снятия скриншотов
            screenshot_task = asyncio.create_task(auto_screenshot(page, task_id))
            
            active_tasks[task_id]["status"] = f"эмуляция поиска (olx.kz)..."
            # Сначала заходим на главную, чтобы создать органический Referer
            await page.goto("https://www.olx.kz/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(random.uniform(2000, 4000))
            
            if url.isdigit():
                active_tasks[task_id]["status"] = f"поиск по ID {url}..."
                search_url = f"https://www.olx.kz/list/q-{url}/"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                
                # Ждём пока React отрисует список объявлений (до 15 секунд)
                try:
                    await page.wait_for_selector('a[href*="/d/obyavlenie/"]', timeout=15000)
                except Exception:
                    pass # Если не дождались, fallback на парсинг того, что есть
                
                html = await page.content()
                import re
                links = set(re.findall(r'href="([^"]*)"', html))
                actual_url = None
                encoded_id = encode_olx_id(url)
                for link in links:
                    if '/d/obyavlenie/' in link and (url in link or encoded_id in link):
                        actual_url = "https://www.olx.kz" + link if link.startswith("/") else link
                        break
                        
                if actual_url:
                    active_tasks[task_id]["status"] = f"открытие объявления..."
                    url = actual_url
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                else:
                    page_title = await page.title()
                    # Если прокси подсунул капчу или заблокирован
                    if "cloudflare" in page_title.lower() or "403" in page_title or "attention required" in page_title.lower() or "blocked" in page_title.lower():
                        raise Exception(f"ERR_PROXY_BLOCKED: Прокси заблокирован Cloudflare/OLX (Title: {page_title})")
                    # Если прокси вернул какую-то чушь (не OLX)
                    elif "olx" not in page_title.lower() and "объявлен" not in page_title.lower():
                        raise Exception(f"ERR_PROXY_BAD_PAGE: Прокси вернул мусорную страницу (Title: {page_title})")
                    else:
                        raise Exception(f"ERR_NOT_FOUND: Объявление с ID {url} не найдено на OLX.kz (Title: {page_title})")
            else:
                active_tasks[task_id]["status"] = f"переход по ссылке..."
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Ждем еще немного для подгрузки JS счетчиков аналитики
            await page.wait_for_timeout(8000)
            
            # Закрываем все назойливые плашки (куки, опросы OLX), которые могут перекрывать экран
            try:
                await page.evaluate('''() => {
                    let btns = Array.from(document.querySelectorAll('button'));
                    for (let b of btns) {
                        let text = b.innerText ? b.innerText.toLowerCase() : "";
                        if (text.includes('закрыть') || text.includes('принять') || text.includes('нет, спасибо')) {
                            b.click();
                        }
                    }
                }''')
                await page.wait_for_timeout(1000)
            except: pass
            
            # Проверка на CloudFront 403 блок
            try:
                page_content = await page.content()
            except Exception:
                page_content = ""
                
            if "403 ERROR" in page_content and "CloudFront" in page_content:
                raise Exception("ERR_PROXY_BLOCKED_403: Прокси заблокирован CloudFront на стороне OLX.")
                
            if "подозрительную активность" in page_content.lower() or "невозможно продолжить, поскольку мы обнаружили" in page_content.lower() or "recaptcha" in page_content.lower():
                raise Exception("ERR_PROXY_BLOCKED_ANTIBOT: OLX заблокировал доступ (подозрительная активность / reCAPTCHA).")
                

            if actions.get("scroll"):
                active_tasks[task_id]["status"] = "просмотр фото..."
                actions_completed["scroll"] = 1
                try:
                    # Ищем главное фото
                    photo = page.locator(".swiper-slide-active img, [data-cy='ad-photos'] img, .swiper-zoom-container img").first
                    if await photo.count() > 0 and await photo.is_visible():
                        # Имитируем свайп фото через чистый JS (чтобы избежать ложных кликов от мыши, которые открывают full-screen галерею)
                        await page.evaluate('''() => {
                            let swiper = document.querySelector('.swiper-wrapper') || document.querySelector('[data-cy="ad-photos"]');
                            if (swiper) {
                                let scrollAmount = 0;
                                let slideTimer = setInterval(() => {
                                    swiper.scrollBy({left: 300, behavior: 'smooth'});
                                    let nextBtn = document.querySelector('.swiper-button-next');
                                    if(nextBtn) nextBtn.click();
                                    scrollAmount += 1;
                                    if(scrollAmount >= 3) clearInterval(slideTimer);
                                }, 1500);
                            }
                        }''')
                        await page.wait_for_timeout(4500)
                                
                except Exception as e:
                    print("Ошибка при просмотре фото:", e)
                
                active_tasks[task_id]["status"] = "плавный скролл вниз..."
                # Универсальный скролл (короткими шагами)
                for _ in range(random.randint(8, 15)):
                    await page.mouse.wheel(0, random.randint(200, 400))
                    await page.evaluate(f"window.scrollBy(0, {random.randint(250, 400)}); if(document.scrollingElement) document.scrollingElement.scrollBy(0, 300);")
                    await page.wait_for_timeout(random.uniform(300, 800))
                    
            if actions.get("click_phone"):
                active_tasks[task_id]["status"] = "ищем кнопку 'Показать телефон'..."
                try:
                    phone_selectors = [
                        "[data-testid='show-phone']",
                        "[data-testid='contact-phone']",
                        "[data-cy='ad-contact-phone']",
                        "button:has-text('Позвонить')",
                        "button:has-text('SMS')",
                        "button:has-text('Показать')",
                        "button:has-text('показать')",
                        "text=Позвонить",
                        "text=показать"
                    ]
                    
                    # Даем React время отрендерить кнопку после скролла (до 5 секунд)
                    try:
                        await page.wait_for_selector(", ".join(phone_selectors[:3]), timeout=5000)
                    except:
                        pass
                        
                    clicked = False
                    for sel in phone_selectors:
                        try:
                            # Пытаемся найти все элементы по селектору и кликаем первый видимый
                            locators = await page.locator(sel).all()
                            for btn in locators:
                                if await btn.is_visible():
                                    await btn.click(timeout=5000)
                                    clicked = True
                                    active_tasks[task_id]["status"] = f"нажали по селектору {sel}..."
                                    break
                            if clicked:
                                break
                        except:
                            pass
                                
                    if not clicked:
                        # Резервный вариант - через выполнение JS в браузере (ищет даже по скрытым классам)
                        active_tasks[task_id]["status"] = "попытка клика через JS..."
                        clicked = await page.evaluate('''() => {
                            // Ищем по дата-атрибутам
                            let btn1 = document.querySelector('[data-testid="show-phone"]');
                            if (btn1) { btn1.click(); return true; }
                            
                            let btn2 = document.querySelector('[data-cy="ad-contact-phone"]');
                            if (btn2) { btn2.click(); return true; }

                            // Ищем по тексту
                            let btns = Array.from(document.querySelectorAll('button, div, span, a'));
                            for (let b of btns) {
                                let text = b.innerText ? b.innerText.toLowerCase().trim() : "";
                                if (text === 'показать' || text === 'показать телефон' || text.includes('позвонить') || text.includes('sms')) {
                                    b.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        
                    if clicked:
                        # Ждем, пока прогрузится сам номер или модальное окно на мобилках
                        await page.wait_for_timeout(random.uniform(2500, 4000))
                        
                        page_content_after = await page.content()
                        if "подозрительную активность" in page_content_after.lower() or "невозможно продолжить, поскольку мы обнаружили" in page_content_after.lower() or "recaptcha" in page_content_after.lower():
                            raise Exception("ERR_PROXY_BLOCKED_ANTIBOT: OLX заблокировал показ телефона (подозрительная активность / reCAPTCHA).")
                        
                        # Кликаем по самому номеру телефона (ссылке tel: или точной кнопке "Позвонить" в модальном окне), чтобы зарегистрировать созвон
                        active_tasks[task_id]["status"] = "кликаем по номеру для регистрации созвона..."
                        try:
                            # Селекторы для ссылки на звонок
                            call_selectors = [
                                "a[href^='tel:']",
                                "a:has-text('Позвонить')",
                                "button:has-text('Позвонить')",
                                "a:has-text('+7')",
                                "a:has-text('87')",
                                "span:has-text('+7')",
                                "span:has-text('87')",
                                "[data-testid='contact-phone'] a",
                                "[data-testid='contact-phone']",
                                "[data-cy='ad-contact-phone']"
                            ]
                            call_clicked = False
                            for c_sel in call_selectors:
                                # Ищем именно внутри модального окна (последний элемент в DOM)
                                c_btn = page.locator(c_sel).last
                                if await c_btn.count() > 0 and await c_btn.is_visible():
                                    try:
                                        # Физический клик мышкой прямо по центру номера (как просит пользователь)
                                        box = await c_btn.bounding_box()
                                        if box:
                                            # На всякий случай блокируем tel: чтобы браузер не пытался открыть Skype/звонилку
                                            await c_btn.evaluate("el => el.addEventListener('click', e => e.preventDefault())")
                                            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                                            await page.mouse.down()
                                            await page.wait_for_timeout(random.uniform(50, 150))
                                            await page.mouse.up()
                                            call_clicked = True
                                            active_tasks[task_id]["status"] = f"нажали прямо на номер ({c_sel})..."
                                            actions_completed["phone"] = 1
                                            break
                                    except:
                                        pass
                                        
                            if not call_clicked:
                                # Резервный вариант клика по tel: или тексту телефона через JS
                                call_clicked = await page.evaluate('''() => {
                                    // 1. Ищем ссылки tel:
                                    let telLink = document.querySelector('a[href^="tel:"]');
                                    if (telLink) {
                                        telLink.addEventListener('click', e => e.preventDefault());
                                        telLink.click();
                                        return true;
                                    }
                                    // 2. Ищем любой элемент с номером +7 или 87 или точную кнопку Позвонить
                                    let els = Array.from(document.querySelectorAll('a, button, span, div, p'));
                                    // Идем с конца (чтобы сначала проверять элементы модалки, которые обычно в конце DOM)
                                    for (let i = els.length - 1; i >= 0; i--) {
                                        let el = els[i];
                                        let text = el.innerText ? el.innerText.trim() : "";
                                        let tLower = text.toLowerCase();
                                        // Проверяем, выглядит ли текст как номер телефона (много цифр)
                                        let digitsCount = (text.match(/\\d/g) || []).length;
                                        if (text.includes('позвонить') || (tLower.includes('+7') || tLower.includes('87')) && digitsCount >= 10 || digitsCount >= 11) {
                                            el.addEventListener('click', e => e.preventDefault());
                                            el.click();
                                            return true;
                                        }
                                    }
                                    return false;
                                }''')
                                if (call_clicked):
                                    active_tasks[task_id]["status"] = "нажали на номер через JS..."
                                    actions_completed["phone"] = 1
                        except Exception as call_ex:
                            print("Ошибка при попытке кликнуть по телефону для созвона:", call_ex)

                        try:
                            path = f"static/live/{task_id}_phone.jpg"
                            await page.screenshot(path=path, type="jpeg", quality=60)
                        except:
                            pass
                    else:
                        active_tasks[task_id]["status"] = "кнопка телефона не найдена"
                except Exception as e:
                    print(f"Ошибка при клике на телефон: {e}")
                    
            if actions.get("click_chat"):
                bot_acc = actions.get("bot_account")
                if not bot_acc or bot_acc == "none":
                    active_tasks[task_id]["status"] = "пропуск чата (без авторизации редирект на логин)"
                    actions["click_chat"] = False

            if actions.get("click_chat"):
                active_tasks[task_id]["status"] = "открываем чат..."
                try:
                    chat_selectors = [
                        "[data-testid='chat-button']",
                        "[data-testid='ad-contact-message-button']",
                        "[data-cy='ad-contact-message-button']",
                        "[data-cy='ad-contact-message']",
                        "button:has-text('Сообщение')",
                        "button:has-text('Написать')",
                        "text=Написать",
                        "text=Сообщение"
                    ]
                    clicked = False
                    for sel in chat_selectors:
                        btn = page.locator(sel).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click()
                            clicked = True
                            active_tasks[task_id]["status"] = f"нажали чат по {sel}..."
                            await page.wait_for_timeout(random.uniform(2000, 4000))
                            break
                    
                    if not clicked:
                        # Попробуем кликнуть через JS, если селекторы не сработали
                        clicked = await page.evaluate('''() => {
                            let els = Array.from(document.querySelectorAll('button, a, div, span'));
                            for (let el of els) {
                                let txt = el.innerText ? el.innerText.toLowerCase().trim() : '';
                                if (txt === 'сообщение' || txt === 'написать') {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        if clicked:
                            active_tasks[task_id]["status"] = "нажали чат через JS..."
                            await page.wait_for_timeout(random.uniform(2000, 4000))

                    if not clicked:
                        active_tasks[task_id]["status"] = "кнопка чата не найдена"
                    else:
                        msg = actions.get("chat_message")
                        if msg:
                            active_tasks[task_id]["status"] = "пишем сообщение..."
                            await page.wait_for_timeout(2000)
                            try:
                                # Ищем поле ввода
                                textarea = page.locator("textarea[name='message.text'], textarea[name='message'], textarea[placeholder*='Напишите'], [data-testid='chat-message-input'], textarea").first
                                if await textarea.count() > 0:
                                    await textarea.fill(msg)
                                    await page.wait_for_timeout(1000)
                                    
                                    # Ищем кнопку отправить (специфичные селекторы для чата)
                                    send_btn = page.locator("button[aria-label='Submit message'], button.css-19gvvnk, [data-testid='chat-send-button'], button:has-text('Отправить'), button:has-text('Send')").first
                                    if await send_btn.count() > 0 and await send_btn.is_visible():
                                        await send_btn.click()
                                        active_tasks[task_id]["status"] = "сообщение отправлено!"
                                        actions_completed["chat"] = 1
                                        await page.wait_for_timeout(2000)
                                    else:
                                        # Попытка найти и кликнуть кнопку отправки внутри формы чата через JS
                                        sent_via_js = await page.evaluate('''() => {
                                            let ta = document.querySelector('textarea[name="message.text"]') || document.querySelector('textarea');
                                            if (ta) {
                                                let form = ta.closest('form');
                                                if (form) {
                                                    let btn = form.querySelector('button[type="submit"]');
                                                    if (btn) {
                                                        btn.click();
                                                        return true;
                                                    }
                                                }
                                            }
                                            return false;
                                        }''')
                                        if sent_via_js:
                                            active_tasks[task_id]["status"] = "сообщение отправлено (JS)!"
                                            actions_completed["chat"] = 1
                                            await page.wait_for_timeout(2000)
                                        else:
                                            # Резерв - отправка через Enter
                                            await textarea.press("Enter")
                                            active_tasks[task_id]["status"] = "сообщение отправлено (Enter)!"
                                            actions_completed["chat"] = 1
                                            await page.wait_for_timeout(2000)
                                else:
                                    active_tasks[task_id]["status"] = "поле ввода чата не найдено"
                            except Exception as e:
                                print("Ошибка при вводе сообщения:", e)
                                active_tasks[task_id]["status"] = "ошибка ввода сообщения"
                            
                except Exception as e:
                    print(f"Ошибка при открытии чата: {e}")
            else:
                # Если чат не нужен, блокируем трекеры и лишние соединения
                await page.route("**/*", lambda route: route.abort() if any(t in route.request.url for t in ["google-analytics", "hotjar", "doubleclick", "facebook", "sentry"]) else route.continue_())
                    
            has_warning = False
            warning_reasons = []
            
            ip_used = active_tasks.get(task_id, {}).get("proxy_server")
            t_mb = (total_bytes_used * 4.2) / (1024*1024)
            
            if actions.get("click_phone") and not actions_completed.get("phone"):
                has_warning = True
                # Если в статусе уже записана ошибка телефона, берем ее, иначе общую фразу
                s = active_tasks[task_id]["status"]
                if "телефон" in s.lower() and "успешно" not in s.lower():
                    warning_reasons.append(f"Не удалось нажать на телефон ({s})")
                else:
                    warning_reasons.append("Кнопка телефона не найдена или заблокирована")
                    
            if actions.get("click_chat") and not actions_completed.get("chat"):
                has_warning = True
                s = active_tasks[task_id]["status"]
                if "чат" in s.lower() and "успешно" not in s.lower() and "отправлено" not in s.lower():
                    warning_reasons.append(f"Не удалось написать в чат ({s})")
                else:
                    warning_reasons.append("Чат недоступен, не найдено поле ввода, либо требует авторизации")
            
            # Ожидание до минимальной длительности работы (1.5 минуты / 90 секунд)
            elapsed = time.time() - start_time
            if elapsed < 90.0:
                wait_dur = 90.0 - elapsed + random.uniform(5.0, 15.0)
                steps = max(1, int(wait_dur / 5.0))
                for step_idx in range(steps):
                    if active_tasks.get(task_id, {}).get("cancel"):
                        break
                    active_tasks[task_id]["status"] = f"имитация чтения описания (осталось {int(wait_dur - step_idx*5)} сек)..."
                    try:
                        await page.mouse.wheel(0, random.choice([-150, 150]))
                        await page.evaluate(f"window.scrollBy(0, {random.choice([-100, 100])});")
                    except:
                        pass
                    await page.wait_for_timeout(5000)
            
            final_status = "warning" if has_warning else "success"
            record_stat(final_status, url, ip_used, actions_completed, traffic_mb=t_mb)
            active_tasks[task_id]["progress"] = 100
            active_tasks[task_id]["status"] = "завершено успешно" if not has_warning else "завершено частично"
            
            with open("bot_queue.log", "a", encoding="utf-8") as f:
                import datetime
                res_txt = f"{final_status} (телефон: {actions_completed.get('phone', 0)}, чат: {actions_completed.get('chat', 0)})"
                if has_warning:
                    res_txt += f" | ПРИЧИНА: {', '.join(warning_reasons)}"
                f.write(f"[{datetime.datetime.now()}] РЕЗУЛЬТАТ {task_id}: {res_txt}\n")
            
            # Даем время (6 сек) доделать последний скриншот и гарантированно отправить аналитику на сервера OLX
            await asyncio.sleep(6)
            if screenshot_task: screenshot_task.cancel()
            await browser.close()
            
    except Exception as e:
        err_str = str(e)
        active_tasks[task_id]["status"] = f"ошибка: {err_str}"
        if screenshot_task: screenshot_task.cancel()
        
        # Если это ошибка сети/прокси, пробрасываем её наверх для повторной попытки
        if any(x in err_str for x in ["ERR_", "Timeout", "Нет доступных прокси", "closed", "disconnected", "Proxy", "proxy", "net::"]):
            raise e
            
        ip_used = active_tasks.get(task_id, {}).get("proxy_server")
        
        t_mb = 0.0
        try:
            t_mb = (total_bytes_used * 4.2) / (1024*1024)
        except:
            pass
            
        print(f"!!! НЕПРЕДВИДЕННАЯ ОШИБКА, ЗАПИСЫВАЕМ В СТАТИСТИКУ: {err_str}")
        record_stat("error", url, ip_used, actions_completed, traffic_mb=t_mb)
        with open("bot_queue.log", "a", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now()}] ОШИБКА OLX {task_id}: {err_str}\n")
        active_tasks[task_id]["progress"] = 100

def bot_worker(task_id, url, actions):
    was_cancelled = False
    if task_id in active_tasks and active_tasks[task_id].get("cancel"):
        was_cancelled = True

    active_tasks[task_id] = {
        "status": "инициализация...", 
        "url": url, 
        "progress": 0,
        "bot_account": actions.get("bot_account", "none")
    }
    if was_cancelled:
        active_tasks[task_id]["cancel"] = True

    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        attempt = 0
        while True:
            if active_tasks.get(task_id, {}).get("cancel"):
                active_tasks[task_id]["status"] = "завершено принудительно"
                active_tasks[task_id]["progress"] = 100
                break
            try:
                loop.run_until_complete(run_playwright_bot(task_id, url, actions))
                break # Успешно или обычная ошибка (которая уже записана)
            except Exception as e:
                err_msg = str(e)
                if "ERR_NOT_FOUND" in err_msg:
                    active_tasks[task_id]["status"] = "завершено: объявление не найдено"
                    active_tasks[task_id]["progress"] = 100
                    record_stat("error", url, active_tasks[task_id].get("proxy_server"), None)
                    with open("bot_queue.log", "a", encoding="utf-8") as f:
                        import datetime
                        f.write(f"[{datetime.datetime.now()}] ОШИБКА: Объявление не найдено {task_id}: {err_msg}\n")
                    break
                if active_tasks.get(task_id, {}).get("cancel"):
                    break
                
                # Пишем в лог каждую неудачную попытку прокси
                with open("bot_queue.log", "a", encoding="utf-8") as f:
                    import datetime
                    f.write(f"[{datetime.datetime.now()}] Сбой {task_id} (попытка {attempt+1}/15): {err_msg[:100]}...\n")
                
                attempt += 1
                if attempt >= 15:
                    active_tasks[task_id]["status"] = f"завершено с ошибкой (превышен лимит попыток)"
                    active_tasks[task_id]["progress"] = 100
                    # Записываем ошибку в статистику, раз мы сдались
                    record_stat("error", url, active_tasks[task_id].get("proxy_server"), None)
                    with open("bot_queue.log", "a", encoding="utf-8") as f:
                        import datetime
                        f.write(f"[{datetime.datetime.now()}] ОШИБКА ПРОКСИ (15 попыток) {task_id}: {str(e)}\n")
                    break
                    
                active_tasks[task_id]["status"] = f"поиск рабочего прокси (попытка {attempt}/15)..."
                    
                time.sleep(1)
    finally:
        loop.close()

    # --- АВТО-ПОВТОР (REQUEUE) ---
    final_status = active_tasks.get(task_id, {}).get("status", "")
    is_cancelled = active_tasks.get(task_id, {}).get("cancel", False)
    
    if ("ошибка" in final_status.lower() or "частично" in final_status.lower()) and not is_cancelled:
        retries = actions.get("task_retries", 0)
        if retries < 3: # Максимум 3 полных перезапуска задачи
            with open("bot_queue.log", "a", encoding="utf-8") as f:
                import datetime
                f.write(f"[{datetime.datetime.now()}] АВТО-ПОВТОР ЗАДАЧИ {url}: {final_status}. Отправка в конец очереди (полный цикл {retries+1}/3)\n")
            
            new_actions = actions.copy()
            new_actions["task_retries"] = retries + 1
            
            # Отправляем в глобальную очередь через 10 секунд
            with global_queue_lock:
                global_task_queue.append({
                    "execute_at": time.time() + 10.0,
                    "task_id": f"{task_id}_R{retries+1}",
                    "url": url,
                    "actions": new_actions
                })
    # -----------------------------

    def cleanup_later():
        time.sleep(120)
        if task_id in active_tasks:
            del active_tasks[task_id]
            try:
                os.remove(f"static/live/{task_id}.jpg")
            except:
                pass
    
    threading.Thread(target=cleanup_later, daemon=True).start()

iproxy_lock = threading.Lock()

def spawn_bots_lazy(url, thread_actions_list, amount, delays_list, task_ids):
    def run_queue():
        for i in range(amount):
            task_id = task_ids[i]
            actions = thread_actions_list[i]
            delay = delays_list[i]
            
            # Если бот должен ждать, сразу показываем его в UI
            if delay > 0:
                active_tasks[task_id] = {
                    "status": f"ожидание ({int(delay)} сек)...",
                    "url": url,
                    "progress": 0,
                    "bot_account": actions.get("bot_account", "none")
                }
                time.sleep(delay)
                
            t = threading.Thread(target=bot_worker, args=(task_id, url, actions), daemon=True)
            t.start()
                
    threading.Thread(target=run_queue, daemon=True).start()

MAX_CONCURRENT_BOTS = 10
global_task_queue = []
global_queue_lock = threading.Lock()
workers_started = False
last_task_start_time = 0

# Флаг паузы для смены IP-адреса роутера
system_paused_for_ip_change = False

def start_workers_if_needed():
    global workers_started
    with global_queue_lock:
        if workers_started:
            return
        workers_started = True
        for _ in range(MAX_CONCURRENT_BOTS):
            threading.Thread(target=queue_worker_loop, daemon=True).start()

def queue_worker_loop():
    global last_task_start_time, system_paused_for_ip_change
    import traceback
    last_log_time = 0
    while True:
        task = None
        
        # Если идет смена IP, просто ждем и не берем новые задачи
        if system_paused_for_ip_change:
            time.sleep(2)
            continue
            
        with global_queue_lock:
            now = time.time()
            
            # ЖЁСТКОЕ ОГРАНИЧЕНИЕ: Запускаем браузеры не чаще чем раз в 10 секунд глобально,
            # чтобы избежать 100% загрузки процессора и мгновенного бана по IP за одновременные запросы!
            if now - last_task_start_time >= 10.0:
                if now - last_log_time > 10:
                    last_log_time = now
                    if len(global_task_queue) > 0:
                        try:
                            with open("bot_queue_debug.log", "w", encoding="utf-8") as f:
                                f.write(f"Now: {now}\n")
                                f.write(f"Queue size: {len(global_task_queue)}\n")
                                f.write(f"First task execute_at: {global_task_queue[0]['execute_at']}\n")
                        except: pass
                        
                for i in range(len(global_task_queue)):
                    if global_task_queue[i]["execute_at"] <= now:
                        task = global_task_queue.pop(i)
                        last_task_start_time = now
                        break
                    
        if task:
            t_id = task["task_id"]
            if t_id in active_tasks:
                active_tasks[t_id]["status"] = "запуск браузера..."
            with open("bot_queue.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now()}] Старт задачи {t_id} для {task['url']}\n")
            try:
                bot_worker(t_id, task["url"], task["actions"])
                with open("bot_queue.log", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.datetime.now()}] Завершение задачи {t_id}\n")
            except Exception as e:
                err = traceback.format_exc()
                with open("bot_queue.log", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.datetime.now()}] Ошибка Worker'а {t_id}: {e}\n{err}\n")
                if t_id in active_tasks:
                    active_tasks[t_id]["status"] = f"ошибка: {e}"
        else:
            time.sleep(1.0)

def start_bot(url, actions, amount=1, delay=2.0):
    task_ids = []
    thread_actions_list = []
    accounts_list = actions.get("bot_accounts", [])
    
    import random
    phone_indices = set()
    chat_indices = set()
    
    dist_phone_count = actions.get("dist_phone_count")
    if dist_phone_count is not None:
        try:
            p_cnt = min(int(dist_phone_count), amount)
            phone_indices = set(random.sample(range(amount), p_cnt))
        except: pass
            
    dist_chat_count = actions.get("dist_chat_count")
    if dist_chat_count is not None:
        try:
            c_cnt = min(int(dist_chat_count), amount)
            chat_indices = set(random.sample(range(amount), c_cnt))
        except: pass
            
    dist_hours = actions.get("dist_hours")
    if dist_hours and amount >= 1:
        try:
            import datetime
            now = datetime.datetime.now()
            w_start = actions.get("work_start", "08:00")
            w_end = actions.get("work_end", "23:00")
            
            def is_in_window(dt):
                try:
                    st_time = datetime.datetime.strptime(w_start, "%H:%M").time()
                    en_time = datetime.datetime.strptime(w_end, "%H:%M").time()
                    t = dt.time()
                    if st_time <= en_time:
                        return st_time <= t <= en_time
                    else:
                        return t >= st_time or t <= en_time
                except: return True

            total_seconds = float(dist_hours) * 3600.0
            valid_seconds = []
            for s in range(int(total_seconds)):
                target_dt = now + datetime.timedelta(seconds=s)
                if is_in_window(target_dt):
                    valid_seconds.append(s)
            
            points = []
            if len(valid_seconds) > 0:
                step = max(1, len(valid_seconds) / amount)
                for i in range(amount):
                    idx = min(len(valid_seconds)-1, int(i * step))
                    points.append(valid_seconds[idx])
            else:
                points = [i * (total_seconds/max(1, amount)) for i in range(amount)]
        except:
            points = [i * delay for i in range(amount)]
    else:
        points = [i * (delay * random.uniform(0.8, 1.2)) for i in range(amount)]

    used_accounts = set()
    import uuid
    for i in range(amount):
        task_id = f"task_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}_{i}"
        task_ids.append(task_id)
        
        thread_actions = actions.copy()
        if dist_phone_count is not None:
            thread_actions["click_phone"] = (i in phone_indices)
        if dist_chat_count is not None:
            thread_actions["click_chat"] = (i in chat_indices)
            
        acc = "none"
        if i < len(accounts_list):
            candidate = accounts_list[i]
            if candidate != "none" and candidate not in used_accounts:
                acc = candidate
                used_accounts.add(candidate)
        thread_actions["bot_account"] = acc
        thread_actions_list.append(thread_actions)
        
        active_tasks[task_id] = {
            "status": "ожидание в очереди...",
            "url": url,
            "progress": 0,
            "bot_account": thread_actions["bot_account"]
        }
    
    start_workers_if_needed()
    with global_queue_lock:
        now_ts = time.time()
        for i in range(amount):
            global_task_queue.append({
                "execute_at": now_ts + points[i],
                "task_id": task_ids[i],
                "url": url,
                "actions": thread_actions_list[i]
            })
    return task_ids

def start_bot_batch(urls, actions, amount=1, delay=2.0):
    task_ids = []
    thread_actions_list = []
    url_list = []
    accounts_list = actions.get("bot_accounts", [])
    
    total_tasks = amount * len(urls)
    
    import random
    url_phone_rounds = {}
    url_chat_rounds = {}
    for u in urls:
        dist_phone_count = actions.get("dist_phone_count")
        p_cnt = min(int(dist_phone_count), amount) if dist_phone_count is not None else 0
        url_phone_rounds[u] = set(random.sample(range(amount), p_cnt))
        
        dist_chat_count = actions.get("dist_chat_count")
        c_cnt = min(int(dist_chat_count), amount) if dist_chat_count is not None else 0
        url_chat_rounds[u] = set(random.sample(range(amount), c_cnt))

    dist_hours = actions.get("dist_hours")
    if dist_hours and total_tasks >= 1:
        try:
            import datetime
            now = datetime.datetime.now()
            w_start = actions.get("work_start", "08:00")
            w_end = actions.get("work_end", "23:00")
            
            def is_in_window(dt):
                try:
                    st_time = datetime.datetime.strptime(w_start, "%H:%M").time()
                    en_time = datetime.datetime.strptime(w_end, "%H:%M").time()
                    t = dt.time()
                    if st_time <= en_time: return st_time <= t <= en_time
                    else: return t >= st_time or t <= en_time
                except: return True

            total_seconds = float(dist_hours) * 3600.0
            valid_seconds = []
            for s in range(int(total_seconds)):
                target_dt = now + datetime.timedelta(seconds=s)
                if is_in_window(target_dt):
                    valid_seconds.append(s)
            
            points = []
            if len(valid_seconds) > 0:
                step = max(1, len(valid_seconds) / total_tasks)
                for i in range(total_tasks):
                    idx = min(len(valid_seconds)-1, int(i * step))
                    points.append(valid_seconds[idx])
            else:
                points = [i * (total_seconds/max(1, total_tasks)) for i in range(total_tasks)]
        except:
            points = [i * delay for i in range(total_tasks)]
    else:
        points = [i * (delay * random.uniform(0.8, 1.2)) for i in range(total_tasks)]

    used_accounts = set()
    import uuid
    import time
    
    task_index = 0
    for r in range(amount): # Круги (rounds)
        for u in urls: # Последовательно по списку ссылок
            task_id = f"task_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}_{task_index}"
            task_ids.append(task_id)
            url_list.append(u)
            
            thread_actions = actions.copy()
            thread_actions["click_phone"] = (r in url_phone_rounds[u])
            thread_actions["click_chat"] = (r in url_chat_rounds[u])
            
            acc = "none"
            if task_index < len(accounts_list):
                candidate = accounts_list[task_index]
                if candidate != "none" and candidate not in used_accounts:
                    acc = candidate
                    used_accounts.add(candidate)
            thread_actions["bot_account"] = acc
            thread_actions_list.append(thread_actions)
            
            active_tasks[task_id] = {
                "status": "ожидание в очереди...",
                "url": u,
                "progress": 0,
                "bot_account": thread_actions["bot_account"]
            }
            task_index += 1
            
    start_workers_if_needed()
    with global_queue_lock:
        now_ts = time.time()
        for i in range(total_tasks):
            global_task_queue.append({
                "execute_at": now_ts + points[i],
                "task_id": task_ids[i],
                "url": url_list[i],
                "actions": thread_actions_list[i]
            })
            
    return task_ids

def get_status():
    return active_tasks
