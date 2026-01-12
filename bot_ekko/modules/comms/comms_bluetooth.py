import threading
import subprocess
from bluezero import peripheral
from bot_ekko.core.logger import get_logger
from bot_ekko.core.models import BluetoothData


logger = get_logger("Bluetooth")

class BluetoothManager(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.peripheral = None
        self.adapter_address = self.get_hci0_addr()

        self.is_connected = False
        self.bt_data = None

    def get_hci0_addr(self):
        try:
            out = subprocess.check_output("hciconfig hci0", shell=True).decode()
            return out.split("BD Address:")[1].split()[0]
        except Exception as e:
            logger.error(f"Failed to get HCI0 address: {e}")
            return None
        
    def get_bt_data(self) -> BluetoothData:
        data = self.bt_data
        self.bt_data = None # reset data after read is complete since its running it a loop
        return data

    def on_write(self, value, options):
        try:
            cmd = bytes(value).decode().strip()
            logger.info(f"[Bluetooth]: Command received via Bluetooth: {cmd}")
            self.is_connected = True
            self.bt_data = BluetoothData(text=cmd, is_connected=self.is_connected)
        except Exception as e:
            logger.error(f"[Bluetooth]: Error processing bluetooth command: {e}")

    def run(self):
        if not self.adapter_address:
            logger.error("[Bluetooth]: No Bluetooth Adapter found. Bluetooth Service not started.")
            return

        logger.info(f"[Bluetooth]: Starting Bluetooth Service on {self.adapter_address}")

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

            self.peripheral.publish()
        except Exception as e:
            logger.error(f"[Bluetooth]: Bluetooth Service crashed: {e}")

    def stop(self):
        self.running = False
        # bluezero peripheral doesn't strictly have a stop method exposed easily 
        # that interrupts the GLib loop cleanly from another thread without some hackery.
        # But since this is a Daemon thread, it will die with the main process.
        pass
