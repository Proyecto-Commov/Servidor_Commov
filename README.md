# Sistema de Captura y Transmisión de Video en Vivo

Este directorio contiene la parte emisora del sistema. Su responsabilidad es capturar video desde la cámara, codificarlo en H.264 con FFmpeg y entregar el bitstream en tiempo real al cliente receptor por TCP.

El proyecto puede utilizar ese mismo flujo de entrada para dos destinos distintos:

- Reproducción directa con FFmpeg en ventana pop-up.
- Reproducción en navegador mediante un receptor WebSocket en el otro repositorio.

## Visión general del flujo

La lógica del emisor es la siguiente:

1. Se abre la cámara local.
2. FFmpeg recibe la señal y la convierte a H.264.
3. El proceso Python lee el bitstream generado por FFmpeg por stdout.
4. Los bloques de bytes se envían por socket TCP al receptor.
5. El receptor decide si los entrega a FFmpeg o al navegador.

No existe almacenamiento intermedio del video. El sistema trabaja como un canal en vivo: lo que sale de la cámara se codifica, se transporta y se reproduce al instante.

## Archivos del directorio

### `video_capture.py`

Es el módulo central del lado del servidor. Encapsula toda la interacción con FFmpeg y expone una API de captura de video reutilizable.

#### Responsabilidad técnica

Este archivo no reproduce video ni se encarga del socket de red. Su trabajo es exclusivamente:

- detectar el sistema operativo;
- construir el comando correcto de FFmpeg;
- iniciar el proceso de captura;
- leer el bitstream H.264 generado por FFmpeg;
- detener el proceso de manera limpia;
- registrar errores y estadísticas.

#### `VideoCaptureConfig`

La clase `VideoCaptureConfig` agrupa los parámetros de captura y codificación:

- `width`: ancho de salida del video.
- `height`: alto de salida.
- `fps`: fotogramas por segundo.
- `bitrate`: bitrate objetivo y máximo de codificación.
- `preset`: velocidad de codificación de libx264.
- `crf`: factor de calidad constante; cuanto menor, mayor calidad.
- `read_timeout`: tiempo máximo esperado para lectura de datos.

En la configuración actual se usa una resolución de 480x360, 24 FPS en el emisor directo, bitrate de 2500k en el archivo del emisor, preset `superfast` y CRF 28 para priorizar latencia y estabilidad.

#### `WebcamVideoCapture`

Es la clase que implementa toda la captura. Contiene el estado del proceso FFmpeg y la lógica de lectura del stream.

##### Atributos principales

- `self.config`: configuración activa.
- `self.process`: proceso `subprocess.Popen` de FFmpeg.
- `self.is_running`: estado interno de ejecución.
- `self._frame_count`: contador acumulado de bytes leídos.
- `self._error_count`: contador de errores consecutivos.
- `self._max_consecutive_errors`: límite para detener la captura.
- `self._stderr_buffer`: buffer en memoria con stderr de FFmpeg.
- `self._stderr_thread`: thread auxiliar para leer stderr sin bloquear.

##### `_capture_stderr()`

Lee `stderr` de FFmpeg línea por línea en un thread aparte. Su propósito es evitar que el proceso se bloquee si FFmpeg escribe mensajes de error o diagnóstico.

Cada línea se decodifica como UTF-8 con reemplazo de errores. Si el texto contiene palabras como `error` o `fail`, se registra a nivel de error. Esta información luego se reutiliza para diagnóstico cuando FFmpeg devuelve EOF o falla.

##### `_get_last_stderr_errors()`

Devuelve los últimos mensajes relevantes capturados desde stderr. Se usa para mostrar el contexto de un fallo cuando la captura deja de producir datos.

##### `_list_dshow_devices()`

Enumera dispositivos de video en Windows usando `ffmpeg -list_devices true -f dshow -i dummy`.

La función analiza la salida de FFmpeg para extraer:

- el nombre visible del dispositivo;
- el nombre alternativo del dispositivo DirectShow.

No se usa en el flujo principal, pero sirve como apoyo para diagnóstico y para confirmar qué cámara detecta el sistema.

##### `_get_input_device()`

Selecciona la forma correcta de acceder a la cámara según el sistema operativo:

- Windows: `video=Integrated Camera` con `dshow`.
- macOS: índice `0` con `avfoundation`.
- Linux: `/dev/video0` con `v4l2`.

Esta función es crítica porque el formato del input cambia por plataforma. En Windows, además, no se añade `-framerate` en DirectShow porque algunos drivers no lo aceptan.

##### `_build_ffmpeg_command()`

Construye la línea completa de FFmpeg.

Este comando define el comportamiento de captura y codificación:

- `-hide_banner`: oculta el banner de FFmpeg.
- `-loglevel error`: reduce ruido en consola.
- `-y`: sobrescribe sin preguntar.
- `-rtbufsize 256M`: aumenta el buffer de entrada para tolerar picos.
- `-f dshow`, `-f avfoundation` o `-f v4l2`: el formato depende del SO.
- `-i <device>`: dispositivo de cámara seleccionado.
- `-vf yadif=0:-1:0,scale=...:flags=lanczos`: aplica desentrelazado y escalado de alta calidad.
- `-c:v libx264`: usa el codificador H.264 de FFmpeg.
- `-preset`: controla la relación velocidad/calidad.
- `-crf`: controla la compresión perceptual.
- `-b:v`, `-maxrate`, `-bufsize`: estabilizan el caudal de bits.
- `-x264opts aq-mode=2:aq-strength=0.8`: activa cuantización adaptativa.
- `-g`: fija el intervalo de keyframes en dos segundos.
- `-pix_fmt yuv420p`: maximiza la compatibilidad con reproductores.
- `-f h264 pipe:1`: envía el bitstream H.264 puro a stdout.

##### `start()`

Inicia FFmpeg con el comando construido y deja preparado el proceso para lectura continua.

También arranca el thread que consume stderr y reinicia los contadores de estado. Si FFmpeg no existe o no puede lanzarse, la función lanza un `RuntimeError` con un mensaje explicativo.

##### `read_frames()`

Es un generador que lee chunks de bytes desde stdout de FFmpeg.

Comportamiento detallado:

- Lee bloques de tamaño configurable, por defecto 4096 bytes.
- Si recibe datos, reinicia el contador de error y devuelve el chunk.
- Si no recibe datos, interpreta EOF o desconexión de la cámara.
- Si los errores consecutivos superan el límite, detiene la captura.
- Entre intentos introduce una pequeña pausa para no entrar en un bucle agresivo.

La función no reconstruye cuadros de video. Devuelve el stream H.264 tal como sale del codificador, lo que es correcto para transporte de bitstream.

##### `stop()`

Detiene el proceso de captura de forma ordenada:

1. marca `is_running` como falso;
2. intenta terminar FFmpeg de forma graciosa;
3. espera hasta 5 segundos;
4. si no termina, fuerza el cierre con `kill()`.

##### `get_stats()`

Devuelve un diccionario con estado operativo y parámetros activos:

- si la captura está corriendo;
- total de bytes capturados;
- número de errores consecutivos;
- resolución, FPS, bitrate y CRF.

##### `save_to_file()`

Permite guardar el bitstream H.264 a disco.

No forma parte del flujo normal de streaming, pero es útil para pruebas y para capturar una muestra local. Si se indica `duration`, la captura se detiene cuando se supera ese tiempo.

##### `main()`

Función de demostración local. Crea una configuración de ejemplo, arranca la captura, guarda H.264 en `output.h264` durante 10 segundos y luego imprime estadísticas finales.

#### Dependencias internas del módulo

- `subprocess`: ejecución de FFmpeg.
- `platform`: detección del sistema operativo.
- `threading`: lectura concurrente de stderr.
- `logging`: diagnóstico.
- `dataclasses`: definición de configuración.
- `pathlib`: creación de rutas de salida.
- `time`: reintentos y control temporal.

### `emisor_directo.py`

Este script es el emisor de red. Se encarga de conectar la captura de `video_capture.py` con el receptor en el puerto 5000.

#### Objetivo funcional

Tomar el bitstream H.264 generado por FFmpeg y enviarlo sin almacenamiento intermedio al otro proceso que está escuchando por TCP.

#### Flujo interno

1. Imprime un encabezado de inicio.
2. Crea una configuración de captura propia.
3. Construye un socket TCP como cliente.
4. Espera 2 segundos antes de conectar para dar margen al receptor.
5. Se conecta a `127.0.0.1:5000`.
6. Arranca `WebcamVideoCapture`.
7. Lee los chunks H.264 con `read_frames()`.
8. Envía cada bloque con `sendall()`.
9. Acumula los bytes enviados para informes.
10. En caso de finalizar, cierra socket y captura.

#### Configuración activa del emisor

Actualmente el emisor usa:

- resolución 480x360;
- 24 FPS;
- bitrate 2500k;
- preset `superfast`;
- CRF 28.

Esta combinación prioriza fluidez y baja latencia por encima de la calidad máxima.

#### Manejo de errores

El script contempla varios casos:

- `ConnectionRefusedError`: el receptor no estaba listo.
- `KeyboardInterrupt`: el usuario interrumpió la ejecución.
- `Exception` genérica: cualquier error inesperado.

En todos los casos se intenta cerrar la conexión y detener la captura.

### `iniciar_todo.py`

Es el orquestador del modo navegador. Levanta el receptor web y luego inicia el emisor.

#### Responsabilidad

Este archivo no captura video ni reproduce nada. Solo coordina el orden de arranque para que el sistema web funcione sin que el emisor intente conectarse antes de que el receptor esté escuchando.

#### Flujo de ejecución

1. Calcula la ruta del directorio del servidor.
2. Deriva la ruta del directorio `CLIENTE_COMMOV`.
3. Verifica que existan `receptor_web.py` y `emisor_directo.py`.
4. Arranca `receptor_web.py` como proceso hijo.
5. Espera 7 segundos para que Flask y el thread H.264 queden listos.
6. Comprueba que el receptor no haya fallado al iniciar.
7. Arranca `emisor_directo.py`.
8. Muestra las URLs y el estado de ejecución.
9. Espera la finalización del emisor.
10. Si el usuario interrumpe, termina el receptor de forma ordenada.

#### Por qué existe la espera de 7 segundos

El receptor web levanta dos cosas distintas:

- el servidor Flask en el puerto 8080;
- un thread separado que escucha el socket H.264 en el puerto 5000.

La pausa evita una carrera entre procesos y da tiempo a que ambos estén disponibles antes de que el emisor empiece a mandar datos.

#### Dependencias internas

- `subprocess`: lanzamiento de procesos hijos.
- `time`: pausas de sincronización.
- `sys`: uso del intérprete actual.
- `pathlib`: composición segura de rutas.

### `validate.py`

Es el script de diagnóstico y validación del entorno.

#### Finalidad

Verificar que el sistema operativo, FFmpeg, los módulos de Python, las cámaras y los archivos del proyecto estén listos para ejecutar la captura.

#### Funciones principales

##### `print_header()`, `print_ok()`, `print_error()`, `print_warning()`, `print_info()`

Son utilidades de formato de salida para mantener mensajes homogéneos durante la validación.

##### `check_python_version()`

Comprueba que la versión de Python sea 3.8 o superior.

##### `check_ffmpeg()`

Ejecuta `ffmpeg -version` y luego `ffmpeg -codecs` para comprobar dos cosas:

- que FFmpeg esté instalado;
- que `libx264` esté disponible.

Si FFmpeg no existe, muestra instrucciones orientadas al sistema operativo detectado.

##### `check_python_modules()`

Verifica que los módulos base necesarios se puedan importar:

- `subprocess`
- `platform`
- `threading`
- `logging`
- `pathlib`

##### `check_webcam_windows()`

Enumera cámaras en Windows mediante DirectShow usando `ffmpeg -list_devices true -f dshow -i dummy`.

##### `check_webcam_macos()`

Lista dispositivos de AVFoundation en macOS con FFmpeg.

##### `check_webcam_linux()`

Busca `/dev/video*` y, si está disponible, intenta complementar con `v4l2-ctl --list-devices`.

##### `check_webcam()`

Despacha la comprobación correcta según el sistema operativo.

##### `check_video_capture_script()`

Verifica la presencia de archivos esperados del proyecto. En el estado actual busca:

- `video_capture.py`
- `examples.py`
- `requirements.txt`
- `INSTALL.md`
- `README.md`

Esto es importante porque el validador documenta una estructura más amplia que la que se encuentra ahora mismo en la carpeta.

##### `test_video_capture()`

Hace una prueba corta de captura. Crea una configuración temporal, arranca `WebcamVideoCapture`, lee un chunk y luego acumula datos durante unos 3 segundos.

##### `generate_report()`

Resume el resultado de las comprobaciones y determina si el sistema está listo.

##### `main()`

Orquesta toda la validación:

1. imprime un banner inicial;
2. ejecuta todas las pruebas de entorno;
3. ofrece una captura de prueba si lo esencial está correcto;
4. genera el informe final.

#### Observación técnica

El validador está orientado a diagnóstico de captura, no al flujo web. Su objetivo es confirmar que el lado de emisión puede funcionar correctamente.

## Cómo se usa este directorio

### Emisión en directo

```powershell
cd c:\SERVIDOR_COMMOV
python emisor_directo.py
```

### Emisión + receptor web

```powershell
cd c:\SERVIDOR_COMMOV
python iniciar_todo.py
```

### Diagnóstico

```powershell
cd c:\SERVIDOR_COMMOV
python validate.py
```

## Dependencias conceptuales del sistema

- FFmpeg realiza la captura y codificación.
- Python transporta los bytes por socket.
- TCP garantiza entrega ordenada en localhost.
- H.264 es el formato de transporte de video.
- No hay archivo temporal de video en el flujo normal.

## Resumen funcional

El directorio `SERVIDOR_COMMOV` convierte la cámara en un stream H.264 continuo y lo entrega al receptor elegido. Todo el sistema está diseñado para priorizar la reproducción en tiempo real por encima de la persistencia o el archivado.
