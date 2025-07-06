# ui_facial_detection.py
"""
UI for testing and using the AI Video Facial Detection System
"""

import streamlit as st
import tempfile
import os
import zipfile
import io
from PIL import Image
import simple_facial_detection as fdm

def display():
    """Main UI for the facial detection tool."""
    st.header("🎭 AI Video Facial Detection")
    st.subheader("Convert AI-generated videos into animation-ready assets")
    
    st.markdown("""
    **Smart AI Video Processing (Simplified):**
    1. Upload a 5-second AI-generated character video
    2. **Auto-estimate** face, mouth, and eye regions using geometric analysis
    3. **Create blank canvas** by removing mouth/eyes with matching skin tone
    4. **Generate tracking data** for animation overlay positioning
    5. **Export** processed frames + tracking data for cartoon generation
    
    **Benefits:** Works on any platform, no external dependencies, optimized for AI-generated character videos.
    
    **Note:** This simplified version uses geometric estimation rather than AI detection for maximum compatibility.
    """)
    
    st.divider()
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose an AI-generated video file",
        type=['mp4', 'mov', 'avi', 'mkv'],
        help="Upload a short video (5-10 seconds) featuring a single character with visible face"
    )
    
    if uploaded_file is not None:
        # Display video info
        st.success(f"✅ Uploaded: {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.1f} MB)")
        
        # Show video preview
        st.video(uploaded_file)
        
        # Processing options
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Processing Options:**")
            
            # Character name for output files
            character_name = st.text_input(
                "Character name", 
                value="character", 
                help="Used for naming output files"
            )
            
            # Action/emotion for output files
            action_name = st.text_input(
                "Action/emotion", 
                value="normal", 
                help="Describe the character's action/emotion in the video"
            )
        
        with col2:
            st.write("**Detection Method:**")
            
            detection_method = st.radio(
                "How to locate the face?",
                ["Manual click positioning", "Automatic estimation"],
                help="Manual click is much more accurate!"
            )
            
            # Number of preview frames to show
            preview_frames = st.slider(
                "Preview frames to show", 
                1, 8, 3,
                help="How many processed frames to preview"
            )
        
        # Manual positioning section
        if detection_method == "Manual click positioning":
            st.divider()
            st.subheader("🎯 Click to Position Face")
            
            # Load first frame for positioning
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                tmp_video.write(uploaded_file.getbuffer())
                temp_video_path = tmp_video.name
            
            try:
                from moviepy.editor import VideoFileClip
                with VideoFileClip(temp_video_path) as video:
                    # Get middle frame for positioning
                    mid_time = video.duration / 2
                    frame = video.get_frame(mid_time)
                    positioning_frame = Image.fromarray(frame.astype('uint8'))
                
                st.write("**Click on the character's face center in this frame:**")
                
                # Convert to bytes for click detection
                img_buffer = io.BytesIO()
                positioning_frame.save(img_buffer, format='PNG')
                img_bytes = img_buffer.getvalue()
                
                # Use click coordinates for positioning
                try:
                    from streamlit_image_coordinates import streamlit_image_coordinates
                    
                    clicked_coords = streamlit_image_coordinates(
                        img_bytes,
                        key="face_position_click",
                        width=min(positioning_frame.width, 600)
                    )
                    
                    face_center = None
                    if clicked_coords is not None:
                        # Calculate scale factor if image was resized
                        display_width = min(positioning_frame.width, 600)
                        scale_factor = positioning_frame.width / display_width
                        
                        face_x = int(clicked_coords["x"] * scale_factor)
                        face_y = int(clicked_coords["y"] * scale_factor)
                        face_center = (face_x, face_y)
                        
                        st.success(f"✅ Face positioned at ({face_x}, {face_y})")
                        
                        # Store in session state
                        st.session_state.manual_face_center = face_center
                    
                    # Show current position if exists
                    if 'manual_face_center' in st.session_state:
                        face_center = st.session_state.manual_face_center
                        st.info(f"Current face center: {face_center}")
                    else:
                        st.warning("👆 Click on the character's face to set position")
                
                except ImportError:
                    st.error("Click positioning requires streamlit-image-coordinates package")
                    detection_method = "Automatic estimation"
                
            except Exception as e:
                st.error(f"Could not load video frame: {e}")
                detection_method = "Automatic estimation"
            
            finally:
                try:
                    os.unlink(temp_video_path)
                except:
                    pass
        
        st.divider()
        
        # Process video button
        if st.button("🤖 Process AI Video", use_container_width=True, type="primary"):
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                tmp_video.write(uploaded_file.getbuffer())
                temp_video_path = tmp_video.name
            
            try:
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def progress_callback(current_frame, total_frames):
                    progress = current_frame / total_frames
                    progress_bar.progress(progress)
                    status_text.write(f"Processing frame {current_frame}/{total_frames}")
                
                # Get manual face center if available
                manual_face_center = None
                if detection_method == "Manual click positioning" and 'manual_face_center' in st.session_state:
                    manual_face_center = st.session_state.manual_face_center
                
                # Process the video
                with st.spinner("🧠 Analyzing facial features..."):
                    blank_frames, tracking_data = fdm.process_ai_video_simple(
                        temp_video_path, 
                        progress_callback=progress_callback,
                        manual_face_center=manual_face_center
                    )
                
                progress_bar.empty()
                status_text.empty()
                
                if blank_frames and tracking_data:
                    st.success(f"✅ Processed {len(blank_frames)} frames successfully!")
                    
                    # Show detection results
                    st.subheader("🔍 Detection Results")
                    
                    # Count successful detections and check method used
                    successful_detections = sum(1 for td in tracking_data if td.get('mouth') is not None)
                    detection_rate = (successful_detections / len(tracking_data)) * 100
                    
                    # Check if manual positioning was used
                    positioning_method = "Manual" if manual_face_center else "Automatic"
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Frames", len(blank_frames))
                    with col2:
                        st.metric("Faces Processed", successful_detections)
                    with col3:
                        st.metric("Success Rate", f"{detection_rate:.1f}%")
                    with col4:
                        st.metric("Method", positioning_method)
                    
                    # Show preview frames
                    st.subheader("🖼️ Processed Frame Preview")
                    st.write("**Before/After Comparison:**")
                    
                    # Show every nth frame for preview
                    frame_step = max(1, len(blank_frames) // preview_frames)
                    preview_indices = range(0, len(blank_frames), frame_step)[:preview_frames]
                    
                    for i, frame_idx in enumerate(preview_indices):
                        st.write(f"**Frame {frame_idx + 1}:**")
                        
                        cols = st.columns(2)
                        
                        # Get original frame for comparison
                        try:
                            from moviepy.editor import VideoFileClip
                            with VideoFileClip(temp_video_path) as video:
                                frame_time = frame_idx / video.fps
                                original_frame = video.get_frame(frame_time)
                                original_image = Image.fromarray(original_frame.astype('uint8'))
                        except:
                            original_image = None
                        
                        with cols[0]:
                            if original_image:
                                st.write("Original Frame")
                                st.image(original_image, use_container_width=True)
                            else:
                                st.write("Original Frame (unavailable)")
                        
                        with cols[1]:
                            st.write("Processed Frame (Blank Canvas)")
                            st.image(blank_frames[frame_idx], use_container_width=True)
                        
                        # Show tracking data for this frame
                        if tracking_data[frame_idx].get('mouth'):
                            td = tracking_data[frame_idx]
                            confidence = td.get('confidence', 0.5)
                            method = td.get('method', 'unknown')
                            
                            mouth_info = f"Mouth: {td['mouth']['center']}, Scale: {td['mouth']['scale']:.2f}"
                            confidence_info = f"Method: {method}, Confidence: {confidence:.1f}"
                            
                            if confidence > 0.9:
                                st.success(f"✅ {mouth_info} | {confidence_info}")
                            elif confidence > 0.7:
                                st.info(f"ℹ️ {mouth_info} | {confidence_info}")
                            else:
                                st.warning(f"⚠️ {mouth_info} | {confidence_info}")
                        else:
                            st.error("❌ No face data for this frame")
                        
                        st.write("---")
                    
                    # Export options
                    st.subheader("📥 Export Processed Assets")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📁 Export Blank Frames", use_container_width=True):
                            export_blank_frames(blank_frames, character_name, action_name)
                    
                    with col2:
                        if st.button("📊 Export Tracking Data", use_container_width=True):
                            export_tracking_data(tracking_data, character_name, action_name)
                    
                    if st.button("📦 Export Complete Package", use_container_width=True, type="primary"):
                        export_complete_package(blank_frames, tracking_data, character_name, action_name)
                
                else:
                    st.error("❌ Failed to process video - no faces detected or processing error")
                    
            except Exception as e:
                st.error(f"❌ Processing failed: {e}")
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_video_path)
                except:
                    pass
    
    # Instructions
    st.divider()
    st.subheader("📝 How to Use Processed Assets")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Blank Frames:**
        - Upload to `Cartoon_Images/[character]/[direction]/[action]/`
        - Rename sequentially: `base_01.png`, `base_02.png`, etc.
        - These become your motion sequence for animation
        """)
    
    with col2:
        st.markdown("""
        **Tracking Data:**
        - Contains mouth/eye positions for each frame
        - Used for automated mouth placement
        - Enables eye blinking and gaze control
        - Perfect positioning without manual tracking dots!
        """)

def export_blank_frames(blank_frames, character_name, action_name):
    """Export blank frames as a ZIP file."""
    try:
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, frame in enumerate(blank_frames):
                # Save frame to bytes
                img_buffer = io.BytesIO()
                frame.save(img_buffer, format='PNG')
                img_bytes = img_buffer.getvalue()
                
                # Add to ZIP
                filename = f"base_{i+1:02d}.png"
                zip_file.writestr(filename, img_bytes)
        
        zip_data = zip_buffer.getvalue()
        
        st.download_button(
            label=f"📥 Download {len(blank_frames)} Blank Frames",
            data=zip_data,
            file_name=f"{character_name}_{action_name}_blank_frames.zip",
            mime="application/zip",
            use_container_width=True
        )
        
        st.success("✅ Blank frames package ready for download!")
        
    except Exception as e:
        st.error(f"Export failed: {e}")

def export_tracking_data(tracking_data, character_name, action_name):
    """Export tracking data as JSON."""
    try:
        import json
        
        # Convert tracking data to JSON-serializable format
        json_data = json.dumps(tracking_data, indent=2)
        
        st.download_button(
            label="📊 Download Tracking Data (JSON)",
            data=json_data,
            file_name=f"{character_name}_{action_name}_tracking.json",
            mime="application/json",
            use_container_width=True
        )
        
        st.success("✅ Tracking data ready for download!")
        
    except Exception as e:
        st.error(f"Export failed: {e}")

def export_complete_package(blank_frames, tracking_data, character_name, action_name):
    """Export both blank frames and tracking data as a complete package."""
    try:
        import json
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add blank frames
            for i, frame in enumerate(blank_frames):
                img_buffer = io.BytesIO()
                frame.save(img_buffer, format='PNG')
                img_bytes = img_buffer.getvalue()
                filename = f"frames/base_{i+1:02d}.png"
                zip_file.writestr(filename, img_bytes)
            
            # Add tracking data
            json_data = json.dumps(tracking_data, indent=2)
            zip_file.writestr("tracking_data.json", json_data)
            
            # Add README
            readme_content = f"""# AI Video Processing Results
            
Character: {character_name}
Action: {action_name}
Total Frames: {len(blank_frames)}

## Files:
- frames/base_XX.png: Blank canvas frames (mouth/eyes removed)
- tracking_data.json: Facial tracking data for animation

## Usage:
1. Upload frames to Cartoon_Images/{character_name}/[direction]/{action_name}/
2. Use tracking data for automated mouth/eye animation
3. Enjoy 100% automated facial animation!
"""
            zip_file.writestr("README.md", readme_content)
        
        zip_data = zip_buffer.getvalue()
        
        st.download_button(
            label=f"📦 Download Complete Package ({len(blank_frames)} frames + tracking data)",
            data=zip_data,
            file_name=f"{character_name}_{action_name}_complete.zip",
            mime="application/zip",
            use_container_width=True
        )
        
        st.success("🎉 Complete AI processing package ready!")
        
    except Exception as e:
        st.error(f"Export failed: {e}")