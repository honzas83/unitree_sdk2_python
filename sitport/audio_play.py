import sys
import logging
import time
import os
import requests
from requests.auth import HTTPDigestAuth

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.core.channel import ChannelFactory
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from wav import read_wav_from_bytes, play_pcm_stream

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def synthesize_text(text):
    logger.info(f"Synthesizing text: {text}")
    url = "https://speechcloud.kky.zcu.cz:8887/tts/v4/synth"
    auth = HTTPDigestAuth("hackathon2025", "pheboa4zeesh4Kie")
    data = {
        "engine": "Oldrich30",
        "text": text,
        "format": "wav"
    }
    
    try:
        response = requests.post(url, auth=auth, data=data, verify=True)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

def main():
    interface = "en9"
    robot_ip = "192.168.123.164" 
    domain_id = 0 # Pro G1 potvrzeno Domain 0
    
    logger.info(f"Connecting to Audio service on {robot_ip} via {interface} (Domain {domain_id})")

    # Inicializace s Peers (využívá moji úpravu v unitree_sdk2py/core/channel.py)
    ChannelFactoryInitialize(domain_id, interface, peers=[robot_ip])
        
    # Wait for discovery to happen in the background
    logger.info("Waiting for DDS discovery (5s)...")
    time.sleep(5.0)

    logger.info("Initializing AudioClient...")
    audioClient = AudioClient()
    audioClient.SetTimeout(10.0)
    audioClient.Init()

    try:
        while True:
            try:
                text = input("\nZadejte text k vyslovení (nebo Ctrl+C pro ukončení): ")
                if not text.strip():
                    continue
            except EOFError:
                break

            wav_data = synthesize_text(text)
            
            if not wav_data:
                logger.error("Failed to synthesize text.")
                continue

            logger.info("Parsing synthesized WAV data...")
            pcm_list, sample_rate, num_channels, is_ok = read_wav_from_bytes(wav_data)
            
            if not is_ok:
                logger.error("Failed to parse synthesized WAV data.")
                continue

            logger.info(f"WAV Info - Sample rate: {sample_rate} Hz, Channels: {num_channels}, PCM bytes: {len(pcm_list)}")
            
            if sample_rate != 16000 or num_channels != 1:
                logger.error(f"Unsupported format: {sample_rate}Hz {num_channels}ch (must be 16kHz mono)")
                continue

            logger.info(f"Starting playback of {len(pcm_list)} bytes...")
            try:
                # 3200 bytes is 100ms of 16kHz 16-bit mono audio. 
                # Sending it every 0.1s should keep the buffer healthy.
                play_pcm_stream(audioClient, pcm_list, "example", chunk_size=3200, sleep_time=0.1, logger=logger)
                logger.info("Playback finished.")
            except Exception as e:
                logger.exception(f"Error during playback: {e}")
            finally:
                audioClient.PlayStop("example")

    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        logger.info("Audio client cleanup.")

if __name__ == "__main__":
    main()
