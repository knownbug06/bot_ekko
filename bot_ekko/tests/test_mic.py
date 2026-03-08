import pyaudio
import wave
import sys

def record_audio(filename="output.wav", record_seconds=5):
    chunk = 1024  # Record in chunks of 1024 samples
    sample_format = pyaudio.paInt16  # 16 bits per sample
    
    # USB mics usually support 1 channel (mono) or 2 channels (stereo)
    # 1 channel is safer for most USB microphones.
    channels = 1
    fs = 44100  # Record at 44100 samples per second
    
    p = pyaudio.PyAudio()  # Create an interface to PortAudio
    
    print(f"Recording for {record_seconds} seconds...")
    
    try:
        # Open the stream using the default input device
        stream = p.open(format=sample_format,
                        channels=channels,
                        rate=fs,
                        frames_per_buffer=chunk,
                        input=True)
    except Exception as e:
        print(f"Error opening audio stream: {e}")
        print("Please check if your USB mic is connected and configured.")
        print("You can list available devices using 'arecord -l' in the terminal.")
        p.terminate()
        sys.exit(1)

    frames = []  # Initialize array to store frames
    
    try:
        # Store data in chunks for specified seconds
        for i in range(0, int(fs / chunk * record_seconds)):
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)
    except KeyboardInterrupt:
        print("\nRecording stopped by user.")
        
    # Stop and close the stream 
    stream.stop_stream()
    stream.close()
    
    # Terminate the PortAudio interface
    p.terminate()
    
    print('Finished recording.')
    
    if not frames:
        print("No audio data was recorded.")
        return
        
    # Save the recorded data as a WAV file
    print(f"Saving to {filename}...")
    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(sample_format))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    print("Done!")

if __name__ == "__main__":
    record_audio(filename="recorded_audio.wav", record_seconds=5)
