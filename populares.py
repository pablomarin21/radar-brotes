"""Qué cuenta como noticia «popular» para el radar.

24-nov, Pablo: «quiero noticias que impacten de verdad al mercado… cosas más populares».
Ese día salieron Abercrombie, Kohl's, Analog Devices, Applied Optoelectronics y Salesforce: noticias reales,
pero de empresas que el público español no conoce. Desde ahora el radar solo avisa cuando la noticia va de:
  · las entidades de entidades.py (Nvidia, Apple, Tesla, Fed, BCE, Santander, Inditex…),
  · o las de esta lista: grandes marcas que todo el mundo conoce, el IBEX 35 y las grandes europeas.
Una empresa fuera de la lista solo pasa si la cuenta todo el mundo a la vez (≥ MEGA medios).
Para añadir un nombre: clave → alias en minúsculas y sin tildes (como aparecen en los titulares).
"""
import re

MEGA = 25

POP_ENT = {
    # EE. UU.: marcas que conoce cualquiera
    "disney": ["disney"], "boeing": ["boeing"], "pfizer": ["pfizer"], "nike": ["nike"], "cocacola": ["coca-cola", "coca cola"],
    "mcdonalds": ["mcdonald"], "starbucks": ["starbucks"], "uber": ["uber"], "airbnb": ["airbnb"], "spotify": ["spotify"],
    "mastercard": ["mastercard"], "lilly": ["eli lilly"],
    "novo": ["novo nordisk", "ozempic", "wegovy"], "coinbase": ["coinbase"], "microstrategy": ["microstrategy"],
    "ethereum": ["ethereum"], "musk": ["elon musk", "musk"], "softbank": ["softbank"],
    # Europa y Asia
    "asml": ["asml"], "sap": ["sap"], "lvmh": ["lvmh"], "ferrari": ["ferrari"], "volkswagen": ["volkswagen"], "bmw": ["bmw"],
    "mercedes": ["mercedes-benz"], "stellantis": ["stellantis"], "renault": ["renault"], "airbus": ["airbus"], "siemens": ["siemens"],
    "nestle": ["nestle"], "totalenergies": ["totalenergies"], "byd": ["byd"], "xiaomi": ["xiaomi"], "alibaba": ["alibaba"],
    "toyota": ["toyota"], "samsung": ["samsung"], "sony": ["sony"],
    # IBEX 35 (los que no estaban ya) y grandes españolas
    "bankinter": ["bankinter"], "unicaja": ["unicaja"], "ferrovial": ["ferrovial"], "acs": ["acs"], "aena": ["aena"],
    "amadeus": ["amadeus"], "iag": ["iag", "iberia", "british airways", "vueling"], "naturgy": ["naturgy"], "endesa": ["endesa"],
    "grifols": ["grifols"], "indra": ["indra"], "cellnex": ["cellnex"], "mapfre": ["mapfre"], "acciona": ["acciona"],
    "redeia": ["redeia", "red electrica"], "enagas": ["enagas"], "puig": ["puig"], "rovi": ["rovi"], "solaria": ["solaria"],
    "sacyr": ["sacyr"], "arcelormittal": ["arcelormittal"], "mercadona": ["mercadona"], "elcorteingles": ["el corte ingles"],
}

# «fed» también es un verbo inglés: «Dog Follows Funeral of Man Who Fed Him» (20 medios, 24-nov) no es la Reserva Federal
NO_FED = re.compile(r"\b(who|that|which|was|were|been|being|get|got|gets|well|grass|breast|spoon|force|hand|i|we|they|he|she|you|many|is|are)[- ]fed\b"
                    r"|\bfed (him|her|them|us|me|you|it|his|their|my|our|up|through|by)\b|\bfed minister"
                    r"|\bfed\b.{0,40}\b(calories|dog|cat|baby|babies|animals?|cattle|livestock)\b")
FED_SEGURO = ("federal reserve", "reserva federal", "jerome powell", "warsh", "fomc", "waller")

# Cobertura mínima para que un titular de Investing.com España sea aviso: otros N medios con la misma empresa o tema en 2 h
# (24-nov: con 2 salía «Ingresos de Xiaomi se mantienen estables», 4 medios; Nvidia arrastrando a los chips tenía 169)
INV_MIN = 5
# 25-nov, Pablo: «noticias que realmente impacten al mercado y a los inversores del día a día».
# …y que hable de algo que MUEVE el mercado (sube, cae, aranceles, tipos, OPA…), no de una opinión:
# «Goldman Sachs: el comercio de IA depende de los retornos, no de Nvidia» no es aviso; «los chips caen tras el rally de Nvidia», sí
IMPACTO = re.compile(r"\b(sube|suben|subida|dispara|disparan|rebota|rebotan|rebote|repunta|repuntan|cae|caen|caida|hunde|hunden|"
                     r"desploma|desploman|desplome|derrumba|derrumbe|arrastra|arrastran|lastra|lastran|rally|record|pierde|pierden|"
                     r"gana|ganan|vuela|vuelan|crash|tipos|aranceles?|opa|fusion|adquiere|adquisicion|compra|quiebra|despide|despidos|"
                     r"dimite|recorta|recortes|eleva|multa|demanda|prohibe|sancion|sanciones|rescate|suspende|veto|alerta|"
                     # lo mismo en inglés, para los estallidos (la mayoría de titulares llegan en inglés)
                     r"soars?|soared|surges?|surged|plunges?|plunged|tumbles?|tumbled|slumps?|slumped|sinks?|sank|jumps?|jumped|"
                     r"rall(y|ies|ied)|crash(es)?|sell-?off|rout|rebounds?|falls?|fell|drops?|dropped|rises?|rose|gains?|slides?|slid|"
                     r"skyrockets?|hikes?|rate cuts?|tariffs?|inflation|bankrupt(cy)?|takeover|merger|acquires?|buyout|layoffs?|job cuts|"
                     r"antitrust|halts?|debut|salida a bolsa|opv|estreno)\b|\d ?%")
# Oro, petróleo, bonos, bitcoin, bolsas y vivienda salen TODOS los días («El oro cae…», «Los rendimientos de los bonos caen…»):
# en Investing directo solo cuentan si el movimiento es fuerte (≥ 2 %, récord, desplome…). Aranceles, IPC o empleo sí valen siempre.
SOLO_FUERTE = {"oro", "petroleo", "bonos", "bitcoin", "wallstreet", "vivienda"}
FUERTE = re.compile(r"hunde|desplom|dispara|record|historic|mayor (caida|subida|desplome|alza)|crash|panico|plunge|soar|"
                    r"\b([2-9]|\d{2})([.,]\d+)? ?%")
# Investing directo: no dos avisos de la misma empresa o tema en menos de 3 h (24-nov: Nvidia a las 08:51 y otra vez a las 09:15)
MISMA_FICHA_H = 3  # (cuenta aunque la empresa fuera secundaria en el aviso anterior)
# Plantillas de Investing que no son noticia («Movimientos previos a la apertura: Nvidia cae; HPE y Semtech bajan»)
RELLENO_EXTRA = re.compile(r"movimientos (previos|en el mercado|destacados|del mercado)|valores (que|a) (seguir|vigilar)|"
                           r"claves (del|de la|para la) (dia|sesion|semana)|lo que (hay que|debes) saber|resumen (del|de la)|"
                           # un banco opinando de otra empresa («Goldman mejora ITM Power tras caída del 61 %») no es noticia de ese banco
                           r"^(goldman( sachs)?|jp ?morgan|morgan stanley|ubs|barclays|citi(group)?|bank of america|bofa|jefferies|bernstein|"
                           r"deutsche bank|hsbc|wells fargo|santander|bbva|renta 4|bankinter) (mejora|rebaja|eleva|recorta|ve |preve|espera|cree|"
                           r"inicia|reitera|apuesta|recomienda|sube el precio|baja el precio)", re.I)

# Lo que mueve el dinero de cualquier inversor (tipos, bancos centrales): cuenta siempre como impacto
MERCADO = {"fed", "bce", "boj", "boe", "inflacion", "empleo", "pib", "aranceles", "vivienda", "petroleo", "oro", "bitcoin", "bonos",
           "ibex", "wallstreet"}

# Alias nuevos para entidades que ya existían
ALIAS = {"amd": ["advanced micro devices"], "nvidia": ["jensen huang"]}


def aplicar(R):
    """Mete la lista en el ENT del radar (llamar justo después de importarlo)."""
    for k, al in POP_ENT.items():
        R.ENT.setdefault(k, al)
    for k, al in ALIAS.items():
        R.ENT[k] = R.ENT[k] + [a for a in al if a not in R.ENT[k]]
    # «Powell» a secas cazaba a un escritor (Tom Powell) y a un jugador de snooker (Riley Powell); la Fed ya es de Warsh
    R.ENT["fed"] = [x for x in R.ENT["fed"] if x != "powell"] + ["jerome powell", "warsh"]
