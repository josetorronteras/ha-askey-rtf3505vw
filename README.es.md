# Askey RTF3505VW — Integración para Home Assistant

Integración custom para Home Assistant que expone los datos del router **Askey RTF3505VW** (distribuido por Movistar España) como entidades nativas.

## Requisitos

- Home Assistant 2024.1 o superior
- Router Askey RTF3505VW accesible en la red local

## Instalación

### Mediante HACS (recomendado)

1. En HACS, pulsa el menú de tres puntos (⋮) arriba a la derecha y selecciona **Repositorios personalizados**.
2. Pega `https://github.com/josetorronteras/ha-askey-rtf3505vw` y selecciona **Integración** como categoría. Pulsa **Añadir**.
3. Busca **Askey RTF3505VW** en HACS e instálalo.
4. Reinicia Home Assistant.
5. Ve a **Ajustes → Dispositivos y servicios → Añadir integración** y busca "Askey RTF3505VW".

### Manual

1. Copia la carpeta `custom_components/askey_rtf3505vw/` en el directorio `custom_components/` de tu instalación de Home Assistant.
2. Reinicia Home Assistant.
3. Ve a **Ajustes → Dispositivos y servicios → Añadir integración** y busca "Askey RTF3505VW".

## Entidades

### Sensores

| Entidad | Descripción |
|---|---|
| Dispositivos conectados | Total de dispositivos en la red |
| Dispositivos por cable | Dispositivos conectados por ethernet |
| WiFi 2.4 GHz | Dispositivos conectados a la banda de 2.4 GHz |
| WiFi 5 GHz | Dispositivos conectados a la banda de 5 GHz |
| Red de invitados | Dispositivos en la red de invitados |
| Uptime | Tiempo de actividad del router en segundos |

Los nombres de las entidades están traducidos al español de forma nativa.

Cada sensor de conteo incluye un atributo `devices` con el listado de hostname, MAC, IP y (para dispositivos Wi-Fi) SSID y RSSI de cada dispositivo.

### Device trackers

Una entidad `device_tracker` por cada dispositivo detectado. Las entidades se crean dinámicamente en la primera detección y persisten aunque el dispositivo se desconecte. El último hostname conocido se conserva mientras el dispositivo está ausente.

### Botón

| Entidad | Descripción |
|---|---|
| Reiniciar router | Envía el comando de reinicio al router |

## Configuración

Se establece durante la configuración inicial y se puede ajustar después desde **Ajustes → Dispositivos y servicios → Configurar**.

| Campo | Por defecto | Descripción |
|---|---|---|
| IP del router | `192.168.1.1` | Dirección IP del router (se fija al crear, no es editable después) |
| Contraseña | — | La contraseña impresa en la pegatina del router |
| Intervalo de escaneo | `300 s` | Frecuencia de consulta al router (mínimo 10 s) |
| Tiempo de gracia de presencia | `180 s` | Segundos antes de marcar un dispositivo como ausente tras perder la conexión. Se eleva automáticamente al intervalo de escaneo para garantizar que el periodo de gracia cubra al menos un ciclo de polling. Usa 0 para desactivar. |

## Notas técnicas

- Usa una sesión `aiohttp` dedicada con `force_close=True` porque el router rechaza conexiones keep-alive.
- Los datos de dispositivos se combinan de tres fuentes: tabla DHCP, tabla ARP y listas de estaciones Wi-Fi.
- La expiración de sesión se detecta automáticamente y lanza un re-login. Un fallo transitorio devuelve datos cacheados; solo dos fallos consecutivos marcan las entidades como no disponibles.
- Lanza un evento `askey_rtf3505vw_device_connected` cuando aparece un dispositivo nuevo en la red (tras el escaneo inicial), útil para automatizaciones.
