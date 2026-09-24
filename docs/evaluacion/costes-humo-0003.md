# Costes de humo-0003

Sesión de Langfuse `novela-humo-0003`. Generado por `novela costes humo-0003 --markdown` desde `GET /api/public/v2/observations`; el coste es el `totalCost` que Langfuse calcula por generación. La entrada incluye la caché leída. Latencia de un paso: tiempo de pared de sus trazas; de la novela: la suma de sus pasos.

## Por paso

| paso | llamadas | entrada | salida | caché leída | coste USD | latencia s |
|---|---:|---:|---:|---:|---:|---:|
| nueva | 32 | 956785 | 63572 | 752757 | 2.6220 | 3086.254 |
| sesión 8f18d74d | 4 | 130274 | 791 | 111940 | 0.1848 | 16.053 |
| capitulo 01 | 55 | 1863713 | 98416 | 1558120 | 2.0441 | 732.947 |
| capitulo 02 | 64 | 2315748 | 161600 | 1827344 | 3.5569 | 1131.635 |
| capitulo 03 | 87 | 3196013 | 177570 | 2622665 | 4.4518 | 1199.571 |
| auditoria | 4 | 118206 | 541 | 103112 | 0.1522 | 14.377 |
| **novela** | 246 | 8580739 | 502490 | 6975938 | 13.0118 | 6180.837 |

## Por rol y paso

La latencia es la media por llamada.

| paso · rol | llamadas | entrada | salida | caché leída | coste USD | latencia s |
|---|---:|---:|---:|---:|---:|---:|
| nueva · arquitecto | 8 | 180213 | 35046 | 85582 | 1.1912 | 43.908 |
| nueva · orquestador | 21 | 682011 | 6875 | 621996 | 0.7419 | 50.653 |
| nueva · trazador | 3 | 94561 | 21651 | 45179 | 0.6890 | 80.323 |
| sesión 8f18d74d · orquestador | 4 | 130274 | 791 | 111940 | 0.1848 | 3.289 |
| capitulo 01 · continuista | 4 | 141265 | 16144 | 92868 | 0.3010 | 40.807 |
| capitulo 01 · cronista | 14 | 364950 | 38330 | 245456 | 0.3655 | 20.527 |
| capitulo 01 · editor-estilo | 6 | 232960 | 20580 | 179728 | 0.3748 | 34.098 |
| capitulo 01 · escritor | 3 | 80352 | 12095 | 42801 | 0.4382 | 48.264 |
| capitulo 01 · lector-suspense | 4 | 107649 | 5729 | 75259 | 0.1533 | 14.83 |
| capitulo 01 · orquestador | 24 | 936537 | 5538 | 922008 | 0.4112 | 3.189 |
| capitulo 02 · continuista | 8 | 289798 | 32225 | 193929 | 0.6007 | 40.274 |
| capitulo 02 · cronista | 6 | 171049 | 36342 | 77942 | 0.3059 | 45.458 |
| capitulo 02 · editor-estilo | 11 | 419470 | 45736 | 309573 | 0.7940 | 41.476 |
| capitulo 02 · escritor | 7 | 267715 | 26572 | 159958 | 1.1022 | 42.826 |
| capitulo 02 · lector-suspense | 8 | 228111 | 15250 | 159193 | 0.3566 | 20.789 |
| capitulo 02 · orquestador | 24 | 939605 | 5475 | 926749 | 0.3975 | 3.487 |
| capitulo 03 · continuista | 13 | 513795 | 51961 | 365876 | 0.9626 | 45.817 |
| capitulo 03 · cronista | 3 | 81248 | 16149 | 37704 | 0.1389 | 56.4 |
| capitulo 03 · editor-estilo | 16 | 572793 | 46421 | 446806 | 0.8685 | 34.335 |
| capitulo 03 · escritor | 6 | 223849 | 25980 | 111634 | 1.1030 | 45.351 |
| capitulo 03 · lector-suspense | 12 | 371066 | 27226 | 267176 | 0.5854 | 28.263 |
| capitulo 03 · orquestador | 37 | 1433262 | 9833 | 1393469 | 0.7934 | 3.521 |
| auditoria · orquestador | 4 | 118206 | 541 | 103112 | 0.1522 | 2.781 |
