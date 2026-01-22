class ServiceError(Exception):
    """Base exception for all service-related errors."""
    def __init__(self, message: str, service_name: str = None):
        self.service_name = service_name
        self.message = message
        if service_name:
            super().__init__(f"[{service_name}] {message}")
        else:
            super().__init__(message)

class ServiceInitializationError(ServiceError):
    """Raised when a service fails to initialize properly."""
    pass

class ServiceConfigurationError(ServiceError):
    """Raised when a service has invalid configuration."""
    pass

class ServiceRuntimeError(ServiceError):
    """Raised when a service encounters an error while running."""
    pass

class ServiceDependencyError(ServiceError):
    """Raised when a service is missing a required dependency."""
    pass

class ServiceTimeoutError(ServiceError):
    """Raised when a service operation times out."""
    pass

class SensorError(ServiceError):
    """Base exception for sensor-related errors."""
    pass

class SensorConnectionError(SensorError):
    """Raised when connecting to a sensor fails."""
    pass

class SensorReadError(SensorError):
    """Raised when reading from a sensor fails."""
    pass

class SensorParseError(SensorError):
    """Raised when parsing sensor data fails."""
    pass
