# facial_detection_module.py
"""
AI Video Facial Detection and Processing System

This module handles:
1. Automated face/mouth/eye detection from AI-generated videos
2. Creation of "blank canvas" faces (mouth/eyes removed)
3. Generation of tracking data for animation overlay
4. Hybrid CV + AI approach for maximum flexibility
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import tempfile
import os
from moviepy.editor import VideoFileClip
import streamlit as st

# --- OpenCV Face Detection Configuration ---
# Download haarcascade files if needed
FACE_CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
EYE_CASCADE_URL = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_eye.xml"

class FacialDetector:
    """Handles face detection and processing for AI-generated videos using OpenCV."""
    
    def __init__(self):
        # Initialize OpenCV cascade classifiers
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        except Exception as e:
            print(f"Warning: Could not load cascade classifiers: {e}")
            self.face_cascade = None
            self.eye_cascade = None
    
    def detect_face_regions(self, image):
        """Detect face, mouth, and eye regions using OpenCV."""
        if self.face_cascade is None:
            return None
        
        # Convert PIL to OpenCV format
        if isinstance(image, Image.Image):
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            image_cv = image
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) == 0:
            return None
        
        # Use the largest face detected
        face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = face
        
        # Estimate mouth region (bottom third of face)
        mouth_y_start = y + int(h * 0.65)
        mouth_y_end = y + h
        mouth_x_start = x + int(w * 0.25)
        mouth_x_end = x + int(w * 0.75)
        
        mouth_region = {
            'bbox': (mouth_x_start, mouth_y_start, mouth_x_end, mouth_y_end),
            'center': ((mouth_x_start + mouth_x_end) // 2, (mouth_y_start + mouth_y_end) // 2)
        }
        
        # Detect eyes within face region
        face_roi = gray[y:y+h, x:x+w]
        eyes = []
        if self.eye_cascade is not None:
            eyes_detected = self.eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=3)
            
            for (ex, ey, ew, eh) in eyes_detected:
                # Convert back to full image coordinates
                eye_region = {
                    'bbox': (x + ex, y + ey, x + ex + ew, y + ey + eh),
                    'center': (x + ex + ew//2, y + ey + eh//2)
                }
                eyes.append(eye_region)
        
        # If no eyes detected, estimate based on face
        if len(eyes) == 0:
            # Estimate eye positions
            eye_y = y + int(h * 0.35)
            left_eye_x = x + int(w * 0.25)
            right_eye_x = x + int(w * 0.75)
            eye_size = int(w * 0.15)
            
            eyes = [
                {  # Left eye
                    'bbox': (left_eye_x - eye_size//2, eye_y - eye_size//2, 
                            left_eye_x + eye_size//2, eye_y + eye_size//2),
                    'center': (left_eye_x, eye_y)
                },
                {  # Right eye
                    'bbox': (right_eye_x - eye_size//2, eye_y - eye_size//2, 
                            right_eye_x + eye_size//2, eye_y + eye_size//2),
                    'center': (right_eye_x, eye_y)
                }
            ]
        
        return {
            'face': {'bbox': (x, y, x+w, y+h), 'center': (x+w//2, y+h//2)},
            'mouth': mouth_region,
            'eyes': eyes,
            'image_size': (image_cv.shape[1], image_cv.shape[0])
        }
    
    def create_blank_face(self, image, face_data, skin_color=None):
        """Create a blank face by removing mouth and eyes using OpenCV detection."""
        if isinstance(image, Image.Image):
            blank_face = image.copy()
        else:
            blank_face = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        if not face_data:
            return blank_face
        
        # Auto-detect skin color if not provided
        if skin_color is None:
            skin_color = self.estimate_skin_color(blank_face, face_data)
        
        # Remove mouth region
        if 'mouth' in face_data:
            mouth_bbox = face_data['mouth']['bbox']
            self.fill_bbox_region(blank_face, mouth_bbox, skin_color)
        
        # Remove eye regions
        if 'eyes' in face_data:
            for eye in face_data['eyes']:
                eye_bbox = eye['bbox']
                self.fill_bbox_region(blank_face, eye_bbox, skin_color)
        
        return blank_face
    
    def estimate_skin_color(self, image, face_data):
        """Estimate skin color from face area excluding mouth and eyes."""
        img_array = np.array(image)
        
        if not face_data or 'face' not in face_data:
            return (220, 180, 140)  # Fallback neutral skin tone
        
        # Sample from the face region, avoiding mouth and eyes
        face_bbox = face_data['face']['bbox']
        x1, y1, x2, y2 = face_bbox
        
        # Sample from cheek areas (sides of face, middle height)
        cheek_y_start = y1 + int((y2 - y1) * 0.4)
        cheek_y_end = y1 + int((y2 - y1) * 0.6)
        
        # Left cheek
        left_cheek_x_start = x1 + int((x2 - x1) * 0.1)
        left_cheek_x_end = x1 + int((x2 - x1) * 0.3)
        
        # Right cheek
        right_cheek_x_start = x1 + int((x2 - x1) * 0.7)
        right_cheek_x_end = x1 + int((x2 - x1) * 0.9)
        
        # Sample pixels from cheek areas
        sample_pixels = []
        
        # Left cheek samples
        if left_cheek_x_start < img_array.shape[1] and cheek_y_start < img_array.shape[0]:
            left_cheek = img_array[cheek_y_start:cheek_y_end, left_cheek_x_start:left_cheek_x_end]
            if left_cheek.size > 0:
                sample_pixels.extend(left_cheek.reshape(-1, 3))
        
        # Right cheek samples
        if right_cheek_x_start < img_array.shape[1] and cheek_y_start < img_array.shape[0]:
            right_cheek = img_array[cheek_y_start:cheek_y_end, right_cheek_x_start:right_cheek_x_end]
            if right_cheek.size > 0:
                sample_pixels.extend(right_cheek.reshape(-1, 3))
        
        if sample_pixels:
            # Use median color for more stable results
            skin_color = np.median(sample_pixels, axis=0).astype(int)
            return tuple(skin_color)
        
        # Fallback to neutral skin tone
        return (220, 180, 140)
    
    def fill_bbox_region(self, image, bbox, color):
        """Fill a bounding box region with specified color."""
        x1, y1, x2, y2 = bbox
        
        # Create a filled rectangle
        draw = ImageDraw.Draw(image)
        draw.rectangle([x1, y1, x2, y2], fill=color)
    
    def generate_tracking_data(self, face_data):
        """Generate tracking data for mouth and eyes from OpenCV detection."""
        if not face_data:
            return None
        
        tracking_data = {
            'mouth': None,
            'eyes': [],
            'face': face_data.get('face')
        }
        
        # Extract mouth tracking data
        if 'mouth' in face_data:
            mouth = face_data['mouth']
            mouth_bbox = mouth['bbox']
            mouth_width = mouth_bbox[2] - mouth_bbox[0]
            mouth_height = mouth_bbox[3] - mouth_bbox[1]
            
            # Calculate scale based on mouth size (normalize to reference size)
            reference_size = 40
            mouth_scale = max(mouth_width, mouth_height) / reference_size
            mouth_scale = max(0.5, min(2.0, mouth_scale))  # Clamp between 0.5x and 2.0x
            
            tracking_data['mouth'] = {
                'center': mouth['center'],
                'scale': mouth_scale,
                'rotation': 0.0,  # OpenCV doesn't provide rotation easily
                'bbox': mouth_bbox
            }
        
        # Extract eye tracking data
        if 'eyes' in face_data:
            for i, eye in enumerate(face_data['eyes']):
                eye_bbox = eye['bbox']
                eye_width = eye_bbox[2] - eye_bbox[0]
                eye_height = eye_bbox[3] - eye_bbox[1]
                
                # Calculate scale
                eye_scale = max(eye_width, eye_height) / 20  # Reference eye size
                eye_scale = max(0.5, min(2.0, eye_scale))
                
                eye_data = {
                    'center': eye['center'],
                    'scale': eye_scale,
                    'rotation': 0.0,
                    'bbox': eye_bbox,
                    'eye_id': f'eye_{i}'
                }
                tracking_data['eyes'].append(eye_data)
        
        return tracking_data

def process_ai_video(video_path, progress_callback=None):
    """
    Main function to process an AI-generated video and extract facial data using OpenCV.
    
    Returns:
    - blank_frames: List of PIL Images with mouth/eyes removed
    - tracking_data: Frame-by-frame facial tracking information
    """
    detector = FacialDetector()
    
    blank_frames = []
    tracking_data = []
    
    try:
        with VideoFileClip(video_path) as video:
            fps = video.fps
            duration = video.duration
            total_frames = int(duration * fps)
            
            for frame_num in range(total_frames):
                frame_time = frame_num / fps
                frame = video.get_frame(frame_time)
                frame_image = Image.fromarray(frame.astype('uint8'))
                
                # Detect face regions using OpenCV
                face_data = detector.detect_face_regions(frame_image)
                
                if face_data:
                    # Create blank face
                    blank_face = detector.create_blank_face(frame_image, face_data)
                    
                    # Generate tracking data
                    frame_tracking = detector.generate_tracking_data(face_data)
                    if frame_tracking:
                        frame_tracking['frame_number'] = frame_num + 1
                        frame_tracking['time'] = frame_time
                    
                    blank_frames.append(blank_face)
                    tracking_data.append(frame_tracking if frame_tracking else {
                        'frame_number': frame_num + 1,
                        'time': frame_time,
                        'mouth': None,
                        'eyes': [],
                        'face': None
                    })
                else:
                    # No face detected - use original frame
                    blank_frames.append(frame_image)
                    tracking_data.append({
                        'frame_number': frame_num + 1,
                        'time': frame_time,
                        'mouth': None,
                        'eyes': [],
                        'face': None
                    })
                
                # Progress update
                if progress_callback:
                    progress_callback(frame_num + 1, total_frames)
    
    except Exception as e:
        raise Exception(f"Error processing video: {e}")
    
    return blank_frames, tracking_data