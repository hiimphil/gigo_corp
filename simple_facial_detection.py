# simple_facial_detection.py
"""
Simplified AI Video Facial Processing System (No OpenCV dependency)

This module provides basic facial region estimation and processing using only PIL and numpy.
While less precise than OpenCV/MediaPipe, it's designed to work on any platform.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageStat
import tempfile
import os
from moviepy.editor import VideoFileClip
import streamlit as st

class SimpleFacialProcessor:
    """Handles basic facial processing without external CV libraries."""
    
    def __init__(self):
        # Simple heuristics for face estimation
        self.face_ratio = 0.7  # Typical face width/height ratio
        self.mouth_face_ratio = 0.3  # Mouth width as fraction of face width
        self.eye_face_ratio = 0.15  # Eye size as fraction of face width
    
    def estimate_face_regions(self, image, manual_face_center=None):
        """Estimate face regions using manual positioning or automatic estimation."""
        if isinstance(image, Image.Image):
            img_array = np.array(image)
            h, w = image.height, image.width
        else:
            img_array = image
            h, w = img_array.shape[:2] if len(img_array.shape) > 2 else img_array.shape
        
        if manual_face_center:
            return self._estimate_from_manual_center(manual_face_center, w, h)
        else:
            return self._estimate_automatic(w, h)
    
    def _estimate_from_manual_center(self, face_center, w, h):
        """Estimate regions based on manually clicked face center."""
        face_center_x, face_center_y = face_center
        
        # Smart face size estimation based on click position and image analysis
        face_width, face_height = self._estimate_smart_face_size(face_center_x, face_center_y, w, h)
        
        # Face region centered on clicked point
        face_x = face_center_x - face_width // 2
        face_y = face_center_y - face_height // 2
        
        # Keep face within image bounds
        face_x = max(0, min(face_x, w - face_width))
        face_y = max(0, min(face_y, h - face_height))
        
        face_region = {
            'bbox': (face_x, face_y, face_x + face_width, face_y + face_height),
            'center': face_center
        }
        
        # Mouth region (below face center)
        mouth_width = int(face_width * self.mouth_face_ratio)
        mouth_height = int(mouth_width * 0.5)
        
        mouth_x = face_center_x - mouth_width // 2
        mouth_y = face_center_y + int(face_height * 0.2)  # Below center
        
        # Keep mouth within bounds
        mouth_x = max(0, min(mouth_x, w - mouth_width))
        mouth_y = max(0, min(mouth_y, h - mouth_height))
        
        mouth_region = {
            'bbox': (mouth_x, mouth_y, mouth_x + mouth_width, mouth_y + mouth_height),
            'center': (mouth_x + mouth_width // 2, mouth_y + mouth_height // 2)
        }
        
        # Eye regions (above face center)
        eye_size = int(face_width * self.eye_face_ratio)
        eye_y = face_center_y - int(face_height * 0.15)  # Above center
        
        left_eye_x = face_center_x - int(face_width * 0.2) - eye_size // 2
        right_eye_x = face_center_x + int(face_width * 0.2) - eye_size // 2
        
        # Keep eyes within bounds
        left_eye_x = max(0, min(left_eye_x, w - eye_size))
        right_eye_x = max(0, min(right_eye_x, w - eye_size))
        eye_y = max(0, min(eye_y, h - eye_size))
        
        eyes = [
            {  # Left eye
                'bbox': (left_eye_x, eye_y, left_eye_x + eye_size, eye_y + eye_size),
                'center': (left_eye_x + eye_size // 2, eye_y + eye_size // 2)
            },
            {  # Right eye  
                'bbox': (right_eye_x, eye_y, right_eye_x + eye_size, eye_y + eye_size),
                'center': (right_eye_x + eye_size // 2, eye_y + eye_size // 2)
            }
        ]
        
        return {
            'face': face_region,
            'mouth': mouth_region,
            'eyes': eyes,
            'confidence': 0.95,  # High confidence for manual positioning
            'method': 'manual'
        }
    
    def _estimate_automatic(self, w, h):
        """Automatic estimation (original method)."""
        # For AI-generated videos, assume face is centered and takes up significant portion
        
        # Estimate face region (center 60% of image, adjusted for typical framing)
        face_width = int(w * 0.6)
        face_height = int(face_width / self.face_ratio)
        
        face_x = (w - face_width) // 2
        face_y = int(h * 0.2)  # Assume face starts 20% down from top
        
        # Ensure face doesn't go out of bounds
        if face_y + face_height > h:
            face_height = h - face_y
            face_width = int(face_height * self.face_ratio)
            face_x = (w - face_width) // 2
        
        face_region = {
            'bbox': (face_x, face_y, face_x + face_width, face_y + face_height),
            'center': (face_x + face_width // 2, face_y + face_height // 2)
        }
        
        # Estimate mouth region (bottom third of face)
        mouth_width = int(face_width * self.mouth_face_ratio)
        mouth_height = int(mouth_width * 0.5)  # Mouth is typically wider than tall
        
        mouth_x = face_x + (face_width - mouth_width) // 2
        mouth_y = face_y + int(face_height * 0.7)
        
        mouth_region = {
            'bbox': (mouth_x, mouth_y, mouth_x + mouth_width, mouth_y + mouth_height),
            'center': (mouth_x + mouth_width // 2, mouth_y + mouth_height // 2)
        }
        
        # Estimate eye regions
        eye_size = int(face_width * self.eye_face_ratio)
        eye_y = face_y + int(face_height * 0.35)
        
        left_eye_x = face_x + int(face_width * 0.25) - eye_size // 2
        right_eye_x = face_x + int(face_width * 0.75) - eye_size // 2
        
        eyes = [
            {  # Left eye
                'bbox': (left_eye_x, eye_y, left_eye_x + eye_size, eye_y + eye_size),
                'center': (left_eye_x + eye_size // 2, eye_y + eye_size // 2)
            },
            {  # Right eye  
                'bbox': (right_eye_x, eye_y, right_eye_x + eye_size, eye_y + eye_size),
                'center': (right_eye_x + eye_size // 2, eye_y + eye_size // 2)
            }
        ]
        
        return {
            'face': face_region,
            'mouth': mouth_region,
            'eyes': eyes,
            'confidence': 0.6,  # Lower confidence for automatic
            'method': 'automatic'
        }
    
    def analyze_skin_color(self, image, face_region):
        """Analyze skin color from face region."""
        try:
            face_bbox = face_region['bbox']
            x1, y1, x2, y2 = face_bbox
            
            # Extract face region
            face_crop = image.crop((x1, y1, x2, y2))
            
            # Sample from upper cheek areas (avoid mouth/eye regions)
            cheek_height = int((y2 - y1) * 0.2)
            cheek_y = int((y2 - y1) * 0.4)
            
            # Left cheek
            left_cheek = face_crop.crop((
                int((x2 - x1) * 0.1),
                cheek_y,
                int((x2 - x1) * 0.35),
                cheek_y + cheek_height
            ))
            
            # Right cheek
            right_cheek = face_crop.crop((
                int((x2 - x1) * 0.65),
                cheek_y,
                int((x2 - x1) * 0.9),
                cheek_y + cheek_height
            ))
            
            # Get average colors
            left_color = ImageStat.Stat(left_cheek).mean
            right_color = ImageStat.Stat(right_cheek).mean
            
            # Average the cheek colors
            skin_color = tuple(int((left_color[i] + right_color[i]) / 2) for i in range(3))
            
            return skin_color
            
        except Exception as e:
            # Fallback to neutral skin tone
            return (220, 180, 140)
    
    def create_blank_face(self, image, face_data):
        """Create blank face by removing mouth and eyes."""
        blank_face = image.copy()
        
        if not face_data:
            return blank_face
        
        # Get skin color
        skin_color = self.analyze_skin_color(image, face_data['face'])
        
        # Remove mouth
        if 'mouth' in face_data:
            mouth_bbox = face_data['mouth']['bbox']
            self.fill_region_with_blur(blank_face, mouth_bbox, skin_color)
        
        # Remove eyes
        if 'eyes' in face_data:
            for eye in face_data['eyes']:
                eye_bbox = eye['bbox']
                self.fill_region_with_blur(blank_face, eye_bbox, skin_color)
        
        return blank_face
    
    def fill_region_with_blur(self, image, bbox, base_color):
        """Fill region with color and slight blur for natural look."""
        x1, y1, x2, y2 = bbox
        
        # Create a slightly larger region for blending
        padding = 3
        blend_x1 = max(0, x1 - padding)
        blend_y1 = max(0, y1 - padding)
        blend_x2 = min(image.width, x2 + padding)
        blend_y2 = min(image.height, y2 + padding)
        
        # Extract the region around the area to fill
        region = image.crop((blend_x1, blend_y1, blend_x2, blend_y2))
        
        # Create filled version
        draw = ImageDraw.Draw(region)
        
        # Fill the inner area
        inner_x1 = x1 - blend_x1
        inner_y1 = y1 - blend_y1
        inner_x2 = x2 - blend_x1
        inner_y2 = y2 - blend_y1
        
        # Add slight color variation for natural look
        color_variation = 10
        varied_color = tuple(
            max(0, min(255, base_color[i] + np.random.randint(-color_variation, color_variation)))
            for i in range(3)
        )
        
        draw.rectangle([inner_x1, inner_y1, inner_x2, inner_y2], fill=varied_color)
        
        # Apply slight blur for smoothing
        region = region.filter(ImageFilter.GaussianBlur(radius=1))
        
        # Paste back
        image.paste(region, (blend_x1, blend_y1))
    
    def generate_tracking_data(self, face_data):
        """Generate tracking data for animation."""
        if not face_data:
            return None
        
        tracking_data = {
            'mouth': None,
            'eyes': [],
            'face': face_data.get('face'),
            'confidence': face_data.get('confidence', 0.5)
        }
        
        # Mouth tracking data
        if 'mouth' in face_data:
            mouth = face_data['mouth']
            mouth_bbox = mouth['bbox']
            mouth_width = mouth_bbox[2] - mouth_bbox[0]
            
            # Calculate scale (normalize to reference size)
            reference_size = 40
            mouth_scale = mouth_width / reference_size
            mouth_scale = max(0.5, min(2.0, mouth_scale))
            
            tracking_data['mouth'] = {
                'center': mouth['center'],
                'scale': mouth_scale,
                'rotation': 0.0,  # Simple version doesn't calculate rotation
                'bbox': mouth_bbox
            }
        
        # Eye tracking data
        if 'eyes' in face_data:
            for i, eye in enumerate(face_data['eyes']):
                eye_bbox = eye['bbox']
                eye_size = eye_bbox[2] - eye_bbox[0]
                
                eye_scale = eye_size / 20  # Reference eye size
                eye_scale = max(0.5, min(2.0, eye_scale))
                
                tracking_data['eyes'].append({
                    'center': eye['center'],
                    'scale': eye_scale,
                    'rotation': 0.0,
                    'bbox': eye_bbox,
                    'eye_id': f'eye_{i}'
                })
        
        return tracking_data
    
    def _estimate_smart_face_size(self, face_center_x, face_center_y, w, h):
        """Intelligently estimate face size based on position and typical proportions."""
        
        # Calculate distance from center - faces closer to center tend to be larger
        center_distance = np.sqrt((face_center_x - w/2)**2 + (face_center_y - h/2)**2)
        max_distance = np.sqrt((w/2)**2 + (h/2)**2)
        center_factor = 1.0 - (center_distance / max_distance) * 0.3  # 0.7 to 1.0 range
        
        # Vertical position factor - faces higher up tend to be smaller (perspective)
        vertical_factor = 1.0 - (face_center_y / h) * 0.2  # Higher = slightly smaller
        
        # Base size estimation (more conservative than before)
        base_width = min(int(w * 0.25), int(h * 0.35))  # Smaller initial estimate
        base_height = int(base_width / self.face_ratio)
        
        # Apply position-based adjustments
        adjusted_width = int(base_width * center_factor * vertical_factor)
        adjusted_height = int(base_height * center_factor * vertical_factor)
        
        # Ensure minimum and maximum bounds
        min_face_size = min(w, h) // 8  # At least 1/8 of smallest dimension
        max_face_size = min(w, h) // 2  # At most 1/2 of smallest dimension
        
        adjusted_width = max(min_face_size, min(adjusted_width, max_face_size))
        adjusted_height = max(min_face_size, min(adjusted_height, max_face_size))
        
        return adjusted_width, adjusted_height
    
    def estimate_face_regions_multi_click(self, image, face_center=None, mouth_center=None, left_eye=None, right_eye=None):
        """Advanced estimation using multiple manual click points."""
        if isinstance(image, Image.Image):
            h, w = image.height, image.width
        else:
            h, w = image.shape[:2] if len(image.shape) > 2 else image.shape
        
        # If we have mouth and eye positions, we can calculate face size more accurately
        if mouth_center and (left_eye or right_eye):
            return self._estimate_from_features(w, h, face_center, mouth_center, left_eye, right_eye)
        elif face_center:
            return self._estimate_from_manual_center(face_center, w, h)
        else:
            return self._estimate_automatic(w, h)
    
    def _estimate_from_features(self, w, h, face_center, mouth_center, left_eye, right_eye):
        """Estimate based on actual facial feature positions."""
        
        # Calculate face dimensions from feature spacing
        if left_eye and right_eye:
            # Eye distance gives us face width reference
            eye_distance = np.sqrt((right_eye[0] - left_eye[0])**2 + (right_eye[1] - left_eye[1])**2)
            # Typical face width is about 2.5x eye distance
            face_width = int(eye_distance * 2.5)
            
            # Face center from eye midpoint
            eye_center_x = (left_eye[0] + right_eye[0]) // 2
            eye_center_y = (left_eye[1] + right_eye[1]) // 2
            
            if mouth_center:
                # Face height from eye-to-mouth distance
                eye_mouth_distance = np.sqrt((mouth_center[0] - eye_center_x)**2 + (mouth_center[1] - eye_center_y)**2)
                # Eyes are typically 1/3 down from top, mouth is 2/3 down
                face_height = int(eye_mouth_distance * 3)
                
                # More accurate face center
                actual_face_center = (eye_center_x, eye_center_y - face_height // 6)
            else:
                face_height = int(face_width / self.face_ratio)
                actual_face_center = (eye_center_x, eye_center_y)
        
        elif face_center and mouth_center:
            # Use face-to-mouth distance
            face_mouth_distance = np.sqrt((mouth_center[0] - face_center[0])**2 + (mouth_center[1] - face_center[1])**2)
            # Mouth is typically 1/6 below face center
            face_height = int(face_mouth_distance * 6)
            face_width = int(face_height * self.face_ratio)
            actual_face_center = face_center
        
        else:
            # Fallback to single point estimation
            return self._estimate_from_manual_center(face_center, w, h)
        
        # Build face region
        face_x = actual_face_center[0] - face_width // 2
        face_y = actual_face_center[1] - face_height // 2
        
        # Keep within bounds
        face_x = max(0, min(face_x, w - face_width))
        face_y = max(0, min(face_y, h - face_height))
        
        face_region = {
            'bbox': (face_x, face_y, face_x + face_width, face_y + face_height),
            'center': actual_face_center
        }
        
        # Use provided mouth position or estimate
        if mouth_center:
            # Use actual mouth position with estimated size
            mouth_width = int(face_width * self.mouth_face_ratio)
            mouth_height = int(mouth_width * 0.5)
            mouth_x = mouth_center[0] - mouth_width // 2
            mouth_y = mouth_center[1] - mouth_height // 2
            
            mouth_region = {
                'bbox': (mouth_x, mouth_y, mouth_x + mouth_width, mouth_y + mouth_height),
                'center': mouth_center
            }
        else:
            # Estimate mouth from face
            mouth_width = int(face_width * self.mouth_face_ratio)
            mouth_height = int(mouth_width * 0.5)
            mouth_x = actual_face_center[0] - mouth_width // 2
            mouth_y = actual_face_center[1] + int(face_height * 0.2)
            
            mouth_region = {
                'bbox': (mouth_x, mouth_y, mouth_x + mouth_width, mouth_y + mouth_height),
                'center': (mouth_x + mouth_width // 2, mouth_y + mouth_height // 2)
            }
        
        # Use provided eye positions or estimate
        eyes = []
        eye_size = int(face_width * self.eye_face_ratio)
        
        if left_eye:
            eyes.append({
                'bbox': (left_eye[0] - eye_size//2, left_eye[1] - eye_size//2, 
                        left_eye[0] + eye_size//2, left_eye[1] + eye_size//2),
                'center': left_eye
            })
        else:
            # Estimate left eye
            left_eye_x = actual_face_center[0] - int(face_width * 0.2)
            left_eye_y = actual_face_center[1] - int(face_height * 0.15)
            eyes.append({
                'bbox': (left_eye_x - eye_size//2, left_eye_y - eye_size//2, 
                        left_eye_x + eye_size//2, left_eye_y + eye_size//2),
                'center': (left_eye_x, left_eye_y)
            })
        
        if right_eye:
            eyes.append({
                'bbox': (right_eye[0] - eye_size//2, right_eye[1] - eye_size//2, 
                        right_eye[0] + eye_size//2, right_eye[1] + eye_size//2),
                'center': right_eye
            })
        else:
            # Estimate right eye
            right_eye_x = actual_face_center[0] + int(face_width * 0.2)
            right_eye_y = actual_face_center[1] - int(face_height * 0.15)
            eyes.append({
                'bbox': (right_eye_x - eye_size//2, right_eye_y - eye_size//2, 
                        right_eye_x + eye_size//2, right_eye_y + eye_size//2),
                'center': (right_eye_x, right_eye_y)
            })
        
        return {
            'face': face_region,
            'mouth': mouth_region,
            'eyes': eyes,
            'confidence': 0.98,  # Very high confidence for multi-point
            'method': 'multi_click'
        }

def process_ai_video_simple(video_path, progress_callback=None, manual_face_center=None):
    """
    Process AI video using simple geometric estimation (no OpenCV required).
    
    Args:
        video_path: Path to video file
        progress_callback: Optional progress callback function
        manual_face_center: Optional (x, y) tuple for manual face positioning
    
    Returns:
        - blank_frames: List of PIL Images with mouth/eyes removed
        - tracking_data: Frame-by-frame facial tracking information
    """
    processor = SimpleFacialProcessor()
    
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
                
                # Estimate face regions (with optional manual positioning)
                face_data = processor.estimate_face_regions(frame_image, manual_face_center)
                
                # Create blank face
                blank_face = processor.create_blank_face(frame_image, face_data)
                
                # Generate tracking data
                frame_tracking = processor.generate_tracking_data(face_data)
                if frame_tracking:
                    frame_tracking['frame_number'] = frame_num + 1
                    frame_tracking['time'] = frame_time
                
                blank_frames.append(blank_face)
                tracking_data.append(frame_tracking if frame_tracking else {
                    'frame_number': frame_num + 1,
                    'time': frame_time,
                    'mouth': None,
                    'eyes': [],
                    'face': None,
                    'confidence': 0.0
                })
                
                # Progress update
                if progress_callback:
                    progress_callback(frame_num + 1, total_frames)
    
    except Exception as e:
        raise Exception(f"Error processing video: {e}")
    
    return blank_frames, tracking_data

def process_ai_video_multi_click(video_path, progress_callback=None, multi_click_positions=None):
    """
    Process AI video using multi-click positioning for maximum accuracy.
    
    Args:
        video_path: Path to video file
        progress_callback: Optional progress callback function
        multi_click_positions: Dict with keys 'face', 'mouth', 'left_eye', 'right_eye'
    
    Returns:
        - blank_frames: List of PIL Images with mouth/eyes removed
        - tracking_data: Frame-by-frame facial tracking information
    """
    processor = SimpleFacialProcessor()
    
    blank_frames = []
    tracking_data = []
    
    # Extract positions from multi-click data
    face_center = multi_click_positions.get('face') if multi_click_positions else None
    mouth_center = multi_click_positions.get('mouth') if multi_click_positions else None
    left_eye = multi_click_positions.get('left_eye') if multi_click_positions else None
    right_eye = multi_click_positions.get('right_eye') if multi_click_positions else None
    
    try:
        with VideoFileClip(video_path) as video:
            fps = video.fps
            duration = video.duration
            total_frames = int(duration * fps)
            
            for frame_num in range(total_frames):
                frame_time = frame_num / fps
                frame = video.get_frame(frame_time)
                frame_image = Image.fromarray(frame.astype('uint8'))
                
                # Use multi-click positioning for precise detection
                face_data = processor.estimate_face_regions_multi_click(
                    frame_image, 
                    face_center=face_center,
                    mouth_center=mouth_center,
                    left_eye=left_eye,
                    right_eye=right_eye
                )
                
                # Create blank face
                blank_face = processor.create_blank_face(frame_image, face_data)
                
                # Generate tracking data
                frame_tracking = processor.generate_tracking_data(face_data)
                if frame_tracking:
                    frame_tracking['frame_number'] = frame_num + 1
                    frame_tracking['time'] = frame_time
                    frame_tracking['method'] = face_data.get('method', 'multi_click')
                
                blank_frames.append(blank_face)
                tracking_data.append(frame_tracking if frame_tracking else {
                    'frame_number': frame_num + 1,
                    'time': frame_time,
                    'mouth': None,
                    'eyes': [],
                    'face': None,
                    'confidence': 0.0,
                    'method': 'failed'
                })
                
                # Progress update
                if progress_callback:
                    progress_callback(frame_num + 1, total_frames)
    
    except Exception as e:
        raise Exception(f"Error processing video: {e}")
    
    return blank_frames, tracking_data