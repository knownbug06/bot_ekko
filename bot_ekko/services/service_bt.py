import subprocess
import logging
from typing import Optional, List
from bluezero import peripheral

from bot_ekko.services.base import ThreadedService
from bot_ekko.services.errors import ServiceDependencyError
from bot_ekko.core.models import BluetoothData, ServiceBluetoothConfig, CommandNames
from bot_ekko.core.command_center import CommandCenter

class BluetoothService(ThreadedService):
    def __init__(self, service_bt_config: ServiceBluetoothConfig, command_center: CommandCenter, name: str = "bluetooth"):
        super().__init__(name, enabled=service_bt_config.enabled)
        self.adapter_address: Optional[str] = None
        self.peripheral: Optional[peripheral.Peripheral] = None
        self.is_connected: bool = False
        self.bt_data: Optional[BluetoothData] = None
        self.service_bt_config: ServiceBluetoothConfig = service_bt_config
        self.command_center: CommandCenter = command_center

    def init(self) -> None:
        """Initialize the Bluetooth service resources."""
        super().init()
        self.adapter_address = self.get_hci0_addr()
        if not self.adapter_address:
             self.logger.error("No Bluetooth Adapter found.")
             # We might want to raise an exception here if the service fails to init without hardware
             # But following original logic, it might just log error. 
             # However, ThreadedService.start() calls init(), and if init fails it logs it.
             # Let's raise an exception so the service status reflects failure/doesn't start properly if critical.
             raise ServiceDependencyError("No Bluetooth Adapter found", self.name)
        
        self.logger.info(f"Bluetooth Service Initialized with adapter: {self.adapter_address}")

    def get_hci0_addr(self) -> Optional[str]:
        try:
            out = subprocess.check_output("hciconfig hci0", shell=True).decode()
            return out.split("BD Address:")[1].split()[0]
        except Exception as e:
            self.logger.error(f"Failed to get HCI0 address: {e}")
            return None

    def get_bt_data(self) -> Optional[BluetoothData]:
        data = self.bt_data
        self.bt_data = None # reset data after read is complete since its running it a loop
        return data

    def on_write(self, value: List[int], options: dict):
        try:
            cmd = bytes(value).decode().strip()
            self.logger.info(f"Command received via Bluetooth: {cmd}")
            self.is_connected = True
            self.bt_data = BluetoothData(text=cmd, is_connected=self.is_connected)
            self.increment_stat("commands_received")
        except Exception as e:
            self.logger.error(f"Error processing bluetooth command: {e}")
            self.update_stat("last_error", str(e))

    def _run(self) -> None:
        if not self.adapter_address:
            self.logger.error("No Bluetooth Adapter found. Bluetooth Service cannot run.")
            return

        self.logger.info(f"Starting Bluetooth Service on {self.adapter_address}")

        try:
            self.peripheral = peripheral.Peripheral(
                self.adapter_address,
                local_name='Ekko'
            )

            self.peripheral.add_service(
                srv_id=1,
                uuid='12345678-1234-5678-1234-56789abcdef0',
                primary=True
            )

            # WRITE characteristic (phone → Pi)
            self.peripheral.add_characteristic(
                srv_id=1,
                chr_id=1,
                uuid='12345678-1234-5678-1234-56789abcdef1',
                value=[],
                notifying=False,
                flags=['write'],
                write_callback=self.on_write
            )

            self.is_connected = True
            
            # publish is blocking, so we need a way to stop it? 
            # The original code just says "daemon=True" so it dies with main process.
            # bluezero's publish() runs the GMainLoop. 
            # stopping is hard. 
            # But ThreadedService expects _run to be the loop. 
            # If publish() blocks, that's fine for _run, but stop() might be tricky.
            self.peripheral.publish()
            
        except Exception as e:
            self.logger.error(f"Bluetooth Service crashed: {e}")
            self.update_stat("crash_error", str(e))
            raise

    def stop(self) -> None:
        """Signal the service to stop."""
        super().stop()
        # Attempt to stop the peripheral if it's running
        # As noted in original file: "bluezero peripheral doesn't strictly have a stop method exposed easily"
        # We rely on daemon thread behavior mostly, but let's see if we can do anything.
        if self.peripheral:
             # There isn't a standard stop method in bluezero.peripheral.Peripheral that is easily accessible/safe
             # from another thread without the potential for issues. 
             pass
    
    def update(self):
        data = self.get_bt_data()
        if data and data.is_connected:
            cmd, query, *_ = data.text.split(";") + [None, None]
            cmd = cmd.upper()
            if cmd == "STATE":
                self.command_center.issue_command(
                    command_name=CommandNames.CHANGE_STATE,
                    params={"target_state": query.upper()}
                )
            



        