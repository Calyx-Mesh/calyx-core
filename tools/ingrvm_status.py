import os
import sys
import psutil
from rich.console import Console
from rich.table import Table

# Add parent dir to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.hardware_monitor import HardwareProtector

def show_status():
    """
    INGRVM Status: A CLI summary of the PC node's health and mesh status.
    """
    console = Console()
    monitor = HardwareProtector()
    vitals = monitor.get_gpu_vitals()
    
    table = Table(title="🌿 INGRVM_NODE: Desktop Status", border_style="green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold yellow")
    table.add_column("Health", style="bold green")

    # 1. GPU Vitals
    if vitals:
        table.add_row("GPU Temp", f"{vitals['temp']}°C", "✅ SAFE" if vitals['temp'] < 75 else "⚠️ WARM")
        table.add_row("GPU Load", f"{vitals['load']}%", "✅ ACTIVE")
        table.add_row("VRAM Usage", f"{vitals['vram_used']:.0f} / {vitals['vram_total']:.0f} MB", "✅ OK" if vitals['vram_free'] > 500 else "⚠️ LOW")
    else:
        table.add_row("GPU", "Not Detected", "❌ ERROR")

    # 2. System Vitals
    mem = psutil.virtual_memory()
    table.add_row("System RAM", f"{mem.percent}%", "✅ OK")
    
    # 3. Hub Status
    # Check if port 8000 is listening
    hub_active = False
    for conn in psutil.net_connections():
        if conn.laddr and conn.laddr.port == 8000:
            hub_active = True
            break
    table.add_row("Hub Server", "Active (v1.3.2)" if hub_active else "Inactive", "✅ ON" if hub_active else "❌ OFF")

    # 4. Phase 2 Progress
    table.add_row("Sprint Progress", "18 / 20 Tasks", "🚀 ON TRACK")

    console.print(table)
    
    print("\n💡 Hub Access (Laptop): http://192.168.68.51:8000")

if __name__ == "__main__":
    show_status()

