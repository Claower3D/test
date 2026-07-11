def weekly_page():
    import urllib.parse as _up, json
    week=request.args.get("week","this")
    items,start,end=_weekly_data(week); sel=_weekly_filtered(items)
    dead_list=[{"id":it["id"],"account":it["account"]} for it in sel if it.get("dead")]
    CONV,MINV,STRONG,WEAK = items[0]["thr"] if items else (10,30,5,3)
    BADGE={"strong":"<b style='color:#16c79a'>🟢 хорошо</b>","weak":"<b style='color:#ff5d5d'>🔴 слабо</b>",
           "mid":"<span style='color:#e0b341'>🟡 средне</span>","low":"<span style='color:#9a9aa3'>⚪ мало данных</span>"}
    REC={"strong":"🔝 в ТОП","weak":"⛔ заменить","mid":"наблюдать","low":"—"}
    cnt=lambda k: sum(1 for it in sel if it["vk"]==k)
    strong,weak,mid,low=cnt("strong"),cnt("weak"),cnt("mid"),cnt("low")
    body=""
    for it in sel:
        topcell=("🔝 до "+it["top"]) if it["top"] else "—"
        idcell=("<a href='%s' target='_blank' rel='noopener' style='font-family:monospace'>%s ↗</a>"%(it["url"],it["id"])) if it["url"] else ("<span style='font-family:monospace'>%s</span>"%it["id"])
        reccell=("<button onclick=\"deact(%s,'%s',this)\" title='Деактивировать в OLX (обратимо)' style='padding:4px 9px;font-size:12px;background:#3a1414;border:1px solid #5a1f1f;color:#ff9d9d;border-radius:7px;cursor:pointer'>🪦 Отключить</button>"%(it["id"],it["account"])) if it.get("dead") else REC[it["vk"]]
        body+=("<tr><td>%s</td><td>%s</td><td>%s</td><td><a href='/advert/%s'>%s</a></td>"
               "<td class=muted>%s</td>"
               "<td class=num>%s</td><td class=num>%s</td><td class=num><b>%s</b></td><td class=num>%s</td><td class=num>%s</td>"
               "<td>%s</td><td>%s</td><td>%s</td></tr>") % (
            it["account"], it["service"], it["city"] or "—", it["id"], it["title"], idcell,
            ("%d дн."%it["dl"] if it["dl"] is not None else "—"), it["dv"], it["leads"], it["dp"], it["conv"],
            BADGE[it["vk"]], topcell, reccell)
    def opts(vals, selv):
        return "".join("<option value=\"%s\"%s>%s</option>"%(v,(" selected" if v==selv else ""),v) for v in vals)
    cities_l=sorted({it["city"] for it in items if it["city"]}); accs_l=sorted({it["account"] for it in items}); svcs_l=sorted({it["service"] for it in items if it["service"]})
    f_city=request.args.get("city",""); f_acc=request.args.get("account",""); f_svc=request.args.get("service",""); f_v=request.args.get("verdict",""); f_k=request.args.get("kind","")
    vmap=[("","Любая оценка"),("strong","🟢 В ТОП"),("weak","🔴 На замену"),("mid","🟡 Средне"),("low","⚪ Мало данных"),("dead","🪦 Мёртвые")]
    vopts="".join("<option value=\"%s\"%s>%s</option>"%(k,(" selected" if k==f_v else ""),lbl) for k,lbl in vmap)
    kmap=[("","Все рубрики"),("услуга","🛠 Услуга"),("товар","📦 Товар"),("вакансия","💼 Вакансия")]
    kopts="".join("<option value=\"%s\"%s>%s</option>"%(k,(" selected" if k==f_k else ""),lbl) for k,lbl in kmap)
    other="prev" if week=="this" else "this"; other_lbl="← прошлая неделя" if week=="this" else "эта неделя →"
    keep={k:v for k,v in request.args.items() if k!="week"}; other_qs="&"+_up.urlencode(keep) if keep else ""
    csv_qs="?"+_up.urlencode({k:v for k,v in request.args.items()}) if request.args else ""
    rule=("🟢 ≥%d лидов · 🔴 &lt;%d лидов и конв.&lt;%.0f%% · ⚪ &lt;%d просм. · 🟡 остальное"%(STRONG,WEAK,CONV,MINV))
    return (THEME +
      "<title>Еженедельная статистика</title>"
      "<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px'>"
      "<h2 style='margin:0'>📅 Еженедельная статистика <span style='font-size:14px;font-weight:400;color:var(--muted)'>&nbsp;<a href='/'>🏠 Главная</a> · <a href='/stats'>📊 Вчерашняя</a></span></h2>"
      "<a href='/weekly.csv"+csv_qs+"'><button type=button>⬇ Скачать CSV</button></a></div>"
      "<div class=muted>Период: <b style='color:#fff'>"+start.isoformat()+" — "+end.isoformat()+"</b> &nbsp; <a href='/weekly?week="+other+other_qs+"'>"+other_lbl+"</a></div>"
      "<div class=rule>Правило оценки: "+rule+"</div>"
      "<form class=bar method=get>"
      "<input type=hidden name=week value=\""+week+"\">"
      "<select name=verdict onchange='this.form.submit()'>"+vopts+"</select>"
      "<select name=city onchange='this.form.submit()'><option value=''>Все города</option>"+opts(cities_l,f_city)+"</select>"
      "<select name=account onchange='this.form.submit()'><option value=''>Все кабинеты</option>"+opts(accs_l,f_acc)+"</select>"
      "<select name=service onchange='this.form.submit()'><option value=''>Все услуги</option>"+opts(svcs_l,f_svc)+"</select>"
      "</form>"
      "<div class=kpi>"
      "<div>Объявлений<b>"+str(len(sel))+"</b></div>"
      "<div>🟢 В ТОП<b style='color:#16c79a'>"+str(strong)+"</b></div>"
      "<div>🔴 На замену<b style='color:#ff5d5d'>"+str(weak)+"</b></div>"
      "<div>🟡 Средне<b style='color:#e0b341'>"+str(mid)+"</b></div>"
      "<div>⚪ Мало данных<b style='color:#9a9aa3'>"+str(low)+"</b></div>"
      "<div>🪦 Мёртвые<b style='color:#ff9d9d'>"+str(len(dead_list))+"</b></div></div>"
      + (("<div style='margin:8px 0 12px'><button onclick='deactAll()' style='padding:8px 16px;background:#3a1414;border:1px solid #6a2020;color:#ff9d9d;border-radius:9px;cursor:pointer;font-weight:700'>🪦 Отключить все мёртвые ("+str(len(dead_list))+")</button> <span class=muted style='font-size:13px'>— уйдут в неактивные в OLX, можно вернуть командой activate</span></div>") if dead_list else "") +
      "<table><thead><tr><th>Кабинет</th><th>Услуга</th><th>Город</th><th>Объявление</th><th>ID</th>"
      "<th>В работе</th><th class=num>👁 за нед</th><th class=num>Лиды</th><th class=num>📞</th><th class=num>Конв.</th>"
      "<th>Оценка</th><th>ТОП</th><th>Рекомендация</th></tr></thead>"
      "<tbody>"+(body or "<tr><td colspan=13>нет объявлений под фильтр</td></tr>")+"</tbody></table>" + SORTJS +
      "<script>window.__dead="+json.dumps(dead_list, ensure_ascii=False)+";"
      "async function deact(id,acc,btn){if(!confirm('Отключить объявление '+id+'? Уйдёт в неактивные, можно вернуть.'))return;btn.disabled=true;btn.textContent='…';try{const r=await fetch('/deactivate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,account:acc})});const j=await r.json();if(j.ok){btn.textContent='✓ отключено';const tr=btn.closest('tr');if(tr)tr.style.opacity=.4;}else{btn.disabled=false;btn.textContent='🪦 Отключить';alert('Ошибка: '+(j.error||''));}}catch(e){btn.disabled=false;btn.textContent='🪦 Отключить';alert('Сеть: '+e);}}"
      "async function deactAll(){const d=window.__dead||[];if(!d.length)return;if(!confirm('Отключить все мёртвые ('+d.length+')? Уйдут в неактивные, можно вернуть.'))return;for(const x of d){try{await fetch('/deactivate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(x)});}catch(e){}}location.reload();}"
      "</script>")