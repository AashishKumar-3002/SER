#%%
import numpy as np
import atexit
import threading
import pyaudio
import wave

class MicrophoneRecorder(object):
      def __init__(self, rate=48000, chunksize=128):
            self.rate = rate
            self.chunksize = chunksize
            self.p = pyaudio.PyAudio()
            self.channels = 1
            self.sample_format = pyaudio.paInt16
            self.stream = self.p.open(format=self.sample_format,
                                    channels=self.channels,
                                    rate=self.rate,
                                    input=True,
                                    frames_per_buffer=self.chunksize,
                                    stream_callback=self.new_frame)
            self.lock = threading.Lock()
            self.stop = False
            self.frames = []
            self._print_frames = np.array([])
            self._print_frames_count = 0
            atexit.register(self.close)

      def new_frame(self, data, frame_count, time_info, status):
            data = np.frombuffer(data, dtype=np.int16)
            with self.lock:
                  self.frames.append(data)
                  if self._print_frames_count == 94:
                        self.thread.print_recording_signal.emit(self._print_frames)
                        # Here we call the emotion processing function
                        self._print_frames = np.array([])
                        self._print_frames_count = 0
                  else:
                        self._print_frames = np.concatenate((self._print_frames,data), axis=0)
                        self._print_frames_count+=1
                  if self.stop:
                        return None, pyaudio.paComplete
            return None, pyaudio.paContinue

      def get_frames(self):
            with self.lock:
                  frames = self.frames
                  return frames

      def save_to_wav(self, filename="output.wav"):
            wf = wave.open(filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.sample_format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.get_frames()))
            wf.close()

      def start(self, thread):
            print("Starting recording")
            self.thread = thread
            self.stream.start_stream()

      def close(self):
            print("Finishing recording")
            with self.lock:
                  self.stop = True
            self.stream.close()
            self.p.terminate()

