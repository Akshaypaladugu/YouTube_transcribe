# Import required libraries
import yt_dlp
import os
import io
import pandas as pd
from google.cloud import speech
from google.oauth2 import service_account
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydub import AudioSegment

# Function to download the audio of the YouTube video using yt-dlp
def download_youtube_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'movie_audio.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        audio_path = 'movie_audio.wav'
    return audio_path

# Function to split the audio into 30-second chunks and export as WAV (16000Hz, LINEAR16)
def split_audio_into_chunks(audio_path, chunk_duration=30):
    audio = AudioSegment.from_file(audio_path)
    chunks = []
    chunk_length_ms = chunk_duration * 1000  # Convert to milliseconds
    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunk_file = f"chunk_{i // chunk_length_ms}.wav"
        # Convert to 16000 Hz and export in LINEAR16 format
        chunk = chunk.set_frame_rate(16000).set_sample_width(2)
        chunk.export(chunk_file, format="wav")
        chunks.append(chunk_file)
    return chunks

# Function to transcribe audio using Google Speech-to-Text API
def transcribe_audio(file_path, language_code="te-IN"):
    credentials = service_account.Credentials.from_service_account_file('E:/new_data_project/service_account_key.json')
    client = speech.SpeechClient(credentials=credentials)
    
    with io.open(file_path, "rb") as audio_file:
        content = audio_file.read()
    
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code
    )

    response = client.recognize(config=config, audio=audio)
    
    transcription = ""
    for result in response.results:
        transcription += result.alternatives[0].transcript + " "
    
    return transcription.strip()

# Function to save transcription and chunk information to Google Drive
def save_to_drive(df, file_name):
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Authorizes locally
    drive = GoogleDrive(gauth)
    
    df.to_csv(file_name, index=False)

    # Create a file in Google Drive
    gfile = drive.CreateFile({'title': file_name})
    gfile.SetContentFile(file_name)
    gfile.Upload()
    print(f"File {file_name} uploaded to Google Drive successfully!")

# Main POC Function
def youtube_transcription_poc(youtube_url):
    # Step 1: Download the audio from the YouTube video
    audio_path = download_youtube_audio(youtube_url)

    # Step 2: Split the audio into 30-second chunks
    audio_chunks = split_audio_into_chunks(audio_path)

    # Step 3: Transcribe each chunk and store the results in a DataFrame
    data = {'Chunk Number': [], 'Transcription': []}
    
    for i, chunk in enumerate(audio_chunks):
        print(f"Transcribing chunk {i + 1}/{len(audio_chunks)}...")
        try:
            transcription = transcribe_audio(chunk)
            data['Chunk Number'].append(i + 1)
            data['Transcription'].append(transcription)
        except Exception as e:
            print(f"Error transcribing chunk {i+1}: {str(e)}")
            data['Chunk Number'].append(i + 1)
            data['Transcription'].append("Error in transcription")

    df = pd.DataFrame(data)

    # Step 4: Save DataFrame to Google Drive
    save_to_drive(df, "youtube_transcription.csv")

# Example usage
youtube_url = input("Enter YouTube video URL: ")
youtube_transcription_poc(youtube_url)
