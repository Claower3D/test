// Function to find user identifier recursively in JSON
function findUserIdentifier(obj) {
  const keysToTry = ['username', 'email', 'name', 'id', 'userId', 'user_id', 'nickname', 'phone', 'login'];
  let found = {};
  
  function search(node) {
    if (!node || typeof node !== 'object') return;
    
    for (const key of keysToTry) {
      if (node[key] && typeof node[key] !== 'object') {
        const val = String(node[key]).trim();
        if (val && val.length > 2 && !found[key]) {
          found[key] = val;
        }
      }
    }
    
    for (const k in node) {
      if (node.hasOwnProperty(k) && typeof node[k] === 'object') {
        search(node[k]);
      }
    }
  }
  
  search(obj);
  
  return found.username || found.nickname || found.email || found.name || found.phone || found.login || found.id || found.userId || found.user_id || null;
}

// Function to run auto import
async function tryAutoImport() {
  if (window.hasRunOlxAutoImport) return;
  window.hasRunOlxAutoImport = true;
  
  const url = window.location.href.toLowerCase();
  if (url.includes("account/login") || url.includes("account/register") || url.includes("olx.kz/payment")) {
    console.log("[OLX Extension] На странице логина или оплаты, пропускаем авто-импорт");
    window.hasRunOlxAutoImport = false; // allow retry when navigation happens
    return;
  }
  
  // Check if we are obviously guest
  if (document.querySelector("a[href*='account/login']") || document.querySelector("[data-testid='login-button']")) {
    if (!document.querySelector("a[href*='logout']") && !document.querySelector("[data-testid='user-profile-name']")) {
      console.log("[OLX Extension] Пользователь не авторизован (гость), пропускаем авто-импорт");
      window.hasRunOlxAutoImport = false;
      return;
    }
  }
  
  let username = "";
  
  // Method 1: Check __NEXT_DATA__ script tag (extremely common in Next.js OLX apps)
  const nextDataEl = document.getElementById("__NEXT_DATA__");
  if (nextDataEl) {
    try {
      const data = JSON.parse(nextDataEl.textContent);
      
      // Target specific user/profile objects in nextState to avoid matching general category names
      let userObj = null;
      if (data.props && data.props.pageProps) {
        const pp = data.props.pageProps;
        userObj = pp.user || pp.profile || pp.account || pp.initialState?.user || pp.initialState?.profile;
      }
      
      if (userObj) {
        const identifier = findUserIdentifier(userObj);
        if (identifier) {
          username = identifier;
        }
      }
    } catch (e) {
      console.log("Failed to parse __NEXT_DATA__:", e);
    }
  }
  
  // Method 2: Check window or other scripts if username is still empty
  if (!username) {
    const scripts = document.querySelectorAll("script");
    for (const s of scripts) {
      if (s.textContent && (s.textContent.includes("initialState") || s.textContent.includes("window.__"))) {
        try {
          const match = s.textContent.match(/\{.*\}/);
          if (match) {
            const data = JSON.parse(match[0]);
            const pp = data.user || data.profile || data.account;
            if (pp) {
              const identifier = findUserIdentifier(pp);
              if (identifier) {
                username = identifier;
                break;
              }
            }
          }
        } catch(e) {}
      }
    }
  }
  
  // Method 3: DOM Selectors fallback with strict blacklist
  if (!username) {
    const selectors = [
      "[data-testid='user-profile-name']",
      ".user-profile h4",
      "div[class*='userName']",
      "h3.css-11tw91w"
    ];
    
    const blacklist = [
      "мой профиль", "my profile", "ваш профиль", "вход", "войти", "регистрация",
      "уведомления", "сообщения", "объявления", "платежи", "настройки", "выход",
      "notifications", "messages", "ads", "payments", "settings", "logout", "login"
    ];
    
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.innerText.trim()) {
        const text = el.innerText.trim();
        const textLower = text.toLowerCase();
        
        const isBlacklisted = blacklist.some(b => textLower.includes(b));
        if (text && !isBlacklisted && text.length > 2) {
          username = text;
          break;
        }
      }
    }
  }

  // Method 4: LocalStorage fallback
  if (!username) {
    try {
      const userSession = localStorage.getItem("user_session") || localStorage.getItem("session");
      if (userSession) {
        const parsed = JSON.parse(userSession);
        username = findUserIdentifier(parsed);
      }
    } catch(e) {}
  }
  
  if (!username) {
    console.log("[OLX Extension] Не удалось обнаружить имя авторизованного пользователя, отмена авто-импорта");
    window.hasRunOlxAutoImport = false;
    return;
  }
  
  // Send message to background script to fetch cookies and upload
  chrome.runtime.sendMessage({ action: "auto_import", username: username }, (response) => {
    if (response && response.ok) {
      showToast(`✅ Автоматически импортирован аккаунт: "${response.name}"`, "success");
    } else {
      console.log("Auto-import response:", response);
      window.hasRunOlxAutoImport = false; // allow retry if failed
    }
  });
}

function showToast(text, type) {
  const toast = document.createElement("div");
  toast.innerText = text;
  toast.style.position = "fixed";
  toast.style.bottom = "20px";
  toast.style.right = "20px";
  toast.style.backgroundColor = type === "success" ? "#00e676" : "#f44336";
  toast.style.color = "#000";
  toast.style.padding = "16px 24px";
  toast.style.borderRadius = "8px";
  toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.3)";
  toast.style.zIndex = "100000";
  toast.style.fontFamily = "sans-serif";
  toast.style.fontWeight = "bold";
  toast.style.fontSize = "14px";
  toast.style.transition = "opacity 0.5s ease";
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 500);
  }, 4000);
}

// Run after a short delay to let page load completely
setTimeout(tryAutoImport, 3000);
