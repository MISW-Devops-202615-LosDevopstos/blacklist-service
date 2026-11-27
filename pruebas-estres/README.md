# Prueba de estrés (Entrega 4)

Plan de Apache JMeter 5.6.3 para generar carga sobre el microservicio y analizarla en New Relic.

## Escenario

| Minutos | Fase | Usuarios | Qué busca |
|---|---|---|---|
| 0 | Preparación | 1 | Crea 50 emails semilla (`seed1@stress.test` … `seed50@stress.test`) |
| 0–5 | 1. Línea base | 5 | Tiempos de referencia |
| 5–15 | 2. Carga | 25 | Uso normal alto |
| 15–25 | 3. Estrés | 50, y 50 más desde el minuto 18 | Saturar la tarea (0,25 vCPU) |
| 20–23 | 3b. Ráfaga de errores | 20 | Subir la tasa de errores 500 por encima del umbral de la alerta |
| 25–30 | 4. Recuperación | 5 | Ver si el servicio vuelve a la normalidad |

Cada usuario espera entre 200 y 500 ms entre peticiones. Mezcla de peticiones en todas las fases, salvo la ráfaga:

| Petición | % | Código esperado |
|---|---|---|
| `GET /blacklists/seed<1-100>@stress.test` (la mitad existe) | 70 | 200 |
| `POST /blacklists` con email nuevo | 20 | 201 |
| `POST /blacklists` duplicado (`seed1@stress.test`) | 3 | 409 |
| `POST /blacklists` con email y `app_uuid` inválidos | 3 | 400 |
| `GET /blacklists/...` sin token | 2 | 401 |
| `POST /blacklists` con `\u0000` en `blocked_reason` (PostgreSQL lo rechaza) | 2 | 500 |

Cada petición tiene una aserción con el código esperado. En el reporte de JMeter, un "error" es una respuesta distinta a la esperada (por ejemplo, un timeout o un 502 del balanceador), no los 4xx/500 provocados.

## Parámetros

Se pasan con `-Jnombre=valor`:

| Parámetro | Por defecto | Uso |
|---|---|---|
| `token` | — (obligatorio) | Token JWT, sin el prefijo `Bearer` |
| `host` / `puerto` / `protocolo` | `localhost` / `8000` / `http` | Servidor |
| `minuto` | `60` | Segundos que dura cada minuto del plan. Con `6`, el plan completo dura 3 minutos (ensayo) |
| `base_usuarios`, `carga_usuarios`, `estres_usuarios`, `estres_extra_usuarios`, `rafaga_usuarios`, `recuperacion_usuarios` | 5, 25, 50, 50, 20, 5 | Usuarios de cada fase |

## Ejecutar

Siempre en modo sin interfaz (`-n`); la interfaz gráfica solo para ver o editar el plan.

```bash
cd pruebas-estres
read -s -p "Token: " TOKEN; echo

# Ensayo de 3 minutos contra Fargate
jmeter -n -t blacklist-stress.jmx -Jhost=blacklist-alb-1344505848.us-east-2.elb.amazonaws.com -Jpuerto=80 \
  -Jtoken="$TOKEN" -Jminuto=6 -Jestres_usuarios=10 -Jestres_extra_usuarios=10 \
  -j resultados/jmeter.log -l resultados/ensayo.jtl -e -o resultados/ensayo-html

# Prueba completa (30 minutos)
jmeter -n -t blacklist-stress.jmx -Jhost=blacklist-alb-1344505848.us-east-2.elb.amazonaws.com -Jpuerto=80 \
  -Jtoken="$TOKEN" -j resultados/jmeter.log -l resultados/final.jtl -e -o resultados/final-html
```

El carácter nulo va en el JSON y no en la URL: el balanceador de AWS rechaza `%00` en la URL con 400 antes de que llegue a la app.

`resultados/` no se sube al repositorio. El reporte queda en `resultados/final-html/index.html`.

Los emails que crea la prueba terminan en `@stress.test`, así que se pueden identificar en la base de datos.
