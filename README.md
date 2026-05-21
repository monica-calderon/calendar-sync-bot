# calendar-sync-bot

Bot en Python para copiar/sincronizar eventos futuros desde uno o varios calendarios de Google Calendar origen hacia un calendario destino compartido.

Está pensado para ejecutarse gratis con GitHub Actions dos veces al día y también mediante llamada externa desde cron-job.org usando `repository\_dispatch`.

## 1\. Qué hace

* Lee eventos futuros de uno o varios calendarios origen.
* Copia los eventos a un calendario destino compartido.
* Evita duplicados mediante un archivo de estado JSON.
* Actualiza eventos ya copiados cuando cambia el evento origen.
* Elimina la copia si el evento origen aparece como cancelado.
* No copia asistentes/invitados.
* No copia enlaces de videollamada ni `conferenceData`.
* No envía notificaciones a invitados.
* No modifica nunca los calendarios origen.
* La descripción de cada copia termina con un texto visible: `Evento de Mónica - \[nombre del calendario]`.
* Marca internamente los eventos creados con `extendedProperties.private.calendarSyncBot=true`, para poder eliminarlos después sin tocar eventos originales del calendario destino.

## 2\. Limitaciones

* Usa `singleEvents=true`, por lo que Google expande recurrencias como eventos individuales dentro de la ventana consultada.
* Si se borra manualmente un evento destino, el estado puede seguir apuntando a una copia inexistente. En ese caso, borra la entrada correspondiente del archivo `state/calendar\_sync\_state.json` o elimina el archivo de estado y resincroniza.
* No sincroniza asistentes, invitados, Google Meet, Zoom ni recordatorios personalizados.
* Por defecto consulta los próximos 60 días.
* Este proyecto usa OAuth con refresh token. La configuración inicial de Google Cloud es manual.

## 3\. Estructura

```text
calendar-sync-bot/
├─ .github/
│  └─ workflows/
│     └─ sync-calendar.yml
├─ src/
│  └─ calendar\_sync/
│     ├─ \_\_init\_\_.py
│     ├─ config.py
│     ├─ google\_calendar.py
│     ├─ state.py
│     ├─ sync.py
│     ├─ cleanup.py
│     └─ main.py
├─ tests/
│  ├─ test\_cleanup.py
│  ├─ test\_state.py
│  └─ test\_sync.py
├─ .env.example
├─ .gitignore
├─ requirements.txt
├─ README.md
└─ AGENTS.md
```

## 4\. Crear el proyecto en Google Cloud

1. Entra en Google Cloud Console.
2. Crea un proyecto nuevo, por ejemplo `calendar-sync-bot`.
3. Entra en el proyecto creado.
4. Ve a **APIs \& Services**.
5. Abre **Library**.
6. Busca **Google Calendar API**.
7. Pulsa **Enable**.

## 5\. Configurar pantalla de consentimiento OAuth

1. Ve a **APIs \& Services** → **OAuth consent screen**.
2. Elige **External** si es una cuenta personal.
3. Completa los campos mínimos:

   * App name: `calendar-sync-bot`
   * User support email: tu email
   * Developer contact information: tu email
4. Añade tu cuenta como usuario de prueba si la app queda en modo testing.
5. Añade el scope:

```text
https://www.googleapis.com/auth/calendar
```

Este scope permite leer y escribir calendarios. El código solo escribe en el calendario destino.

## 6\. Crear credenciales OAuth

1. Ve a **APIs \& Services** → **Credentials**.
2. Pulsa **Create credentials** → **OAuth client ID**.
3. Tipo de aplicación: **Desktop app**.
4. Nombre: `calendar-sync-bot-local`.
5. Guarda:

   * `GOOGLE\_CLIENT\_ID`
   * `GOOGLE\_CLIENT\_SECRET`

## 7\. Obtener el refresh token

Necesitas obtener un `refresh\_token` una vez. Puedes usar este script temporal local.

Crea un archivo temporal llamado `get\_refresh\_token.py` fuera del repositorio o bórralo después:

```python
from google\_auth\_oauthlib.flow import InstalledAppFlow

SCOPES = \["https://www.googleapis.com/auth/calendar"]

client\_config = {
    "installed": {
        "client\_id": "TU\_GOOGLE\_CLIENT\_ID",
        "client\_secret": "TU\_GOOGLE\_CLIENT\_SECRET",
        "auth\_uri": "https://accounts.google.com/o/oauth2/auth",
        "token\_uri": "https://oauth2.googleapis.com/token",
        "redirect\_uris": \["http://localhost"],
    }
}

flow = InstalledAppFlow.from\_client\_config(client\_config, SCOPES)
credentials = flow.run\_local\_server(port=0, access\_type="offline", prompt="consent")
print("REFRESH TOKEN:")
print(credentials.refresh\_token)
```

Instala temporalmente la librería necesaria:

```bash
pip install google-auth-oauthlib
python get\_refresh\_token.py
```

Inicia sesión con la cuenta que tiene acceso a los calendarios origen y destino. Copia el valor impreso como `GOOGLE\_REFRESH\_TOKEN`.

Después borra el script temporal.

## 8\. Configurar calendarios origen y destino

### Calendarios origen

Puedes usar:

```text
primary
```

O IDs de calendarios secundarios, normalmente con este formato:

```text
xxxxx@group.calendar.google.com
```

Para varios calendarios, sepáralos por coma:

```text
primary,otro-calendario@group.calendar.google.com
```

### Calendario destino

Debe ser un calendario donde la cuenta OAuth tenga permiso de escritura.

Si es un calendario compartido:

1. Abre Google Calendar.
2. Entra en configuración del calendario destino.
3. Comparte el calendario con la cuenta usada en OAuth.
4. Dale permiso para **hacer cambios en eventos**.
5. Copia el **ID del calendario**.

## 9\. Variables de entorno

Copia `.env.example` a `.env` para ejecución local:

```bash
cp .env.example .env
```

Rellena:

```env
GOOGLE\_CLIENT\_ID=...
GOOGLE\_CLIENT\_SECRET=...
GOOGLE\_REFRESH\_TOKEN=...
SOURCE\_CALENDAR\_IDS=primary,otro@group.calendar.google.com
DESTINATION\_CALENDAR\_ID=destino@group.calendar.google.com
DAYS\_AHEAD=60
TIMEZONE=Europe/Madrid
STATE\_FILE=state/calendar\_sync\_state.json
EVENT\_OWNER\_NAME=Mónica
```

## 10\. Ejecutar localmente

```bash
python -m venv .venv
```

En Windows PowerShell:

```powershell
.\\.venv\\Scripts\\Activate.ps1
```

En macOS/Linux:

```bash
source .venv/bin/activate
```

Instala dependencias:

```bash
pip install -r requirements.txt
```

Ejecuta tests:

```bash
pytest -q
```

Instala dependencias:

```bash

pip install -e .

```



Ejecuta la sincronización:

```bash
python -m calendar\_sync.main
```

## 11\. Borrar eventos sincronizados

El proyecto incluye un script de limpieza para eliminar solo los eventos del calendario destino que fueron creados por el bot. No borra eventos originales del calendario destino.

Funciona usando dos señales:

* El archivo de estado `state/calendar\_sync\_state.json`.
* La marca interna de Google Calendar `extendedProperties.private.calendarSyncBot=true`.

Ejecución local:

```bash
python -m calendar\_sync.cleanup
```

Ejecución desde GitHub Actions:

1. GitHub → **Actions**.
2. Selecciona **Sync Google Calendars**.
3. Pulsa **Run workflow**.
4. En `mode`, elige `cleanup`.

También puede llamarse con `repository\_dispatch` usando `event\_type`: `cleanup-calendar`.

Al terminar, el script vacía el estado JSON y el workflow lo commitea automáticamente.

## 12\. Configurar GitHub Secrets

El repositorio debe ser privado.

En GitHub:

1. Entra en tu repositorio.
2. Ve a **Settings** → **Secrets and variables** → **Actions**.
3. Crea estos **Repository secrets**:

```text
GOOGLE\_CLIENT\_ID
GOOGLE\_CLIENT\_SECRET
GOOGLE\_REFRESH\_TOKEN
SOURCE\_CALENDAR\_IDS
DESTINATION\_CALENDAR\_ID
```

4. Opcionalmente crea estas **Repository variables**:

```text
DAYS\_AHEAD=60
TIMEZONE=Europe/Madrid
EVENT\_OWNER\_NAME=Mónica
```

No subas el archivo `.env`.

## 13\. Ejecutar desde GitHub Actions

El workflow está en:

```text
.github/workflows/sync-calendar.yml
```

Se ejecuta automáticamente a estas horas UTC:

```text
08:00 UTC
20:00 UTC
```

También permite ejecución manual:

1. GitHub → pestaña **Actions**.
2. Selecciona **Sync Google Calendars**.
3. Pulsa **Run workflow**.

## 14\. Ejecutar desde cron-job.org

El workflow admite `repository\_dispatch` con tipo `sync-calendar`.

### Crear token de GitHub

1. Ve a GitHub → **Settings** → **Developer settings** → **Personal access tokens**.
2. Crea un token fine-grained para este repositorio.
3. Permisos recomendados:

   * Repository permissions → **Contents: Read and write**
   * Repository permissions → **Actions: Read and write**
   * Repository permissions → **Metadata: Read**

### URL para cron-job.org

Usa método `POST`:

```text
https://api.github.com/repos/TU\_USUARIO/calendar-sync-bot/dispatches
```

Headers:

```text
Accept: application/vnd.github+json
Authorization: Bearer TU\_TOKEN\_GITHUB
X-GitHub-Api-Version: 2022-11-28
Content-Type: application/json
```

Body:

```json
{
  "event\_type": "sync-calendar"
}
```

Puedes programarlo 2 veces al día, por ejemplo:

```text
08:00 UTC
20:00 UTC
```

Nota: si ya usas `schedule` de GitHub Actions, cron-job.org es redundante. Puede servir como alternativa si quieres forzar la ejecución externa.

## 15\. Persistencia del estado

El bot guarda el estado en:

```text
state/calendar\_sync\_state.json
```

El workflow lo commitea automáticamente si cambia.

El archivo guarda:

```json
{
  "records": {
    "source\_calendar\_id::source\_event\_id": {
      "source\_calendar\_id": "...",
      "source\_event\_id": "...",
      "destination\_event\_id": "...",
      "source\_updated": "...",
      "last\_synced\_at": "..."
    }
  }
}
```

No contiene secretos.

## 16\. Logs

Los logs muestran:

* Calendario origen leído.
* Número de eventos encontrados.
* Eventos creados.
* Eventos actualizados.
* Eventos omitidos por no cambiar.
* Eventos cancelados/eliminados.
* Errores por evento.
* Resumen final.

Para verlos:

1. GitHub → **Actions**.
2. Abre la ejecución.
3. Abre el job `sync`.
4. Revisa el paso **Run calendar sync**.

## 17\. Errores comunes

### `Missing required environment variable`

Falta un secret o variable. Revisa GitHub Secrets o tu `.env` local.

### `invalid\_grant`

El refresh token no es válido o fue revocado. Genera uno nuevo con `prompt="consent"`.

### `403 Forbidden`

La cuenta OAuth no tiene permisos suficientes sobre algún calendario.

Solución:

* Revisa que puede leer los calendarios origen.
* Revisa que puede escribir en el calendario destino.
* Revisa que el scope sea `https://www.googleapis.com/auth/calendar`.

### `404 Not Found` al actualizar o borrar

La copia destino pudo haberse borrado manualmente. Elimina la entrada concreta de `state/calendar\_sync\_state.json` o borra el archivo de estado completo y resincroniza.

### No aparecen eventos recurrentes

El bot usa:

```text
singleEvents=true
orderBy=startTime
```

Solo se expanden recurrencias dentro de la ventana `DAYS\_AHEAD`.

### Los horarios salen mal

Revisa:

```text
TIMEZONE=Europe/Madrid
EVENT\_OWNER\_NAME=Mónica
```

Y comprueba que los eventos origen tienen `dateTime` y zona horaria correctos.

## 18\. Seguridad

* Usa un repositorio privado.
* No subas `.env`.
* No subas tokens reales.
* Usa GitHub Secrets.
* No pegues el refresh token en issues, commits o logs.
* El archivo de estado no contiene credenciales.

## 19\. Desarrollo

Ejecutar tests:

```bash
pytest -q
```

Ejecutar sincronización:

```bash
python -m calendar\_sync.main
```

Ejecutar limpieza de eventos sincronizados:

```bash
python -m calendar\_sync.cleanup
```

