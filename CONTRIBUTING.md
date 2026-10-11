# Cómo contribuir

1. Lee [CLAUDE.md](CLAUDE.md): reglas del proyecto y mapa de archivos.
2. Antes de programar algo, búscalo en [docs/inventario/README.md](docs/inventario/README.md): probablemente ya existe en un repo base.
3. Prepara el entorno (ver [README.md](README.md#puesta-en-marcha)).
4. Trabaja en una rama, con tests:
   - `pytest -m "not red"`: tests sin conexión (los mismos que la CI).
   - `pytest`: incluye los que consultan la SEC real (necesitan `EDGAR_IDENTITY` en `.env`).
   - `ruff check src tests`: estilo.
5. Commits en español, con el porqué del cambio y qué se reutilizó.

## Convenciones

- Código, docs y mensajes en español; nombres de la SEC/XBRL tal cual (`LongTermDebt`, `Item 1A`).
- Las cifras salen de código; la IA solo elige y resume fragmentos literales (ver [docs/ia.md](docs/ia.md)).
- Nada de secretos en git: `.env` está ignorado; usa `.env.example` como guía.
- Código de terceros: MIT/Apache con atribución en el docstring; AGPL o sin licencia, solo como idea.
