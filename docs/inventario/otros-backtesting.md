# ai-hedge-fund, vectorbt y Lean

Repositorios añadidos el 2026-10-11. **Cobertura** (2026-10-12): listado del 100 % de los archivos, búsqueda dirigida de valoración (DCF, intrínseco, inverso), puntuaciones (Altman, Piotroski, Beneish) y eventos, y lectura de los README y las licencias. Son motores de *trading*, señales y *backtesting*: no cubren el informe de *equity research*, salvo lo que se indica.

| Repo | Licencia | Archivos | Qué es | Qué se reutiliza |
|---|---|---:|---|---|
| **ai-hedge-fund** (`ai-hedge-fund-main.zip`) | MIT | 135 | Fondo simulado con agentes LLM: `hedge_fund/signals/` (Graham, Lynch, Munger, Druckenmiller, PEAD), `event_study/` (motor de estudio de eventos con estadísticos), `backtesting/`, `portfolio/`, `risk/`, `brokers/` (papel) | **Idea para el apartado 21 del índice**: reacción bursátil tras los resultados, con `event_study/engine.py`, `stats.py` y `signals/pead.py` (deriva tras el anuncio de resultados). No tiene DCF ni puntuaciones contables |
| **vectorbt** (`vectorbt-master.zip`) | Apache-2.0 **con «Commons Clause»** (prohíbe vender el software) | 336 | *Backtesting* vectorizado (portafolio, señales, indicadores, retornos) | **No usable en un SaaS** por la Commons Clause. Como mucho, ideas de métricas de riesgo (apartado 24, aparcado) |
| **Lean** (`Lean-master.zip`) | Apache-2.0 | 6.934 | Motor de *trading* algorítmico de QuantConnect en C# (`Common`, `Engine`, `Algorithm.*`, `Indicators`, `Brokerages`, `Report`) | Nada en esta fase; `Report/` (informe de *backtest*) puede ser idea para el apartado 25 (seguimiento) |
