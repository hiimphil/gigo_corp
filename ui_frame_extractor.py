# ui_frame_extractor.py
import streamlit as st
import os
import tempfile
from moviepy.editor import VideoFileClip
from PIL import Image
import numpy as np
import zipfile
import io

def calculate_frame_hash(frame_array):
    """Calculate a simple hash for frame comparison."""
    # Resize to small size for faster comparison
    small_frame = Image.fromarray(frame_array).resize((32, 32))
    return hash(small_frame.tobytes())

def extract_and_analyze_frames(video_path, output_dir, frame_prefix="base"):
    """Extract ALL frames and calculate similarity scores for analysis."""
    try:
        with VideoFileClip(video_path) as video:
            duration = video.duration
            fps = video.fps
            total_frames = int(duration * fps)
            
            st.write(f"📹 Video info: {duration:.2f}s, {fps} FPS, {total_frames} frames")
            st.write("📊 Extracting all frames and analyzing similarities...")
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_frames = []
            similarity_scores = []
            
            # Step 1: Extract all frames
            for i in range(total_frames):
                frame_time = i / fps
                frame = video.get_frame(frame_time)
                
                # Convert to PIL Image and save
                frame_image = Image.fromarray(frame.astype('uint8'))
                frame_filename = f"{frame_prefix}_{i+1:03d}.png"  # Use 3-digit numbering for sorting
                frame_path = os.path.join(output_dir, frame_filename)
                
                frame_image.save(frame_path, "PNG")
                all_frames.append({
                    'path': frame_path,
                    'filename': frame_filename,
                    'frame_number': i + 1,
                    'time': frame_time,
                    'image_array': np.array(frame_image)
                })
                
                # Update progress
                progress = (i + 1) / total_frames
                progress_bar.progress(progress * 0.7)  # First 70% for extraction
                status_text.write(f"Extracting frame {i+1}/{total_frames}")
            
            # Step 2: Calculate similarity scores
            st.write("🧮 Calculating similarity scores between consecutive frames...")
            
            for i in range(1, len(all_frames)):
                # Compare current frame with previous frame
                prev_frame = all_frames[i-1]['image_array']
                curr_frame = all_frames[i]['image_array']
                
                # Resize for faster comparison
                prev_small = Image.fromarray(prev_frame).resize((32, 32))
                curr_small = Image.fromarray(curr_frame).resize((32, 32))
                
                prev_array = np.array(prev_small, dtype=float)
                curr_array = np.array(curr_small, dtype=float)
                
                # Calculate similarity
                diff = np.mean(np.abs(prev_array - curr_array)) / 255.0
                similarity = 1.0 - diff
                
                similarity_scores.append({
                    'frame_number': i + 1,
                    'similarity_to_previous': similarity,
                    'frame_data': all_frames[i]
                })
                
                # Update progress
                progress = 0.7 + (i / len(all_frames)) * 0.3  # Last 30% for similarity calculation
                progress_bar.progress(progress)
                status_text.write(f"Analyzing similarities {i}/{len(all_frames)-1}")
            
            progress_bar.empty()
            status_text.empty()
            
            # Calculate statistics
            similarities = [s['similarity_to_previous'] for s in similarity_scores]
            min_sim = min(similarities) if similarities else 0
            max_sim = max(similarities) if similarities else 0
            avg_sim = sum(similarities) / len(similarities) if similarities else 0
            
            st.success(f"✅ Analysis complete! {total_frames} frames extracted.")
            st.write(f"📈 Similarity range: {min_sim:.4f} to {max_sim:.4f} (avg: {avg_sim:.4f})")
            
            return {
                'all_frames': all_frames,
                'similarity_scores': similarity_scores,
                'stats': {
                    'total_frames': total_frames,
                    'min_similarity': min_sim,
                    'max_similarity': max_sim,
                    'avg_similarity': avg_sim
                }
            }, None
            
    except Exception as e:
        return None, f"Error extracting frames: {str(e)}"

def filter_frames_by_criteria(analysis_data, similarity_threshold=None, target_frame_count=None):
    """Filter frames based on similarity threshold or target count."""
    if not analysis_data:
        return [], {}
    
    all_frames = analysis_data['all_frames']
    similarity_scores = analysis_data['similarity_scores']
    
    # Always include the first frame
    filtered_frames = [all_frames[0]['path']]
    kept_frames_info = [{'frame_number': 1, 'similarity': 0.0, 'reason': 'First frame'}]
    
    if target_frame_count:
        # Sort by lowest similarity (most different from previous frame)
        sorted_scores = sorted(similarity_scores, key=lambda x: x['similarity_to_previous'])
        frames_to_keep = min(target_frame_count - 1, len(sorted_scores))  # -1 because we already have first frame
        
        selected_scores = sorted_scores[:frames_to_keep]
        # Sort back by frame number to maintain sequence
        selected_scores.sort(key=lambda x: x['frame_number'])
        
        for score_data in selected_scores:
            filtered_frames.append(score_data['frame_data']['path'])
            kept_frames_info.append({
                'frame_number': score_data['frame_number'],
                'similarity': score_data['similarity_to_previous'],
                'reason': f'Top {frames_to_keep} most different'
            })
    
    elif similarity_threshold is not None:
        # Keep frames below similarity threshold
        for score_data in similarity_scores:
            if score_data['similarity_to_previous'] < similarity_threshold:
                filtered_frames.append(score_data['frame_data']['path'])
                kept_frames_info.append({
                    'frame_number': score_data['frame_number'],
                    'similarity': score_data['similarity_to_previous'],
                    'reason': f'Below threshold {similarity_threshold:.4f}'
                })
    
    return filtered_frames, {
        'kept_count': len(filtered_frames),
        'total_count': len(all_frames),
        'frames_info': kept_frames_info
    }

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
        frame_prefix = st.text_input(
            "Frame filename prefix",
            value="base",
            help="Frames will be named: prefix_001.png, prefix_002.png, etc."
        )
        
        st.divider()
        
        # Step 1: Extract and Analyze
        if st.button("🎬 Extract & Analyze Video", use_container_width=True, type="primary"):
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                tmp_video.write(uploaded_file.getbuffer())
                temp_video_path = tmp_video.name
            
            # Create temporary directory for extracted frames
            temp_output_dir = tempfile.mkdtemp()
            
            try:
                # Extract and analyze all frames
                analysis_data, error = extract_and_analyze_frames(
                    temp_video_path, 
                    temp_output_dir, 
                    frame_prefix
                )
                
                if error:
                    st.error(f"❌ Extraction failed: {error}")
                else:
                    # Store analysis data in session state
                    st.session_state.frame_analysis = analysis_data
                    st.session_state.temp_frame_dir = temp_output_dir
                    st.session_state.frame_prefix = frame_prefix
                    st.rerun()
                
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                try:
                    os.unlink(temp_video_path)
                    import shutil
                    shutil.rmtree(temp_output_dir)
                except:
                    pass
        
        # Step 2: Filter and Download (show only if analysis is complete)
        if 'frame_analysis' in st.session_state and st.session_state.frame_analysis:
            st.divider()
            st.subheader("📊 Frame Analysis Results")
            
            analysis = st.session_state.frame_analysis
            stats = analysis['stats']
            
            # Show analysis stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Frames", stats['total_frames'])
            with col2:
                st.metric("Min Similarity", f"{stats['min_similarity']:.4f}")
            with col3:
                st.metric("Max Similarity", f"{stats['max_similarity']:.4f}")
            with col4:
                st.metric("Avg Similarity", f"{stats['avg_similarity']:.4f}")
            
            st.subheader("🎛️ Choose Filtering Method")
            
            filter_method = st.radio(
                "How would you like to filter frames?",
                ["Target frame count", "Similarity threshold"],
                help="Choose frames by count (easier) or by similarity score (more precise)"
            )
            
            col1, col2 = st.columns(2)
            
            if filter_method == "Target frame count":
                with col1:
                    target_count = st.slider(
                        "How many frames do you want?", 
                        2, min(50, stats['total_frames']), 
                        min(20, stats['total_frames'] // 5),
                        help="Pick the most different frames to keep motion variety"
                    )
                    
                    if st.button("📊 Preview Frame Selection", use_container_width=True):
                        filtered_frames, filter_info = filter_frames_by_criteria(
                            analysis, target_frame_count=target_count
                        )
                        st.session_state.filtered_frames = filtered_frames
                        st.session_state.filter_info = filter_info
                        st.rerun()
                        
            else:  # Similarity threshold
                with col1:
                    # Use actual data range for better slider
                    threshold = st.slider(
                        "Similarity threshold", 
                        stats['min_similarity'], stats['max_similarity'], 
                        stats['avg_similarity'], 0.0001,
                        help="Keep frames BELOW this similarity (lower = more frames kept)",
                        format="%.4f"
                    )
                    
                    if st.button("📊 Preview Frame Selection", use_container_width=True):
                        filtered_frames, filter_info = filter_frames_by_criteria(
                            analysis, similarity_threshold=threshold
                        )
                        st.session_state.filtered_frames = filtered_frames
                        st.session_state.filter_info = filter_info
                        st.rerun()
            
            # Show filtering results
            if 'filter_info' in st.session_state and st.session_state.filter_info:
                with col2:
                    filter_info = st.session_state.filter_info
                    st.write("**Filter Results:**")
                    st.metric("Frames Selected", f"{filter_info['kept_count']}/{filter_info['total_count']}")
                    
                    reduction = (1 - filter_info['kept_count'] / filter_info['total_count']) * 100
                    st.metric("Reduction", f"{reduction:.1f}%")
                
                # Show preview grid
                if 'filtered_frames' in st.session_state:
                    st.subheader("🖼️ Selected Frames Preview")
                    
                    preview_frames = st.session_state.filtered_frames[:12]  # Show first 12
                    cols = st.columns(4)
                    
                    for i, file_path in enumerate(preview_frames):
                        with cols[i % 4]:
                            st.image(file_path, caption=os.path.basename(file_path), width=150)
                    
                    if len(st.session_state.filtered_frames) > 12:
                        st.info(f"Showing 12 of {len(st.session_state.filtered_frames)} selected frames")
                    
                    # Download button
                    st.subheader("📥 Download Selected Frames")
                    
                    if st.button("📥 Create Download ZIP", use_container_width=True, type="primary"):
                        with st.spinner("Creating ZIP file..."):
                            zip_data = create_download_zip(st.session_state.filtered_frames)
                        
                        st.download_button(
                            label=f"📥 Download {len(st.session_state.filtered_frames)} Selected Frames",
                            data=zip_data,
                            file_name=f"{st.session_state.frame_prefix}_filtered_frames.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                        
                        st.success("✅ ZIP file ready for download!")
        
        # Instructions
        if 'frame_analysis' in st.session_state:
            st.divider()
            st.subheader("📝 Next Steps")
            st.markdown(f"""
            **To use these frames in your cartoon maker:**
            
            1. **Download** the filtered frames ZIP
            2. **Edit each frame** to:
               - Remove the mouth area (make it transparent or match background)
               - Add **green tracking dot** (left mouth corner)
               - Add **blue tracking dot** (right mouth corner)
            3. **Rename and upload** to your project at:
               ```
               Cartoon_Images/[character]/[direction]/[action]/
               ├── base_01.png
               ├── base_02.png
               └── ...
               ```
            4. **Test in cartoon maker** - the system will automatically detect and use the motion sequence!
            """)
    
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
        - **Duplicate removal** helps eliminate static sections
        """)
    
    with col2:
        st.markdown("""
        **Frame Editing Tips:**
        - Use image editor with layers (GIMP, Photoshop)
        - Make mouth area transparent
        - Keep tracking dots consistent across frames
        - Name files sequentially: base_01.png, base_02.png, etc.
        """)