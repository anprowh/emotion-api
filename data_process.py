from deepface import DeepFace
import cv2
import numpy as np
import imageio
from emotion_recognizer import pred_images

framerate = 30

def video_bytes_to_frames_array(video_bytes):
    video = imageio.v3.imread(video_bytes,  format_hint='.mp4')
    frames = []
    for i, frame in enumerate(video):
        if (i % 10 == 0):
            frames.append([i / framerate, frame[::-1]])
    return frames

if False:
    def frames_to_emotions(frames):
        gender = DeepFace.analyze(frames[len(frames)//2][1], actions = ['gender'], enforce_detection=False, prog_bar=False)
        gender = gender['gender'][0]
        data = DeepFace.analyze([el[1] for el in frames], actions = ['emotion'], enforce_detection=False, prog_bar=False)
        res = []
        for index, i in zip([el[0] for el in frames], range(len(data))):
            instance = data[f'instance_{i+1}']
            emotion = instance['emotion']
            res.append([index] + [emotion.get('angry'), emotion.get('disgust'), emotion.get('fear'), emotion.get('happy'), emotion.get('sad'), emotion.get('surprise'), emotion.get('neutral'), gender])
        return res
else:
    def frames_to_emotions(frames):
        gender = DeepFace.analyze(frames[len(frames)//2][1], actions = ['gender'], enforce_detection=False, prog_bar=False)
        gender = gender['gender'][0]
        emotions = pred_images([el[1] for el in frames])
        res = [[i, *emotion, gender] for i, emotion in zip([el[0] for el in frames], emotions)]
        return res



def video_to_emotions(video_bytes):
    frames = video_bytes_to_frames_array(video_bytes)
    return frames_to_emotions(frames)

# get main emotion by getting average of the last n emotions
def emotions_to_main_emotion(emotions, start=0, end=None):
    emotion_labels = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
    emotion_counts = [0, 0, 0, 0, 0, 0, 0]
    count = 0
    for timestamp, angry, disgust, fear, happy, sad, surprise, neutral, gender in emotions:
        if timestamp < start or (end is not None and timestamp > end):
            continue
        emotion_counts[0] += angry
        emotion_counts[1] += disgust
        emotion_counts[2] += fear
        emotion_counts[3] += happy
        emotion_counts[4] += sad
        emotion_counts[5] += surprise
        emotion_counts[6] += neutral
        count += 1

    # get average emotion
    emotion_counts = [x / count for x in emotion_counts]
    main_emotion_index = emotion_counts.index(max(emotion_counts))
    main_emotion = emotion_labels[main_emotion_index]
    emotions_dict = dict(zip(emotion_labels, emotion_counts))
    print(main_emotion, emotions_dict)
    return main_emotion, emotions_dict
