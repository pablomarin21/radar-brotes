# radar-brotes

Detector de **estallidos de noticias financieras**: cada 5 minutos lee titulares de feeds RSS públicos (Google News,
Bloomberg, CNBC, MarketWatch, Investing, Expansión, Cinco Días, Europa Press) y salta cuando un mismo nombre aparece
de golpe en muchos medios distintos (≥ 12 en 20 minutos y ≥ 4 veces lo normal de las 6 horas anteriores).

Sin IA y sin dependencias: solo la biblioteca estándar de Python. Solo lee titulares, medio y hora; no baja artículos.
El estado (titulares vistos en las últimas 30 h y disparos) se guarda en la caché de GitHub Actions entre pasadas.

```
python3 radar.py            # una pasada: imprime los disparos nuevos
python3 radar.py --avisar   # además los deja en el repositorio de avisos (GH_TOKEN_AVISOS, REPO_AVISOS)
```
