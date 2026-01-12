import threading
import time
import json
import subprocess
import os
from datetime import datetime
from bot_ekko.core.logger import get_logger
from bot_ekko.sys_config import SYSTEM_LOG_FILE, SYSTEM_SAMPLE_RATE

logger = get_logger("SystemMonitor")

class SystemMonitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.log_file = SYSTEM_LOG_FILE
        self.sample_rate = SYSTEM_SAMPLE_RATE
        
        # CPU Usage Calculation State
        self.prev_idle = 0
        self.prev_total = 0
        
        # Ensure log file exists or creates it (append mode will handle it)
        logger.info(f"System Monitor initialized. Logging to {self.log_file}")

    def run(self):
        logger.info("System Monitor started.")
        while self.running:
            try:
                stats = self._collect_stats()
                self._log_stats(stats)
            except Exception as e:
                logger.error(f"Error in SystemMonitor loop: {e}")
            
            time.sleep(self.sample_rate)

    def stop(self):
        self.running = False
        logger.info("System Monitor stopped.")

    def _collect_stats(self):
        """Collects current system metrics."""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_temp": self._get_cpu_temp(),
            "cpu_usage": self._get_cpu_usage(),
            "gpu_memory": self._get_gpu_mem(),
            "gpu_clock_mhz": self._get_gpu_clock(),
            "throttled": self._get_throttled_status(),
            "voltage": self._get_core_voltage()
        }

    def _log_stats(self, stats):
        """Appends stats to the JSON log file."""
        try:
            with open(self.log_file, 'a') as f:
                json.dump(stats, f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to write system logs: {e}")

    def _get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read()) / 1000.0
            return temp
        except Exception:
            return 0.0

    def _get_gpu_mem(self):
        try:
            # Output: "gpu=64M"
            output = subprocess.check_output(["vcgencmd", "get_mem", "gpu"]).decode().strip()
            return output.split("=")[1]
        except Exception:
            return "N/A"

    def _get_gpu_clock(self):
        try:
            # Output: "frequency(43)=500000000" (Hz)
            output = subprocess.check_output(["vcgencmd", "measure_clock", "v3d"]).decode().strip()
            clock_hz = int(output.split("=")[1])
            return round(clock_hz / 1_000_000, 1) # Convert to MHz
        except Exception:
            return 0.0

    def _get_throttled_status(self):
        """
        Returns raw hex string from vcgencmd get_throttled.
        0x0: No throttling
        Bit 0: Under-voltage detected
        Bit 1: Arm frequency capped
        Bit 2: Currently throttled
        Bit 16: Under-voltage has occurred
        Bit 17: Arm frequency capped has occurred
        Bit 18: Throttling has occurred
        """
        try:
            output = subprocess.check_output(["vcgencmd", "get_throttled"]).decode().strip()
            # output format: "throttled=0x0"
            return output.split("=")[1]
        except Exception:
            return "N/A"

    def _get_core_voltage(self):
        try:
            output = subprocess.check_output(["vcgencmd", "measure_volts", "core"]).decode().strip()
            # output format: "volt=0.8500V"
            return output.split("=")[1]
        except Exception:
            return "N/A"

    def _get_cpu_usage(self):
        """Calculates CPU usage percentage using /proc/stat."""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            
            parts = line.split()
            # parts[0] is 'cpu'
            # parts[1] user, [2] nice, [3] system, [4] idle, [5] iowait, ...
            
            user = int(parts[1])
            nice = int(parts[2])
            system = int(parts[3])
            idle = int(parts[4])
            iowait = int(parts[5])
            irq = int(parts[6])
            softirq = int(parts[7])
            steal = int(parts[8])
            
            total = user + nice + system + idle + iowait + irq + softirq + steal
            
            # Use deltas
            delta_total = total - self.prev_total
            delta_idle = idle - self.prev_idle
            
            self.prev_total = total
            self.prev_idle = idle
            
            if delta_total == 0:
                return 0.0
                
            usage = 1.0 - (delta_idle / delta_total)
            return round(usage * 100, 1)
            
        except Exception:
            return 0.0
