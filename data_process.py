from deepface import DeepFace
import cv2
import numpy as np
import imageio
from io import BytesIO

def video_bytes_to_frames_array(video_bytes):
    video = imageio.v3.imread(video_bytes,  format_hint='.mp4')
    frames = []
    for i, frame in enumerate(video):
        if (i % 10 == 0):
            frames.append([i, frame])
    return frames

def frame_to_emotions(frame):
    data = DeepFace.analyze(frame, actions = ['emotion', 'gender'], enforce_detection=False)
    emotion = data['emotion']
    res = [emotion.get('angry'), emotion.get('disgust'), emotion.get('fear'), emotion.get('happy'), emotion.get('sad'), emotion.get('surprise'), emotion.get('neutral'), data['gender'][0]]
    return res

def video_to_emotions(video_bytes):
    frames = video_bytes_to_frames_array(video_bytes)
    emotions = []
    for i, frame in frames:
        emotions.append([i] + frame_to_emotions(frame))
    return emotions
