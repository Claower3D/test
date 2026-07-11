import asyncio
import os
import sys
import json
import csv
from playwright.async_api import async_playwright
import time
import winreg
import shlex
import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def load_whatsapp_groups():
    config_file = "whatsapp_groups.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []

def save_whatsapp_groups(data):
    config_file = "whatsapp_groups.json"
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

async def type_text_to_whatsapp(page, element, text):
    """
    Печатает текст в поле ввода WhatsApp Web.
    Сначала очищает поле, затем вводит текст построчно, используя Shift+Enter для новых строк.
    """
    await element.focus()
    await element.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await asyncio.sleep(0.5)
    
    lines = text.split('\n')
    for idx, line in enumerate(lines):
        if line:
            await page.keyboard.type(line)
        if idx < len(lines) - 1:
            await page.keyboard.down("Shift")
            await page.keyboard.press("Enter")
            await page.keyboard.up("Shift")
            await asyncio.sleep(0.1)

async def main():
    groups = load_whatsapp_groups()
    if not groups:
        print("База групп пуста.")
        return
        
    limit = 0
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except:
            pass
            
    processed_count = 0
        
    config_file = "config_whatsapp.json"
    sheet_id = None
    sheet_name = None
    sheets_service = None
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cdata = json.load(f)
                sheet_id = cdata.get("google_sheet_id")
                sheet_name = cdata.get("google_sheet_name")
        except: pass
        
    if sheet_id and os.path.exists("credentials.json"):
        try:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            sheets_service = build('sheets', 'v4', credentials=creds)
            print("Google Sheets API успешно подключен.")
        except Exception as e:
            print(f"Не удалось подключить Google Sheets: {e}")

    exe_path = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as key:
            command = winreg.QueryValueEx(key, "")[0]
        parts = shlex.split(command)
        if parts and os.path.exists(parts[0]):
            exe_path = parts[0]
    except:
        pass

    temp_dir = os.path.abspath("whatsapp_profile2")
    os.makedirs(temp_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser_args = {
            "headless": False,
            "viewport": {"width": 1280, "height": 720},
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        if exe_path:
            browser_args["executable_path"] = exe_path

        try:
            context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
        except Exception:
            try:
                browser_args["channel"] = "msedge"
                browser_args.pop("executable_path", None)
                context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
            except Exception:
                browser_args.pop("channel", None)
                context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)

        page = context.pages[0] if context.pages else await context.new_page()

        print("Открываю WhatsApp Web. Пожалуйста, отсканируйте QR-код, если нужно.")
        await page.goto("https://web.whatsapp.com/")
        
        try:
            print("Ожидаем загрузку чатов (это может занять время)...")
            await page.wait_for_selector('#pane-side', timeout=300000)
            print("Авторизация успешна!")
        except Exception as e:
            print(f"Не дождались авторизации. Ошибка: {e}. Закрываю.")
            await context.close()
            return

        # Load active template text and specific media
        config_file = "config_whatsapp.json"
        text_template = ""
        media_path = None
        
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    active_idx = data.get("active_template", 0)
                    templates = data.get("templates", [])
                    
                    if templates and 0 <= active_idx < len(templates):
                        text_template = templates[active_idx].get("text", "")
                        
                        m_path = templates[active_idx].get("media", "")
                        if m_path and os.path.exists(m_path):
                            media_path = os.path.abspath(m_path)
                    else:
                        text_template = data.get("text_template", "")
            except:
                pass

        if not text_template:
            text_template = "Здравствуйте! Еду в ваш ЖК на установку решетки от выпадения детей и москитной сетки 2в1.\nПишите на вотсапп +77478375125, мой робот примет заявку, и после установки я зайду к вам на замеры! Сделаю скидку! Даю гарантию! Есть рассрочка и Kaspi Red!"
            
        if not media_path and os.path.exists("video.mp4"):
            media_path = os.path.abspath("video.mp4")
            
        print(f"Текст рассылки: {text_template}")
        
        if media_path:
            print(f"Найдено медиа для этого шаблона: {media_path}")
        else:
            print("Медиа не прикреплено. Отправка будет только текстом.")

        for i, group in enumerate(groups):
            if limit > 0 and processed_count >= limit:
                print(f"Достигнут лимит рассылки ({limit} групп). Останавливаем.")
                break
                
            if group.get("status") == "success":
                continue 
                
            if page.is_closed():
                print("Браузер закрыт пользователем или системой. Прерываем рассылку.")
                break
                
            processed_count += 1
                
            url = group.get("url")
            
            # Если это ссылка на приглашение, переделываем её в ссылку для веб-версии
            if "chat.whatsapp.com/" in url:
                invite_code = url.split("chat.whatsapp.com/")[-1].split("?")[0].strip("/")
                url = f"https://web.whatsapp.com/accept?code={invite_code}"
                
            print(f"Переходим в {url}")
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                
                # Ждем либо поле ввода, либо кнопку вступления
                try:
                    await page.wait_for_selector('div[title="Ввести сообщение"], div[title="Type a message"]', timeout=15000)
                except Exception:
                    # Ищем кнопки вступления в группу через JS по тексту на кнопках (независимо от локализации)
                    join_btn = None
                    req_btn = None
                    
                    try:
                        join_btn_handle = await page.evaluate_handle('''() => {
                            const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
                            for (const btn of buttons) {
                                const text = (btn.innerText || '').toLowerCase();
                                if ((text.includes('присоединиться') || text.includes('вступить') || text.includes('join') || text.includes('посмотреть') || text.includes('открыть') || text.includes('перейти')) && !text.includes('запрос') && !text.includes('заявка')) {
                                    return btn;
                                }
                            }
                            return null;
                        }''')
                        join_btn = join_btn_handle.as_element()
                    except Exception as je:
                        print("Ошибка JS при поиске кнопки Вступить:", je)
                        
                    try:
                        req_btn_handle = await page.evaluate_handle('''() => {
                            const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
                            for (const btn of buttons) {
                                const text = (btn.innerText || '').toLowerCase();
                                if (text.includes('запрос') || text.includes('заявк') || text.includes('request')) {
                                    return btn;
                                }
                            }
                            return null;
                        }''')
                        req_btn = req_btn_handle.as_element()
                    except Exception as re:
                        print("Ошибка JS при поиске кнопки Запрос:", re)
                        
                    if req_btn:
                        await req_btn.click()
                        await asyncio.sleep(5)
                        group["status"] = "success"
                        group["reason"] = "Подана заявка (группа закрытая)"
                        save_whatsapp_groups(groups)
                        continue
                    elif join_btn:
                        await join_btn.click()
                        await asyncio.sleep(6) # Ждем открытия чата
                    else:
                        group["status"] = "error"
                        group["reason"] = "Не удалось вступить в группу"
                        save_whatsapp_groups(groups)
                        continue

                # Ищем поле ввода
                try:
                    msg_box = await page.wait_for_selector('footer div[contenteditable="true"], div[title="Ввести сообщение"], div[title="Type a message"]', timeout=15000)
                except Exception:
                    # Проверяем, не закрыта ли группа для отправки сообщений
                    admin_only_selectors = [
                        'span:has-text("Только администраторы")',
                        'span:has-text("Only admins")',
                        'div:has-text("Отправка сообщений ограничена")'
                    ]
                    is_admin_only = False
                    for sel in admin_only_selectors:
                        if await page.query_selector(sel):
                            is_admin_only = True
                            break
                    
                    if is_admin_only:
                        group["status"] = "error"
                        group["reason"] = "Только администраторы могут писать"
                    else:
                        group["status"] = "error"
                        group["reason"] = "Не найдено поле ввода"
                        
                    save_whatsapp_groups(groups)
                    continue
                
                if media_path:
                    plus_btn = None
                    try:
                        # Попробуем сначала стандартный wait_for_selector
                        plus_btn = await page.wait_for_selector('span[data-icon="plus"], span[data-icon="clip"], span[data-icon="attach-menu-plus"], button[title*="Прикреп"], button[aria-label*="Прикреп"]', timeout=8000)
                    except Exception:
                        pass
                        
                    if not plus_btn:
                        # Если не нашли стандартным селектором, ищем умным JS-скриптом
                        try:
                            plus_btn_handle = await page.evaluate_handle('''() => {
                                const footer = document.querySelector('footer');
                                if (!footer) return null;
                                const buttons = footer.querySelectorAll('button, div[role="button"]');
                                for (const btn of buttons) {
                                    const label = (btn.getAttribute('aria-label') || btn.getAttribute('title') || '').toLowerCase();
                                    if (label.includes('прикреп') || label.includes('attach') || label.includes('вложен') || label.includes('plus') || label.includes('плюс')) {
                                        return btn;
                                    }
                                    if (btn.querySelector('[data-icon="plus"]') || btn.querySelector('[data-icon="clip"]') || btn.querySelector('[data-icon="attach-menu-plus"]')) {
                                        return btn;
                                    }
                                }
                                if (buttons.length > 0) return buttons[0];
                                return null;
                            }''')
                            plus_btn = plus_btn_handle.as_element()
                        except Exception as pe:
                            print("Ошибка поиска кнопки плюс через JS:", pe)
                        
                    if plus_btn:
                        await plus_btn.click()
                        await asyncio.sleep(1.5)
                        
                        # Перехватываем всплывающее окно выбора файла (File Chooser)
                        file_input_success = False
                        try:
                            photo_video_option = await page.wait_for_selector('span[data-icon="attach-image"], span:has-text("Фото и видео"), span:has-text("Photos & Videos"), [aria-label*="Фото"], [aria-label*="Photo"]', timeout=5000)
                            if photo_video_option:
                                async with page.expect_file_chooser(timeout=15000) as fc_info:
                                    await photo_video_option.click()
                                file_chooser = await fc_info.value
                                await file_chooser.set_files(media_path)
                                file_input_success = True
                        except Exception as e:
                            print(f"Ошибка выбора файла (file_chooser): {e}")
                            
                        if file_input_success:
                            
                            try:
                                caption_box = await page.wait_for_selector('div[contenteditable="true"], div[title="Добавить подпись"], div[title="Add a caption"]', timeout=25000)
                                if caption_box:
                                    await type_text_to_whatsapp(page, caption_box, text_template)
                                    await asyncio.sleep(1)
                            except Exception as e:
                                print(f"Не удалось найти поле подписи: {e}")
                            
                            # Отправляем медиа
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(6) # Больше времени для загрузки больших медиафайлов
                            
                            send_btn = await page.query_selector('span[data-icon="send"], span[data-icon="send-light"], button[aria-label="Send"], button[aria-label="Отправить"]')
                            if send_btn:
                                await send_btn.click()
                                await asyncio.sleep(8) # Ожидание отправки медиа
                            else:
                                # На случай если Enter уже отправил
                                await asyncio.sleep(5)
                                
                            group["status"] = "success"
                            group["reason"] = "Успешно отправлено медиа"
                            save_whatsapp_groups(groups)
                        else:
                            group["status"] = "error"
                            group["reason"] = "Не найдено поле загрузки файла"
                            save_whatsapp_groups(groups)
                    else:
                        try:
                            footer_html = await page.evaluate('document.querySelector("footer").innerHTML')
                            with open("footer_dump.html", "w", encoding="utf-8") as dump_file:
                                dump_file.write(footer_html)
                        except Exception as e:
                            print(f"FOOTER DUMP FAILED: {e}")
                            
                        group["status"] = "error"
                        group["reason"] = "Не найдена кнопка прикрепления"
                        save_whatsapp_groups(groups)
                else:
                    # Отправка только текста
                    await type_text_to_whatsapp(page, msg_box, text_template)
                    await asyncio.sleep(2) # Задержка перед отправкой
                    
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(5) # Ждем отправку сообщения
                    
                    send_btn = await page.query_selector('span[data-icon="send"], button[aria-label="Send"], button[aria-label="Отправить"]')
                    if send_btn:
                        await send_btn.click()
                        await asyncio.sleep(4) # Еще задержка после клика
                        
                    group["status"] = "success"
                    group["reason"] = "Успешно отправлен текст"
                    save_whatsapp_groups(groups)
                        
            except Exception as e:
                err_str = str(e)
                print(f"Ошибка при обработке {url}: {e}")
                group["status"] = "error"
                group["reason"] = err_str[:50]
                
                # Если браузер закрыт, прерываем рассылку
                if "closed" in err_str.lower() or "navigation failed" in err_str.lower():
                    save_whatsapp_groups(groups)
                    print("Критическое событие: браузер закрыт. Выход.")
                    break
                
            save_whatsapp_groups(groups)
            
            # Обновляем Google Таблицу с ограничением частоты запросов (rate limit)
            row_idx = group.get("row_index")
            if row_idx and sheet_id and sheet_name and sheets_service:
                status_text = "Да" if group["status"] == "success" else "Ошибка"
                date_text = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                sender_text = "Бот"
                reason_text = group.get("reason", "")
                
                range_to_update = f"'{sheet_name}'!E{row_idx}:H{row_idx}"
                body = {"values": [[status_text, date_text, sender_text, reason_text]]}
                
                for retry in range(3):
                    try:
                        sheets_service.spreadsheets().values().update(
                            spreadsheetId=sheet_id, range=range_to_update,
                            valueInputOption="USER_ENTERED", body=body
                        ).execute()
                        print(f"Обновлена строка {row_idx} в Google Таблице.")
                        await asyncio.sleep(1.2) # Лимит 60 запросов в минуту
                        break
                    except Exception as e:
                        if "429" in str(e) or "quota" in str(e).lower():
                            print(f"Превышен лимит Google Sheets API. Ожидание 5 сек (попытка {retry+1}/3)...")
                            await asyncio.sleep(5)
                        else:
                            print("Ошибка при обновлении Google Таблицы:", e)
                            break
            
        print("Рассылка завершена!")
        await asyncio.sleep(5)
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
