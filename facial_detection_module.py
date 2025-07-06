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
from PIL import Image, ImageDraw
import mediapipe as mp
import tempfile
import os
from moviepy.editor import VideoFileClip
import streamlit as st

# --- MediaPipe Configuration ---
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# --- Face landmark indices for mouth and eyes ---
MOUTH_LANDMARKS = [
    # Outer mouth boundary
    61, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318,
    # Inner mouth
    78, 95, 88, 178, 87, 14, 317, 402, 318, 324
]

EYE_LANDMARKS = {
    'left_eye': [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
    'right_eye': [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
}

class FacialDetector:
    """Handles face detection and processing for AI-generated videos."""
    
    def __init__(self):
        self.face_detection = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    
    def detect_face_landmarks(self, image):
        """Detect face landmarks using MediaPipe."""
        # Convert PIL to OpenCV format
        if isinstance(image, Image.Image):
            image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            image_cv = image
        
        # Convert to RGB for MediaPipe
        image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
        
        # Detect face mesh
        results = self.face_mesh.process(image_rgb)
        
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            h, w = image_rgb.shape[:2]
            
            # Convert normalized landmarks to pixel coordinates
            landmarks = []
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                landmarks.append((x, y))
            
            return landmarks, (w, h)
        
        return None, None
    
    def extract_mouth_region(self, image, landmarks, padding=20):
        """Extract mouth region with padding."""
        if not landmarks:
            return None, None
        
        # Get mouth landmark points
        mouth_points = [landmarks[i] for i in MOUTH_LANDMARKS if i < len(landmarks)]
        
        if not mouth_points:
            return None, None
        
        # Find bounding box
        xs = [p[0] for p in mouth_points]
        ys = [p[1] for p in mouth_points]
        
        min_x, max_x = min(xs) - padding, max(xs) + padding
        min_y, max_y = min(ys) - padding, max(ys) + padding
        
        # Create mouth mask
        if isinstance(image, Image.Image):
            mask = Image.new('L', image.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.polygon(mouth_points, fill=255)
        else:
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.fillPoly(mask, [np.array(mouth_points)], 255)
        
        mouth_region = {
            'bbox': (min_x, min_y, max_x, max_y),
            'mask': mask,
            'center': ((min_x + max_x) // 2, (min_y + max_y) // 2),
            'landmarks': mouth_points
        }
        
        return mouth_region, mouth_points
    
    def extract_eye_regions(self, image, landmarks, padding=15):
        """Extract eye regions with padding."""
        if not landmarks:
            return None, None
        
        eye_regions = {}
        
        for eye_name, eye_indices in EYE_LANDMARKS.items():
            eye_points = [landmarks[i] for i in eye_indices if i < len(landmarks)]
            
            if not eye_points:
                continue
            
            # Find bounding box
            xs = [p[0] for p in eye_points]
            ys = [p[1] for p in eye_points]
            
            min_x, max_x = min(xs) - padding, max(xs) + padding
            min_y, max_y = min(ys) - padding, max(ys) + padding
            
            # Create eye mask
            if isinstance(image, Image.Image):
                mask = Image.new('L', image.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.polygon(eye_points, fill=255)
            else:
                mask = np.zeros(image.shape[:2], dtype=np.uint8)
                cv2.fillPoly(mask, [np.array(eye_points)], 255)
            
            eye_regions[eye_name] = {
                'bbox': (min_x, min_y, max_x, max_y),
                'mask': mask,
                'center': ((min_x + max_x) // 2, (min_y + max_y) // 2),
                'landmarks': eye_points
            }
        
        return eye_regions
    
    def create_blank_face(self, image, mouth_region, eye_regions, skin_color=None):
        """Create a blank face by removing mouth and eyes."""
        if isinstance(image, Image.Image):
            blank_face = image.copy()
        else:
            blank_face = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # Auto-detect skin color if not provided
        if skin_color is None:
            skin_color = self.estimate_skin_color(blank_face, mouth_region, eye_regions)
        
        # Remove mouth
        if mouth_region:
            self.fill_region(blank_face, mouth_region['mask'], skin_color)
        
        # Remove eyes
        if eye_regions:
            for eye_region in eye_regions.values():
                self.fill_region(blank_face, eye_region['mask'], skin_color)
        
        return blank_face
    
    def estimate_skin_color(self, image, mouth_region, eye_regions):
        """Estimate skin color from face area excluding mouth and eyes."""
        # Convert to numpy for processing
        img_array = np.array(image)
        
        # Create exclusion mask (areas to avoid when sampling skin)
        h, w = img_array.shape[:2]
        exclusion_mask = np.zeros((h, w), dtype=np.uint8)
        
        # Add mouth and eye regions to exclusion mask
        if mouth_region:
            mouth_mask = np.array(mouth_region['mask'])
            exclusion_mask = cv2.bitwise_or(exclusion_mask, mouth_mask)
        
        if eye_regions:
            for eye_region in eye_regions.values():
                eye_mask = np.array(eye_region['mask'])
                exclusion_mask = cv2.bitwise_or(exclusion_mask, eye_mask)
        
        # Sample skin color from non-excluded areas
        valid_pixels = img_array[exclusion_mask == 0]
        
        if len(valid_pixels) > 0:
            # Use median color for more stable results
            skin_color = np.median(valid_pixels, axis=0).astype(int)
            return tuple(skin_color)
        
        # Fallback to neutral skin tone
        return (220, 180, 140)
    
    def fill_region(self, image, mask, color):
        """Fill a masked region with specified color."""
        # Convert mask to PIL format if needed
        if isinstance(mask, np.ndarray):
            mask_pil = Image.fromarray(mask)
        else:
            mask_pil = mask
        
        # Create solid color image
        color_img = Image.new('RGB', image.size, color)
        
        # Paste color where mask is white
        image.paste(color_img, mask=mask_pil)
    
    def generate_tracking_data(self, landmarks, image_size):
        """Generate tracking data for mouth and eyes."""
        if not landmarks:
            return None
        
        w, h = image_size
        
        # Extract mouth data
        mouth_points = [landmarks[i] for i in MOUTH_LANDMARKS if i < len(landmarks)]
        mouth_center = self.get_center_point(mouth_points)
        mouth_scale = self.calculate_scale(mouth_points)
        mouth_rotation = self.calculate_rotation(mouth_points)
        
        # Extract eye data
        eye_data = {}
        for eye_name, eye_indices in EYE_LANDMARKS.items():
            eye_points = [landmarks[i] for i in eye_indices if i < len(landmarks)]
            if eye_points:
                eye_data[eye_name] = {
                    'center': self.get_center_point(eye_points),
                    'scale': self.calculate_scale(eye_points),
                    'rotation': self.calculate_rotation(eye_points)
                }
        
        tracking_data = {
            'mouth': {
                'center': mouth_center,
                'scale': mouth_scale,
                'rotation': mouth_rotation,
                'landmarks': mouth_points
            },
            'eyes': eye_data,
            'face_landmarks': landmarks
        }
        
        return tracking_data
    
    def get_center_point(self, points):
        """Calculate center point of a set of landmarks."""
        if not points:
            return (0, 0)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (sum(xs) // len(xs), sum(ys) // len(ys))
    
    def calculate_scale(self, points):
        """Calculate scale factor based on landmark spread."""
        if len(points) < 2:
            return 1.0
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        
        # Normalize to reference size (adjust based on your needs)
        reference_size = 40
        scale = max(width, height) / reference_size
        return max(0.5, min(2.0, scale))  # Clamp between 0.5x and 2.0x
    
    def calculate_rotation(self, points):
        """Calculate rotation angle based on landmark orientation."""
        if len(points) < 2:
            return 0.0
        
        # Use first and last points to estimate orientation
        p1, p2 = points[0], points[-1]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        # Calculate angle in degrees
        angle = np.degrees(np.arctan2(dy, dx))
        return angle

def process_ai_video(video_path, progress_callback=None):
    """
    Main function to process an AI-generated video and extract facial data.
    
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
                
                # Detect face landmarks
                landmarks, image_size = detector.detect_face_landmarks(frame_image)
                
                if landmarks:
                    # Extract facial regions
                    mouth_region, _ = detector.extract_mouth_region(frame_image, landmarks)
                    eye_regions = detector.extract_eye_regions(frame_image, landmarks)
                    
                    # Create blank face
                    blank_face = detector.create_blank_face(frame_image, mouth_region, eye_regions)
                    
                    # Generate tracking data
                    frame_tracking = detector.generate_tracking_data(landmarks, image_size)
                    frame_tracking['frame_number'] = frame_num + 1
                    frame_tracking['time'] = frame_time
                    
                    blank_frames.append(blank_face)
                    tracking_data.append(frame_tracking)
                else:
                    # No face detected - use original frame
                    blank_frames.append(frame_image)
                    tracking_data.append({
                        'frame_number': frame_num + 1,
                        'time': frame_time,
                        'mouth': None,
                        'eyes': None,
                        'face_landmarks': None
                    })
                
                # Progress update
                if progress_callback:
                    progress_callback(frame_num + 1, total_frames)
    
    except Exception as e:
        raise Exception(f"Error processing video: {e}")
    
    return blank_frames, tracking_data