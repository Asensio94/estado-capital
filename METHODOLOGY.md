# Metodología

Este documento recoge las decisiones que no son evidentes al leer el código y los límites de
cada indicador. Las definiciones operativas (códigos exactos) están en
[`src/etl/catalog.py`](src/etl/catalog.py) y en el `META` de cada módulo de
[`src/indicators/`](src/indicators/).

## Principios comunes

1. **Solo fuentes oficiales, guardadas íntegras.** Cada respuesta de la API se guarda en
   `data/raw/` con la URL, la fecha de extracción y la fecha de última actualización que declara
   la fuente. El procesado puede repetirse sin red a partir de esa caché.
2. **Códigos verificados en cada ejecución.** Antes de descargar, el ETL consulta la *content
   constraint* SDMX del dataset (no el codelist completo, que lista códigos que el cubo no
   contiene) y aborta si algún código pedido no existe. Así, un cambio de Eurostat rompe el ETL
   en lugar de devolver silenciosamente una serie vacía.
3. **Nada se inventa ni se interpola.** Cada indicador se construye sobre una rejilla completa
   de país × periodo. Si falta una entrada, el valor queda `NaN` y la fila lleva
   `status = partial` (falta alguna entrada) o `missing` (faltan todas). Los gráficos dibujan
   el hueco y cada tarjeta lista los tramos ausentes.
4. **Los flags de la fuente se conservan.** Las marcas de Eurostat (`p` provisional, `e`
   estimado, `b` ruptura de serie, `d` definición distinta…) se guardan en `obs_flags` como
   `PARTIDA:flag`.
5. **Porcentajes desde niveles.** Eurostat publica `PC_GDP` redondeado a una décima. Los
   porcentajes del PIB se calculan aquí dividiendo niveles en millones de euros por el PIB a
   precios corrientes (`nama_10_gdp`, B1GQ). Los porcentajes publicados se guardan como
   control: los tests exigen que ambos coincidan dentro del redondeo.

### Cambios respecto a la especificación inicial

Verificados contra la API el 21/10/2026:

| Especificación | Código real | Motivo |
|---|---|---|
| PIB en `gov_10a_main` | `nama_10_gdp`, B1GQ, CP_MEUR | B1GQ no está en el cubo `gov_10a_main` |
| Intereses D41 | `D41PAY` | D41 no existe en `gov_10a_main`; D41PAY es el gasto en intereses (después de SIFMI) |
| `nrg_pc_205_h` (serie anterior a 2007) | `nrg_pc_205`, `nrg_cons=MWH2000` | el dataset histórico se integró en `nrg_pc_205` |
| Banda de consumo industrial | `nrg_cons=MWH2000-19999` (banda ID) | banda intermedia; la Ie anterior a 2007 es un consumidor tipo de 2 000 MWh/año |
| Productividad por hora | `NLPR_HW` (PPS, UE-27 = 100) y `RLPR_HW` (real, 2015 = 100) | son las dos únicas medidas por hora del cubo |

## Indicador 1: inversión pública neta

**Definición.** (P51G − P51C) / B1GQ para el sector S13 (todas las administraciones públicas).
Un valor ≤ 0 indica que la formación bruta de capital fijo del año no cubre el consumo de
capital fijo estimado.

### Límites del consumo de capital fijo como medida de la depreciación

El consumo de capital fijo (P51C) **no es una medición física del desgaste**. Es una estimación
contable con estos límites:

- **Método del inventario permanente.** Los institutos estadísticos acumulan la inversión
  pasada por tipo de activo, la revalorizan a precios del año y le aplican una vida útil media y
  una función de retiro (normalmente lognormal, gamma o de Winfrey) y un perfil de depreciación
  (lineal o geométrico). Nadie inspecciona carreteras, edificios ni redes para estimarlo.
- **Vidas útiles supuestas y distintas entre países.** Cada país elige las vidas medias por
  activo: una carretera puede depreciarse en 40 años en un país y en 60 en otro. La
  comparación entre países mezcla diferencias reales con diferencias de supuestos. Las
  diferencias de nivel del P51C deben leerse con esa cautela; la evolución dentro de un mismo
  país es más fiable.
- **No capta el mantenimiento diferido.** Si un país deja de mantener un puente, el P51C no
  sube: el modelo supone que el activo pierde valor según su perfil, se mantenga o no. Un
  deterioro físico acelerado por falta de mantenimiento (el riesgo que este proyecto quiere
  vigilar) es invisible en este indicador.
- **El mantenimiento no es inversión.** Las reparaciones ordinarias son consumo intermedio
  (P2), no P51G. Un país que gasta mucho en mantener puede tener una inversión neta baja sin
  que su stock se degrade, y al revés.
- **Revalorización.** Al calcularse a coste de reposición, el P51C sube con los precios de la
  construcción aunque el stock físico no cambie. En años de inflación de costes (2021–2023) parte
  del aumento del P51C es precio, no desgaste.
- **Inversión a través de otros sectores.** Las concesiones, las asociaciones
  público-privadas y las empresas públicas clasificadas fuera de S13 (por ejemplo, gestores de
  infraestructuras ferroviarias o de carreteras según cada país) no aparecen en P51G de S13.
  Las diferencias de perímetro entre países afectan a la comparación de niveles.

Por eso la fase 2 prevé contrastar con stocks de capital por activo (BBVA-Ivie para España,
INSEE para Francia) y, donde existan, con indicadores físicos (estado de puentes y presas,
accidentes ferroviarios).

### Redondeo

`PC_GDP` de Eurostat viene redondeado a 0,1. Restar dos porcentajes redondeados da un error de
hasta ±0,1 pp, del mismo orden que los valores cuyo signo importa: en 8 casos la resta de los
publicados da 0,0 cuando el cálculo desde niveles es ligeramente positivo. Por eso:

- el indicador se calcula desde niveles;
- el dashboard marca la franja de ±0,1 pp como «signo no concluyente», porque el propio
  P51C tiene un error de estimación mayor que esa franja;
- los tests comprueban que el porcentaje calculado y el publicado difieren como máximo
  0,05 pp (más un margen de coma flotante). La diferencia máxima observada es 0,050.

## Indicador 2: intereses frente a educación

**Definición.** Gasto en intereses de S13 (D41PAY) dividido por el gasto total de S13 en la
función educación de la COFOG (GF09, TE). Ambos se expresan también en % del PIB.

- **La serie COFOG empieza en 1995 para los países, pero en 2010 para la UE-27**, y se publica
  con un año de retraso respecto a los agregados principales. Esos años salen como ausentes
  (`partial`).
- La tolerancia del control frente a los `PC_GDP` publicados es 0,1 pp en COFOG (0,05 en los
  agregados principales): la mayor diferencia observada, 0,083 en Alemania, se debe
  probablemente a que COFOG usa una añada anterior del PIB.
- El gasto en educación incluye gasto corriente y de capital; no distingue la inversión en
  capital humano del resto.
- Los intereses dependen del tipo de interés además del volumen de deuda: el cociente puede
  bajar porque bajan los tipos sin que cambie la carga de deuda.

## Indicador 3: precio de la electricidad para la industria

**Definición.** Precio semestral sin IVA ni otros impuestos recuperables (`tax=X_VAT`) en euros
por kWh, de `nrg_pc_205`.

- **Ruptura en 2007.** Hasta 2007 Eurostat publicaba precios para consumidores tipo (Ie: 2 000
  MWh/año); desde 2007, medias por banda de consumo (ID: 2 000–19 999 MWh/año). Las dos series
  se dibujan por separado (la anterior, punteada) y **no se empalman**: cambian a la vez la
  definición de consumidor y el método de recogida.
- **Semestres.** Cada semestre se sitúa en su punto medio (1 de abril o 1 de octubre). No se
  calculan medias anuales.
- **EE. UU. (opcional).** Precio medio anual de la electricidad vendida a la industria según la
  EIA (centavos de dólar por kWh), convertido a euros con el tipo medio anual del BCE publicado
  por Eurostat (`ert_bil_eur_a`). Es ingreso medio por kWh de todas las bandas, sin desglose de
  impuestos homogéneo con Eurostat: sirve para comparar órdenes de magnitud, no décimas de
  céntimo. La serie empieza en 2001. Si la API de la EIA falla, el ETL avisa y continúa.

## Indicador 4: productividad por hora

- **Nivel** (`NLPR_HW`): PIB por hora trabajada en paridades de poder de compra, UE-27 = 100.
  Sirve para comparar países dentro de un mismo año. Eurostat desaconseja leerlo como serie
  temporal, porque las PPA se recalculan cada año.
- **Evolución** (`RLPR_HW`): productividad real por hora, índice 2015 = 100, reescalado aquí a
  1995 = 100 dividiendo por el valor de 1995. Es una operación exacta sobre la serie publicada,
  no una estimación.
- La productividad media depende de la composición sectorial y del empleo: destruir empleo poco
  productivo la sube sin que nadie trabaje mejor (España, 2008–2013).

## Indicador 5: PISA por cohortes

- PISA no está en la API SDMX de la OCDE ni en el OECD Data Explorer. La fuente es el libro
  Excel del informe *PISA 2022 Results (Volume I)*, anexo B1, capítulo 5 (StatLink
  <https://stat.link/wh9d4z>): tabla I.B1.5.4 (matemáticas, 2003–2022) y I.B1.5.5 (lectura,
  2000–2022). `python -m etl.pisa_statlink` la convierte en `data/manual/pisa/pisa.csv`, copia
  medias y errores típicos con toda su precisión y anota en `pisa.meta.json` la fecha de
  descarga, la URL y el SHA-256 del libro. Las celdas `m` se quedan sin fila; nunca se rellenan.
- Referencia: **media OCDE-23**, los países de la OCDE que pueden comparar su rendimiento en
  todas las ediciones de 2000 a 2022. Se prefiere a la «media OCDE» de cada informe porque su
  composición no cambia, y porque el libro solo trae esta última para 2012, 2015 y 2022.
- La cohorte es el año de nacimiento aproximado: edición − 15.
- Las tendencias de matemáticas solo son comparables desde 2003 (lectura desde 2000); la tabla
  de tendencias no incluye matemáticas de 2000, así que esa edición queda ausente.
- España no tiene 2018 en ninguna de las dos tablas: la OCDE retuvo su lectura de 2018 por
  respuestas anómalas y la tabla de matemáticas de 2022 también la marca como `m`. Las líneas se
  cortan en ese hueco.
- La edición de 2022 se aplazó un año por la pandemia.
- Diferencias de pocos puntos no son significativas: el error típico de cada media ronda 2–4
  puntos.

## Revisiones

Las cifras de los últimos años son provisionales y Eurostat las revisa en cada notificación
(abril y octubre para las cuentas públicas). Cada ejecución del ETL guarda la fecha de
actualización de la fuente; dos ejecuciones en fechas distintas pueden dar cifras distintas
para los mismos años.
