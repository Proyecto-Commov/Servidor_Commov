import subprocess
import time
import sys
import os
from pathlib import Path

def iniciar_sistema():
    """
    Inicia el sistema completo: Receptor Web en CLIENTE_COMMOV + Emisor en SERVIDOR_COMMOV
    """
    print("=" * 60)
    print("[START] Iniciando Sistema Commov (Emisor + Receptor Web)")
    print("=" * 60)
    
    # Obtener rutas de los directorios
    servidor_dir = Path(__file__).parent  # c:\SERVIDOR_COMMOV
    cliente_dir = servidor_dir.parent / "CLIENTE_COMMOV"  # c:\CLIENTE_COMMOV
    
    # Verificar que existan los archivos necesarios
    receptor_web = cliente_dir / "receptor_web.py"
    emisor_directo = servidor_dir / "emisor_directo.py"
    
    if not receptor_web.exists():
        print(f"[ERROR] Error: No se encontro {receptor_web}")
        print(f"Asegúrate de que CLIENTE_COMMOV existe en: {cliente_dir}")
        return
    
    if not emisor_directo.exists():
        print(f"[ERROR] Error: No se encontro {emisor_directo}")
        return
    
    # Iniciar receptor web (debe estar listo ANTES del emisor)
    print("\n[INIT] Iniciando Receptor Web (Puerto 8080)...")
    print(f"   Ejecutando desde: {cliente_dir}")
    sys.stdout.flush()
    
    receptor_process = subprocess.Popen(
        [sys.executable, str(receptor_web)],
        cwd=str(cliente_dir),
        # No redirigir salida - mostrar en consola directamente
        bufsize=1,
        universal_newlines=True
    )
    
    # Esperar a que el servidor Flask esté listo (IMPORTANTE: dar tiempo al thread H.264)
    print("[WAITING] Esperando 7 segundos para que receptor este listo...")
    sys.stdout.flush()
    time.sleep(7)
    
    # Verificar que el receptor está corriendo
    if receptor_process.poll() is not None:
        print("[ERROR] Error: El receptor web fallo al iniciar.")
        return
    
    print("[OK] Receptor Web iniciado correctamente")
    print("   Accede a: http://localhost:8080")
    print("   WebSocket: ws://localhost:8080/video")
    
    # Iniciar emisor
    print("\n[INIT] Iniciando Camara y Transmision...")
    print(f"   Conectara a: localhost:5000")
    
    try:
        emisor_process = subprocess.Popen(
            [sys.executable, str(emisor_directo)],
            cwd=str(servidor_dir),
            # No redirigir salida - mostrar en consola directamente
            bufsize=1,
            universal_newlines=True
        )
        
        print("[OK] Emisor iniciado")
        print("\n" + "=" * 60)
        print("[RUNNING] SISTEMA EN FUNCIONAMIENTO")
        print("=" * 60)
        print("Abre tu navegador en: http://localhost:8080")
        print("Presiona Ctrl+C para detener el sistema")
        print("=" * 60 + "\n")
        
        # Esperar a que termine el emisor (o Ctrl+C)
        emisor_process.wait()
        
    except KeyboardInterrupt:
        print("\n\n[STOP] Deteniendo sistema...")
    except Exception as e:
        print(f"[ERROR] Error al iniciar emisor: {e}")
    finally:
        # Terminar el receptor
        print("\n[CLEANUP] Cerrando Receptor Web...")
        sys.stdout.flush()
        if receptor_process.poll() is None:
            receptor_process.terminate()
            try:
                receptor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                receptor_process.kill()
        
        print("[OK] Sistema cerrado correctamente.")

if __name__ == "__main__":
    iniciar_sistema()