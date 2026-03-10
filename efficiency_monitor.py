try:
    import torch
    HAS_ML = True
except ImportError:
    HAS_ML = False
import psutil
import os
try:
    import GPUtil
except ImportError:
    GPUtil = None

from typing import Dict

class EfficiencyMonitor:
    """
    Quantifies the 'Solarpunk Advantage' of Neuromorphic SNNs.
    Converts Joules into tangible human metrics.
    Also handles Thermal Guarding and Resource Quotas (Task #8).
    """
    def __init__(self, 
                 cpu_threshold=85.0, 
                 gpu_threshold=80.0, 
                 max_cpu_pct=50.0, 
                 max_ram_mb=2048):
        self.cpu_threshold = cpu_threshold
        self.gpu_threshold = gpu_threshold
        self.max_cpu_pct = max_cpu_pct
        self.max_ram_mb = max_ram_mb
        
        self.ENERGY_MAC_DENSE = 3.1  # Picojoules (pJ)
        self.ENERGY_SPIKE_ADD = 0.1  # pJ
        
        # Conversion Constants
        self.J_PER_PHONE_CHARGE_MIN = 60.0 # 1 minute of charging ~60 Joules
        self.J_PER_LED_SEC = 9.0           # 9W LED bulb uses 9 Joules/sec

    def check_node_health(self) -> Dict:
        """
        Comprehensive health check including thermal and resource quotas (Task #8).
        """
        vitals = {
            "cpu_temp": 0.0, 
            "gpu_temp": 0.0, 
            "vram_used_pct": 0.0,
            "process_cpu_pct": 0.0,
            "process_ram_mb": 0.0,
            "is_safe": True, 
            "reason": "OK"
        }
        
        # 1. Thermal Checks
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                vitals["cpu_temp"] = max([t.current for t in temps['coretemp']])
            elif 'cpu_thermal' in temps:
                vitals["cpu_temp"] = temps['cpu_thermal'][0].current
        except Exception: pass
        
        if vitals["cpu_temp"] > self.cpu_threshold:
            vitals["is_safe"] = False
            vitals["reason"] = f"CPU_OVERHEAT ({vitals['cpu_temp']}C)"

        # 2. Resource Quotas (Task #8)
        try:
            process = psutil.Process(os.getpid())
            vitals["process_cpu_pct"] = process.cpu_percent(interval=0.1)
            vitals["process_ram_mb"] = process.memory_info().rss / (1024 * 1024)
            
            if vitals["process_cpu_pct"] > self.max_cpu_pct:
                vitals["is_safe"] = False
                vitals["reason"] = f"QUOTA_CPU_EXCEEDED ({vitals['process_cpu_pct']:.1f}%)"
            
            if vitals["process_ram_mb"] > self.max_ram_mb:
                vitals["is_safe"] = False
                vitals["reason"] = f"QUOTA_RAM_EXCEEDED ({vitals['process_ram_mb']:.1f}MB)"
        except Exception: pass

        # 3. GPU Checks
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    vitals["gpu_temp"] = gpu.temperature
                    vitals["vram_used_pct"] = gpu.memoryUtil * 100
                    
                    if vitals["gpu_temp"] > self.gpu_threshold:
                        vitals["is_safe"] = False
                        vitals["reason"] = f"GPU_OVERHEAT ({vitals['gpu_temp']}C)"
                    
                    if vitals["vram_used_pct"] > 90.0:
                        vitals["is_safe"] = False
                        vitals["reason"] = f"VRAM_PRESSURE ({vitals['vram_used_pct']:.1f}%)"
            except Exception: pass
            
        return vitals

    def calculate_savings(self, 
                          num_inputs: int, 
                          num_hidden: int, 
                          num_outputs: int, 
                          actual_spikes: int) -> Dict:
        
        total_ingrvms = (num_inputs * num_hidden) + (num_hidden * num_outputs)
        energy_dense_pj = total_ingrvms * self.ENERGY_MAC_DENSE
        energy_snn_pj = actual_spikes * self.ENERGY_SPIKE_ADD
        
        energy_saved_pj = energy_dense_pj - energy_snn_pj
        joules_saved = energy_saved_pj / 1e12
        
        phone_mins = joules_saved / self.J_PER_PHONE_CHARGE_MIN
        led_secs = joules_saved / self.J_PER_LED_SEC
        
        return {
            "joules_saved": joules_saved,
            "reduction_pct": round((energy_saved_pj / energy_dense_pj) * 100, 2),
            "phone_charge_mins": round(phone_mins, 4),
            "led_bulb_secs": round(led_secs, 2)
        }

if __name__ == "__main__":
    # Test Resource Quota Trigger
    monitor = EfficiencyMonitor(max_ram_mb=10) # Set very low to trigger quota
    health = monitor.check_node_health()
    print(f"Health Check: {'✅' if health['is_safe'] else '❌'}")
    print(f"Status: {health['reason']}")
    print(f"RAM Usage: {health['process_ram_mb']:.1f}MB")
