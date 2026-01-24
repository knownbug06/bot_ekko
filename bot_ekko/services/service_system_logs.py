import json
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, Union

from bot_ekko.core.base import ThreadedService, ServiceStatus
from bot_ekko.core.models import ServiceSystemLogsConfig
from bot_ekko.sys_config import SYSTEM_LOG_FILE as DEFAULT_LOG_FILE


class SystemLogsService(ThreadedService):
    """
    Service to monitor and log system statistics (CPU, RAM, GPU, etc.).
    """
    def __init__(self, service_config: ServiceSystemLogsConfig) -> None:
        """
        Initialize the System Logs Service.

        Args:
            service_config (ServiceSystemLogsConfig): Configuration object.
        """
        super().__init__(service_config.name, enabled=service_config.enabled)
        self.config = service_config
        self.sample_rate = service_config.sample_rate
        self.log_file = service_config.log_file or DEFAULT_LOG_FILE

        # CPU Usage Calculation State
        self.prev_idle = 0
        self.prev_total = 0

    def init(self) -> None:
        """Initialize the service."""
        self.logger.info(f"System Logs Service initialized. Logging to {self.log_file}")
        super().init()

    def _run(self) -> None:
        """
        Main loop for collecting and logging statistics.
        """
        self.logger.info("System Logs Service Loop Started")

        while not self._stop_event.is_set():
            try:
                stats = self._collect_stats()
                self._log_stats(stats)

                # Update service stats
                self.update_stat("last_update", datetime.now().isoformat())
                if isinstance(stats["cpu_temp"], (int, float)):
                     self.update_stat("cpu_temp", stats["cpu_temp"])
                if isinstance(stats["cpu_usage"], (int, float)):
                     self.update_stat("cpu_usage", stats["cpu_usage"])

                self._stop_event.wait(self.sample_rate)

            except Exception as e: # pylint: disable=broad-except
                self.logger.error(f"Error in SystemLogsService loop: {e}")
                self.increment_stat("errors")
                self.update_stat("last_error", str(e))
                # Avoid tight loop in case of persistent error
                time.sleep(1)

    def _collect_stats(self) -> Dict[str, Any]:
        """
        Collects current system metrics.

        Returns:
            Dict[str, Any]: Dictionary containing system stats.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_temp": self._get_cpu_temp(),
            "cpu_usage": self._get_cpu_usage(),
            "gpu_memory": self._get_gpu_mem(),
            "gpu_clock_mhz": self._get_gpu_clock(),
            "throttled": self._get_throttled_status(),
            "voltage": self._get_core_voltage()
        }

    def _log_stats(self, stats: Dict[str, Any]) -> None:
        """
        Appends stats to the JSON log file.

        Args:
            stats (Dict[str, Any]): The stats to log.
        """
        try:
            with open(self.log_file, 'a') as f:
                json.dump(stats, f)
                f.write('\n')
        except Exception as e: # pylint: disable=broad-except
            self.logger.error(f"Failed to write system logs: {e}")
            self.increment_stat("write_errors")

    def _get_cpu_temp(self) -> float:
        """Gets CPU temperature in Celsius."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read()) / 1000.0
            return temp
        except Exception: # pylint: disable=broad-except
            return 0.0

    def _get_gpu_mem(self) -> str:
        """Gets GPU memory split."""
        try:
            # Output: "gpu=64M"
            output = subprocess.check_output(["vcgencmd", "get_mem", "gpu"]).decode().strip()
            return output.split("=")[1]
        except Exception: # pylint: disable=broad-except
            return "N/A"

    def _get_gpu_clock(self) -> float:
        """Gets GPU clock speed in MHz."""
        try:
            # Output: "frequency(43)=500000000" (Hz)
            output = subprocess.check_output(["vcgencmd", "measure_clock", "v3d"]).decode().strip()
            clock_hz = int(output.split("=")[1])
            return round(clock_hz / 1_000_000, 1)  # Convert to MHz
        except Exception: # pylint: disable=broad-except
            return 0.0

    def _get_throttled_status(self) -> str:
        """
        Returns raw hex string from vcgencmd get_throttled.
        """
        try:
            output = subprocess.check_output(["vcgencmd", "get_throttled"]).decode().strip()
            # output format: "throttled=0x0"
            return output.split("=")[1]
        except Exception: # pylint: disable=broad-except
            return "N/A"

    def _get_core_voltage(self) -> str:
        """Gets core voltage."""
        try:
            output = subprocess.check_output(["vcgencmd", "measure_volts", "core"]).decode().strip()
            # output format: "volt=0.8500V"
            return output.split("=")[1]
        except Exception: # pylint: disable=broad-except
            return "N/A"

    def _get_cpu_usage(self) -> float:
        """Calculates CPU usage percentage using /proc/stat."""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
                if not line:
                    return 0.0

            parts = line.split()
            # parts[0] is 'cpu'

            if len(parts) < 8:
                return 0.0

            # Provide default 0 if mapping fails
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

        except Exception: # pylint: disable=broad-except
            return 0.0

    def update(self) -> None:
        """Empty update method as this service runs in a thread."""
        pass

    def stop(self) -> None:
        """Stop the service."""
        super().stop()

