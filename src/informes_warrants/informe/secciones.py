"""Bloques del informe y quién los produce.

Orden de preferencia (regla del proyecto: usar la IA lo menos posible):
  AUTO      → lo calcula y maqueta el código (tablas, gráficos, cifras).
  PLANTILLA → texto fijo con huecos que rellena el código con datos (sin IA).
  IA        → solo donde hace falta leer lenguaje natural del 10-K; siempre con cita literal verificada.
  ANALISTA  → criterio humano; aparece marcado en el borrador y bloquea la emisión hasta completarse.

La estructura sigue docs/estructura-informe.md (§1-§9, anexos A1-A5 y aviso legal).
"""

from dataclasses import dataclass
from enum import StrEnum


class Tipo(StrEnum):
    AUTO = "auto"
    PLANTILLA = "plantilla"
    IA = "ia"
    ANALISTA = "analista"


@dataclass(frozen=True)
class Bloque:
    id: str
    seccion: str
    titulo: str
    tipo: Tipo
    fuente: str
    plantilla: str | None = None  # archivo en plantillas/secciones/ (tipos PLANTILLA y ANALISTA)


BLOQUES: tuple[Bloque, ...] = (
    # §1 Portada
    Bloque("portada.recomendacion", "1", "Recomendación y precio objetivo", Tipo.ANALISTA,
           "El SaaS propone el precio objetivo (DCF y múltiplos) y una recomendación por potencial; el analista la confirma",
           "recomendacion.md.j2"),
    Bloque("portada.titulares", "1", "Titulares de la tesis", Tipo.ANALISTA,
           "Plantilla con las cifras clave; el analista escribe la tesis", "titulares.md.j2"),
    Bloque("portada.datos_mercado", "1", "Datos de mercado", Tipo.AUTO, "Precio, acciones, market cap, EV, rangos 12m"),
    Bloque("portada.accionariado", "1", "Estructura accionarial", Tipo.AUTO, "Proxy (Item 403), 13D/G, Form 4"),
    Bloque("portada.datos_financieros", "1", "Datos financieros básicos", Tipo.AUTO, "XBRL + estimaciones"),
    Bloque("portada.multiplos", "1", "Ratios y múltiplos", Tipo.AUTO, "Capa 2"),
    Bloque("portada.comportamiento", "1", "Comportamiento relativo en bolsa", Tipo.AUTO, "Precios vs S&P 500 y ETF sectorial"),
    # §2 Conclusiones
    Bloque("conclusiones.hechos_clave", "2", "Hechos clave (4)", Tipo.PLANTILLA,
           "Reglas sobre la analítica (patrón FRAA insight_engine)", "hechos_clave.md.j2"),
    Bloque("conclusiones.situacion", "2", "A) Situación actual", Tipo.PLANTILLA, "Histórico XBRL", "situacion.md.j2"),
    Bloque("conclusiones.perspectivas", "2", "B) Perspectivas", Tipo.ANALISTA,
           "Plantilla con las estimaciones; el analista explica el porqué", "perspectivas.md.j2"),
    Bloque("conclusiones.fortalezas_riesgos", "2", "C) Fortalezas y riesgos clave", Tipo.ANALISTA,
           "Los riesgos vienen del bloque de IA; las fortalezas, del analista", "fortalezas_riesgos.md.j2"),
    Bloque("conclusiones.checklist", "2", "Checklist de entrada: criterios cualitativos", Tipo.ANALISTA,
           "Los criterios cuantitativos los evalúa el SaaS con los parámetros del fondo (B4)", "checklist.md.j2"),
    Bloque("conclusiones.seguimiento", "2", "Seguimiento: criterios de salida", Tipo.ANALISTA,
           "Fechas de revisión, precio objetivo y stop del SaaS; la salida por tesis, del analista (B4)", "seguimiento.md.j2"),
    # §3
    Bloque("graficos_clave", "3", "La compañía en 8 gráficos", Tipo.AUTO, "Capa 3"),
    # §4 Negocio
    Bloque("negocio.descripcion", "4", "Descripción del negocio", Tipo.PLANTILLA,
           "Cita literal del inicio del Item 1 + segmentos XBRL", "descripcion.md.j2"),
    Bloque("negocio.segmentos", "4", "Ingresos por segmento, plantilla y costes", Tipo.AUTO, "Segmentos XBRL, LaborAndRelatedExpense"),
    Bloque("negocio.pipeline", "4", "Pipeline de producto (farmacia y biotecnología)", Tipo.ANALISTA,
           "Solo en esos sectores (SIC 2833-2836, 8731): la SEC no lo publica como datos", "pipeline.md.j2"),
    Bloque("negocio.competencia", "4", "Competencia según la empresa", Tipo.IA,
           "Apartado «Competition» del Item 1, extraído por código y traducido por IA con verificación (A5)"),
    Bloque("negocio.posicionamiento", "4", "Posicionamiento competitivo", Tipo.ANALISTA,
           "Criterio del analista", "posicionamiento.md.j2"),
    # §5 Industria
    Bloque("industria.comparables", "5", "Compañías comparables", Tipo.AUTO, "SIC (edgartools get_companies_by_industry)"),
    Bloque("industria.mercado", "5", "Tamaño y tendencias del mercado", Tipo.ANALISTA,
           "Ningún repo tiene fuente de tamaño de mercado", "mercado.md.j2"),
    # §6 Análisis financiero
    Bloque("financiero.tablas", "6", "Análisis financiero (tablas y gráficos)", Tipo.AUTO, "Capas 2 y 3"),
    Bloque("financiero.comentario", "6", "Comentario de la evolución financiera", Tipo.PLANTILLA, "Capa 2", "financiero.md.j2"),
    # §7 Valoración
    Bloque("valoracion.dcf", "7", "DCF, múltiplos y sensibilidad", Tipo.AUTO, "Capa 2 con las estimaciones del analista"),
    Bloque("valoracion.comentario", "7", "Conclusión de la valoración", Tipo.PLANTILLA, "Capa 2", "valoracion.md.j2"),
    # §8 Riesgos
    Bloque("riesgos.lista", "8", "Factores de riesgo declarados (lista completa)", Tipo.AUTO, "Títulos del Item 1A extraídos del HTML"),
    Bloque("riesgos.resumen", "8", "Riesgos principales", Tipo.IA, "Selección y resumen de títulos del Item 1A, con cita literal"),
    Bloque("riesgos.catalizadores", "8", "Catalizadores según la dirección (MD&A)", Tipo.IA, "Item 7, con cita literal"),
    # §9 Gobierno
    Bloque("gobierno.datos", "9", "Accionariado, retribución y auditor", Tipo.AUTO, "Proxy DEF 14A, Form 4, auditor"),
    Bloque("gobierno.consejo", "9", "Consejo y valoración del gobierno corporativo", Tipo.ANALISTA,
           "El consejo no está estructurado en ningún repo", "gobierno.md.j2"),
    # Anexos y legal
    Bloque("anexo.proyecciones", "A1", "Proyecciones financieras", Tipo.AUTO, "XBRL + estimaciones"),
    Bloque("anexo.fcf", "A2", "Analítica del FCF", Tipo.AUTO, "Capa 2"),
    Bloque("anexo.ev", "A3", "Cálculo del EV", Tipo.AUTO, "Capa 2"),
    Bloque("anexo.historico", "A4", "Comportamiento histórico", Tipo.AUTO, "XBRL company facts"),
    Bloque("anexo.comparables", "A5", "Principales comparables", Tipo.AUTO, "Capa 2"),
    Bloque("anexo.metodologia", "A6", "Metodología y fuentes", Tipo.AUTO, "calculo/definiciones.py y documentos usados"),
    Bloque("legal", "L", "Descargo de responsabilidad", Tipo.AUTO, "plantillas/legal/descargo.md"),
)


def bloques_por_tipo(tipo: Tipo) -> list[Bloque]:
    return [b for b in BLOQUES if b.tipo == tipo]
