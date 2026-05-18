#!/bin/bash
# QUICK_START.sh — Script de inicio rápido del sistema con limpieza automática

cleanup() {
    echo ""
    echo "=================================================="
    echo "  Limpiando procesos..."
    echo "=================================================="
    if [ ! -z "$TEMP_PID" ] && kill -0 $TEMP_PID 2>/dev/null; then
        echo "Terminando Simulador de Temperatura (PID $TEMP_PID)..."
        kill $TEMP_PID 2>/dev/null
        sleep 2
        kill -9 $TEMP_PID 2>/dev/null || true
    fi
    echo "Procesos terminados"
    echo "=================================================="
}

# Solo limpiar en caso de interrupción, no en salida normal
trap cleanup SIGINT SIGTERM

echo "=================================================="
echo "  SERVIDOR_COMMOV — Sistema de Monitorización"
echo "=================================================="
echo ""

WORKDIR="/home/avatarloren/Commov/SERVIDOR_COMMOV"
cd "$WORKDIR" || exit 1

# Limpiar puertos antes de iniciar
echo "[0/2] Liberando puertos 9000 y 9001..."
fuser -k 9000/tcp 9001/tcp 2>/dev/null || true
sleep 1

# Activar venv
echo "[1/2] Activando entorno virtual..."
source venv/bin/activate

# Iniciar servidor de temperatura simulado
echo "[2/2] Iniciando simulador de temperatura (puerto 9001)..."
python3 temp_simulator.py > /tmp/temp_simulator.log 2>&1 &
TEMP_PID=$!
sleep 2

# Verificar que el proceso está vivo
if ! kill -0 $TEMP_PID 2>/dev/null; then
    echo "❌ Error: Simulador de temperatura no se inició"
    cat /tmp/temp_simulator.log
    exit 1
fi
echo "✓ Simulador iniciado (PID $TEMP_PID)"

# Mostrar instrucciones
echo ""
echo "=================================================="
echo "  CONFIGURACIÓN LISTA"
echo "=================================================="
echo "Servidor de Temperatura: PID $TEMP_PID (puerto 9001)"
echo "  Log: tail -f /tmp/temp_simulator.log"
echo ""
echo "Ahora abre otra terminal y ejecuta:"
echo "  cd $WORKDIR"
echo "  source venv/bin/activate"
echo "  python3 monitor_app.py"
echo ""
echo "La aplicación capturará vídeo directamente de /dev/video2"
echo "y se conectará al sensor de temperatura."
echo ""
echo "Presiona Ctrl+C para detener el simulador"
echo "=================================================="
echo ""

# Esperar a los procesos
wait
