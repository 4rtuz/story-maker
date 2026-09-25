# Presupuesto y coste

Propuesta económica de Story Maker para el cliente (ficticio) Cuentalia Regalos. Generado por
`python docs/presupuesto/calcular.py`: cambiar un supuesto y relanzarlo recalcula todo.

## De dónde sale cada número

- **Tokens por novela: 24.52 USD** medidos en Langfuse sobre la novela de ejemplo completa (`novela costes ejemplo-carmen`, 511 llamadas, 10 capítulos, auditoría, Lean y juez; [costes-ejemplo-carmen.md](evaluacion/costes-ejemplo-carmen.md)). Es el coste a precio de API que calcula Langfuse; en desarrollo corre sobre una suscripción de Claude Code.
- **Tokens por revisión: 11.71 USD**, medida en Langfuse sobre la versión 2 de ejemplo-carmen (cam-001: 3 capítulos regenerados, 7 reaplicados y auditoría con Lean y juez): la sesión pasó de 24,52 a 36,23 USD. Es una cota alta: incluye los reintentos de dos bugs de la regeneración que se arreglaron esa noche (docs/proceso/iteraciones.md).
- Tipo de cambio: 1 USD = 0.92 € (supuesto).
- Revisión editorial humana: 10,00 € (20 min a 30 €/h): una persona hojea el PDF antes de enviarlo, porque es un regalo.
- Soporte: 2,50 €; pasarela de pago: 1,4 % + 0,25 €.
- Infraestructura mensual (supuesto): servidor para API, panel y trabajos, copias de seguridad, Langfuse Cloud y dominio; 100,00 € a 50 novelas/mes, 100,00 € a 200 novelas/mes, 350,00 € a 1000 novelas/mes.
- Media de 1 revisión por novela (supuesto); el precio incluye hasta 3.

## Coste unitario (200 novelas/mes)

| Concepto | € por novela |
|---|---:|
| tokens | 22,56 € |
| revisiones | 10,77 € |
| infraestructura | 0,50 € |
| revisión editorial | 10,00 € |
| soporte | 2,50 € |
| pasarela de pago | 1,36 € |
| **coste total** | **47,69 €** |
| precio de venta (IVA aparte) | 79,00 € |
| **margen** | **31,31 € (39,6 %)** |

## Escenarios de volumen

| Novelas/mes | Coste unitario | Margen unitario | Ingresos/mes | Margen/mes |
|---:|---:|---:|---:|---:|
| 50 | 49,19 € | 29,81 € (37,7 %) | 3.950,00 € | 1.490,62 € |
| 200 | 47,69 € | 31,31 € (39,6 %) | 15.800,00 € | 6.262,48 € |
| 1000 | 47,54 € | 31,46 € (39,8 %) | 79.000,00 € | 31.462,40 € |

## Análisis de sensibilidad (200 novelas/mes)

| Escenario | Coste unitario | Margen |
|---|---:|---:|
| base | 47,69 € | 31,31 € (39,6 %) |
| tokens +50 % | 64,35 € | 14,65 € (18,5 %) |
| 3 revisiones, todas incluidas | 69,23 € | 9,77 € (12,4 %) |
| 4 revisiones, sin cobrar la 4.ª | 80,01 € | -1,01 € (-1,3 %) |
| 4 revisiones, cobrando 15,00 € la 4.ª | 80,01 € | 13,99 € |
| 5 revisiones, cobrando 15,00 € desde la 4.ª | 90,78 € | 18,22 € |

Cada revisión cuesta 10,77 € en tokens. Cobrar 15,00 € por revisión a partir de la 4.ª deja 4,23 € por revisión extra.

## Coste del proyecto de desarrollo

| Fase | Horas | Importe |
|---|---:|---:|
| Diseño y specs | 60 | 3.300,00 € |
| Desarrollo | 280 | 15.400,00 € |
| Validación y evaluación | 110 | 6.050,00 € |
| Despliegue | 40 | 2.200,00 € |
| **total** | **490** | **26.950,00 €** |

Tarifa: 55,00 €/h. A 200 novelas/mes, el margen mensual (6.262,48 €) recupera el desarrollo en 4,3 meses.
