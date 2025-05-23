# SoundCloud Metadata Updater

This script helps you update the metadata (artist and genre) of your music files by matching them with tracks from a SoundCloud playlist.

## Prerequisites

1. Python 3.6 or higher

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the script:
```bash
python soundcloud_metadata_updater.py
```

2. When prompted:
   - Enter the URL of the SoundCloud playlist containing the songs
   - Enter the path to your music directory

The script will:
- Scan your music directory for files without artist or genre metadata
- Match them with tracks from the SoundCloud playlist using fuzzy matching
- Update the metadata with the artist and genre information from SoundCloud

## Supported File Formats
- MP3
- M4A
- FLAC

## Notes
- The script uses fuzzy matching to find similar song names, with an 80% similarity threshold
- Only files missing either artist or genre metadata will be processed
- The script will print progress information and any errors encountered
- The script uses web scraping to get track information from SoundCloud #   s o u n d c l o u d _ m e t a d a t a _ c r a w l e r - u p d a t e r  
 