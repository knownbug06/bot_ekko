import subprocess
from typing import Optional, List, Dict, Any
from bluezero import peripheral # type: ignore

from bot_ekko.core.base import ThreadedService
from bot_ekko.core.errors import ServiceDependencyError
from bot_ekko.core.models import BluetoothData, ServiceBluetoothConfig, CommandNames
from bot_ekko.core.command_center import CommandCenter

class BluetoothService(ThreadedService):
    """
    Manages Bluetooth Low Energy (BLE) communication.
    Acts as a peripheral to accept commands from a central device (e.g., phone app).
    """
    def __init__(self, service_bt_config: ServiceBluetoothConfig, command_center: CommandCenter, name: str = "bluetooth"):
        """
        Initialize the Bluetooth Service.

        Args:
            service_bt_config (ServiceBluetoothConfig): Configuration object.
            command_center (CommandCenter): Command issuer.
            name (str, optional): Service name. Defaults to "bluetooth".
        """
        super().__init__(name, enabled=service_bt_config.enabled)
        self.adapter_address: Optional[str] = None
        self.peripheral: Optional[peripheral.Peripheral] = None
        self.is_connected: bool = False
        self.bt_data: Optional[BluetoothData] = None
        self.service_bt_config: ServiceBluetoothConfig = service_bt_config
        self.command_center: CommandCenter = command_center

    def init(self) -> None:
        """
        Initialize the Bluetooth service resources.
        
        Raises:
            ServiceDependencyError: If no Bluetooth adapter is found.
        """
        super().init()
        self.adapter_address = self.get_hci0_addr()
        if not self.adapter_address:
             self.logger.error("No Bluetooth Adapter found.")
             raise ServiceDependencyError("No Bluetooth Adapter found", self.name)
        
        self.logger.info(f"Bluetooth Service Initialized with adapter: {self.adapter_address}")

    def get_hci0_addr(self) -> Optional[str]:
        """
        Retrieves the MAC address of the HCI0 adapter using hciconfig.
        
        Returns:
            Optional[str]: MAC Address string or None if failed.
        """
        try:
            # Note: This is Linux specific
            out = subprocess.check_output("hciconfig hci0", shell=True).decode()
            return out.split("BD Address:")[1].split()[0]
        except Exception as e: # pylint: disable=broad-except
            self.logger.error(f"Failed to get HCI0 address: {e}")
            return None

    def get_bt_data(self) -> Optional[BluetoothData]:
        """
        Retrieves and clears the latest bluetooth data.
        
        Returns:
            Optional[BluetoothData]: The data object or None.
        """
        data = self.bt_data
        self.bt_data = None # consume data
        return data

    def on_write(self, value: List[int], options: Dict[str, Any]) -> None:
        """
        Callback for when data is written to the characteristic.
        
        Args:
            value (List[int]): The byte values received.
            options (Dict[str, Any]): Write options.
        """
        try:
            cmd = bytes(value).decode().strip()
            self.logger.info(f"Command received via Bluetooth: {cmd}")
            self.is_connected = True
            self.bt_data = BluetoothData(text=cmd, is_connected=self.is_connected)
            self.increment_stat("commands_received")
        except Exception as e: # pylint: disable=broad-except
            self.logger.error(f"Error processing bluetooth command: {e}")
            self.update_stat("last_error", str(e))

    def _run(self) -> None:
        """
        Main service loop. Publishes the BLE service.
        Note: peripheral.publish() is blocking.
        """
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
            
            # This call blocks until stopped
            self.peripheral.publish()
            
        except Exception as e: # pylint: disable=broad-except
            self.logger.error(f"Bluetooth Service crashed: {e}")
            self.update_stat("crash_error", str(e))
            raise

    def stop(self) -> None:
        """Signal the service to stop."""
        super().stop()
        # Bluezero peripheral doesn't have a clean stop from another thread.
        # Relies on daemon thread termination for now.
    
    def update(self) -> None:
        """Checks for new commands and issues them to the command center."""
        data = self.get_bt_data()
        if data and data.is_connected:
            # Simple command parsing: CMD;QUERY
            parts = data.text.split(";")
            cmd = parts[0].upper()
            query = parts[1] if len(parts) > 1 else None

            if cmd == "STATE" and query:
                self.command_center.issue_command(
                    command_name=CommandNames.CHANGE_STATE,
                    params={"target_state": query.upper()}
                )
            



        