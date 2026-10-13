# Editor y versiones

Cómo se produce cada parte del informe, qué hace el analista y cómo se versiona. El código está en [src/informes_warrants/informe/](../src/informes_warrants/informe/) y [src/informes_warrants/almacenamiento/](../src/informes_warrants/almacenamiento/).

## Quién produce cada bloque

Regla: **usar la IA lo menos posible**. Cada bloque se resuelve con la primera opción que funcione:

| Tipo | Quién | Bloques | Ejemplos |
|---|---|---|---|
| AUTO | Código | 18 | Tablas, múltiplos, gráficos, DCF, lista completa de riesgos, anexos, aviso legal |
| PLANTILLA | Texto fijo con huecos que rellena el código | 4 | Situación actual, descripción del negocio (cita literal del Item 1), comentario financiero, conclusión de la valoración |
| IA | Modelo de lenguaje, solo elige y resume fragmentos literales | **2** | Riesgos principales (Item 1A), catalizadores (MD&A) |
| ANALISTA | Analista, con marcador `[[ANALISTA: …]]` | 7 | Recomendación, titulares de la tesis, perspectivas, fortalezas, posicionamiento, mercado, consejo |

- La tabla completa está en [secciones.py](../src/informes_warrants/informe/secciones.py) y las plantillas Markdown en [plantillas/secciones/](../src/informes_warrants/plantillas/secciones/).
- Los bloques del analista también parten de una plantilla con los datos ya escritos, de modo que el analista solo completa los marcadores.
- Mientras quede algún marcador, el informe no se puede emitir.
- **Cómo usa la IA el SaaS:** el código extrae del 10-K los candidatos literales (títulos de riesgo en negrita o cursiva del Item 1A; frases prospectivas del MD&A) y los numera. El modelo solo devuelve números y un resumen de una línea. La cita la pone el código a partir del número elegido, así que no puede inventarse ([ia/seleccion.py](../src/informes_warrants/ia/seleccion.py)).

## Edición

Implementado en `ui/` (A12, `informes-warrants interfaz`) y `informe/versionado.py` (A11). La interfaz reúne una vez los datos de la SEC y del mercado (`reunir`) y recompone el informe sin red en cada cambio (`componer`); el analista puede sustituir los bloques ANALISTA y cualquier bloque que el SaaS dejó con un marcador.

- Markdown, con vista previa en tiempo real.
  - La vista HTML se regenera en cada cambio con la misma plantilla que el PDF (milisegundos).
  - El PDF se recompila en segundo plano: WeasyPrint tarda unos 2 s por documento.
- Recomendación: el SaaS propone el precio objetivo (media ponderada de los métodos con valor, con `pesos`: tabla «Derivación del precio objetivo») y una recomendación mecánica por potencial: **Comprar ≥ +15 %**, **Vender ≤ −10 %**, Mantener entre ambos. El analista la confirma o la cambia en el bloque `portada.recomendacion`. El informe muestra siempre el precio objetivo y el potencial calculados; si el analista fija su propio precio objetivo (`Estimaciones.precio_objetivo_analista`), prevalece en la portada junto al del DCF, y el potencial y la propuesta los recalcula el código (decisión del usuario, 2026-10-11).
- Emisión: un apartado **«Confirmar emisión del informe»** con un botón. Desde el 2026-10-14 los apartados pendientes **no bloquean**: se avisan y se completan después en una revisión nueva (botón «Seguir editando», v+1). Bloquean solo la calidad de los datos en rojo y unas estimaciones no válidas. Al emitir, la versión pasa a `emitida` y queda inmutable.
- Borradores de la IA: cada apartado del analista trae un borrador marcado (`ia/borradores.py`) que el analista revisa, edita o sustituye; mientras no lo marque como revisado, cuenta como pendiente.

## Estimaciones que ajusta el analista

Son los supuestos que mueven la proyección, el BPA estimado y el DCF ([estimaciones.py](../src/informes_warrants/informe/estimaciones.py)). Todo lo demás es histórico y no se toca. Los valores por defecto son la media de los 3 últimos periodos de doce meses (los 2 últimos ejercicios y el LTM).

| Estimación | Por defecto | Origen |
|---|---|---|
| Crecimiento de ventas (5 años explícitos) | Media de los 3 últimos periodos | Capa 2 |
| Margen EBITDA (5 años) | Media de los 3 últimos periodos | Capa 2 |
| Años de convergencia hacia g | 5 | financial-research-analyst-agent `dcf_model` (idea) |
| D&A, capex y circulante sobre ventas | Media de los 3 últimos periodos | Capa 2 |
| Tasa fiscal | Tipo efectivo medio (5-35 %) | Capa 2 |
| Tipo libre de riesgo (Rf) | Bono a 10 años del día (FRED DGS10) | `ingesta/mercado.tipo_libre_riesgo` |
| Prima de riesgo (ERP) | 5,5 % | financial-research-analyst-agent `_EQUITY_RISK_PREMIUM` |
| Beta | Semanal a 5 años frente al S&P 500 | Capa 1 |
| Coste de la deuda | Intereses / deuda | Capa 2 |
| g (perpetuidad) | 2,5 % | Informe de referencia |
| Resultado financiero / ventas, cuota de minoritarios, variación de acciones, pay-out | Medias de los 3 últimos ejercicios (las de ventas, como suma / suma) | Proyección hasta el BPA (`calculo/proyeccion.py`) |
| Remuneración en acciones / ventas, recompras / FCF tras SBC | Suma / suma y media de los 3 últimos ejercicios | Proyección del flujo y del balance (R12) |
| Pesos del precio objetivo (`pesos`) | DCF 50 %, comparables 50 %, múltiplos históricos 0 %, suma de partes 0 % | Se reparten entre los métodos con valor (R8) |
| Múltiplos de la suma de partes (`multiplos_sotp`) | Vacío: mediana EV/EBIT de los comparables del analista | EV/EBIT por segmento (R14) |
| Precio objetivo del analista | Vacío (manda el del modelo) | Decisión del usuario |

**Escenarios** (`Escenarios`): pesimista, base y optimista. Cada uno es un juego completo de estimaciones editable, con su desencadenante (`desencadenantes`; por defecto, sus supuestos en una frase). Por defecto, el pesimista y el optimista son la base ∓ 1 desviación típica histórica del crecimiento (2-5 pp) y del margen (1-3 pp), con probabilidades 25/50/25. El valor DCF es la media ponderada.

**Calendario de catalizadores** (`calendario`, A4): lo introduce preferentemente el analista. Mientras esté vacío, el informe muestra el borrador del SaaS marcado «Revisar» (fechas estimadas a partir de los filings, siempre posteriores a la emisión) y hay un aviso antes de emitir, que no bloquea.

**Comparables:** el SaaS propone una lista por SIC y tamaño, marcada «Revisar», **solo orientativa**: no entra en el precio objetivo (que queda por DCF) y genera un **aviso antes de emitir**, que no bloquea la emisión ni aparece en el informe (`Version.avisos()`). El analista introduce su lista (`construir(..., comparables=[...])`, o `--comparables` en la CLI) para que la valoración por múltiplos entre en el precio objetivo.

Los valores se validan: rangos razonables, g inferior al coste del capital y probabilidades que suman 100 %.

**Autoría** (R6): nombre, correo y teléfono del analista, empresa y su contacto. Los introduce cada usuario (`informes-warrants autoria`; en la interfaz, la pantalla de configuración) y se guardan en `autoria.json` de la carpeta de datos, nunca en el repositorio. Vacíos, la portada no muestra el bloque.

**Cambios frente al informe anterior** (R16): cada informe guarda su resumen JSON junto al PDF; `--comparar-con <resumen.json>` muestra qué cambió y cuánto explica cada grupo de supuestos del cambio del valor DCF (atribución secuencial, que cuadra con el total). El historial de recomendaciones (R17) sale de las versiones emitidas.

## Qué puede tocar el analista en el bloque fijo

Solo **dos** cosas, cada una con motivo obligatorio y visible en el informe ([bloque_fijo.py](../src/informes_warrants/informe/bloque_fijo.py)):

1. **Comparables: quitar o añadir.** El SaaS los propone por código SIC y tamaño, pero el SIC agrupa negocios distintos (por ejemplo, Apple con fabricantes de PC). Solo quien conoce el negocio sabe si un comparable lo es de verdad.
2. **Partidas no recurrentes del EBITDA.** El SaaS no puede decidir si un gasto se repetirá. Como referencia muestra el *Adjusted EBITDA* que publica la empresa (edgartools `earnings.py`), y el analista marca qué partidas excluye.

Descartado, con el motivo:

| Ajuste | Por qué no |
|---|---|
| Editar cifras, tablas o gráficos | Salen de la SEC; editarlas rompe el rigor y la trazabilidad |
| Ocultar o reordenar secciones | La estructura fija hace comparables las versiones y las empresas |
| Elegir años o periodos | El SaaS usa los 5 últimos ejercicios + TTM del último filing |
| Elegir índice de referencia | Lo asigna el SaaS: S&P 500 + ETF sectorial por SIC |
| Corregir la clasificación sectorial | La da edgartools; si no encaja, la empresa va a «plantilla pendiente de validar» |
| Cambiar fórmulas de métricas | Las definiciones son únicas en la capa 2, iguales para todos los informes |

## Alcance

Se cubren todas las empresas de EEUU que presentan informes a la SEC, con la plantilla que corresponde a su categoría de negocio (edgartools `Company.business_category`). Código: [cobertura.py](../src/informes_warrants/informe/cobertura.py) y [perfiles.py](../src/informes_warrants/calculo/perfiles.py).

| Categoría | Plantilla | Métricas propias | Valoración | Validada con |
|---|---|---|---|---|
| Empresa operativa, holding, gestora | General | Capa 2 | DCF + múltiplos | AAPL, MSFT, TSLA |
| Banco, agencia de crédito | Banca | Margen de intereses/activos, eficiencia, coste del riesgo, préstamos/depósitos, ROE, ROA, ROTE, patrimonio tangible | P/BV y P/TBV vs ROE/ROTE; P/BV justo = (ROE − g)/(Ke − g) | JPM, BAC, WFC |
| Aseguradora | Seguros | Siniestralidad, gastos, ratio combinado, rendimiento de inversiones, ROE | P/BV vs ROE; PER | TRV, ALL, PGR |
| REIT | Inmobiliario | FFO, dividendos/FFO, deuda/activos (LTV), ROE | P/FFO, rentabilidad por dividendo | O, PLD, SPG |
| BDC, fondo cerrado | Inversión | NAV por acción, cobertura del dividendo, deuda/patrimonio, ingreso neto de inversiones/patrimonio | P/NAV, rentabilidad por dividendo | ARCC, MAIN, FSK |
| Emisor extranjero (20-F/40-F) | La de su categoría | Las de su categoría, en USD | La de su categoría | TSM (20-F, IFRS, TWD) |
| SPAC, ETF, fondo abierto, desconocida | **Plantilla pendiente de validar** | — | — | — |

**Qué resolvían los repos y qué se ha construido:**
- **Datos de los repos:**
  - edgartools ya extrae los estados propios de banca, seguros, inmobiliario y sociedades de inversión (`entity/data/industry_extensions/`), y los de fondos y BDC (`funds/`, `bdc/`).
  - También extrae el 20-F (`TwentyF.risk_factors`, Item 3.D) y los tipos de cambio declarados (`xbrl/currency.CurrencyConverter`).
  - Los textos (riesgos y MD&A) funcionan igual en todas las categorías.
- **Métricas construidas aquí:** NIM, eficiencia, ratio combinado, FFO, P/TBV y NAV no estaban en ningún repo (verificado con grep en los 9). edgar_analytics, con `is_financial=True`, solo desactiva el circulante y el Altman Z. Se calculan sobre conceptos us-gaap con alternativas, y cada cifra lleva su concepto, su ejercicio y su número de registro (`informes-warrants metricas JPM`).
- **Métricas esenciales y secundarias:**
  - Las esenciales tienen que salir para dar el perfil por validado.
  - Si una empresa no declara una secundaria en XBRL estándar, sale «n.d.» con marcador para el analista. Ejemplos: WFC no da el total de préstamos sin desglose, ALL declara sus siniestros con concepto propio y SPG solo da el dividendo por acción.
- **Emisores extranjeros:**
  - Las cifras se pasan a USD con el tipo declarado en el filing o, si no lo hay, con la media anual de yfinance ([divisas.py](../src/informes_warrants/ingesta/divisas.py)). Ejemplo: TSM 2024 = 90.300 M USD.
  - Si la empresa remite sus riesgos a un anexo (por ejemplo, NVO), el bloque pasa al analista.

## Versiones

```
DETECTADA ──confirmar──► BORRADOR ──emitir──► EMITIDA (inmutable)
    └──descartar──► DESCARTADA ◄──descartar──┘       └──nueva revisión──► BORRADOR (v+1)
```

| Aspecto | Cómo lo resuelve el SaaS | Pieza reutilizada |
|---|---|---|
| Creación | Al abrir la app (o con `informes-warrants versiones detectar TICKER`) busca el último 10-Q/10-K sin enmiendas. Si no tiene versión, crea una `detectada` que el analista confirma o descarta | edgartools `get_filings(amendments=False)`; patrón de stock-screener `ScreeningScheduler.run_once` para la comprobación periódica |
| Nombre | Año y periodo fiscal de la empresa: `AAPL · FY2026 Q3 · v1`, `AAPL · FY2026 · v1` | `xbrl().entity_info` (`fiscal_year`, `fiscal_period`) |
| Estados | `detectada`, `borrador`, `emitida`, `descartada`, con transiciones controladas | — |
| Herencia | La versión nueva copia **solo lo que aportó el analista**: textos, estimaciones, ajustes del bloque fijo y recomendación. Los bloques AUTO, PLANTILLA e IA se regeneran desde el filing nuevo, para no arrastrar cifras antiguas | — |
| Comparación | Diferencias de texto de cada bloque (diff), cambios de estimaciones, de métricas clave y de recomendación | `difflib` (estándar) |
| Correcciones | Una versión emitida no cambia: se crea la revisión `v2` del mismo periodo | — |
| Almacenamiento | SQLite en la carpeta de datos del usuario, **fuera de OneDrive** (`%LOCALAPPDATA%\informes-warrants\`, configurable con `INFORMES_DATA_DIR`). Un trigger impide modificar o borrar una versión emitida | `sqlite3` (estándar), `platformdirs` |
