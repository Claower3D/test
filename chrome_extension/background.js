chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "auto_import") {
    let botName = request.username || "";
    
    chrome.cookies.getAll({ domain: "olx.kz" }, async (cookies) => {
      if (!cookies || cookies.length === 0) {
        sendResponse({ ok: false, error: "No cookies found" });
        return;
      }
      
      // If we don't have a solid name, let's extract it from cookies
      if (!botName || botName === "olx_auto_user" || botName === "olx_user") {
        let cookieUser = "";
        
        // Try common cookie identifiers
        for (const c of cookies) {
          const nameLower = c.name.toLowerCase();
          if (nameLower === "user_name" || nameLower === "username" || nameLower === "user_nickname") {
            cookieUser = decodeURIComponent(c.value);
            break;
          }
        }
        
        if (!cookieUser) {
          for (const c of cookies) {
            if (c.name.toLowerCase().includes("email")) {
              cookieUser = decodeURIComponent(c.value);
              break;
            }
          }
        }
        
        if (!cookieUser) {
          for (const c of cookies) {
            if (c.name.toLowerCase() === "user_id" || c.name.toLowerCase() === "userid") {
              cookieUser = "user_" + c.value;
              break;
            }
          }
        }
        
        if (cookieUser) {
          botName = cookieUser.replace(/[^a-zA-Z0-9а-яА-ЯёЁ_]/g, "").substring(0, 20);
        }
      }
      
      // Final fallback if absolutely nothing found
      if (!botName) {
        // Generate a simple name with a random 4-digit number to avoid collision
        const randId = Math.floor(1000 + Math.random() * 9000);
        botName = "olx_bot_" + randId;
      }
      
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
        if (c.sameSite === "no_restriction") {
          pwCookie.sameSite = "None";
        } else if (["lax", "strict", "none"].includes(c.sameSite)) {
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
          sendResponse({ ok: true, name: botName });
        } else {
          sendResponse({ ok: false, error: result.error });
        }
      } catch (err) {
        sendResponse({ ok: false, error: "Server offline" });
      }
    });
    return true; // Keep message channel open for async response
  }
});
