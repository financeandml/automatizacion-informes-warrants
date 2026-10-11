# Identidad corporativa y maquetación

## Marca
- Logo: `src/informes_warrants/plantillas/marca/logo.svg`. Vectorizado como polígonos exactos (3 piezas: 2 barras y 1 triángulo, con el borde superior común).
- Nombre comercial: `src/informes_warrants/plantillas/marca/nombre.svg`. Trazado vectorial (potrace) del original.
- Ambos son vectoriales (escalan a cualquier resolución), sin fondo (transparentes) y en negro `#000000`. Fidelidad frente al PNG original: el 99,7 % de los píxeles coincide en el logo y el 98,7 % en el nombre; las diferencias son de subpíxel en los bordes antialiasados.

## Colores (solo estos tres)
| Uso | Color | Hex |
|---|---|---|
| Acento: titulares, filetes, cabeceras de tabla, serie principal de los gráficos | Burdeos muy oscuro, casi negro | `#2B0B02` |
| Texto y logo | Negro | `#000000` |
| Fondo | Blanco | `#FFFFFF` |

En los gráficos con varias series se usan esos tres colores combinados con tramas o grosores de línea, nunca colores nuevos.

## Tipografía
- **Títulos:** Montserrat (la misma familia geométrica del nombre comercial). **Texto y tablas:** Inter (cifras tabulares, muy legible en tablas densas).
- Ambas tienen licencia OFL: se incluyen en el repo y el PDF se genera igual en cualquier máquina.
- Se descartó Cambria: es serif (menos coherente con el estilo Morningstar y la marca) y su licencia de Microsoft impide incluirla en el repo y usarla fuera de Windows.

## Estilo
- Referencia de maquetación: informes de *equity research* de Morningstar. Solo se toma la estructura visual: barra lateral de datos clave en la portada, filetes finos, tipografía sans-serif sobria y tablas densas sin sombreados. No se usan sus marcas ni sus métricas propias (estrellas, *Economic Moat*, *Fair Value*).
- Las formas, líneas y detalles los elige el desarrollador, manteniendo un estilo sobrio, formal e institucional.

## Texto legal
`src/informes_warrants/plantillas/legal/descargo.md` (texto definitivo del usuario; el año se rellena automáticamente).
