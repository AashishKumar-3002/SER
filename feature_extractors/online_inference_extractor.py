# %%
import os
import librosa
import numpy as np
import tensorflow as tf
from util import *

from tqdm import tqdm
from feature_extractors.end_to_end_data_producers import Data_Producer_End_to_End
# %%
class Feature_Extractor(object):
      def _get_audio_features(self, wav_file):
            pass

class Online_Feature_Extractor_End_to_End(Feature_Extractor):
      def __init__(self):
            super().__init__()

      def reshape_frames(self, stft, window_length):
            """  RESHAPE THE SPECTOGRAM INTO WINDOWS OF SHAPE 128x128 
                  -Arguments:
                        stft : The spectogram of the audio signal
                  -Returns:
                        The reshaped signal that will be passed to the convolutional layer
            """
            stft = np.transpose(stft)
            window_nr = (stft.shape[0] // window_length + 1) * window_length
            pad_size = window_nr - stft.shape[0]
            stft = np.pad(stft, ((0, pad_size), (0, 1)), 'edge')
            conv_frames = np.array(([stft[i * window_length:(i+1) * window_length]
                                     for i in range(int(stft.shape[0]/(stft.shape[1]) + 1))]))
            return conv_frames[:, :, 0:window_length]

      def _get_audio_features(self, frames, org_rt):
            librosa.core.time_to_frames
            stft = librosa.feature.melspectrogram(frames, n_fft=256, win_length=128, hop_length=32, center=False)
            return stft
      
      def get_features_from_frames(self, session ,frames, org_rt):
            self.features = np.array(self.reshape_frames(self._get_audio_features(frames, org_rt), 128))
            self.features = np.array([self.features, self.features])
            self.features = np.array([np.reshape(stft, (stft.shape[0], stft[0].shape[0],  stft[0].shape[1])) for stft in self.features])
            return self.features

class Online_Data_Producer_End_to_End_Inference(Data_Producer_End_to_End):
      def __init__(self):
            self._feature_extractor = Online_Feature_Extractor_End_to_End()

      def _import_data(self, session, frames, org_rt):
            self._features = self._feature_extractor.get_features_from_frames(session, frames, org_rt)

      def produce_data(self, session, frames, org_rt, name=None):
            """ CONSTRUCTING TF.DATASETS BASED ON THE FEATURES EXTRACTED
                    -Arguments:
                        session: the tf.Session() the model is running on
                    -Returns:
                        inputs - the features extracted from the convolutional layers
                        inference_length - the number of files in the inference folder
                        self._files - the names of the files in the inference folder to pretty print              
            """
            self._import_data(session, frames, org_rt)
            self._features = np.array([_inputs.reshape([_inputs.shape[0], _inputs.shape[1], _inputs.shape[2]]) for _inputs in self._features])

            inference_length = self._features.shape[0]
            self._features_dt = tf.data.Dataset.from_generator(lambda: self._features, tf.float32, output_shapes=[None, self._features[0].shape[1], self._features[0].shape[2]]).repeat()
            features = self._features_dt.make_one_shot_iterator()
            inputs = features.get_next()
            inputs = self._convolutional_feature_extractor(inputs, 1.0)

            return inputs, inference_length


class Online_Feature_Extractor_Hand_Crafted(Feature_Extractor):
      def __init__(self):
            super().__init__()
            self.feature_names = ['MFCC', 'Delta', 'Delta-Deltas', 'RMS', 'ZCR', 'Chrmoa', 'Roll-off']

      def _flatten_features(self, row):
            new_features = np.array([])
            for feature in row:
                  new_values = np.array([])
                  for val in feature:
                        new_values = np.append(new_values, values=val)
                  new_features = np.append(new_features, new_values)
            return new_features

      def _reshape_features_for_one_file(self, features):
            steps = features.shape[0]
            # new_features = np.array([[feature[i] for feature in features] for i in range(steps)])
            return np.array([self._flatten_features(row) for row in features])

      def _reshape_features(self, features):
            features = np.array(features)
            print(features.shape)
            print(features[0].shape)
            files_features = np.array([np.transpose(feature) for feature in features])
            print(files_features.shape)
            print(files_features[0].shape)
            return np.array([self._reshape_features_for_one_file(files_features)])


      def _get_audio_features(self, frames, org_rt):
            mfcc = librosa.feature.mfcc(y=frames, sr=org_rt, hop_length=260, n_mfcc=20)
            delta = librosa.feature.delta(mfcc)
            delta_deltas = librosa.feature.delta(delta)
            rms = librosa.feature.rms(y=frames, frame_length=640, hop_length=260)
            zcr = librosa.feature.zero_crossing_rate(y=frames, frame_length=640, hop_length=260)
            chroma = librosa.feature.chroma_stft(y=frames, sr=org_rt, n_fft=820, win_length=640, hop_length=260)
            rolloff = librosa.feature.spectral_rolloff(y=frames, sr=org_rt, n_fft=820, win_length=640, hop_length=260)

            features = [mfcc, delta, delta_deltas, rms, zcr, chroma, rolloff]
            return features

      def get_featurs_and_targets(self, session, frames, org_rt):
            self.features = self._get_audio_features(frames, org_rt)
            self.features = self._reshape_features(self.features)
            return self.features

class Online_Data_Producer_Hand_Crafted_Inference(Data_Producer_End_to_End):
      def __init__(self):
            self._feature_extractor = Online_Feature_Extractor_Hand_Crafted()

      def _import_data(self, session, frames, org_rt):
            self._features = self._feature_extractor.get_featurs_and_targets(session, frames, org_rt)

      def produce_data(self, session, frames, org_rt, name=None):
            self._import_data(session, frames, org_rt)
            print(self._features.shape)
            print(self._features[0].shape)
            self._features = np.array(self._features.reshape([self._features.shape[0], self._features.shape[1], self._features.shape[2]]))

            inference_length = self._features.shape[0]
            
            self._features_dt = tf.data.Dataset.from_generator(lambda: self._features, tf.float32, output_shapes=[None, self._features[0].shape[1], self._features[0].shape[2]]).repeat()
            features = self._features_dt.make_one_shot_iterator()
            inputs = features.get_next()

            return inputs, inference_length
