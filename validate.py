#!/usr/bin/env python3
"""
Script de validación y diagnóstico.

Verifica que todas las dependencias necesarias estén instaladas
y que el sistema esté configurado correctamente para captura de video.
"""

import subprocess
import platform
import sys
from pathlib import Path
from typing import Tuple, List

def print_header(text: str) -> None:
    """Imprime un encabezado formateado."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")

def print_ok(text: str) -> None:
    """Imprime un mensaje de éxito."""
    print(f"✓ {text}")

def print_error(text: str) -> None:
    """Imprime un mensaje de error."""
    print(f"✗ {text}")

def print_warning(text: str) -> None:
    """Imprime un mensaje de advertencia."""
    print(f"⚠ {text}")

def print_info(text: str) -> None:
    """Imprime un mensaje informativo."""
    print(f"ℹ {text}")

def check_python_version() -> bool:
    """Verifica que Python sea 3.8 o superior."""
    print_header("Verificando versión de Python")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major >= 3 and version.minor >= 8:
        print_ok(f"Python {version_str}")
        return True
    else:
        print_error(f"Python {version_str} (se requiere 3.8 o superior)")
        return False

def check_ffmpeg() -> bool:
    """Verifica que FFmpeg esté instalado."""
    print_header("Verificando instalación de FFmpeg")
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Extraer versión
            first_line = result.stdout.split('\n')[0]
            print_ok(f"FFmpeg instalado: {first_line}")
            
            # Verificar que libx264 esté disponible
            config_result = subprocess.run(
                ["ffmpeg", "-codecs"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "libx264" in config_result.stdout:
                print_ok("Códec H.264 (libx264) disponible")
                return True
            else:
                print_error("Códec H.264 (libx264) no disponible")
                print_warning("Instala FFmpeg con soporte para libx264")
                return False
        else:
            print_error(f"FFmpeg retornó código de error: {result.returncode}")
            return False
    
    except FileNotFoundError:
        print_error("FFmpeg no encontrado o no está en el PATH")
        print_info("Instrucciones de instalación:")
        
        system = platform.system()
        if system == "Windows":
            print("  1. Descarga desde: https://ffmpeg.org/download.html")
            print("  2. O usa: choco install ffmpeg (si tienes Chocolatey)")
            print("  3. Agrega la carpeta de FFmpeg al PATH")
        elif system == "Darwin":
            print("  1. Usa Homebrew: brew install ffmpeg")
        else:
            print("  1. Usa tu gestor de paquetes: apt install ffmpeg")
        
        return False
    
    except subprocess.TimeoutExpired:
        print_error("FFmpeg tardó demasiado en responder (timeout)")
        return False
    except Exception as e:
        print_error(f"Error al verificar FFmpeg: {e}")
        return False

def check_python_modules() -> bool:
    """Verifica que los módulos Python necesarios estén disponibles."""
    print_header("Verificando módulos de Python")
    
    required_modules = {
        "subprocess": "Para invocar FFmpeg",
        "platform": "Para detectar el SO",
        "threading": "Para manejo concurrente",
        "logging": "Para logging",
        "pathlib": "Para manejo de rutas",
    }
    
    all_ok = True
    
    for module_name, description in required_modules.items():
        try:
            __import__(module_name)
            print_ok(f"{module_name:20} - {description}")
        except ImportError:
            print_error(f"{module_name:20} - No disponible")
            all_ok = False
    
    return all_ok

def check_webcam_windows() -> bool:
    """Verifica cámaras disponibles en Windows."""
    print("\nDispositivos de video en Windows:")
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout + result.stderr
        
        if "video" in output.lower():
            print_ok("Cámaras detectadas")
            
            # Mostrar cámaras encontradas
            lines = output.split('\n')
            for line in lines:
                if 'video' in line.lower() or 'camera' in line.lower():
                    print(f"    {line.strip()}")
            
            return True
        else:
            print_warning("No se detectaron cámaras con formato dshow")
            return False
    
    except Exception as e:
        print_warning(f"No se pudo verificar cámaras: {e}")
        return False

def check_webcam_macos() -> bool:
    """Verifica cámaras disponibles en macOS."""
    print("\nDispositivos de video en macOS:")
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stdout + result.stderr
        
        if "AVFoundation" in output or "[" in output:
            print_ok("Verificación de cámaras completada")
            
            # Mostrar información
            lines = output.split('\n')
            for line in lines:
                if '[' in line and ']' in line:
                    print(f"    {line.strip()}")
            
            return True
        else:
            print_warning("No se detectaron cámaras con formato avfoundation")
            return False
    
    except Exception as e:
        print_warning(f"No se pudo verificar cámaras: {e}")
        return False

def check_webcam_linux() -> bool:
    """Verifica cámaras disponibles en Linux."""
    print("\nDispositivos de video en Linux:")
    
    try:
        # Buscar /dev/video*
        video_devices = list(Path("/dev").glob("video*"))
        
        if video_devices:
            print_ok(f"Dispositivos encontrados: {', '.join(str(d.name) for d in video_devices)}")
            
            # Intentar usar v4l2-ctl si está disponible
            try:
                result = subprocess.run(
                    ["v4l2-ctl", "--list-devices"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print("\nInformación detallada:")
                    print(result.stdout)
            except FileNotFoundError:
                print_info("Instala v4l-utils para información detallada: sudo apt install v4l-utils")
            
            return True
        else:
            print_error("No se encontraron dispositivos en /dev/video*")
            return False
    
    except Exception as e:
        print_warning(f"No se pudo verificar cámaras: {e}")
        return False

def check_webcam() -> bool:
    """Verifica disponibilidad de cámara según el SO."""
    print_header("Verificando disponibilidad de cámara")
    
    system = platform.system()
    
    if system == "Windows":
        return check_webcam_windows()
    elif system == "Darwin":
        return check_webcam_macos()
    elif system == "Linux":
        return check_webcam_linux()
    else:
        print_warning(f"SO no soportado: {system}")
        return False

def check_video_capture_script() -> bool:
    """Verifica que el script de captura exista."""
    print_header("Verificando archivos del proyecto")
    
    required_files = {
        "video_capture.py": "Módulo principal",
        "examples.py": "Ejemplos de uso",
        "requirements.txt": "Dependencias",
        "INSTALL.md": "Documentación de instalación",
        "README.md": "Documentación principal",
    }
    
    all_ok = True
    current_dir = Path(".")
    
    for filename, description in required_files.items():
        filepath = current_dir / filename
        
        if filepath.exists():
            size = filepath.stat().st_size
            print_ok(f"{filename:25} ({size:,} bytes) - {description}")
        else:
            print_error(f"{filename:25} - No encontrado")
            all_ok = False
    
    return all_ok

def test_video_capture() -> bool:
    """Intenta una captura de prueba rápida."""
    print_header("Prueba de captura (3 segundos)")
    
    try:
        print("Iniciando captura de prueba...")
        print("(Presiona Ctrl+C si deseas detener antes)")
        
        from video_capture import WebcamVideoCapture, VideoCaptureConfig
        
        config = VideoCaptureConfig(
            width=640,
            height=480,
            fps=15,
            bitrate="1000k"
        )
        
        capture = WebcamVideoCapture(config)
        capture.start()
        
        import time
        for chunk in capture.read_frames(chunk_size=4096):
            if chunk:
                print_ok(f"Datos capturados: {len(chunk)} bytes")
                break

        # Ejecutar por 3 segundos
        start = time.time()
        total_bytes = 0
        
        for chunk in capture.read_frames(chunk_size=4096):
            if chunk:
                total_bytes += len(chunk)
            
            if (time.time() - start) > 3:
                break
        
        capture.stop()
        
        if total_bytes > 0:
            print_ok(f"Captura exitosa: {total_bytes:,} bytes en 3 segundos")
            return True
        else:
            print_error("No se capturaron datos")
            return False
    
    except ImportError as e:
        print_error(f"Error al importar módulo: {e}")
        return False
    except Exception as e:
        print_error(f"Error en captura de prueba: {e}")
        return False

def generate_report(results: dict) -> None:
    """Genera un reporte resumen."""
    print_header("REPORTE DE DIAGNÓSTICO")
    
    checks = [
        ("Python versión", results.get("python_version", False)),
        ("FFmpeg instalado", results.get("ffmpeg", False)),
        ("Módulos de Python", results.get("python_modules", False)),
        ("Cámara disponible", results.get("webcam", False)),
        ("Archivos del proyecto", results.get("video_capture_script", False)),
    ]
    
    print("Estado de verificaciones:\n")
    
    passed = 0
    failed = 0
    
    for check_name, status in checks:
        if status:
            print_ok(f"{check_name}")
            passed += 1
        else:
            print_error(f"{check_name}")
            failed += 1
    
    print(f"\nResultado: {passed} pasadas, {failed} fallidas\n")
    
    if failed == 0:
        print_header("✓ SISTEMA LISTO")
        print("Todas las verificaciones pasaron correctamente.")
        print("Puedes ejecutar: python video_capture.py")
    else:
        print_header("⚠ CONFIGURACIÓN INCOMPLETA")
        print("Por favor, revisa los errores anteriores y ejecuta este script nuevamente.")
    
    print()

def main():
    """Función principal."""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     VALIDADOR DE CONFIGURACIÓN - CAPTURA DE VIDEO           ║
    ║                                                              ║
    ║  Este script verifica que tu sistema esté correctamente     ║
    ║  configurado para ejecutar el sistema de captura de video. ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    results = {}
    
    try:
        # Ejecutar verificaciones
        results["python_version"] = check_python_version()
        results["ffmpeg"] = check_ffmpeg()
        results["python_modules"] = check_python_modules()
        results["webcam"] = check_webcam()
        results["video_capture_script"] = check_video_capture_script()
        
        # Ofrecer prueba de captura si todo está bien
        all_essential_ok = all([
            results.get("python_version"),
            results.get("ffmpeg"),
            results.get("python_modules"),
            results.get("video_capture_script"),
        ])
        
        if all_essential_ok and results.get("webcam"):
            print_header("Prueba de captura opcional")
            print("¿Deseas ejecutar una prueba de captura de 3 segundos?")
            print("(Requiere que tengas una cámara disponible y funcional)")
            
            try:
                response = input("\n¿Ejecutar prueba? (s/n): ").strip().lower()
                if response in ['s', 'si', 'sí']:
                    results["capture_test"] = test_video_capture()
            except KeyboardInterrupt:
                print("\n[Prueba omitida]")
        
        # Generar reporte
        generate_report(results)
    
    except KeyboardInterrupt:
        print("\n\n[Validación interrumpida por el usuario]")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
