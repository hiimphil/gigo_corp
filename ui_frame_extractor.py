# ui_frame_extractor.py
import streamlit as st
import os
import tempfile
from moviepy.editor import VideoFileClip
from PIL import Image
import numpy as np
import zipfile
import io

def extract_frames_from_video(video_path, output_dir, frame_prefix="base"):
    """Extract all frames from video and save as PNG files."""
    try:
        with VideoFileClip(video_path) as video:
            duration = video.duration
            fps = video.fps
            total_frames = int(duration * fps)
            
            st.write(f"📹 Video info: {duration:.2f}s, {fps} FPS, {total_frames} frames")
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            extracted_files = []
            
            for i in range(total_frames):
                frame_time = i / fps
                frame = video.get_frame(frame_time)
                
                # Convert to PIL Image
                frame_image = Image.fromarray(frame.astype('uint8'))
                
                # Generate filename with zero-padded numbers
                frame_filename = f"{frame_prefix}_{i+1:02d}.png"
                frame_path = os.path.join(output_dir, frame_filename)
                
                # Save frame
                frame_image.save(frame_path, "PNG")
                extracted_files.append(frame_path)
                
                # Update progress
                progress = (i + 1) / total_frames
                progress_bar.progress(progress)
                status_text.write(f"Extracting frame {i+1}/{total_frames}: {frame_filename}")
            
            progress_bar.empty()
            status_text.empty()
            
            return extracted_files, None
            
    except Exception as e:
        return None, f"Error extracting frames: {str(e)}"

def create_download_zip(file_paths):
    """Create a ZIP file containing all extracted frames."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            zip_file.write(file_path, filename)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def display():
    """Main UI for the frame extractor."""
    st.header("🎬 Video Frame Extractor")
    st.subheader("Convert video files to individual PNG frames for cartoon animation")
    
    st.markdown("""
    **Perfect for preparing AI-generated motion videos for the cartoon maker!**
    
    **Workflow:**
    1. Upload a short video (MP4) with character motion
    2. Extract all frames as numbered PNG files
    3. Download the frames
    4. Edit frames to remove mouths and add tracking dots
    5. Upload to your `Cartoon_Images` folder as motion sequences
    """)
    
    st.divider()
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=['mp4', 'mov', 'avi', 'mkv'],
        help="Upload a short video file (preferably 2-10 seconds for best results)"
    )
    
    if uploaded_file is not None:
        # Display video info
        st.success(f"✅ Uploaded: {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.1f} MB)")
        
        # Show video preview
        st.video(uploaded_file)
        
        # Configuration options
        col1, col2 = st.columns(2)
        
        with col1:
            frame_prefix = st.text_input(
                "Frame filename prefix",
                value="base",
                help="Frames will be named: prefix_01.png, prefix_02.png, etc."
            )
        
        with col2:
            st.write("**Preview Settings:**")
            show_preview = st.checkbox("Show frame previews", value=True)
            max_preview_frames = st.slider("Max preview frames", 1, 20, 6)
        
        st.divider()
        
        # Extract frames button
        if st.button("🎬 Extract Frames", use_container_width=True, type="primary"):
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                tmp_video.write(uploaded_file.getbuffer())
                temp_video_path = tmp_video.name
            
            # Create temporary directory for extracted frames
            temp_output_dir = tempfile.mkdtemp()
            
            try:
                # Extract frames
                with st.spinner("Extracting frames from video..."):
                    extracted_files, error = extract_frames_from_video(
                        temp_video_path, 
                        temp_output_dir, 
                        frame_prefix
                    )
                
                if error:
                    st.error(f"❌ Extraction failed: {error}")
                else:
                    st.success(f"✅ Successfully extracted {len(extracted_files)} frames!")
                    
                    # Show preview grid
                    if show_preview and extracted_files:
                        st.subheader("🖼️ Frame Preview")
                        
                        # Show subset of frames for preview
                        preview_files = extracted_files[:max_preview_frames]
                        cols = st.columns(min(len(preview_files), 4))
                        
                        for i, file_path in enumerate(preview_files):
                            with cols[i % len(cols)]:
                                st.image(file_path, caption=os.path.basename(file_path), width=150)
                        
                        if len(extracted_files) > max_preview_frames:
                            st.info(f"Showing {max_preview_frames} of {len(extracted_files)} frames")
                    
                    # Create download
                    st.subheader("📥 Download Frames")
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        with st.spinner("Creating ZIP file..."):
                            zip_data = create_download_zip(extracted_files)
                        
                        st.download_button(
                            label=f"📥 Download All Frames ({len(extracted_files)} files)",
                            data=zip_data,
                            file_name=f"{frame_prefix}_frames.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                    
                    with col2:
                        st.metric("Total Frames", len(extracted_files))
                        st.metric("ZIP Size", f"{len(zip_data) / 1024 / 1024:.1f} MB")
                    
                    # Instructions
                    st.subheader("📝 Next Steps")
                    st.markdown(f"""
                    **To use these frames in your cartoon maker:**
                    
                    1. **Download and extract** the ZIP file
                    2. **Edit each frame** to:
                       - Remove the mouth area (make it transparent or match background)
                       - Add **green tracking dot** (left mouth corner)
                       - Add **blue tracking dot** (right mouth corner)
                    3. **Upload to your project** at:
                       ```
                       Cartoon_Images/[character]/[direction]/[action]/
                       ├── {frame_prefix}_01.png
                       ├── {frame_prefix}_02.png
                       └── ...
                       ```
                    4. **Test in cartoon maker** - the system will automatically detect and use the motion sequence!
                    """)
                
            finally:
                # Clean up temporary files
                try:
                    os.unlink(temp_video_path)
                    import shutil
                    shutil.rmtree(temp_output_dir)
                except:
                    pass
    
    # Additional help
    st.divider()
    st.subheader("💡 Tips & Best Practices")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Video Guidelines:**
        - Keep videos short (2-10 seconds)
        - Use consistent character positioning
        - Ensure mouth area is clearly visible
        - Higher FPS = more frames = smoother motion
        """)
    
    with col2:
        st.markdown("""
        **Frame Editing Tips:**
        - Use image editor with layers (GIMP, Photoshop)
        - Make mouth area transparent
        - Keep tracking dots consistent across frames
        - Name files sequentially: base_01.png, base_02.png, etc.
        """)