document.getElementById("importBtn").addEventListener("click", async () => {
  const botName = document.getElementById("botName").value.trim();
  const statusDiv = document.getElementById("status");
  
  if (!botName) {
    showStatus("Введите имя бота!", "error");
    return;
  }
  
  showStatus("Получение куков...", "success");
  
  try {
    // Получаем все куки для домена olx.kz
    chrome.cookies.getAll({ domain: "olx.kz" }, async (cookies) => {
      if (!cookies || cookies.length === 0) {
        showStatus("Куки OLX не найдены. Вы вошли на olx.kz?", "error");
        return;
      }
      
      // Преобразуем куки в формат Playwright
      const playwrightCookies = cookies.map(c => {
        const pwCookie = {
          name: c.name,
          value: c.value,
          domain: c.domain,
          path: c.path,
          httpOnly: c.httpOnly,
          secure: c.secure
        };
        if (c.expirationDate) {
          pwCookie.expires = Math.floor(c.expirationDate);
        }
        
        // Преобразование sameSite
        if (c.sameSite === "no_restriction") {
          pwCookie.sameSite = "None";
        } else if (["lax", "strict", "none"].includes(c.sameSite)) {
          // Playwright ожидает Cap-case: Lax, Strict, None
          pwCookie.sameSite = c.sameSite.charAt(0).toUpperCase() + c.sameSite.slice(1);
        } else {
          pwCookie.sameSite = "Lax";
        }
        return pwCookie;
      });
      
      const payload = {
        name: botName,
        cookies: JSON.stringify(playwrightCookies)
      };
      
      showStatus("Отправка в панель...", "success");
      
      try {
        const response = await fetch("http://127.0.0.1:8000/bots/import_cookies_json", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        if (result.ok) {
          showStatus(`Успешно! Бот '${result.name || botName}' добавлен в панель.`, "success");
        } else {
          showStatus(`Ошибка панели: ${result.error}`, "error");
        }
      } catch (err) {
        showStatus("Ошибка отправки: убедитесь, что панель запущена на 127.0.0.1:8000", "error");
      }
    });
  } catch (e) {
    showStatus(`Ошибка расширения: ${e.message}`, "error");
  }
});

function showStatus(text, type) {
  const statusDiv = document.getElementById("status");
  statusDiv.innerText = text;
  statusDiv.className = type;
  statusDiv.style.display = "block";
}
