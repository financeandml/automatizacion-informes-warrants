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

- Markdown, con vista previa en tiempo real.
  - La vista HTML se regenera en cada cambio con la misma plantilla que el PDF (milisegundos).
  - El PDF se recompila en segundo plano: WeasyPrint tarda unos 2 s por documento.
- Recomendación: el SaaS propone el precio objetivo (DCF y múltiplos, ponderados por `peso_dcf`) y una recomendación mecánica por potencial: **Comprar ≥ +15 %**, **Vender ≤ −10 %**, Mantener entre ambos. El analista la confirma o la cambia en el bloque `portada.recomendacion`.
- Emisión: un apartado **«Confirmar emisión del informe»** con un botón. Solo se activa cuando no quedan marcadores y las estimaciones son válidas. Al pulsarlo, la versión pasa a `emitida` y queda inmutable.

## Estimaciones que ajusta el analista

Son los supuestos que mueven la proyección y el DCF ([estimaciones.py](../src/informes_warrants/informe/estimaciones.py)). Todo lo demás es histórico y no se toca.

| Estimación | Por defecto | Origen |
|---|---|---|
| Crecimiento de ventas (3 años) | Media histórica de 3-5 años | Capa 2 (edgar_analytics `multi_period_analysis`) |
| Margen EBITDA (3 años) | Media histórica | Capa 2 |
| D&A, capex y circulante sobre ventas | Media histórica | Capa 2 |
| Tasa fiscal | 21 % | Tipo federal; financial-research-analyst-agent `dcf_model` |
| Tipo libre de riesgo (Rf) | 4,5 % | financial-research-analyst-agent `_DEFAULT_RISK_FREE` |
| Prima de riesgo (ERP) | 5,5 % | financial-research-analyst-agent `_EQUITY_RISK_PREMIUM` |
| Beta | Histórico de precios | Capa 1 (`provider.get_history`) |
| Coste de la deuda | Intereses / deuda | Capa 2 |
| g (perpetuidad) | 2,5 % | Informe de referencia |
| Peso DCF frente a múltiplos | 50 % | Propuesta |

Los valores se validan: rangos razonables y g inferior al coste del capital.

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

Se cubren todas las empresas de EEUU con 10-K. La plantilla general sirve para las empresas operativas y los holdings. Bancos, aseguradoras, REIT, fondos, BDC, SPAC y emisores extranjeros (20-F/40-F) se generan con la plantilla general marcada como **«plantilla pendiente de validar»** ([cobertura.py](../src/informes_warrants/informe/cobertura.py)), hasta que tengan plantilla propia.

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
