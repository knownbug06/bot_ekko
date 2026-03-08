import sys
import time
import wave
import os

# Add the project root to the path so we can run this directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bot_ekko.core.models import SystemConfig
from bot_ekko.services.service_mic import MicService

def test_threaded_mic_service():
    # 1. Load configuration
    try:
        system_config = SystemConfig.from_json_file("bot_ekko/config.json")
    except Exception as e:
        print(f"Failed to load system config: {e}")
        return

    # 2. Initialize the Service
    mic_service_config = system_config.services.mic_service
    print(f"Mic Service Config: {mic_service_config}")
    
    mic_service = MicService(service_mic_config=mic_service_config)
    
    # 3. Start the service
    print("Starting Mic Service...")
    mic_service.start()
    
    frames = []
    record_seconds = 5
    print(f"Recording for {record_seconds} seconds using the threaded service...")
    
    # 4. Consume from the buffer in a loop
    start_time = time.time()
    while time.time() - start_time < record_seconds:
        chunks = mic_service.read_mic()
        if chunks:
            frames.extend(chunks)
        time.sleep(0.1) # Simulate main loop tick
        
    # 5. Stop the service
    print("Stopping Mic Service...")
    mic_service.stop()
    
    # Give the thread a moment to cleanly terminate
    time.sleep(0.5)
    
    if not frames:
        print("Test failed: No audio frames were collected from the buffer.")
        return
        
    print(f"Collected {len(frames)} chunks from the buffer.")
    
    # 6. Save the results
    filename = "test_mic_service_output.wav"
    print(f"Saving to {filename} to verify audio...")
    wf = wave.open(filename, 'wb')
    wf.setnchannels(mic_service_config.channels)
    
    import pyaudio
    p = pyaudio.PyAudio()
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(mic_service_config.sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    p.terminate()
    
    print("Test Complete!")

if __name__ == "__main__":
    test_threaded_mic_service()
