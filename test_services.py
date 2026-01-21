import time
import sys
import logging
from bot_ekko.services.base import Service, ThreadedService, ServiceStatus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MyThreadedService(ThreadedService):
    def _run(self):
        self.logger.info("Threaded service loop starting")
        count = 0
        while not self._stop_event.is_set():
            count += 1
            self.update_stat("loop_count", count)
            time.sleep(0.1)
        self.logger.info("Threaded service loop ended")

class MyService(Service):
    def perform_action(self):
        self.start()
        self.increment_stat("actions_performed")
        self.logger.info("Action performed")
        self.stop()

def main():
    print("--- Testing ThreadedService ---")
    ts = MyThreadedService("threaded-test")
    assert ts.status == ServiceStatus.INITIALIZED
    
    ts.start()
    # Give it a moment to change status and run a loop
    time.sleep(0.2) 
    
    assert ts.status == ServiceStatus.RUNNING
    print(f"Threaded Service Stats: {ts.stats}")
    assert ts.stats.get("loop_count", 0) > 0
    
    ts.stop()
    ts.join()
    assert ts.status == ServiceStatus.STOPPED
    print("ThreadedService passed.")

    print("\n--- Testing Service ---")
    s = MyService("normal-test")
    assert s.status == ServiceStatus.INITIALIZED
    
    s.perform_action()
    assert s.status == ServiceStatus.STOPPED
    print(f"Service Stats: {s.stats}")
    assert s.stats.get("actions_performed") == 1
    print("Service passed.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
