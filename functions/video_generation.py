import random
from moviepy import (
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
)
from .frame_utils import load_animation_frames


def generate_doraemon_video(audio_path, output_path):
    """Generate video with Doraemon animations."""
    # Load audio and get duration
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration

    # Calculate segments
    walk_segment_duration = 0.8  # Slower walking animation (0.8 seconds per frame)
    talk_segment_duration = 0.5  # Slower talking animation (0.5 seconds per frame)
    talk_repeats = 2  # Number of times to repeat each talk frame

    # Load animation frames
    frames = load_animation_frames("doraemon")
    talk_frames = frames["talk_frames"]
    left_walk_frames = frames["left_walk_frames"]
    right_walk_frames = frames["right_walk_frames"]

    # Calculate segment durations
    walk_cycle_duration = len(left_walk_frames) * walk_segment_duration
    talk_cycle_duration = len(talk_frames) * talk_segment_duration * talk_repeats

    # Generate video segments
    segments = []
    current_duration = 0
    walking_direction = 1  # 1 for right, -1 for left

    while current_duration < audio_duration:
        # Randomly choose between walk and talk
        if random.random() < 0.5:  # 50% chance for walk
            # Walk cycle
            walk_frames = (
                right_walk_frames if walking_direction > 0 else left_walk_frames
            )
            for i in range(len(walk_frames)):
                character_clip = ImageClip(walk_frames[i])
                character_clip = character_clip.resized(width=character_clip.w * 0.3)
                character_segment = character_clip.with_duration(walk_segment_duration)
                character_segment = character_segment.with_position(
                    ("center", "center")
                )
                segments.append(character_segment)
                current_duration += walk_segment_duration
                if current_duration >= audio_duration:
                    break

            # Switch walking direction
            walking_direction *= -1
        else:
            # Talk cycle with repeats
            for _ in range(talk_repeats):
                for i in range(len(talk_frames)):
                    character_clip = ImageClip(talk_frames[i])
                    character_clip = character_clip.resized(
                        width=character_clip.w * 0.3
                    )
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
