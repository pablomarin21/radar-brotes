#!/usr/bin/env python3
"""Radar de ESTALLIDOS de noticias financieras. Sin IA, solo la biblioteca estándar de Python.

Una noticia gorda se nota porque de golpe la cuentan muchos medios a la vez. Salta solo si:
  1) un nombre (empresa, persona, banco central…) aparece en ≥ MIN_MEDIOS medios distintos en los últimos VENTANA min,
  2) eso es ≥ FACTOR veces lo normal para ese nombre en las 6 h anteriores (un tema de fondo no dispara),
  3) los titulares son de mercados/empresas/economía,
  4) ese nombre no tuvo disparo en ENFRIAR_H horas (salvo que el tema vuelva con el DOBLE de medios) y no se pasó el
     tope del día.

    python3 radar.py              # una pasada: lee titulares, guarda el estado e imprime los disparos nuevos (JSON)
    python3 radar.py --avisar-git DIR   # además deja cada disparo en DIR/aviso.json (copia de trabajo de la rama de
                                        #   avisos) y hace commit + push, si no se avisó ya en las últimas 48 h

Solo lee titulares + medio + hora de feeds RSS públicos: no baja artículos.
"""
import base64, email.utils, gzip, json, os, re, sys, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import entidades as R

TZ = ZoneInfo("Europe/Madrid")
UA = {"User-Agent": "news-burst-radar/1.0"}
AQUI = Path(__file__).resolve().parent
ESTADO = Path(os.environ.get("RADAR_ESTADO", AQUI / "estado.json"))
SEMILLA = AQUI / "semilla.json.gz"  # solo se usa si no hay estado (primer arranque o caché perdida)
VENTANA, MIN_MEDIOS, FACTOR, ENFRIAR_H, TOPE_DIA, ESCALADA = 20, 8, 4.0, 48, 12, 15  # 24-nov: 12→8 medios y tope 3→12 (se escapaban Tesla–SpaceX, Fed Williams…)

GN = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={gl}:{lang}"
Q_EN = '(stock OR shares OR CEO OR "Wall Street" OR earnings OR merger OR acquisition OR IPO OR "Federal Reserve" OR bankruptcy OR tariffs)'
Q_ES = '(bolsa OR acciones OR "consejero delegado" OR CEO OR BCE OR Ibex OR OPA OR fusión OR resultados OR Fed OR aranceles)'
def gn(q, lang):
    hl, gl, lg = ("en-US", "US", "en") if lang == "en" else ("es", "ES", "es")
    return GN.format(q=urllib.parse.quote(q), hl=hl, gl=gl, lang=lg)

VIVO = {
    "gn_en": (gn(Q_EN + " when:1h", "en"), None), "gn_es": (gn(Q_ES + " when:1h", "es"), None),
    "gn_tec": (gn("(Nvidia OR Apple OR Microsoft OR Tesla OR Amazon OR Alphabet OR Google OR Meta OR OpenAI OR Anthropic OR SpaceX OR Intel OR AMD) when:1h", "en"), None),
    "gn_tec_es": (gn("(Nvidia OR Apple OR Microsoft OR Tesla OR Amazon OR Google OR Meta OR OpenAI OR Anthropic OR SpaceX) when:1h", "es"), None),
    "gn_bc": (gn('("Federal Reserve" OR Fed OR ECB OR Powell OR Warsh OR Lagarde OR "Bank of Japan") when:1h', "en"), None),
    "gn_ibex": (gn("(Ibex OR Santander OR BBVA OR Inditex OR Iberdrola OR Telefónica OR Repsol OR CaixaBank OR Sabadell OR BCE) when:1h", "es"), None),
    "gn_bus_us": ("https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en", None),
    "gn_bus_es": ("https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=es&gl=ES&ceid=ES:es", None),
    "bbg_mk": ("https://feeds.bloomberg.com/markets/news.rss", "Bloomberg"),
    "bbg_te": ("https://feeds.bloomberg.com/technology/news.rss", "Bloomberg"),
    "cnbc": ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "CNBC"),
    "mw_bul": ("https://feeds.content.dowjones.io/public/rss/mw_bulletins", "MarketWatch"),
    "inv": ("https://es.investing.com/rss/news.rss", "Investing.com España"),
    "inv_25": ("https://es.investing.com/rss/news_25.rss", "Investing.com España"),
    "inv_1": ("https://es.investing.com/rss/news_1.rss", "Investing.com España"),
    "inv_11": ("https://es.investing.com/rss/news_11.rss", "Investing.com España"),
    "inv_14": ("https://es.investing.com/rss/news_14.rss", "Investing.com España"),
    "inv_95": ("https://es.investing.com/rss/news_95.rss", "Investing.com España"),
    "inv_301": ("https://es.investing.com/rss/news_301.rss", "Investing.com España"),
    "inv_287": ("https://es.investing.com/rss/news_287.rss", "Investing.com España"),
    "inv_288": ("https://es.investing.com/rss/news_288.rss", "Investing.com España"),  # 24-nov: a Pablo le gustan sus noticias
    "exp": ("https://e00-expansion.uecdn.es/rss/mercados.xml", "Expansión"),
    "cinco": ("https://feeds.elpais.com/mrss-s/pages/ep/site/cincodias.elpais.com/portada", "Cinco Días"),
    "ep": ("https://www.europapress.es/rss/rss.aspx?ch=00136", "Europa Press"),
}

FIN = ["stock", "stocks", "shares", "ceo", "market", "markets", "investor", "investors", "earnings", "profit", "revenue", "deal",
       "merger", "acquisition", "acquire", "ipo", "bank", "fed", "rates", "rate", "inflation", "bond", "yields", "tariff", "oil",
       "board", "chief executive", "billion", "valuation", "bolsa", "acciones", "mercado", "mercados", "inversores", "beneficio",
       "ventas", "opa", "fusion", "compra", "banco", "tipos", "inflacion", "consejo", "consejero delegado", "presidente ejecutivo",
       "millones", "valoracion", "cotizacion", "dispara", "desploma", "sube", "cae", "soar", "plunge", "jump", "surge", "slump"]
NO_NOMBRE = set("""the a an and or of to in on for at by with from as is are was be after before over under into amid
new says said say will would could may might its it this that these those his her their what why how who when where
stock stocks shares market markets wall street ceo chief executive board us u.s. uk eu ai news live update updates report
week today day monday tuesday wednesday thursday friday saturday sunday year years month quarter q1 q2 q3 q4 record
jump jumps soar soars surge surges fall falls plunge plunges drop drops rise rises gains gain loses loss rally slump
reinstates reinstated return returns back comeback rehire rehires names named exit exits steps down out up
el la los las un una y o de del al en por para con sin sobre tras ante segun como que se su sus es son fue ha han
bolsa acciones mercado mercados hoy ayer este esta lunes martes miercoles jueves viernes sabado domingo nuevo nueva
consejero delegado presidente ejecutivo director sube suben cae caen dispara disparan desploma vuelve vuelta regreso
here heres what's whats inc corp co ltd plc sa group holdings
earnings call price below above chart analysis shows trading premarket results reports sales net tech just cup
billion billions million millions tokenized artificial intelligence deals best picks sale incredible happens calculator ondo buy convierte invest
usd acquisition corporation technologies commerce revenue stifel upgrades downgrades rating target""".split())
GEN = R.ENT_GEN | {"wallstreet", "ia", "trump", "china", "ipo", "oro", "petroleo", "pib", "inflacion", "empleo", "vivienda",
                   "bonos", "aranceles", "bitcoin", "pce", "rising", "prices", "falling", "growth", "outlook", "forecast",
                   "analysts", "investors", "europe", "european", "asia", "asian", "america", "american", "global", "black", "friday"}


def medio_de(it, fijo):
    if fijo:
        return fijo
    s = it.find("source")
    if s is not None and (s.text or "").strip():
        return s.text.strip()
    m = re.search(r"\s[-–]\s([^-–]{2,40})$", it.findtext("title") or "")
    return m.group(1).strip() if m else "?"


def limpia(t):
    return re.sub(r"\s[-–]\s[^-–]{2,40}$", "", t).strip()


def leer(url, fijo):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
    out = []
    for it in ET.fromstring(raw).findall(".//item"):
        t, link = (it.findtext("title") or "").strip(), (it.findtext("link") or "").strip()
        try:
            pub = email.utils.parsedate_to_datetime(it.findtext("pubDate")).astimezone(TZ).isoformat(timespec="seconds")
        except Exception:
            pub = None
        if t and link:
            out.append({"t": limpia(t), "o": medio_de(it, fijo), "link": link, "pub": pub})
    return out


_CACHE = {}


def nombres(t):
    if t in _CACHE:
        return _CACHE[t]
    _CACHE[t] = r = _nombres(t)
    return r


def _nombres(t):
    """Fichas de un titular: entidades conocidas (ES/EN) + nombres propios (palabras con mayúscula no comunes)."""
    n = R.norm(t)
    fichas = {c for c, al in R.ENT.items() if any(R.has(a, n) for a in al)}
    for w in re.findall(r"[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ&\-]+(?:'s|’s)?", t):
        k = R.norm(re.sub(r"('s|’s)$", "", w))
        if len(k) >= 3 and k not in NO_NOMBRE:
            fichas.add(k)
    for c, al in R.ENT.items():  # alias → canónica (google→alphabet, powell→fed…)
        for a in al:
            if R.norm(a) in fichas and " " not in a:
                fichas.discard(R.norm(a)); fichas.add(c)
    return fichas


def es_finanzas(t):
    n = R.norm(t)
    return any(R.has(k, n) for k in FIN)


# Dos redes (24-nov): el ESTALLIDO (≥ MIN_MEDIOS en 20 min) y la noticia que corre MÁS DESPACIO (≥ 12 medios en 2 h,
# ≥ 3× lo normal). Ej.: la fusión Tesla–SpaceX se contó poco a poco (15 titulares de 11:26 a 14:44) y la red rápida no la vio.
# 3.ª red (24-nov, Pablo: «me gustan mucho las noticias de investing.com»): lo que publica Investing.com ESPAÑA (sus
# feeds en español; ojo: Google News llama «Investing.com» a la web inglesa, que NO cuenta aquí) y en 2 h recogen
# ≥ 7 medios más (8 en total), a ≥ 4× lo normal. Su titular (en español) va de principal en el aviso.
VENTANAS = [(VENTANA, None, None, None), (120, 12, 3.0, None), (120, 8, 4.0, "Investing.com España")]


def evaluar(items, ahora, E):
    """items: dicts con t, o, ts(datetime). Devuelve disparos nuevos (y los apunta en E)."""
    hoy = ahora.strftime("%Y-%m-%d")
    hechos_hoy = sum(d["ts"][:10] == hoy for d in E["disparos"])
    nuevos, cands, ya = [], [], set()
    for ven, minimo, factor, exige in VENTANAS:
        minimo, factor = minimo or MIN_MEDIOS, factor or FACTOR
        v0 = ahora - timedelta(minutes=ven)
        b0 = ahora - timedelta(hours=6) if ven == VENTANA else v0 - timedelta(hours=6)
        recientes = [x for x in items if v0 < x["ts"] <= ahora]
        previos = [x for x in items if b0 < x["ts"] <= v0]
        por = {}
        for x in recientes:
            for f in nombres(x["t"]):
                por.setdefault(f, []).append(x)
        base = {}
        for x in previos:
            for f in nombres(x["t"]):
                base.setdefault(f, set()).add(x["o"])
        for f, xs in por.items():
            if f in GEN or f in ya:
                continue
            medios = {x["o"] for x in xs}
            if len(medios) < minimo or (exige and exige not in medios):
                continue
            normal = max(0.5, len(base.get(f, ())) / ((b0 - v0).total_seconds() / -60 / ven))
            if len(medios) < factor * normal:
                continue
            if sum(es_finanzas(x["t"]) for x in xs) < 0.5 * len(xs):
                continue
            cands.append((len(medios) / normal, f, xs, medios, normal))
            ya.add(f)
    for ratio, f, xs, medios, normal in sorted(cands, key=lambda c: -c[0]):
        if hechos_hoy >= TOPE_DIA:
            break
            continue
        junto = {}
        for x in xs:
            for g in nombres(x["t"]) - {f}:
                junto[g] = junto.get(g, 0) + 1
        socios = [g for g, c in sorted(junto.items(), key=lambda kv: -kv[1]) if c >= max(2, len(xs) // 3)][:3]
        # Ya avisado = mismo nombre Y algo más en común (SpaceX+IPO ≠ SpaceX+fusión con Tesla: otra noticia). 24-nov.
        # Escalada: la misma historia vuelve con el DOBLE de medios (y ≥ ESCALADA) → se avisa otra vez.
        clave = {f} | set(socios)
        frio = [d for d in E["disparos"] if f in d["fichas"] and (len(clave & set(d["fichas"])) >= 2 or len(d["fichas"]) == 1 or not socios)
                and (ahora - datetime.fromisoformat(d["ts"])).total_seconds() < ENFRIAR_H * 3600]
        if frio and not (len(medios) >= ESCALADA and len(medios) >= 2 * max(d["medios"] for d in frio)):
            continue
        rep = max(xs, key=lambda x: (len(nombres(x["t"]) & ({f} | set(socios))), x["o"] == "Investing.com España", "newsroom" in x["o"].lower() or "press" in x["o"].lower(), x["o"] in ("Investing.com", "Expansión", "Cinco Días", "EL PAÍS", "Europa Press", "Investing.com España")))
        es = [x for x in xs if re.search(r"[áéíóúñ¿¡]| (el|la|los|las|del|tras) ", x["t"])]
        d = {"ts": ahora.isoformat(timespec="seconds"), "fichas": [f] + socios, "medios": len(medios), "normal": round(normal, 1),
             "titular": rep["t"], "medio": rep["o"], "link": rep.get("link", ""),
             "titulares": [{"o": x["o"], "t": x["t"], "link": x.get("link", "")} for x in sorted(xs, key=lambda x: x["ts"])][:12],
             "en_espanol": [x["t"] for x in es][:5],
             "investing": [{"t": x["t"], "link": x.get("link", "")} for x in xs if x["o"] == "Investing.com España"][:5]}
        E["disparos"].append(d)
        nuevos.append(d)
        hechos_hoy += 1
    return nuevos


def a_items(vistos):
    out = []
    for x in vistos.values():
        try:
            out.append({**x, "ts": datetime.fromisoformat(x.get("pub") or x["visto"])})
        except Exception:
            pass
    return out


# ---------- avisos (repo privado de avisos, vía API de GitHub) ----------
def _gh(ruta, metodo="GET", cuerpo=None):
    req = urllib.request.Request(f"https://api.github.com{ruta}", method=metodo,
                                 data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 headers={"Authorization": f"Bearer {os.environ['GH_TOKEN_AVISOS']}", "Accept": "application/vnd.github+json",
                                          "User-Agent": UA["User-Agent"], "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read() or b"null")


def avisos_recientes(repo, rama):
    """Los avisos ya enviados (por este radar o por otro), leídos de los últimos commits de la rama de avisos."""
    out = []
    for c in _gh(f"/repos/{repo}/commits?sha={rama}&per_page=20"):
        msg = c["commit"]["message"]
        try:
            out.append(json.loads(msg[msg.index("{"):]))
        except Exception:
            pass
    return out


def ya_avisado(d, previos):
    """¿Ya se avisó de esto en ENFRIAR_H horas? (salvo escalada: el doble de medios y ≥ ESCALADA)."""
    t = datetime.fromisoformat(d["ts"])
    for a in previos:
        try:
            ta = datetime.fromisoformat(a["ts"])
        except Exception:
            continue
        if not (0 <= (t - ta).total_seconds() < ENFRIAR_H * 3600):
            continue
        fa = a.get("fichas", [])
        if d["fichas"][0] in fa and (len(set(d["fichas"]) & set(fa)) >= 2 or len(fa) == 1 or len(d["fichas"]) == 1):
            if not (d["medios"] >= ESCALADA and d["medios"] >= 2 * a.get("medios", 0)):
                return True
    return False


def avisar(d):
    repo, rama = os.environ["REPO_AVISOS"], os.environ.get("RAMA_AVISOS", "avisos")
    if ya_avisado(d, avisos_recientes(repo, rama)):
        return "ya avisado"
    try:
        sha = _gh(f"/repos/{repo}/contents/aviso.json?ref={rama}")["sha"]
    except Exception:
        sha = None
    js = json.dumps(d, ensure_ascii=False, indent=1)
    cuerpo = {"message": f"AVISO {d['ts'][11:16]} · {d['titular'][:120]}\n\n{js}", "content": base64.b64encode(js.encode()).decode(),
              "branch": rama, "committer": {"name": "radar", "email": "radar@users.noreply.github.com"}}
    if sha:
        cuerpo["sha"] = sha
    _gh(f"/repos/{repo}/contents/aviso.json", "PUT", cuerpo)
    return "ok"


def _git(d, *args, **kw):
    import subprocess
    return subprocess.run(["git", "-C", str(d), *args], capture_output=True, text=True, timeout=60, **kw)


def avisos_git(d):
    """Avisos ya enviados (por cualquier radar): los mensajes de los últimos commits de la rama de avisos."""
    out = []
    for msg in _git(d, "log", "-20", "--format=%B%x00").stdout.split("\x00"):
        try:
            out.append(json.loads(msg[msg.index("{"):]))
        except Exception:
            pass
    return out


def avisar_git(disp, d):
    """Escribe aviso.json en la copia de la rama de avisos (d) y hace commit + push. Reintenta si otro radar empujó antes."""
    for intento in range(3):
        _git(d, "pull", "-q", "--rebase", "origin", "avisos")
        if ya_avisado(disp, avisos_git(d)):
            return "ya avisado"
        js = json.dumps(disp, ensure_ascii=False, indent=1)
        (Path(d) / "aviso.json").write_text(js)
        _git(d, "add", "aviso.json")
        _git(d, "-c", "user.name=radar", "-c", "user.email=radar@users.noreply.github.com", "commit", "-q",
             "-m", f"AVISO {disp['ts'][11:16]} · {disp['titular'][:120]}", "-m", js)
        r = _git(d, "push", "-q", "origin", "HEAD:avisos")
        if r.returncode == 0:
            return "ok"
        _git(d, "reset", "-q", "--hard", "origin/avisos")
        time.sleep(3)
    return "FALLO push: " + r.stderr[-200:]


# ---------- pasada ----------
def cargar():
    if ESTADO.exists():
        return json.loads(ESTADO.read_text())
    if SEMILLA.exists():
        return json.loads(gzip.decompress(SEMILLA.read_bytes()))
    return {"vistos": {}, "disparos": [], "log": []}


def vivo():
    E = cargar()
    ahora = datetime.now(TZ)
    errores = []
    for fid, (url, fijo) in VIVO.items():
        try:
            for it in leer(url, fijo):
                x = E["vistos"].setdefault(it["link"], {**it, "visto": ahora.isoformat(timespec="seconds")})
                if not x.get("pub") or not (ahora - timedelta(hours=30) < datetime.fromisoformat(x["pub"]) <= ahora + timedelta(minutes=5)):
                    x["pub"] = x["visto"]
        except Exception as e:
            errores.append(f"{fid}: {str(e)[:50]}")
        time.sleep(0.5)
    lim = (ahora - timedelta(hours=30)).isoformat()
    E["vistos"] = {k: v for k, v in E["vistos"].items() if v["visto"] >= lim}
    # sin 6 h de historia (estado perdido y sin semilla) no hay «lo normal» con qué comparar: aprende, no avisa
    mas_viejo = min((v["visto"] for v in E["vistos"].values()), default=ahora.isoformat())
    aprendiendo = datetime.fromisoformat(mas_viejo) > ahora - timedelta(hours=6)
    nuevos = [] if aprendiendo else evaluar(a_items(E["vistos"]), ahora, E)
    notas = []
    if "--avisar-git" in sys.argv:
        dir_avisos = sys.argv[sys.argv.index("--avisar-git") + 1]
        for d in nuevos:
            try:
                notas.append(f"aviso {d['ts'][11:16]} → {avisar_git(d, dir_avisos)}")
            except Exception as e:
                notas.append(f"aviso {d['ts'][11:16]} → FALLO {str(e)[:120]}")
    if "--avisar" in sys.argv:
        for d in nuevos:
            try:
                notas.append(f"aviso {d['ts'][11:16]} → {avisar(d)}")
            except Exception as e:
                notas.append(f"aviso {d['ts'][11:16]} → FALLO {str(e)[:120]}")
    E["disparos"] = E["disparos"][-200:]
    E["log"] = (E["log"] + [f"{ahora:%Y-%m-%d %H:%M} · {len(E['vistos'])} vistos · {len(nuevos)} disparos" + (" · APRENDIENDO" if aprendiendo else "")
                            + (f" · ERRORES {errores}" if errores else "") + (f" · {' · '.join(notas)}" if notas else "")])[-500:]
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ESTADO.with_suffix(".tmp"); tmp.write_text(json.dumps(E, ensure_ascii=False)); tmp.replace(ESTADO)
    print(E["log"][-1])
    print(json.dumps(nuevos, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    vivo()
