# Informe del endpoint Race Center

## Alcance y fecha de consulta

Endpoint analizado:

`https://racecenter.lavuelta.es/api/rankingType-2026-{stage}`

La consulta se realizó el 23 de agosto de 2026 usando `{stage}` entre 1 y 21. El endpoint pertenece a `racecenter.lavuelta.es`, por lo que el año `2026` identifica la competición de La Vuelta configurada en ese servicio, no la Volta a Portugal del proyecto.

## Resultado principal

En el momento del análisis:

| URL | HTTP | Respuesta | Tamaño aproximado |
|---|---:|---|---:|
| `rankingType-2026-1` | 200 | Payload poblado | 470 633 bytes |
| `rankingType-2026-2` a `rankingType-2026-21` | 200 | `[]` | 2 bytes |

La etapa 1 contiene datos de una prueba contrarreloj de 9,4 km. No contiene datos de las etapas de la Volta a Portugal descritas en `stages.json`. Un HTTP 200 no significa que haya resultados: hay que comprobar que el cuerpo no sea una lista vacía.

## Forma general de la respuesta

Cuando hay datos, la respuesta es una lista heterogénea. En la muestra de la etapa 1 tenía 224 objetos:

- 13 objetos de rankings (`_bind: rankingType-2026-1`).
- 184 corredores (`_bind: allCompetitors-2026`).
- 23 equipos (`_bind: team-2026`).
- 4 puntos de control (`_bind: checkpointList-2026-1`).

Los objetos comparten metadatos internos como `_id`, `_origin`, `_bind`, `_updatedAt` y `_virtual`. Estos campos parecen proceder del sistema de sincronización del Race Center y no deberían tratarse como una API pública estable sin validación.

### Objeto de ranking

Las claves observadas en un bloque de clasificación son:

```json
{
  "type": "itt",
  "types": ["C"],
  "status": "0",
  "length": 5.7,
  "checkpoint": 16,
  "rankings": []
}
```

Un elemento de `rankings` tiene esta forma:

```json
{
  "$rider": "allCompetitors-2026:<id interno>",
  "bib": 124,
  "position": 1,
  "absolute": 389910,
  "relative": 0,
  "penality": 0,
  "bonus": 0
}
```

Interpretación práctica:

- `position`: posición en esa clasificación. Puede ser prudente compararla como texto para aceptar `1` y `"1"`.
- `bib`: dorsal del corredor.
- `absolute`: valor absoluto en milisegundos para rankings de tiempo; en rankings de puntos puede ser una cantidad de puntos.
- `relative`: diferencia respecto al primero, normalmente en milisegundos en rankings de tiempo.
- `penality`: penalización, aparentemente en milisegundos en rankings de tiempo.
- `bonus`: bonificación, aparentemente en milisegundos en rankings de tiempo.
- `$rider`: referencia a un objeto de `allCompetitors-2026`, no el nombre del corredor.

## Códigos de clasificación observados

La etapa 1 contiene estos tipos y tamaños. La interpretación de los códigos está basada en la forma de los datos y en la nomenclatura habitual del Race Center; conviene confirmarla contra la documentación o una respuesta oficial de una etapa finalizada.

| `type` | Tamaño | Interpretación probable | Evidencia observada |
|---|---:|---|---|
| `ijg` | 65 | Clasificación general juvenil | 65 filas; tiempos acumulados |
| `ije` | 65 | Clasificación juvenil de etapa | 65 filas; tiempo absoluto distinto |
| `itg` | 184 | Clasificación general individual | 184 filas; tiempo acumulado |
| `ite` | 184 | Clasificación individual de etapa | 184 filas; tiempo de llegada |
| `itt` | 184 | Clasificación individual por tiempo | aparece cuatro veces con distintos `types` |
| `ipg` | 15 | Clasificación general por puntos | valores como 20 y 17, no milisegundos |
| `ipe` | 15 | Clasificación de puntos de etapa | 15 filas y valores de puntos |
| `etg` | 23 | Clasificación general por equipos | 23 filas; tiempos acumulados |
| `ete` | 23 | Clasificación de equipos de etapa | 23 filas; tiempos |
| `img` | 1 | Clasificación de montaña u otro premio de líder | una sola fila; requiere confirmación |

### Por qué `type == "itt"` no es suficiente

Hay cuatro bloques `itt` en la respuesta de la etapa 1:

| `types` | `length` | `checkpoint` | Primer `absolute` | Uso probable |
|---|---:|---:|---:|---|
| `C` | 5.7 | 16 | 389 910 | resultado del tramo/contrarreloj actual |
| `F` | 0 | 3 | 58 620 000 | clasificación de meta o referencia distinta |
| `R` | 0 | 4 | 58 620 357 | ranking de referencia |
| `N`, `A` | 9.4 | 27 | 657 140 | clasificación final/acumulada |

Para obtener el ganador de la etapa que necesita la calculadora, la selección observada más coherente es el bloque `itt` con `types: ["C"]`, si existe. Elegir el primer `itt` funciona en la respuesta actual, pero es una dependencia frágil: el orden de la lista no debe considerarse contrato.

## Datos de corredores y equipos

Los datos personales están separados del ranking. Los corredores incluyen:

- `firstname`, `lastname`, `lastnameshort`.
- `bib`, `nationality`, `sex`, `birthdate`, `idUCI`, `UCICode`.
- `profile`, `profile_sm`, `profile_podium_live`.
- `siteLinks` para páginas en español, inglés y francés.
- `victories`, `podiums` y referencia `$team`.

Los equipos contienen la información necesaria para resolver `$team`, incluyendo nombre, abreviatura, país, logo y referencias internas. La relación completa entre `$rider` y el objeto de corredor debe resolverse mediante los identificadores internos (`_id`, `_virtual` o la convención del sistema), no mediante el dorsal, ya que el dorsal no es necesariamente una clave global.

## Conversión de tiempos

Para un ranking temporal:

```text
segundos = absolute / 1000
diferencia = relative / 1000
```

En la muestra, el ganador de la clasificación `itt` con `types: ["C"]` tenía `absolute = 389910`, equivalente a `389,91 s` o `00:06:30` redondeado al segundo. La precisión observada es de milisegundos, pero la interfaz actual redondea al segundo antes de rellenar horas, minutos y segundos.

No se debe convertir automáticamente `absolute` a tiempo en todos los rankings: `ipg` e `ipe` contienen puntos y pueden producir valores pequeños que no representan milisegundos.

## Puntos de control

La respuesta incluye objetos de `_bind: checkpointList-2026-1`. En la etapa 1 se observaron cuatro puntos de control, con campos como `checkpoint`, `checkpointMeteo`, `checkpointSummits`, `checkpointTypes`, `caravanSchedule`, `lowSchedule` y `middleSchedule`. Estos datos pueden servir para mostrar:

- paso por controles y referencias del recorrido;
- meteorología asociada;
- cumbres y tipos de control;
- horarios de caravana y ventanas temporales.

La respuesta analizada no permite afirmar sin más qué campo contiene el tiempo real de paso de cada corredor; esa información podría estar en otra variante del API o en el estado actualizado del ranking.

## Recomendaciones de integración

1. Mantener el proxy del servidor para evitar depender de CORS del navegador.
2. Comprobar siempre que la respuesta sea una lista no vacía.
3. Seleccionar el ranking por `type` y `types`, no solo por posición en el array.
4. Validar que `absolute` sea numérico y positivo antes de convertirlo.
5. Resolver el corredor desde `$rider` solo cuando se necesite nombre, equipo o nacionalidad.
6. Guardar la URL, la etapa, `_updatedAt` y la hora de consulta para poder auditar resultados.
7. Aplicar un timeout, limitar las peticiones y usar `Cache-Control: no-store` solo cuando se necesite tiempo en directo.
8. Tratar una lista vacía como “sin datos publicados”, no como error de red.
9. No asumir que los códigos, el orden de los bloques o los campos internos `_id` y `_virtual` son contratos permanentes.
10. Verificar que el identificador de carrera corresponde a la competición deseada antes de mostrar los datos al usuario.

## Conclusión

El endpoint es un agregador de estado de carrera, no una respuesta simple de “ganador de etapa”. Puede proporcionar clasificaciones de etapa y generales, puntos, equipos, referencias de corredores, equipos y puntos de control. Sin embargo, la URL analizada actualmente está asociada a datos de La Vuelta y solo tiene poblada la variante `stage=1`; no es una fuente válida para rellenar automáticamente las etapas de la Volta a Portugal 2026 sin localizar primero el endpoint o el identificador de competición correcto.