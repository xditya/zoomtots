import os
import glob
import re
import random


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


def load_animation_frames(character="doraemon"):
    """Load all animation frames for a character."""
    # Map character names to their directory names
    character_dirs = {"doraemon": "doraemon", "chhota_bheem": "chhota_bheem"}

    character_dir = character_dirs.get(character, character)
    talk_folders = ["set1", "set2"]
    talk_folder = random.choice(talk_folders)

    # Load frames
    talk_frames = get_sorted_frames(
        os.path.join("images", character_dir, "talk", talk_folder), "talk-*.png"
    )
    left_walk_frames = get_sorted_frames(
        os.path.join("images", character_dir, "walk", "left"), "walk-*.png"
    )
    right_walk_frames = get_sorted_frames(
        os.path.join("images", character_dir, "walk", "right"), "walk-*.png"
    )

    if not talk_frames or not left_walk_frames or not right_walk_frames:
        raise FileNotFoundError(f"Missing animation frames for {character}")

    return {
        "talk_frames": talk_frames,
        "left_walk_frames": left_walk_frames,
        "right_walk_frames": right_walk_frames,
    }
