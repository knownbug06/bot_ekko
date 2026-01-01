import threading
import subprocess
from bluezero import peripheral
from bot_ekko.core.logger import get_logger

logger = get_logger("Bluetooth")

class BluetoothManager(threading.Thread):
    def __init__(self, command_queue):
        super().__init__(daemon=True)
        self.command_queue = command_queue
        self.running = True
        self.peripheral = None
        self.adapter_address = self.get_hci0_addr()

    def get_hci0_addr(self):
        try:
            out = subprocess.check_output("hciconfig hci0", shell=True).decode()
            return out.split("BD Address:")[1].split()[0]
        except Exception as e:
            logger.error(f"Failed to get HCI0 address: {e}")
            return None

    def on_write(self, value, options):
        try:
            cmd = bytes(value).decode().strip()
            logger.info(f"📥 Command received via Bluetooth: {cmd}")
            self.command_queue.put(cmd)
        except Exception as e:
            logger.error(f"Error processing bluetooth command: {e}")

    def run(self):
        if not self.adapter_address:
            logger.error("No Bluetooth Adapter found. Bluetooth Service not started.")
            return

        logger.info(f"Starting Bluetooth Service on {self.adapter_address}")

        try:
            self.peripheral = peripheral.Peripheral(
                self.adapter_address,
                local_name='Ekko-Pi'
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

            self.peripheral.publish()
        except Exception as e:
            logger.error(f"Bluetooth Service crashed: {e}")

    def stop(self):
        self.running = False
        # bluezero peripheral doesn't strictly have a stop method exposed easily 
        # that interrupts the GLib loop cleanly from another thread without some hackery.
        # But since this is a Daemon thread, it will die with the main process.
        pass
