import os
import sys
from mutagen import File
from mutagen.id3 import ID3, TPE1, TCON
from fuzzywuzzy import fuzz
import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class SoundCloudMetadataUpdater:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
        
        # Initialize the Chrome driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
    def __del__(self):
        """Cleanup the driver when the object is destroyed"""
        if hasattr(self, 'driver'):
            self.driver.quit()
        
    def get_playlist_tracks(self, playlist_url: str) -> List[Dict]:
        """Fetch all tracks from a SoundCloud playlist using Selenium."""
        try:
            print("Loading playlist page...")
            self.driver.get(playlist_url)
            
            # Wait for the track list to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'trackList__item')))
            
            # Scroll to bottom multiple times to ensure all tracks are loaded
            print("Scrolling to load all tracks...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                # Scroll down to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                time.sleep(2)
                
                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # If heights are the same, we've reached the bottom
                    break
                last_height = new_height
                print("Scrolling...")
            
            print("Finished scrolling, collecting tracks...")
            
            tracks = []
            track_elements = self.driver.find_elements(By.CLASS_NAME, 'trackList__item')
            
            print(f"Found {len(track_elements)} track elements")
            
            for element in track_elements:
                try:
                    # Get track title
                    title_elem = element.find_element(By.CLASS_NAME, 'trackItem__trackTitle')
                    # Get artist name
                    artist_elem = element.find_element(By.CLASS_NAME, 'trackItem__username')
                    # Get play count
                    try:
                        play_count_elem = element.find_element(By.CLASS_NAME, 'trackItem__playCount')
                        play_count = play_count_elem.text.strip()
                    except:
                        play_count = '0'
                    
                    track = {
                        'title': title_elem.text.strip(),
                        'user': {'username': artist_elem.text.strip()},
                        'genre': 'Unknown Genre',  # Genre is not available in the new structure
                        'play_count': play_count
                    }
                    tracks.append(track)
                    print(f"Found track: {track['title']} by {track['user']['username']}")
                    
                except Exception as e:
                    print(f"Warning: Could not parse track element: {str(e)}")
                    continue
            
            if not tracks:
                print("Warning: Could not find any tracks in the playlist. The page structure might have changed.")
                return []
                
            print(f"Successfully found {len(tracks)} tracks")
            return tracks
            
        except Exception as e:
            print(f"Error fetching playlist: {str(e)}")
            return []
        finally:
            # Clean up the driver
            self.driver.quit()
            # Create a new driver for next use
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=Options()
            )

    def find_best_match(self, filename: str, tracks: List[Dict]) -> Optional[Dict]:
        """Find the best matching track from SoundCloud using fuzzy matching."""
        # Clean filename for comparison
        clean_filename = os.path.splitext(os.path.basename(filename))[0].lower()
        
        best_match = None
        best_score = 0
        
        for track in tracks:
            track_title = track.get('title', '').lower()
            artist_name = track.get('user', {}).get('username', '').lower()
            
            # Try different matching strategies
            # 1. Direct title match
            title_score = fuzz.ratio(clean_filename, track_title)
            
            # 2. Title match with artist name removed from filename
            # Some filenames might include artist name like "Artist - Title"
            if ' - ' in clean_filename:
                filename_without_artist = clean_filename.split(' - ', 1)[1]
                title_score = max(title_score, fuzz.ratio(filename_without_artist, track_title))
            
            # 3. Partial ratio for better substring matching
            partial_score = fuzz.partial_ratio(clean_filename, track_title)
            
            # 4. Token sort ratio to handle word order differences
            token_score = fuzz.token_sort_ratio(clean_filename, track_title)
            
            # Get the best score from all matching strategies
            score = max(title_score, partial_score, token_score)
            
            # If the filename contains the artist name, boost the score
            if artist_name and artist_name in clean_filename:
                score += 10
            
            if score > best_score and score > 50:  # Lowered threshold to 50%
                best_score = score
                best_match = track
                print(f"Found potential match: {track_title} (Score: {score})")
        
        if best_match:
            print(f"Best match found: {best_match['title']} by {best_match['user']['username']} (Score: {best_score})")
        return best_match

    def update_file_metadata(self, file_path: str, artist: str, genre: str):
        """Update the metadata of an audio file."""
        try:
            # For MP3 files, use ID3 directly instead of File
            if file_path.lower().endswith('.mp3'):
                try:
                    # First try to load existing tags
                    audio = ID3(file_path)
                except:
                    # If no tags exist, create a new ID3 object
                    audio = ID3()
                
                # Set artist and genre tags
                audio.add(TPE1(encoding=3, text=[artist]))
                audio.add(TCON(encoding=3, text=[genre]))
                
                # Save to file
                audio.save(file_path)
                print(f"Updated metadata for: {file_path}")
                return
            
            # For other file formats, use the File approach
            audio = File(file_path)
            if audio is None:
                print(f"Could not read file: {file_path}")
                return
            
            # Handle other formats
            if hasattr(audio, 'tags'):  # M4A and other formats
                if audio.tags is None:
                    audio.add_tags()
                audio.tags['artist'] = artist
                audio.tags['genre'] = genre
                audio.save()
                print(f"Updated metadata for: {file_path}")
            else:
                print(f"Unsupported file format: {file_path}")
                
        except Exception as e:
            print(f"Error updating metadata for {file_path}: {str(e)}")
            print(f"Debug info - Artist: '{artist}', Genre: '{genre}'")  # Debug info

def main():
    updater = SoundCloudMetadataUpdater()
    
    # Get playlist URL from user
    playlist_url = input("Please enter the SoundCloud playlist URL: ")
    
    # Get music directory path
    music_dir = input("Please enter the path to your music directory: ")
    
    # Verify the directory exists
    if not os.path.exists(music_dir):
        print(f"Error: Directory '{music_dir}' does not exist")
        return
    
    # Fetch playlist tracks
    print("Fetching playlist tracks...")
    tracks = updater.get_playlist_tracks(playlist_url)
    if not tracks:
        print("No tracks found in playlist or error occurred")
        return
    
    print(f"Found {len(tracks)} tracks in the playlist")
    
    # Process each file in the directory
    print(f"\nScanning directory: {music_dir}")
    files_processed = 0
    files_updated = 0
    
    for root, _, files in os.walk(music_dir):
        for file in files:
            if file.lower().endswith(('.mp3', '.m4a', '.flac')):
                file_path = os.path.join(root, file)
                files_processed += 1
                print(f"\nProcessing file {files_processed}: {file}")
                
                try:
                    # Check if file can be read
                    audio = File(file_path)
                    if audio is None:
                        print(f"Could not read file: {file_path}")
                        continue
                    
                    # Find matching track
                    track = updater.find_best_match(file_path, tracks)
                    if track:
                        artist = track.get('user', {}).get('username', 'Unknown Artist')
                        genre = track.get('genre', 'Unknown Genre')
                        
                        # Update metadata
                        updater.update_file_metadata(file_path, artist, genre)
                        files_updated += 1
                    else:
                        print(f"No matching track found for: {file}")
                        
                except Exception as e:
                    print(f"Error processing file {file}: {str(e)}")
    
    print(f"\nProcessing complete!")
    print(f"Total files processed: {files_processed}")
    print(f"Files updated: {files_updated}")
    print(f"Files skipped: {files_processed - files_updated}")

if __name__ == "__main__":
    main() 