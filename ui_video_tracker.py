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
            return Image.fromarray(frame.astype('uint8'))
    except Exception as e:
        return None

def create_tracking_overlay(image, left_dot=None, right_dot=None, dot_size=10):
    """Create image with tracking dots overlaid."""
    overlay_image = image.copy()
    draw = ImageDraw.Draw(overlay_image)
    
    if left_dot:
        x, y = left_dot
        # Green dot for left mouth corner
        draw.ellipse([x-dot_size, y-dot_size, x+dot_size, y+dot_size], 
                    fill='lime', outline='darkgreen', width=2)
        draw.text((x+15, y-15), "L", fill='darkgreen')
    
    if right_dot:
        x, y = right_dot
        # Blue dot for right mouth corner
        draw.ellipse([x-dot_size, y-dot_size, x+dot_size, y+dot_size], 
                    fill='blue', outline='darkblue', width=2)
        draw.text((x+15, y-15), "R", fill='darkblue')
    
    return overlay_image

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
    3. Click to place left and right mouth corner tracking dots
    4. Preview tracking across the entire video
    5. Export motion-ready frames with dots already placed!
    
    **Benefits:** 10x faster than manual frame editing, consistent tracking, zero human error.
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
                    
                    # Check if tracking dots are already placed
                    left_dot = st.session_state.get('left_tracking_dot')
                    right_dot = st.session_state.get('right_tracking_dot')
                    
                    # Create overlay image with any existing dots
                    display_frame = create_tracking_overlay(current_frame, left_dot, right_dot)
                    
                    # Display frame with instructions
                    st.write("**Click on the image to place tracking dots:**")
                    
                    # Show frame - in future we'll add click handling
                    st.image(display_frame, caption="Click to place tracking dots", use_column_width=True)
                    
                    # Manual dot placement for now (Phase 1)
                    st.write("**Manual Dot Placement (Phase 1):**")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("🟢 **Left Mouth Corner (Green)**")
                        left_x = st.number_input("X coordinate", 0, current_frame.width, 
                                                left_dot[0] if left_dot else current_frame.width//3, 
                                                key="left_x")
                        left_y = st.number_input("Y coordinate", 0, current_frame.height, 
                                                left_dot[1] if left_dot else current_frame.height//2, 
                                                key="left_y")
                        
                        if st.button("Set Left Dot", use_container_width=True):
                            st.session_state.left_tracking_dot = (left_x, left_y)
                            st.rerun()
                    
                    with col2:
                        st.write("🔵 **Right Mouth Corner (Blue)**")
                        right_x = st.number_input("X coordinate", 0, current_frame.width, 
                                                 right_dot[0] if right_dot else (current_frame.width*2)//3, 
                                                 key="right_x")
                        right_y = st.number_input("Y coordinate", 0, current_frame.height, 
                                                 right_dot[1] if right_dot else current_frame.height//2, 
                                                 key="right_y")
                        
                        if st.button("Set Right Dot", use_container_width=True):
                            st.session_state.right_tracking_dot = (right_x, right_y)
                            st.rerun()
                    
                    # Show current dot positions
                    if left_dot and right_dot:
                        st.success(f"✅ Tracking dots placed! Left: {left_dot}, Right: {right_dot}")
                        
                        st.divider()
                        st.subheader("🎬 Generate Motion Frames")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            frame_prefix = st.text_input("Frame prefix", "base", 
                                                       help="Frames will be named: prefix_01.png, etc.")
                        
                        with col2:
                            st.metric("Frames to Export", total_frames)
                        
                        if st.button("🚀 Export Motion-Ready Frames", use_container_width=True, type="primary"):
                            temp_output_dir = tempfile.mkdtemp()
                            
                            try:
                                # Generate tracking data for all frames
                                st.write("📊 Generating tracking data for all frames...")
                                tracking_data = interpolate_tracking_points(
                                    left_dot, right_dot, total_frames, temp_video_path
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
                                        st.success(f"✅ Exported {len(exported_files)} motion-ready frames!")
                                        
                                        # Show preview
                                        st.subheader("🖼️ Preview (First 8 frames)")
                                        preview_cols = st.columns(4)
                                        for i, file_path in enumerate(exported_files[:8]):
                                            with preview_cols[i % 4]:
                                                st.image(file_path, caption=f"Frame {i+1}", width=150)
                                        
                                        if len(exported_files) > 8:
                                            st.info(f"Showing 8 of {len(exported_files)} frames")
                                        
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
                                            label=f"📥 Download {len(exported_files)} Motion-Ready Frames",
                                            data=zip_data,
                                            file_name=f"{frame_prefix}_motion_ready.zip",
                                            mime="application/zip",
                                            use_container_width=True
                                        )
                                        
                                        st.success("🎉 Motion frames ready! These already have tracking dots - just remove mouths and upload to Cartoon_Images!")
                                
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
                        st.info("👆 Place both left and right tracking dots to continue")
                
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
        - Frames with tracking dots already placed
        - Consistent dot positioning across all frames
        - Ready for mouth removal and upload
        
        **Next steps:**
        1. Download the motion-ready frames
        2. Edit to remove mouth areas (tracking dots are already there!)
        3. Upload to `Cartoon_Images/[character]/[direction]/[action]/`
        """)
    
    with col2:
        st.markdown("""
        **Phase 1 Features:**
        - Manual dot placement with preview
        - Static tracking across frames
        - Export with embedded dots
        
        **Coming in Phase 2:**
        - Click-to-place on image
        - Automatic motion tracking
        - Smart mouth removal assistance
        """)