# Automatización de informes de warrants

SaaS para automatizar la generación de informes de inversión sobre empresas cotizadas en EEUU, a partir de los datos públicos de la SEC (EDGAR) mediante [edgartools](https://github.com/dgunning/edgartools).

> En desarrollo.

## Puesta en marcha

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (en macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
copy .env.example .env          # y rellena EDGAR_IDENTITY con tu nombre y email
```

## Uso

```bash
informes-warrants AAPL
```

Muestra la cuenta de resultados, el balance y los flujos de caja del último 10-K.

## Tests

```bash
pytest
```

## Licencia

[MIT](LICENSE)
