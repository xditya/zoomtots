import random
from moviepy import (
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
)
from .frame_utils import load_animation_frames
import os
import logging
import traceback
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_even_dimensions(width, height):
    """Ensure both width and height are even numbers."""
    if width % 2 != 0:
        width += 1
    if height % 2 != 0:
        height += 1
    return width, height


def generate_character_video(audio_path, output_path, character="doraemon"):
    """Generate video with character animations."""
    try:
        start_time = time.time()
        logger.info(f"Starting video generation for {character}")
        logger.info(f"Audio path: {audio_path}")
        logger.info(f"Output path: {output_path}")

        # Load audio and get duration
        logger.info("Loading audio file...")
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration
        logger.info(f"Audio duration: {audio_duration} seconds")

        # Calculate segments
        walk_segment_duration = 0.8  # Slower walking animation (0.8 seconds per frame)
        talk_segment_duration = 0.5  # Slower talking animation (0.5 seconds per frame)
        talk_repeats = 2  # Number of times to repeat each talk frame

        # Load animation frames
        logger.info("Loading animation frames...")
        frames = load_animation_frames(character)
        talk_frames = frames["talk_frames"]
        left_walk_frames = frames["left_walk_frames"]
        right_walk_frames = frames["right_walk_frames"]
        logger.info(
            f"Loaded {len(talk_frames)} talk frames, {len(left_walk_frames)} left walk frames, {len(right_walk_frames)} right walk frames"
        )

        # Verify frame paths exist
        for frame_list in [talk_frames, left_walk_frames, right_walk_frames]:
            for frame_path in frame_list:
                if not os.path.exists(frame_path):
                    raise FileNotFoundError(f"Frame not found: {frame_path}")

        # Pre-generate talk segments
        logger.info("Pre-generating talk segments...")
        talk_segments = []
        for i in range(len(talk_frames)):
            try:
                logger.info(f"Processing talk frame {i+1}/{len(talk_frames)}")
                character_clip = ImageClip(talk_frames[i])
                # Calculate new dimensions ensuring they're even
                new_width = int(character_clip.w * 0.3)
                new_height = int(character_clip.h * (new_width / character_clip.w))
                new_width, new_height = ensure_even_dimensions(new_width, new_height)
                character_clip = character_clip.resized((new_width, new_height))
                character_segment = character_clip.with_duration(talk_segment_duration)
                character_segment = character_segment.with_position(
                    ("center", "center")
                )
                talk_segments.append(character_segment)
            except Exception as e:
                logger.error(f"Error processing talk frame {i}: {str(e)}")
                logger.error(traceback.format_exc())
                raise

        # Pre-generate walk segments
        logger.info("Pre-generating walk segments...")
        left_walk_segments = []
        right_walk_segments = []

        for i in range(len(left_walk_frames)):
            try:
                logger.info(f"Processing left walk frame {i+1}/{len(left_walk_frames)}")
                character_clip = ImageClip(left_walk_frames[i])
                new_width = int(character_clip.w * 0.3)
                new_height = int(character_clip.h * (new_width / character_clip.w))
                new_width, new_height = ensure_even_dimensions(new_width, new_height)
                character_clip = character_clip.resized((new_width, new_height))
                character_segment = character_clip.with_duration(walk_segment_duration)
                character_segment = character_segment.with_position(
                    ("center", "center")
                )
                left_walk_segments.append(character_segment)
            except Exception as e:
                logger.error(f"Error processing left walk frame {i}: {str(e)}")
                logger.error(traceback.format_exc())
                raise

        for i in range(len(right_walk_frames)):
            try:
                logger.info(
                    f"Processing right walk frame {i+1}/{len(right_walk_frames)}"
                )
                character_clip = ImageClip(right_walk_frames[i])
                new_width = int(character_clip.w * 0.3)
                new_height = int(character_clip.h * (new_width / character_clip.w))
                new_width, new_height = ensure_even_dimensions(new_width, new_height)
                character_clip = character_clip.resized((new_width, new_height))
                character_segment = character_clip.with_duration(walk_segment_duration)
                character_segment = character_segment.with_position(
                    ("center", "center")
                )
                right_walk_segments.append(character_segment)
            except Exception as e:
                logger.error(f"Error processing right walk frame {i}: {str(e)}")
                logger.error(traceback.format_exc())
                raise

        # Generate video segments
        logger.info("Generating video sequence...")
        segments = []
        current_duration = 0
        walking_direction = 1  # 1 for right, -1 for left
        segment_count = 0

        while current_duration < audio_duration:
            segment_count += 1
            logger.info(
                f"Generating segment {segment_count} (current duration: {current_duration:.2f}s)"
            )

            # Randomly choose between walk and talk
            if random.random() < 0.5:  # 50% chance for walk
                logger.info("Adding walk segment...")
                # Use pre-generated walk segments
                walk_segments = (
                    right_walk_segments if walking_direction > 0 else left_walk_segments
                )
                segments.extend(walk_segments)
                current_duration += len(walk_segments) * walk_segment_duration
                walking_direction *= -1
            else:
                logger.info("Adding talk segment...")
                # Use pre-generated talk segments
                segments.extend(talk_segments)
                current_duration += len(talk_segments) * talk_segment_duration

            if current_duration >= audio_duration:
                break

        logger.info(f"Generated {len(segments)} segments")

        # Concatenate all segments
        logger.info("Concatenating video segments...")
        final_video = concatenate_videoclips(segments, method="compose")

        # Set audio
        logger.info("Adding audio to video...")
        final_video = final_video.with_audio(audio)

        # Write the final video with optimized settings
        logger.info("Writing final video file...")
        write_start_time = time.time()

        # Get video dimensions
        width, height = final_video.size
        logger.info(f"Video dimensions: {width}x{height}")

        # Ensure dimensions are even
        width, height = ensure_even_dimensions(width, height)
        if width != final_video.size[0] or height != final_video.size[1]:
            logger.info(f"Resizing video to even dimensions: {width}x{height}")
            final_video = final_video.resize((width, height))

        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            threads=4,
            preset="ultrafast",  # Changed from medium to ultrafast for faster encoding
            bitrate="2000k",  # Reduced bitrate for faster encoding
            audio_bitrate="128k",  # Reduced audio bitrate
            ffmpeg_params=[
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-profile:v",
                "baseline",
                "-level",
                "3.0",
                "-crf",
                "23",  # Added constant rate factor for better quality/size balance
                "-tune",
                "fastdecode",  # Optimize for fast decoding
                "-x264-params",
                "keyint=24:min-keyint=24:scenecut=0",  # Optimize keyframe placement
            ],
            logger=None,  # Disable moviepy's logger to avoid confusion
        )

        write_duration = time.time() - write_start_time
        logger.info(f"Video writing completed in {write_duration:.2f} seconds")
        logger.info(f"Total processing time: {time.time() - start_time:.2f} seconds")

        # Clean up
        audio.close()
        final_video.close()
        for segment in segments:
            segment.close()

        return True
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        logger.error(traceback.format_exc())
        # Clean up any partial files
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e
