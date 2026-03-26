#!/usr/bin/env python3
"""
Ejemplos de uso del sistema de captura de video en tiempo real.

Este archivo contiene varios ejemplos de cómo usar la clase WebcamVideoCapture
para diferentes casos de uso.
"""

import time
from video_capture import WebcamVideoCapture, VideoCaptureConfig
from pathlib import Path


def ejemplo_1_captura_basica():
    """
    Ejemplo 1: Captura básica de 10 segundos.
    
    Este es el caso de uso más simple: abrir la cámara, capturar
    video durante un tiempo determinado y guardarlo.
    """
    print("=" * 60)
    print("EJEMPLO 1: Captura básica de 10 segundos")
    print("=" * 60)
    
    config = VideoCaptureConfig()
    capture = WebcamVideoCapture(config)
    
    try:
        capture.start()
        capture.save_to_file("ejemplo_1_basico.h264", duration=10)
        print("✓ Video guardado en: ejemplo_1_basico.h264")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        capture.stop()


def ejemplo_2_calidad_personalizada():
    """
    Ejemplo 2: Captura con configuración personalizada de alta calidad.
    
    Captura video a mayor resolución y calidad, pero esto requiere
    más CPU y genera archivos más grandes.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 2: Captura de alta calidad (1080p, 60 FPS)")
    print("=" * 60)
    
    config = VideoCaptureConfig(
        width=1920,
        height=1080,
        fps=60,
        bitrate="8000k",
        preset="slow",  # Mejora la compresión pero es más lento
        crf=18  # Mejor calidad (valor bajo)
    )
    
    capture = WebcamVideoCapture(config)
    
    try:
        capture.start()
        print("Capturando video de alta calidad por 5 segundos...")
        capture.save_to_file("ejemplo_2_hd.h264", duration=5)
        print("✓ Video guardado en: ejemplo_2_hd.h264")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        capture.stop()


def ejemplo_3_baja_latencia():
    """
    Ejemplo 3: Captura optimizada para baja latencia.
    
    Ideal para aplicaciones que necesitan procesamiento en tiempo real,
    como streaming o reconocimiento de objetos. Sacrifica calidad por
    velocidad de procesamiento.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 3: Captura optimizada para baja latencia")
    print("=" * 60)
    
    config = VideoCaptureConfig(
        width=640,
        height=480,
        fps=30,
        bitrate="1500k",
        preset="ultrafast",  # Máxima velocidad
        crf=35  # Menor calidad pero más rápido
    )
    
    capture = WebcamVideoCapture(config)
    
    try:
        capture.start()
        print("Capturando video de baja latencia por 3 segundos...")
        
        start_time = time.time()
        bytes_capturados = 0
        
        for chunk in capture.read_frames():
            if chunk:
                bytes_capturados += len(chunk)
            
            if (time.time() - start_time) > 3:
                capture.stop()
                break
        
        print(f"✓ Capturados {bytes_capturados} bytes")
        print(f"✓ Bitrate real: {(bytes_capturados * 8) / 3 / 1_000_000:.2f} Mbps")
    
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        capture.stop()


def ejemplo_4_lectura_manual_y_procesamiento():
    """
    Ejemplo 4: Lectura manual de frames para procesamiento en tiempo real.
    
    En lugar de guardar a archivo, procesamos cada chunk de datos.
    Esto es útil si necesitas aplicar filtros, enviar a un servidor,
    o realizar análisis de video.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 4: Lectura manual y procesamiento de frames")
    print("=" * 60)
    
    config = VideoCaptureConfig(
        width=1280,
        height=720,
        fps=30,
        bitrate="2500k"
    )
    
    capture = WebcamVideoCapture(config)
    
    try:
        capture.start()
        print("Leyendo frames por 3 segundos...")
        
        start_time = time.time()
        frame_count = 0
        total_bytes = 0
        
        for chunk in capture.read_frames(chunk_size=8192):
            if chunk:
                # Aquí puedes procesar el chunk:
                # - Guardarlo en memoria
                # - Enviarlo a un servidor
                # - Procesarlo con visión por computadora
                # - etc.
                
                total_bytes += len(chunk)
                frame_count += 1
                
                # Mostrar progreso cada 10 frames
                if frame_count % 10 == 0:
                    elapsed = time.time() - start_time
                    fps_real = frame_count / elapsed
                    print(f"  Frame {frame_count}: {total_bytes/1_000_000:.1f} MB | "
                          f"FPS real: {fps_real:.1f}")
            
            if (time.time() - start_time) > 3:
                capture.stop()
                break
        
        print(f"✓ Total frames capturados: {frame_count}")
        print(f"✓ Total datos: {total_bytes/1_000_000:.1f} MB")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        capture.stop()


def ejemplo_5_manejo_de_errores():
    """
    Ejemplo 5: Demostración de manejo robusto de errores.
    
    Simula condiciones problemáticas como desconexión de cámara.
    El script continúa intentando reconectarse.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 5: Manejo robusto de errores")
    print("=" * 60)
    
    config = VideoCaptureConfig()
    capture = WebcamVideoCapture(config)
    
    try:
        capture.start()
        print("Capturando... (Intenta desconectar la cámara para probar el manejo de errores)")
        
        start_time = time.time()
        error_count = 0
        success_count = 0
        
        for chunk in capture.read_frames():
            if chunk:
                success_count += 1
            else:
                error_count += 1
                print(f"  ⚠ Error detectado (Error #{error_count}), reintentando...")
            
            # Ejecutar por 5 segundos
            if (time.time() - start_time) > 5:
                capture.stop()
                break
        
        stats = capture.get_stats()
        print(f"\n✓ Captura completada:")
        print(f"  - Chunks exitosos: {success_count}")
        print(f"  - Errores: {error_count}")
        print(f"  - Estadísticas: {stats}")
    
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        capture.stop()


def ejemplo_6_comparacion_configuraciones():
    """
    Ejemplo 6: Comparar diferentes configuraciones.
    
    Captura video con diferentes configuraciones y muestra
    el tamaño de archivo resultante.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 6: Comparación de configuraciones")
    print("=" * 60)
    
    configuraciones = {
        "Ultra ligero": VideoCaptureConfig(
            width=320, height=240, fps=15, bitrate="500k", preset="ultrafast", crf=40
        ),
        "Baja latencia": VideoCaptureConfig(
            width=640, height=480, fps=30, bitrate="1500k", preset="ultrafast", crf=35
        ),
        "Estándar": VideoCaptureConfig(
            width=1280, height=720, fps=30, bitrate="2500k", preset="fast", crf=28
        ),
        "Alta calidad": VideoCaptureConfig(
            width=1920, height=1080, fps=30, bitrate="5000k", preset="slow", crf=22
        ),
    }
    
    for nombre, config in configuraciones.items():
        capture = WebcamVideoCapture(config)
        output_file = f"ejemplo_6_{nombre.lower().replace(' ', '_')}.h264"
        
        try:
            print(f"\n  Capturando '{nombre}'...")
            capture.start()
            capture.save_to_file(output_file, duration=2)
            
            # Obtener tamaño del archivo
            size_mb = Path(output_file).stat().st_size / 1_000_000
            print(f"  ✓ {nombre}: {size_mb:.1f} MB (2 segundos)")
            
        except Exception as e:
            print(f"  ✗ Error en {nombre}: {e}")
        finally:
            capture.stop()


def ejemplo_7_estadisticas_en_vivo():
    """
    Ejemplo 7: Mostrar estadísticas en vivo durante la captura.
    
    Demuestra cómo monitorear el rendimiento de la captura.
    """
    print("\n" + "=" * 60)
    print("EJEMPLO 7: Estadísticas en vivo")
    print("=" * 60)
    
    config = VideoCaptureConfig(
        width=1280,
        height=720,
        fps=30,
        bitrate="2500k"
    )
    
    capture = WebcamVideoCapture(config)
    
    try:
        capture.start()
        
        start_time = time.time()
        last_report = start_time
        total_bytes = 0
        
        print("\nCaptura en progreso (presiona Ctrl+C para detener):\n")
        
        for chunk in capture.read_frames(chunk_size=16384):
            if chunk:
                total_bytes += len(chunk)
                
                # Mostrar estadísticas cada segundo
                current_time = time.time()
                if (current_time - last_report) >= 1.0:
                    elapsed = current_time - start_time
                    throughput_mbps = (total_bytes * 8) / elapsed / 1_000_000
                    avg_chunk_size = total_bytes / (elapsed * 30)  # ~30 FPS
                    
                    print(f"  Tiempo: {elapsed:.1f}s | "
                          f"Total: {total_bytes/1_000_000:.1f} MB | "
                          f"Throughput: {throughput_mbps:.1f} Mbps | "
                          f"Chunk avg: {avg_chunk_size/1024:.2f} KB")
                    
                    last_report = current_time
                    
                    # Ejecutar por 10 segundos
                    if elapsed > 10:
                        capture.stop()
                        break
    
    except KeyboardInterrupt:
        print("\n  [Captura detenida por el usuario]")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        capture.stop()


def main():
    """Ejecuta los ejemplos."""
    print("\n" + "=" * 60)
    print("EJEMPLOS DE USO - CAPTURA DE VIDEO CON FFmpeg")
    print("=" * 60)
    
    ejemplos = [
        ("1 - Captura básica", ejemplo_1_captura_basica),
        ("2 - Alta calidad", ejemplo_2_calidad_personalizada),
        ("3 - Baja latencia", ejemplo_3_baja_latencia),
        ("4 - Lectura manual", ejemplo_4_lectura_manual_y_procesamiento),
        ("5 - Manejo de errores", ejemplo_5_manejo_de_errores),
        ("6 - Comparación", ejemplo_6_comparacion_configuraciones),
        ("7 - Estadísticas", ejemplo_7_estadisticas_en_vivo),
    ]
    
    print("\nEjemplos disponibles:")
    for i, (nombre, _) in enumerate(ejemplos, 1):
        print(f"  {i}. {nombre}")
    
    print("\n¿Cuál ejemplo deseas ejecutar? (1-7, 0 para todos, o 'q' para salir):")
    
    try:
        choice = input().strip().lower()
        
        if choice == 'q':
            print("Saliendo...")
            return
        
        elif choice == '0':
            # Ejecutar todos
            for nombre, func in ejemplos:
                try:
                    func()
                    time.sleep(1)
                except KeyboardInterrupt:
                    print("\n[Ejemplo interrumpido]")
                    break
        
        else:
            # Ejecutar uno específico
            idx = int(choice) - 1
            if 0 <= idx < len(ejemplos):
                ejemplos[idx][1]()
            else:
                print("Opción inválida.")
    
    except ValueError:
        print("Entrada inválida.")
    except KeyboardInterrupt:
        print("\n[Programa interrumpido por el usuario]")


if __name__ == "__main__":
    main()
