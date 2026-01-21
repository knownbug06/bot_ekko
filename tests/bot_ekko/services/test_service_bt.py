import pytest
from unittest.mock import MagicMock, patch
from bot_ekko.services.service_bt import BluetoothService
from bot_ekko.services.errors import ServiceDependencyError
from bot_ekko.core.models import BluetoothData

@pytest.fixture
def mock_subprocess():
    with patch("bot_ekko.services.service_bt.subprocess") as mock:
        yield mock

@pytest.fixture
def mock_bluezero():
    with patch("bot_ekko.services.service_bt.peripheral") as mock:
        yield mock

@pytest.fixture
def service(mock_subprocess):
    # Setup successful init by default
    mock_subprocess.check_output.return_value = b"BD Address: 00:11:22:33:44:55\n"
    svc = BluetoothService("test_bt")
    return svc

def test_init_success(service, mock_subprocess):
    service.init()
    assert service.adapter_address == "00:11:22:33:44:55"
    mock_subprocess.check_output.assert_called_with("hciconfig hci0", shell=True)

def test_init_failure(mock_subprocess):
    mock_subprocess.check_output.side_effect = Exception("No device")
    svc = BluetoothService("test_bt")
    with pytest.raises(ServiceDependencyError, match="No Bluetooth Adapter"):
        svc.init()

def test_run_success(service, mock_bluezero):
    service.init()
    mock_peripheral_instance = MagicMock()
    mock_bluezero.Peripheral.return_value = mock_peripheral_instance
    
    # We don't want to actually block in run, so we need to run it in a way 
    # that doesn't block forever or we check what it calls.
    # Since run calls publish() which blocks, we can mock publish to return immediately.
    
    service._run()
    
    mock_bluezero.Peripheral.assert_called_with("00:11:22:33:44:55", local_name='Ekko')
    mock_peripheral_instance.add_service.assert_called()
    mock_peripheral_instance.add_characteristic.assert_called()
    mock_peripheral_instance.publish.assert_called()
    assert service.is_connected is True

def test_run_no_adapter(service, mock_bluezero):
    # If init was not called or failed silently (if we changed logic), but let's say adapter is None
    service.adapter_address = None
    service._run()
    # Should log error and return
    mock_bluezero.Peripheral.assert_not_called()

def test_on_write(service):
    # Simulate data
    data = [65, 66, 67] # "ABC"
    service.on_write(data, {})
    
    assert service.is_connected is True
    assert service.bt_data is not None
    assert service.bt_data.text == "ABC"
    assert service.bt_data.is_connected is True
    assert service.stats["commands_received"] == 1

def test_get_bt_data(service):
    # Setup data
    service.bt_data = BluetoothData(text="test", is_connected=True)
    
    data = service.get_bt_data()
    assert data.text == "test"
    
    # Should be cleared after read
    assert service.bt_data is None
