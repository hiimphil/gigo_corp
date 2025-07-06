# ui_video_tracker.py
import streamlit as st
import os
import tempfile
from moviepy.editor import VideoFileClip
from PIL import Image, ImageDraw
import numpy as np
import zipfile
import io
import json
import base64

def load_video_frame(video_path, frame_time):
    """Load a specific frame from video at given time."""
    try:
        with VideoFileClip(video_path) as video:
            frame = video.get_frame(frame_time)
            # Ensure frame is valid numpy array
            if frame is None:
                return None
            if not isinstance(frame, np.ndarray):
                return None
            # Convert to PIL Image
            pil_image = Image.fromarray(frame.astype('uint8'))
            # Validate the PIL image
            if not hasattr(pil_image, 'save'):
                return None
            return pil_image
    except Exception as e:
        print(f"Error loading video frame: {e}")
        return None

def load_mouth_overlay():
    """Load the mouth overlay image for placement."""
    mouth_path = "Cartoon_Images/a/mouths/open-large.png"  # Default mouth
    try:
        if os.path.exists(mouth_path):
            return Image.open(mouth_path).convert("RGBA")
        else:
            # Create a simple rectangle as fallback
            mouth_img = Image.new("RGBA", (40, 20), (255, 0, 0, 128))
            return mouth_img
    except:
        # Fallback rectangle
        mouth_img = Image.new("RGBA", (40, 20), (255, 0, 0, 128))
        return mouth_img

def create_mouth_overlay(image, mouth_center=None, mouth_scale=1.0, show_tracking_dots=True):
    """Create image with mouth overlay and optional tracking dots."""
    if image is None:
        return None, None, None
    
    try:
        overlay_image = image.copy()
        
        if mouth_center:
            mouth_img = load_mouth_overlay()
            if mouth_img is None:
                return overlay_image, None, None
            
            # Scale mouth
            if mouth_scale != 1.0:
                new_size = (int(mouth_img.width * mouth_scale), int(mouth_img.height * mouth_scale))
                mouth_img = mouth_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Calculate mouth position
            mouth_x = mouth_center[0] - mouth_img.width // 2
            mouth_y = mouth_center[1] - mouth_img.height // 2
            
            # Paste mouth overlay with transparency
            overlay_image.paste(mouth_img, (mouth_x, mouth_y), mouth_img)
            
            if show_tracking_dots:
                # Calculate tracking dot positions based on mouth placement
                left_dot = (mouth_x, mouth_center[1])  # Left edge of mouth
                right_dot = (mouth_x + mouth_img.width, mouth_center[1])  # Right edge of mouth
                
                # Draw tracking dots
                draw = ImageDraw.Draw(overlay_image)
                dot_size = 8
                
                # Green dot for left
                draw.ellipse([left_dot[0]-dot_size, left_dot[1]-dot_size, 
                             left_dot[0]+dot_size, left_dot[1]+dot_size], 
                            fill='lime', outline='darkgreen', width=2)
                
                # Blue dot for right
                draw.ellipse([right_dot[0]-dot_size, right_dot[1]-dot_size, 
                             right_dot[0]+dot_size, right_dot[1]+dot_size], 
                            fill='blue', outline='darkblue', width=2)
                
                return overlay_image, left_dot, right_dot
        
        return overlay_image, None, None
        
    except Exception as e:
        print(f"Error in create_mouth_overlay: {e}")
        return None, None, None

def interpolate_keyframes(keyframes, total_frames, fps):
    """Interpolate mouth positions between keyframes."""
    if len(keyframes) < 1:
        return []
    
    # Sort keyframes by time
    sorted_keyframes = sorted(keyframes, key=lambda k: k['time'])
    tracking_data = []
    
    for frame_num in range(1, total_frames + 1):
        frame_time = (frame_num - 1) / fps
        
        # Find surrounding keyframes
        before_kf = None
        after_kf = None
        
        for kf in sorted_keyframes:
            if kf['time'] <= frame_time:
                before_kf = kf
            elif kf['time'] > frame_time and after_kf is None:
                after_kf = kf
                break
        
        # Calculate interpolated position
        if before_kf and after_kf:
            # Interpolate between keyframes
            time_range = after_kf['time'] - before_kf['time']
            time_progress = (frame_time - before_kf['time']) / time_range
            
            # Linear interpolation of mouth center
            mouth_x = before_kf['mouth_center'][0] + (after_kf['mouth_center'][0] - before_kf['mouth_center'][0]) * time_progress
            mouth_y = before_kf['mouth_center'][1] + (after_kf['mouth_center'][1] - before_kf['mouth_center'][1]) * time_progress
            mouth_center = (int(mouth_x), int(mouth_y))
            
            # Interpolate scale
            scale = before_kf['mouth_scale'] + (after_kf['mouth_scale'] - before_kf['mouth_scale']) * time_progress
            
        elif before_kf:
            # Use last keyframe
            mouth_center = before_kf['mouth_center']
            scale = before_kf['mouth_scale']
        elif after_kf:
            # Use first keyframe
            mouth_center = after_kf['mouth_center']
            scale = after_kf['mouth_scale']
        else:
            continue
        
        # Calculate tracking dots from mouth placement
        mouth_img = load_mouth_overlay()
        if scale != 1.0:
            mouth_img = mouth_img.resize(
                (int(mouth_img.width * scale), int(mouth_img.height * scale)), 
                Image.Resampling.LANCZOS
            )
        
        left_dot = (mouth_center[0] - mouth_img.width // 2, mouth_center[1])
        right_dot = (mouth_center[0] + mouth_img.width // 2, mouth_center[1])
        
        tracking_data.append({
            'frame_number': frame_num,
            'time': frame_time,
            'mouth_center': mouth_center,
            'mouth_scale': scale,
            'left_dot': left_dot,
            'right_dot': right_dot
        })
    
    return tracking_data

def interpolate_tracking_points(left_start, right_start, total_frames, video_path):
    """Generate tracking points for all frames using simple interpolation."""
    tracking_data = []
    
    try:
        with VideoFileClip(video_path) as video:
            fps = video.fps
            duration = video.duration
            
            # For now, use simple static positioning
            # In Phase 2, we can add motion tracking
            for i in range(total_frames):
                frame_time = i / fps
                if frame_time > duration:
                    break
                    
                tracking_data.append({
                    'frame_number': i + 1,
                    'time': frame_time,
                    'left_dot': left_start,
                    'right_dot': right_start
                })
    except Exception as e:
        st.error(f"Error generating tracking data: {e}")
        return []
    
    return tracking_data

def export_frames_with_tracking(video_path, tracking_data, output_dir, frame_prefix="base"):
    """Export all frames with tracking dots embedded."""
    try:
        exported_files = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with VideoFileClip(video_path) as video:
            for i, track_point in enumerate(tracking_data):
                frame_time = track_point['time']
                frame = video.get_frame(frame_time)
                frame_image = Image.fromarray(frame.astype('uint8'))
                
                # Add tracking dots
                tracked_frame = create_tracking_overlay(
                    frame_image,
                    track_point['left_dot'],
                    track_point['right_dot']
                )
                
                # Save frame
                frame_filename = f"{frame_prefix}_{track_point['frame_number']:02d}.png"
                frame_path = os.path.join(output_dir, frame_filename)
                tracked_frame.save(frame_path, "PNG")
                exported_files.append(frame_path)
                
                # Update progress
                progress = (i + 1) / len(tracking_data)
                progress_bar.progress(progress)
                status_text.write(f"Exporting frame {i+1}/{len(tracking_data)}")
        
        progress_bar.empty()
        status_text.empty()
        return exported_files, None
        
    except Exception as e:
        return None, f"Error exporting frames: {e}"

def display():
    """Main UI for the video tracking tool."""
    st.header("🎯 Interactive Video Tracker")
    st.subheader("Place tracking dots on video frames for automated motion preparation")
    
    st.markdown("""
    **Revolutionary workflow:**
    1. Upload your AI-generated motion video
    2. Scrub to a clear frame where the mouth is visible
    3. **Click directly on the mouth** to place mouth overlay
    4. Set keyframes at different head positions for motion tracking
    5. Export motion-ready frames with interpolated tracking dots!
    
    **Benefits:** 100x faster than manual frame editing, realistic head movement tracking, zero human error.
    """)
    
    st.divider()
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=['mp4', 'mov', 'avi', 'mkv'],
        help="Upload your AI-generated character motion video"
    )
    
    if uploaded_file is not None:
        # Display video info
        st.success(f"✅ Uploaded: {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.1f} MB)")
        
        # Save video temporarily and load metadata
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(uploaded_file.getbuffer())
            temp_video_path = tmp_video.name
        
        try:
            with VideoFileClip(temp_video_path) as video:
                duration = video.duration
                fps = video.fps
                total_frames = int(duration * fps)
                
                st.write(f"📹 Video: {duration:.2f}s, {fps} FPS, {total_frames} frames")
                
                # Show video preview
                st.video(uploaded_file)
                
                st.divider()
                st.subheader("🎯 Place Tracking Dots")
                
                # Frame navigation
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    frame_time = st.slider(
                        "Scrub to position mouth tracking dots",
                        0.0, duration, duration/2, 0.1,
                        help="Find a clear frame where mouth corners are visible"
                    )
                
                with col2:
                    frame_number = int(frame_time * fps) + 1
                    st.metric("Frame", f"{frame_number}/{total_frames}")
                
                # Load and display current frame
                current_frame = load_video_frame(temp_video_path, frame_time)
                if current_frame:
                    
                    # Initialize keyframes in session state
                    if 'mouth_keyframes' not in st.session_state:
                        st.session_state.mouth_keyframes = []
                    
                    # Check if there's a keyframe at current time
                    current_keyframe = None
                    for kf in st.session_state.mouth_keyframes:
                        if abs(kf['time'] - frame_time) < 0.1:  # Within 0.1 seconds
                            current_keyframe = kf
                            break
                    
                    # Get current mouth position (from keyframe or default)
                    if current_keyframe:
                        mouth_center = current_keyframe['mouth_center']
                        mouth_scale = current_keyframe['mouth_scale']
                    else:
                        mouth_center = st.session_state.get('temp_mouth_center', (current_frame.width//2, current_frame.height//2))
                        mouth_scale = st.session_state.get('temp_mouth_scale', 1.0)
                    
                    # Create overlay image with mouth and tracking dots
                    try:
                        display_frame, left_dot, right_dot = create_mouth_overlay(
                            current_frame, mouth_center, mouth_scale, show_tracking_dots=True
                        )
                        if display_frame is None:
                            st.error("Failed to create mouth overlay")
                            display_frame = current_frame.copy()
                            left_dot = right_dot = None
                        # Ensure display_frame is a valid PIL Image
                        if not hasattr(display_frame, 'save'):
                            st.error(f"create_mouth_overlay returned invalid type: {type(display_frame)}")
                            display_frame = current_frame.copy()
                            left_dot = right_dot = None
                    except Exception as e:
                        st.error(f"Error creating mouth overlay: {e}")
                        display_frame = current_frame.copy()
                        left_dot = right_dot = None
                    
                    # Display frame with click-to-place functionality
                    st.write("**🎯 Click on the image to place mouth center:**")
                    
                    # Use streamlit-image-coordinates for click detection
                    if display_frame is not None:
                        try:
                            from streamlit_image_coordinates import streamlit_image_coordinates
                            
                            # Try multiple approaches for streamlit-image-coordinates
                            # Method 1: Convert to bytes (most reliable)
                            try:
                                img_buffer = io.BytesIO()
                                display_frame.save(img_buffer, format='PNG')
                                img_bytes = img_buffer.getvalue()
                                
                                # Use a unique key that includes mouse position state
                                click_key = f"image_click_{frame_time}_{mouth_center[0]}_{mouth_center[1]}"
                                clicked_coords = streamlit_image_coordinates(
                                    img_bytes,
                                    key=click_key,
                                    width=display_frame.width if display_frame.width <= 800 else 800
                                )
                            except Exception as bytes_error:
                                st.write(f"Bytes method failed: {bytes_error}")
                                # Method 2: Try numpy array
                                try:
                                    display_array = np.array(display_frame)
                                    st.write(f"Trying numpy array: {type(display_array)}, shape: {display_array.shape}")
                                    
                                    # Use a unique key that includes mouse position state
                                    click_key_array = f"image_click_{frame_time}_{mouth_center[0]}_{mouth_center[1]}_array"
                                    clicked_coords = streamlit_image_coordinates(
                                        display_array,
                                        key=click_key_array,
                                        width=display_frame.width if display_frame.width <= 800 else 800
                                    )
                                except Exception as array_error:
                                    st.error(f"Both methods failed - Bytes: {bytes_error}, Array: {array_error}")
                                    clicked_coords = None
                            
                            # If image was clicked, update mouth position
                            if clicked_coords is not None:
                                # Get current click coordinates
                                click_x_raw = clicked_coords.get("x", 0)
                                click_y_raw = clicked_coords.get("y", 0)
                                
                                # Check if this is a new click (different from current position)
                                last_click_key = f"last_click_{frame_time}"
                                current_click = (click_x_raw, click_y_raw)
                                last_click = st.session_state.get(last_click_key, None)
                                
                                st.write(f"DEBUG: Current click: {current_click}, Last click: {last_click}")
                                
                                if last_click != current_click and current_click != (0, 0):
                                    # Calculate scale factor if image was resized for display
                                    display_width = min(display_frame.width, 800)
                                    scale_factor = display_frame.width / display_width
                                    
                                    # Scale click coordinates back to original image size
                                    click_x = int(click_x_raw * scale_factor)
                                    click_y = int(click_y_raw * scale_factor)
                                    
                                    # Update mouth center
                                    st.session_state.temp_mouth_center = (click_x, click_y)
                                    st.session_state[last_click_key] = current_click
                                    
                                    st.success(f"✅ Mouth placed at ({click_x}, {click_y})")
                                    st.rerun()
                        
                        except ImportError:
                            # Fallback to regular image if streamlit-image-coordinates not available
                            st.image(display_frame, caption="Manual controls available below", use_container_width=True)
                            st.warning("💡 **Click-to-place available!** Install for better UX: `pip install streamlit-image-coordinates`")
                            st.info("Using manual controls below for now - still fully functional!")
                        
                        except Exception as e:
                            # Any other error with the click functionality
                            st.image(display_frame, caption="Click functionality error - using manual controls", use_container_width=True)
                            st.error(f"Click detection error: {e}")
                    else:
                        # Display frame is None, fall back to error message
                        st.error("Could not load video frame for tracking")
                    
                    # Mouth placement controls
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**👄 Fine-tune Position:**")
                        mouth_x = st.number_input(
                            "X", 0, current_frame.width, 
                            mouth_center[0], key=f"mouth_x_{frame_time}",
                            help="Click image or adjust manually"
                        )
                        mouth_y = st.number_input(
                            "Y", 0, current_frame.height, 
                            mouth_center[1], key=f"mouth_y_{frame_time}",
                            help="Click image or adjust manually"
                        )
                    
                    with col2:
                        st.write("**🔍 Scale:**")
                        mouth_scale = st.slider(
                            "Mouth Size", 0.5, 2.0, mouth_scale, 0.1,
                            key=f"mouth_scale_{frame_time}",
                            help="Adjust mouth size to fit character"
                        )
                        
                        # Show current position info
                        st.info(f"Position: ({mouth_x}, {mouth_y})")
                    
                    with col3:
                        st.write("**📌 Keyframes:**")
                        if st.button("Set Keyframe", use_container_width=True, help="Save mouth position at this time"):
                            # Remove existing keyframe at this time
                            st.session_state.mouth_keyframes = [
                                kf for kf in st.session_state.mouth_keyframes 
                                if abs(kf['time'] - frame_time) >= 0.1
                            ]
                            # Add new keyframe
                            st.session_state.mouth_keyframes.append({
                                'time': frame_time,
                                'frame_number': frame_number,
                                'mouth_center': (mouth_x, mouth_y),
                                'mouth_scale': mouth_scale
                            })
                            st.success(f"✅ Keyframe set at {frame_time:.1f}s")
                            st.rerun()
                        
                        if current_keyframe and st.button("Remove", use_container_width=True):
                            st.session_state.mouth_keyframes = [
                                kf for kf in st.session_state.mouth_keyframes 
                                if abs(kf['time'] - frame_time) >= 0.1
                            ]
                            st.success("Keyframe removed")
                            st.rerun()
                    
                    # Update temporary positions
                    st.session_state.temp_mouth_center = (mouth_x, mouth_y)
                    st.session_state.temp_mouth_scale = mouth_scale
                    
                    # Show keyframes info
                    if st.session_state.mouth_keyframes:
                        st.write("**📌 Current Keyframes:**")
                        keyframe_text = " | ".join([f"Frame {kf['frame_number']} ({kf['time']:.1f}s)" for kf in sorted(st.session_state.mouth_keyframes, key=lambda k: k['time'])])
                        st.info(keyframe_text)
                        
                        if len(st.session_state.mouth_keyframes) >= 1:
                            st.divider()
                            st.subheader("🎬 Generate Motion Frames")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                frame_prefix = st.text_input("Frame prefix", "base", 
                                                           help="Frames will be named: prefix_01.png, etc.")
                            
                            with col2:
                                st.metric("Keyframes Set", len(st.session_state.mouth_keyframes))
                                st.metric("Frames to Export", total_frames)
                            
                            if st.button("🚀 Export Motion-Ready Frames", use_container_width=True, type="primary"):
                                temp_output_dir = tempfile.mkdtemp()
                                
                                try:
                                    # Generate interpolated tracking data
                                    st.write("📊 Interpolating mouth positions between keyframes...")
                                    tracking_data = interpolate_keyframes(
                                        st.session_state.mouth_keyframes, total_frames, fps
                                    )
                                    
                                    if tracking_data:
                                        # Export frames with tracking dots
                                        st.write("🎯 Exporting frames with tracking dots...")
                                        exported_files, error = export_frames_with_tracking(
                                            temp_video_path, tracking_data, temp_output_dir, frame_prefix
                                        )
                                        
                                        if error:
                                            st.error(f"❌ Export failed: {error}")
                                        else:
                                            st.success(f"✅ Exported {len(exported_files)} motion-ready frames with keyframe interpolation!")
                                            
                                            # Show preview
                                            st.subheader("🖼️ Preview (Every 5th frame)")
                                            preview_cols = st.columns(4)
                                            preview_frames = exported_files[::5][:8]  # Every 5th frame, max 8
                                            for i, file_path in enumerate(preview_frames):
                                                with preview_cols[i % 4]:
                                                    st.image(file_path, caption=f"Frame {(i*5)+1}", width=150)
                                            
                                            # Create download ZIP
                                            st.subheader("📥 Download Motion-Ready Frames")
                                            
                                            with st.spinner("Creating ZIP file..."):
                                                zip_buffer = io.BytesIO()
                                                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                                    for file_path in exported_files:
                                                        filename = os.path.basename(file_path)
                                                        zip_file.write(file_path, filename)
                                                zip_data = zip_buffer.getvalue()
                                            
                                            st.download_button(
                                                label=f"📥 Download {len(exported_files)} Interpolated Frames",
                                                data=zip_data,
                                                file_name=f"{frame_prefix}_keyframe_motion.zip",
                                                mime="application/zip",
                                                use_container_width=True
                                            )
                                            
                                            st.success("🎉 Keyframe-interpolated motion frames ready!")
                                    
                                except Exception as e:
                                    st.error(f"❌ Error during export: {e}")
                                
                                finally:
                                    # Cleanup
                                    try:
                                        import shutil
                                        shutil.rmtree(temp_output_dir)
                                    except:
                                        pass
                        else:
                            st.info("👆 Set at least 1 keyframe to generate motion frames")
                    else:
                        st.info("🎯 Position the mouth overlay and click 'Set Keyframe' to start tracking")
                        
                
                else:
                    st.error("Could not load video frame")
        
        except Exception as e:
            st.error(f"Error loading video: {e}")
        
        finally:
            try:
                os.unlink(temp_video_path)
            except:
                pass
    
    # Instructions
    st.divider()
    st.subheader("📝 How to Use Motion-Ready Frames")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **What you get:**
        - Frames with tracking dots that follow head movement
        - Keyframe interpolation for smooth motion tracking
        - Visual mouth overlay for precise placement
        
        **Next steps:**
        1. Download the motion-ready frames
        2. Edit to remove mouth areas (tracking dots are already positioned!)
        3. Rename and upload to `Cartoon_Images/[character]/[direction]/[action]/`
        """)
    
    with col2:
        st.markdown("""
        **Keyframe Workflow:**
        1. **Scrub to first position** where mouth is clear
        2. **Place mouth overlay** using controls
        3. **Set keyframe** to save position
        4. **Scrub to different position** (head moved)
        5. **Adjust mouth position** and set another keyframe
        6. **Export** - tracking dots interpolate between keyframes!
        
        **Result:** Realistic head movement tracking!
        """)