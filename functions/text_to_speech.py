import os
from elevenlabs import generate, save, set_api_key, voices
from decouple import config

ELEVENLABS_API_KEY = config("ELEVENLABS_API")

if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY not found in environment variables")

# Set API key
set_api_key(ELEVENLABS_API_KEY)


def text_to_audio(text, output_path, character):
    """
    Convert text to speech using ElevenLabs API and save to file.

    Args:
        text (str): Text to convert to speech
        output_path (str): Path to save the audio file

    Returns:
        bool: True if successful, False otherwise
    """
    if character == "doraemon":
        voice = "Laura"
    elif character == "chhota_bheem":
        voice = "Callum"
    try:
        # Generate audio using ElevenLabs
        audio = generate(
            text=text,
            voice=voice,
            model="eleven_monolingual_v1",
        )

        # Save the audio file
        save(audio, output_path)
        return True
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return False
