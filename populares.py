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
    "jpmorgan": ["jpmorgan", "jp morgan"], "goldman": ["goldman sachs"], "mastercard": ["mastercard"], "lilly": ["eli lilly"],
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
FED_SEGURO = ("federal reserve", "reserva federal", "powell", "fomc", "waller")

# Cobertura mínima para que un titular de Investing.com España sea aviso: otros N medios con la misma empresa o tema en 2 h
# (24-nov: con 2 salía «Ingresos de Xiaomi se mantienen estables», 4 medios; Nvidia arrastrando a los chips tenía 169)
INV_MIN = 5
# …y que hable de algo que MUEVE el mercado (sube, cae, aranceles, tipos, OPA…), no de una opinión:
# «Goldman Sachs: el comercio de IA depende de los retornos, no de Nvidia» no es aviso; «los chips caen tras el rally de Nvidia», sí
IMPACTO = re.compile(r"\b(sube|suben|subida|dispara|disparan|rebota|rebotan|rebote|repunta|repuntan|cae|caen|caida|hunde|hunden|"
                     r"desploma|desploman|desplome|derrumba|derrumbe|arrastra|arrastran|lastra|lastran|rally|record|pierde|pierden|"
                     r"gana|ganan|vuela|vuelan|crash|tipos|aranceles?|opa|fusion|adquiere|adquisicion|compra|quiebra|despide|despidos|"
                     r"dimite|recorta|recortes|eleva|multa|demanda|prohibe|sancion|sanciones|rescate|suspende|veto|alerta)\b|\d ?%")

# Alias nuevos para entidades que ya existían
ALIAS = {"amd": ["advanced micro devices"], "nvidia": ["jensen huang"]}


def aplicar(R):
    """Mete la lista en el ENT del radar (llamar justo después de importarlo)."""
    for k, al in POP_ENT.items():
        R.ENT.setdefault(k, al)
    for k, al in ALIAS.items():
        R.ENT[k] = R.ENT[k] + [a for a in al if a not in R.ENT[k]]
