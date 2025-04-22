from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from pptx import Presentation
from gtts import gTTS
import os
from moviepy import (
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
import random
import math
import glob
import re
import uuid
from functions.text_to_speech import text_to_audio
from functions.extract_text_from_ppt import extract_text_from_ppt
from functions.video_generation import generate_doraemon_video
import time
from pydub import AudioSegment

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"
VIDEO_OUTPUT_FOLDER = os.path.join(STATIC_FOLDER, "videos")
BACKGROUND_FOLDER = os.path.join(STATIC_FOLDER, "backgrounds")
TEMP_FOLDER = os.path.join(STATIC_FOLDER, "temp")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIDEO_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(BACKGROUND_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)


# Function to extract text from PPT
def extract_text_from_ppt(ppt_file_path):
    try:
        prs = Presentation(ppt_file_path)
        slides_text = []
        for slide in prs.slides:
            text = ""
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + " "
            if text.strip():
                slides_text.append(text.strip())
        return slides_text
    except Exception as e:
        print(f"Error processing PPT: {e}")
        return []


# Function to convert text to audio
def text_to_audio(text, output_filename, lang="en"):
    try:
        # Split text into smaller chunks to avoid connection timeouts
        max_chunk_length = 500  # Maximum characters per chunk
        chunks = [
            text[i : i + max_chunk_length]
            for i in range(0, len(text), max_chunk_length)
        ]

        # Create a temporary directory for audio chunks
        temp_dir = os.path.join(TEMP_FOLDER, "audio_chunks")
        os.makedirs(temp_dir, exist_ok=True)

        chunk_files = []

        # Process each chunk
        for i, chunk in enumerate(chunks):
            chunk_file = os.path.join(temp_dir, f"chunk_{i}.mp3")
            chunk_files.append(chunk_file)

            # Try up to 3 times for each chunk
            for attempt in range(3):
                try:
                    tts = gTTS(text=chunk, lang=lang, slow=False)
                    tts.save(chunk_file)
                    print(f"Successfully generated audio chunk {i+1}/{len(chunks)}")
                    break
                except Exception as e:
                    print(f"Attempt {attempt+1} failed for chunk {i+1}: {str(e)}")
                    if attempt == 2:  # Last attempt
                        raise Exception(
                            f"Failed to generate audio after 3 attempts: {str(e)}"
                        )
                    time.sleep(1)  # Wait before retrying

        # If there's only one chunk, just rename it
        if len(chunk_files) == 1:
            os.rename(chunk_files[0], output_filename)
        else:
            # Combine all chunks
            combined = AudioSegment.empty()
            for chunk_file in chunk_files:
                segment = AudioSegment.from_mp3(chunk_file)
                combined += segment

            # Export the combined audio
            combined.export(output_filename, format="mp3")

        # Clean up temporary files
        for chunk_file in chunk_files:
            if os.path.exists(chunk_file):
                os.remove(chunk_file)

        return output_filename
    except Exception as e:
        print(f"Error in text_to_audio: {str(e)}")
        # If the output file exists but is incomplete, remove it
        if os.path.exists(output_filename):
            os.remove(output_filename)
        raise Exception(f"Failed to generate audio: {str(e)}")


def get_sorted_frames(folder_path, pattern):
    """Get sorted frames from a folder based on the pattern."""
    frames = []
    for file in glob.glob(os.path.join(folder_path, pattern)):
        # Extract number from filename
        match = re.search(r"(\d+)\.(png|jpg)$", file)
        if match:
            frames.append((int(match.group(1)), file))
    # Sort by frame number
    return [frame[1] for frame in sorted(frames, key=lambda x: x[0])]


def generate_doraemon_video(audio_path, output_path):
    """Generate video with Doraemon animations."""
    try:
        # Load audio and get duration
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration

        # Calculate segments
        walk_segment_duration = 0.8  # Slower walking animation (0.8 seconds per frame)
        talk_segment_duration = 0.5  # Slower talking animation (0.5 seconds per frame)
        talk_repeats = 2  # Number of times to repeat each talk frame

        # Load animation frames
        talk_folders = ["set1", "set2"]
        talk_folder = random.choice(talk_folders)
        talk_frames = get_sorted_frames(
            os.path.join("images", "doraemon", "talk", talk_folder), "talk-*.png"
        )
        left_walk_frames = get_sorted_frames(
            os.path.join("images", "doraemon", "walk", "left"), "walk-*.png"
        )
        right_walk_frames = get_sorted_frames(
            os.path.join("images", "doraemon", "walk", "right"), "walk-*.png"
        )

        if not talk_frames or not left_walk_frames or not right_walk_frames:
            raise FileNotFoundError("Missing animation frames")

        # Calculate segment durations
        walk_cycle_duration = len(left_walk_frames) * walk_segment_duration
        talk_cycle_duration = len(talk_frames) * talk_segment_duration * talk_repeats

        # Generate video segments
        segments = []
        current_duration = 0

        # Function to ensure dimensions are even
        def resize_with_even_dimensions(clip, scale_factor=0.3):
            # Calculate new width
            new_width = int(clip.w * scale_factor)
            # Make sure width is even
            if new_width % 2 != 0:
                new_width += 1
            # Calculate height to maintain aspect ratio
            new_height = int(clip.h * (new_width / clip.w))
            # Make sure height is even
            if new_height % 2 != 0:
                new_height += 1
            return clip.resized((new_width, new_height))

        # First, add a single walk cycle (from right to left)
        walk_duration = min(
            walk_cycle_duration, audio_duration * 0.2
        )  # Walk for 20% of audio duration
        walk_frames = left_walk_frames  # Walk from right to left

        for i in range(len(walk_frames)):
            character_clip = ImageClip(walk_frames[i])
            character_clip = resize_with_even_dimensions(character_clip)
            character_segment = character_clip.with_duration(walk_segment_duration)
            character_segment = character_segment.with_position(("center", "center"))
            segments.append(character_segment)
            current_duration += walk_segment_duration
            if current_duration >= walk_duration:
                break

        # Then add talking segments for the rest of the video
        while current_duration < audio_duration:
            # Talk cycle with repeats
            for _ in range(talk_repeats):
                for i in range(len(talk_frames)):
                    character_clip = ImageClip(talk_frames[i])
                    character_clip = resize_with_even_dimensions(character_clip)
                    character_segment = character_clip.with_duration(
                        talk_segment_duration
                    )
                    character_segment = character_segment.with_position(
                        ("center", "center")
                    )
                    segments.append(character_segment)
                    current_duration += talk_segment_duration
                    if current_duration >= audio_duration:
                        break
                if current_duration >= audio_duration:
                    break

        # Concatenate all segments
        final_video = concatenate_videoclips(segments, method="compose")

        # Set audio
        final_video = final_video.with_audio(audio)

        # Write the final video with specific settings
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            threads=4,
            preset="medium",
            bitrate="5000k",
            audio_bitrate="192k",
            ffmpeg_params=[
                "-pix_fmt",
                "yuv420p",  # Ensure compatibility
                "-movflags",
                "+faststart",  # Enable fast start
                "-profile:v",
                "baseline",  # Use baseline profile
                "-level",
                "3.0",  # Set compatibility level
            ],
        )

        # Clean up
        audio.close()
        final_video.close()
        for segment in segments:
            segment.close()

        return True
    except Exception as e:
        print(f"Error generating video: {str(e)}")
        # Clean up any partial files
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e


# Function to generate video with fading backgrounds and selected character
def generate_static_video(audio_path, output_path, character):
    if character == "doraemon":
        generate_doraemon_video(audio_path, output_path)
    else:
        # Original static video generation code
        image_path = os.path.join(STATIC_FOLDER, "img", f"{character}.png")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Character image not found at {image_path}")
        print(f"Using character image: {image_path}")

        # List background images
        background_files = [
            f for f in os.listdir(BACKGROUND_FOLDER) if f.endswith((".jpg", ".png"))
        ]
        if not background_files:
            raise FileNotFoundError(
                f"No background images found in {BACKGROUND_FOLDER}"
            )
        print(f"Found {len(background_files)} background images: {background_files}")

        # Load audio and get duration
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration
        bg_change_duration = 5  # Change background every 5 seconds
        num_bg_segments = math.ceil(audio_duration / bg_change_duration)
        print(f"Audio duration: {audio_duration}s, Segments: {num_bg_segments}")

        # Load character image
        character_clip = ImageClip(image_path)
        character_clip = character_clip.resized(
            width=character_clip.w * 0.75
        )  # Scale down to 75%

        # Generate video segments
        segments = []
        for i in range(num_bg_segments):
            start_time = i * bg_change_duration
            duration = min(bg_change_duration, audio_duration - start_time)
            if duration <= 0:
                break

            # Select background
            bg_file = random.choice(background_files)
            bg_path = os.path.join(BACKGROUND_FOLDER, bg_file)
            bg_clip = ImageClip(bg_path).with_duration(duration)

            # Position character in center
            character_segment = character_clip.with_duration(duration)
            character_segment = character_segment.with_position(("center", "center"))

            # Create composite clip
            composite = CompositeVideoClip([bg_clip, character_segment])

            # Add fade effects
            if i > 0 and i < num_bg_segments - 1:
                composite = composite.crossfadein(1).crossfadeout(1)
            elif i > 0:
                composite = composite.crossfadein(1)
            elif i < num_bg_segments - 1:
                composite = composite.crossfadeout(1)

            segments.append(composite)

        # Concatenate all segments
        final_video = concatenate_videoclips(segments, method="compose")

        # Set audio
        final_video = final_video.with_audio(audio)

        # Write the final video
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            threads=4,
            preset="medium",
        )

        # Clean up
        audio.close()
        final_video.close()
        for segment in segments:
            segment.close()


# Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html", dashboard_url=url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/upload_selection")
def upload_selection():
    return render_template("upload_selection.html")


@app.route("/logout")
def logout():
    return redirect(url_for("index"))


@app.route("/video/<video_id>")
def video(video_id):
    # Check if the video file exists
    video_path = os.path.join(VIDEO_OUTPUT_FOLDER, f"{video_id}.mp4")
    if not os.path.exists(video_path):
        return "Video not found", 404
    return render_template("video.html", video_id=video_id)


@app.route("/video_file/<video_id>")
def video_file(video_id):
    video_path = os.path.join(VIDEO_OUTPUT_FOLDER, f"{video_id}.mp4")
    if not os.path.exists(video_path):
        return "Video not found", 404
    return send_file(
        video_path, mimetype="video/mp4", as_attachment=False, conditional=True
    )


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return "No file part in request", 400
        file = request.files["file"]
        if file.filename == "":
            return "No file selected", 400
        if not file.filename.endswith(".pptx"):
            return "Invalid file format. Please upload a .pptx file", 400

        character = request.form.get("character")
        if not character:
            return "No character selected", 400

        # Generate unique video ID
        video_id = str(uuid.uuid4())

        filename = secure_filename(file.filename)
        ppt_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(ppt_path)

        slides_text = extract_text_from_ppt(ppt_path)
        if not slides_text:
            return "No text extracted from PPT", 400
        full_text = " ".join(slides_text)

        audio_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_audio.mp3")
        if not text_to_audio(full_text, audio_path):
            return "Failed to generate audio", 500

        video_path = os.path.join(VIDEO_OUTPUT_FOLDER, f"{video_id}.mp4")
        if character == "doraemon":
            generate_doraemon_video(audio_path, video_path)
        else:
            return "Unsupported character", 400

        # Clean up the audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)

        # Return just the video ID
        return video_id
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return f"Error processing upload: {str(e)}", 500


if __name__ == "__main__":
    app.run(debug=True)
