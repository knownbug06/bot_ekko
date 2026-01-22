from bot_ekko.core.base import ServiceStatus, ThreadedService
import time

class TestService:
    def test_initial_status(self, base_service):
        assert base_service.status == ServiceStatus.INITIALIZED
        assert base_service.name == "test_service"
        assert base_service.stats == {}

    def test_start_stop(self, base_service):
        base_service.start()
        assert base_service.status == ServiceStatus.RUNNING
        
        base_service.update_stat("test_key", "test_value")
        assert base_service.stats["test_key"] == "test_value"
        
        base_service.stop()
        assert base_service.status == ServiceStatus.STOPPED

    def test_stats_management(self, base_service):
        base_service.update_stat("counter", 10)
        assert base_service.stats["counter"] == 10
        
        base_service.increment_stat("counter")
        assert base_service.stats["counter"] == 11
        
        base_service.increment_stat("counter", 5)
        assert base_service.stats["counter"] == 16
        
        # Test non-numeric increment
        base_service.update_stat("string_stat", "value")
        base_service.increment_stat("string_stat")
        assert base_service.stats["string_stat"] == "value"

class TestThreadedService:
    def test_lifecycle(self, threaded_service):
        assert threaded_service.status == ServiceStatus.INITIALIZED
        
        threaded_service.start()
        assert threaded_service.status == ServiceStatus.RUNNING or threaded_service.is_alive()
        
        # Give it a moment to run
        time.sleep(0.05)
        assert threaded_service.run_count > 0
        
        threaded_service.stop()
        threaded_service.join(timeout=1.0)
        assert not threaded_service.is_alive()
        
    def test_double_start(self, threaded_service):
        threaded_service.start()
        assert threaded_service.is_alive()
        
        # Try starting again
        threaded_service.start()
        assert threaded_service.is_alive()
        
        threaded_service.stop()
        threaded_service.join()

    def test_error_handling(self):
        class CrashingService(ThreadedService):
            def _run(self) -> None:
                raise RuntimeError("Crash boom bang")

        service = CrashingService("crash_service")
        service.start()
        service.join()
        
        assert service.status == ServiceStatus.ERROR
        assert "Crash boom bang" in str(service.stats.get("last_error"))

