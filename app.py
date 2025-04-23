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
from functions.video_generation import generate_character_video
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


# Function to generate video with fading backgrounds and selected character
def generate_static_video(audio_path, output_path, character):
    if character in ["doraemon", "chhota_bheem", "chotta_bheem"]:
        generate_character_video(audio_path, output_path, character)
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
        print(f"Generated video ID: {video_id}")

        filename = secure_filename(file.filename)
        ppt_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(ppt_path)

        slides_text = extract_text_from_ppt(ppt_path)
        if not slides_text:
            return "No text extracted from PPT", 400

        if character == "doraemon":
            msg = "Hi, I'm Doraemon. Let's start the presentation!"
        elif character == "chhota_bheem":
            msg = "Hi, I'm Chhota Bheem. Let's start the presentation!"

        full_text = " ".join(slides_text)
        full_text = f"{msg} {full_text}"

        audio_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_audio.mp3")
        if not text_to_audio(full_text, audio_path, character):
            return "Failed to generate audio", 500

        video_path = os.path.join(VIDEO_OUTPUT_FOLDER, f"{video_id}.mp4")
        if character in ["doraemon", "chhota_bheem"]:
            try:
                generate_character_video(audio_path, video_path, character)
            except Exception as e:
                print(f"Video generation error: {str(e)}")
                return f"Error generating video: {str(e)}", 500
        else:
            return "Unsupported character", 400

        # Clean up the audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)

        # Return the full video URL
        video_url = url_for("video", video_id=video_id)
        return video_url
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return f"Error processing upload: {str(e)}", 500


if __name__ == "__main__":
    app.run(debug=True)
