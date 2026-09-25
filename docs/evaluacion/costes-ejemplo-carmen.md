# Costes de ejemplo-carmen

Sesión de Langfuse `novela-ejemplo-carmen`. Generado por `novela costes ejemplo-carmen --markdown` desde `GET /api/public/v2/observations`; el coste es el `totalCost` que Langfuse calcula por generación. La entrada incluye la caché leída. Latencia de un paso: tiempo de pared de sus trazas; de la novela: la suma de sus pasos.

## Por paso

| paso | llamadas | entrada | salida | caché leída | coste USD | latencia s |
|---|---:|---:|---:|---:|---:|---:|
| nueva | 29 | 1182091 | 61943 | 995464 | 1.3830 | 623.186 |
| capitulo 01 | 54 | 2028573 | 57790 | 1785967 | 1.7052 | 540.742 |
| capitulo 02 | 49 | 1800609 | 78754 | 1515909 | 1.7821 | 702.382 |
| capitulo 03 | 36 | 1462449 | 75092 | 1218729 | 1.9209 | 723.088 |
| capitulo 04 | 39 | 1567485 | 76757 | 1286132 | 1.9404 | 690.172 |
| capitulo 05 | 58 | 2528409 | 93788 | 2162218 | 2.8305 | 935.22 |
| capitulo 06 | 40 | 1658657 | 77520 | 1366727 | 2.0077 | 892.438 |
| capitulo 07 | 41 | 1692645 | 85119 | 1385838 | 2.1632 | 799.77 |
| capitulo 08 | 59 | 2263687 | 133923 | 1827166 | 3.1440 | 1046.987 |
| capitulo 09 | 42 | 1762531 | 108760 | 1422141 | 2.4673 | 961.171 |
| capitulo 10 | 44 | 1856184 | 90478 | 1528210 | 2.1992 | 814.496 |
| auditoria | 20 | 939229 | 22674 | 812398 | 0.9758 | 275.278 |
| **novela** | 511 | 20742549 | 962598 | 17306899 | 24.5193 | 9004.93 |

## Por rol y paso

La latencia es la media por llamada.

| paso · rol | llamadas | entrada | salida | caché leída | coste USD | latencia s |
|---|---:|---:|---:|---:|---:|---:|
| nueva · arquitecto | 4 | 122266 | 20075 | 76561 | 0.6453 | 48.758 |
| nueva · orquestador | 11 | 519533 | 3139 | 495266 | 0.3559 | 3.613 |
| nueva · trazador | 14 | 540292 | 38729 | 423637 | 0.3818 | 25.636 |
| capitulo 01 · continuista | 5 | 124904 | 10057 | 91306 | 0.1014 | 24.437 |
| capitulo 01 · cronista | 8 | 170758 | 15485 | 110746 | 0.1635 | 19.86 |
| capitulo 01 · editor-estilo | 5 | 124311 | 9317 | 90461 | 0.0979 | 20.888 |
| capitulo 01 · escritor | 4 | 121191 | 13875 | 82738 | 0.4863 | 37.805 |
| capitulo 01 · lector-suspense | 4 | 75829 | 3855 | 52501 | 0.0537 | 11.786 |
| capitulo 01 · orquestador | 28 | 1411580 | 5201 | 1358215 | 0.8024 | 2.692 |
| capitulo 02 · continuista | 5 | 119573 | 7760 | 86730 | 0.0885 | 18.335 |
| capitulo 02 · cronista | 11 | 259094 | 31070 | 156316 | 0.2994 | 28.844 |
| capitulo 02 · editor-estilo | 3 | 74735 | 9277 | 38775 | 0.0952 | 35.652 |
| capitulo 02 · escritor | 5 | 201679 | 19198 | 146390 | 0.6897 | 40.395 |
| capitulo 02 · lector-suspense | 5 | 99483 | 7175 | 72097 | 0.0773 | 18.382 |
| capitulo 02 · orquestador | 20 | 1046045 | 4274 | 1015601 | 0.5320 | 2.878 |
| capitulo 03 · continuista | 4 | 93129 | 3793 | 63810 | 0.0620 | 11.475 |
| capitulo 03 · cronista | 4 | 192761 | 39361 | 115929 | 0.6089 | 97.801 |
| capitulo 03 · editor-estilo | 4 | 89071 | 6777 | 57497 | 0.0791 | 20.621 |
| capitulo 03 · escritor | 4 | 148508 | 17918 | 96428 | 0.6380 | 45.385 |
| capitulo 03 · lector-suspense | 3 | 55738 | 3696 | 31812 | 0.0516 | 15.373 |
| capitulo 03 · orquestador | 17 | 883242 | 3547 | 853253 | 0.4814 | 2.866 |
| capitulo 04 · continuista | 4 | 106370 | 9591 | 70870 | 0.0994 | 25.184 |
| capitulo 04 · cronista | 4 | 191962 | 36766 | 83717 | 0.6550 | 94.914 |
| capitulo 04 · editor-estilo | 4 | 99968 | 9620 | 65775 | 0.0974 | 26.169 |
| capitulo 04 · escritor | 5 | 183798 | 14418 | 134528 | 0.5616 | 29.421 |
| capitulo 04 · lector-suspense | 5 | 97887 | 3419 | 74062 | 0.0543 | 7.816 |
| capitulo 04 · orquestador | 17 | 887500 | 2943 | 857180 | 0.4727 | 2.739 |
| capitulo 05 · continuista | 5 | 145582 | 13615 | 105072 | 0.1292 | 33.698 |
| capitulo 05 · cronista | 7 | 269633 | 43319 | 151794 | 0.7581 | 60.445 |
| capitulo 05 · editor-estilo | 4 | 96151 | 8140 | 62904 | 0.0885 | 23.742 |
| capitulo 05 · escritor | 6 | 199433 | 16676 | 112397 | 0.7912 | 32.037 |
| capitulo 05 · lector-suspense | 4 | 78382 | 3778 | 54472 | 0.0542 | 11.205 |
| capitulo 05 · orquestador | 32 | 1739228 | 8260 | 1675579 | 1.0093 | 3.892 |
| capitulo 06 · continuista | 4 | 104784 | 7683 | 69688 | 0.0892 | 24.183 |
| capitulo 06 · cronista | 3 | 126394 | 34080 | 14841 | 0.6226 | 110.958 |
| capitulo 06 · editor-estilo | 5 | 142281 | 12365 | 105071 | 0.1188 | 30.002 |
| capitulo 06 · escritor | 4 | 149352 | 15444 | 97781 | 0.5863 | 79.586 |
| capitulo 06 · lector-suspense | 4 | 79400 | 4268 | 54745 | 0.0576 | 12.97 |
| capitulo 06 · orquestador | 20 | 1056446 | 3680 | 1024601 | 0.5331 | 3.622 |
| capitulo 07 · continuista | 4 | 112154 | 8887 | 74864 | 0.0985 | 22.752 |
| capitulo 07 · cronista | 3 | 131498 | 37622 | 14787 | 0.6710 | 129.677 |
| capitulo 07 · editor-estilo | 8 | 218114 | 12382 | 179194 | 0.1285 | 17.278 |
| capitulo 07 · escritor | 5 | 207369 | 18619 | 150211 | 0.6882 | 40.633 |
| capitulo 07 · lector-suspense | 3 | 56252 | 3702 | 32044 | 0.0520 | 14.556 |
| capitulo 07 · orquestador | 18 | 967258 | 3907 | 934738 | 0.5251 | 2.739 |
| capitulo 08 · continuista | 8 | 221681 | 18035 | 157648 | 0.1860 | 23.691 |
| capitulo 08 · cronista | 3 | 143536 | 46353 | 14790 | 0.7883 | 151.85 |
| capitulo 08 · editor-estilo | 11 | 264006 | 18754 | 207363 | 0.1853 | 17.646 |
| capitulo 08 · escritor | 8 | 327204 | 32830 | 217671 | 1.2478 | 38.616 |
| capitulo 08 · lector-suspense | 8 | 165068 | 12169 | 121512 | 0.1274 | 16.701 |
| capitulo 08 · orquestador | 21 | 1142192 | 5782 | 1108182 | 0.6092 | 3.057 |
| capitulo 09 · continuista | 4 | 114686 | 10929 | 73477 | 0.1135 | 31.445 |
| capitulo 09 · cronista | 3 | 157572 | 56585 | 14784 | 0.9258 | 182.586 |
| capitulo 09 · editor-estilo | 8 | 217304 | 12061 | 179390 | 0.1256 | 18.017 |
| capitulo 09 · escritor | 4 | 163829 | 18504 | 106503 | 0.6780 | 47.464 |
| capitulo 09 · lector-suspense | 4 | 86934 | 6239 | 59019 | 0.0720 | 20.425 |
| capitulo 09 · orquestador | 19 | 1022206 | 4442 | 988968 | 0.5524 | 3.128 |
| capitulo 10 · continuista | 5 | 166545 | 10282 | 124808 | 0.1161 | 24.313 |
| capitulo 10 · cronista | 3 | 150268 | 45453 | 14791 | 0.7962 | 154.282 |
| capitulo 10 · editor-estilo | 6 | 158456 | 13075 | 120041 | 0.1254 | 24.488 |
| capitulo 10 · escritor | 4 | 156887 | 12523 | 103693 | 0.5372 | 31.931 |
| capitulo 10 · lector-suspense | 5 | 105807 | 5006 | 78916 | 0.0665 | 12.264 |
| capitulo 10 · orquestador | 21 | 1118221 | 4139 | 1085961 | 0.5579 | 2.829 |
| auditoria · juez | 6 | 299514 | 18610 | 214312 | 0.4420 | 34.326 |
| auditoria · orquestador | 14 | 639715 | 4064 | 598086 | 0.5338 | 3.571 |
