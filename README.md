YouTube Playlist Video Manager
This Python script automates downloading and managing videos from a YouTube playlist, tailored for private playlists with restricted videos. It downloads videos to a temporary SSD path, moves them to a final HDD path with author-based folder structure (e.g., @channel_id [uploader]), and maintains a metadata archive in archive.csv. Features include fuzzy matching for existing files, renaming old files to include video IDs, checking for deleted videos, and generating reports.
Features

Download New Videos: Syncs a YouTube playlist, downloading new videos (720p-1440p, video+audio, with subtitles in zh-CN, zh-, en-, ja).
Metadata Management: Stores video metadata (ID, title, channel_id, uploader, etc.) in archive.csv.
Fuzzy Matching: Initializes archive.csv by matching existing local files to playlist videos.
File Renaming: Optionally renames old files to include [video_id] for consistency.
Deleted Video Detection: Marks unavailable videos as "deleted" in archive.csv.
Author-Based Organization: Saves videos in folders like @channel_id [uploader], matching your existing structure (e.g., @user-wb4qi1rg8u [秋風だんご]).
Multi-Playlist Support: Override playlist URL via command-line argument.
Unicode Support: Handles Chinese, Japanese, and other non-ASCII characters correctly in archive.csv.

Prerequisites

Python 3.6+: Install from python.org.
yt-dlp: Install via pip install yt-dlp or download from GitHub.
pandas: Install via pip install pandas.
Microsoft Edge: Must be logged into YouTube with the account that has access to the private playlist.
Disk Setup: SSD (e.g., D:\Videos\temp_download) for temporary downloads, HDD (e.g., F:\Videos\youtube download\MMD) for final storage.

Installation

Clone or Download:
Save main.py and config.py to a directory (e.g., D:\myself manager).


Install Dependencies:pip install yt-dlp pandas


Update yt-dlp (recommended):yt-dlp -U


Verify Edge Login:
Open Edge, ensure you're logged into YouTube with the account that owns the private playlist.



Configuration
Edit config.py to match your setup:
# Playlist URL (private OK)
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLsNiJ5ulrY_FB-BWOCLmObaEtg51bu9i6"

# Browser for cookies
BROWSER = "edge"  # Use "edge:PROFILE_NAME" if specific profile needed

# Temporary download path (SSD)
TEMP_DOWNLOAD_PATH = "D:\\Videos\\temp_download"

# Final storage path (HDD)
FINAL_DOWNLOAD_PATH = "F:\\Videos\\youtube download\\MMD"

# Archive CSV path
ARCHIVE_CSV = "F:\\Videos\\youtube download\\archive.csv"

# Download format (720p-1440p, video+audio)
FORMAT = "bestvideo[height>=720][height<=1440]+bestaudio/best[height>=720][height<=1440]"

# Subtitle languages (priority: zh-CN > zh-* > en-* > ja)
SUB_LANGS = "zh-CN,zh-*,en-*,ja"

# Supported video extensions
VIDEO_EXTS = ('.mp4', '.mkv', '.webm')

# Fuzzy matching threshold (0-1, higher = stricter)
MATCH_THRESHOLD = 0.9


Ensure paths use double backslashes (\\) on Windows.
Update PLAYLIST_URL if you change playlists.
If Edge cookies fail, export cookies manually (see Troubleshooting).

Usage
Run commands from the script directory (e.g., D:\myself manager) using:
python main.py --mode MODE [--url PLAYLIST_URL]

Modes

init: Initialize archive.csv by matching existing local files to playlist videos.
python main.py --mode init


Generates archive.csv (metadata) and unmatched_remote.csv (unmatched videos).
Check and edit archive.csv in Excel/Notepad++ if matches are incorrect.
Columns: video_id, title, channel_id, uploader, download_date, file_path, status, duplicate_of, tags, notes.


sync: Download new videos to TEMP_DOWNLOAD_PATH, move to FINAL_DOWNLOAD_PATH, update archive.csv.
python main.py --mode sync


Downloads only videos not in archive.csv.
Creates author folders (e.g., @user-wb4qi1rg8u [秋風だんご]).
Files named like title [video_id].mp4.


rename: Rename existing files to include [video_id] (e.g., y2mate.com - title.mp4 -> y2mate.com - title [video_id].mp4).
python main.py --mode rename


Updates file_path in archive.csv.
Backup FINAL_DOWNLOAD_PATH before running.


refresh: Check for deleted videos and update titles in archive.csv.
python main.py --mode refresh


Marks unavailable videos as status=deleted.
Notes title changes in notes column.


report: Generate deleted_videos.csv for videos marked as deleted.
python main.py --mode report



Override Playlist URL
To use a different playlist:
python main.py --mode sync --url https://www.youtube.com/playlist?list=NEW_PLAYLIST_ID

Example Workflow

First Run:python main.py --mode init


Check archive.csv and unmatched_remote.csv.
Edit archive.csv if needed (e.g., add unmatched videos or mark duplicates in duplicate_of).


Rename Old Files (optional):python main.py --mode rename


Sync New Videos:python main.py --mode sync


Check for Updates/Deleted Videos:python main.py --mode refresh
python main.py --mode report



Troubleshooting

Cookie Errors:
If yt-dlp fails with authentication errors:
Verify Edge is logged into YouTube.
Test manually:yt-dlp --cookies-from-browser edge --flat-playlist --print id https://www.youtube.com/playlist?list=PLsNiJ5ulrY_FB-BWOCLmObaEtg51bu9i6


Manual cookie export:
Install Edge extension "Get cookies.txt".
Export cookies to D:\myself manager\cookies.txt.
Edit main.py, replace --cookies-from-browser edge with --cookies cookies.txt in get_playlist_videos and sync_download.






Chinese Character Issues:
If archive.csv shows garbled text in Excel, open in Notepad++ or import into Excel with UTF-8 encoding.


Network Errors (e.g., WinError 10054):
Retry after a few minutes.
Disable VPN/firewall temporarily.


Fuzzy Matching Issues:
If init mismatches files, adjust MATCH_THRESHOLD in config.py (e.g., lower to 0.8 for looser matching).



Notes

Backup: Always back up FINAL_DOWNLOAD_PATH before running rename or modifying files.
CSV Editing: Use Excel or a text editor to update archive.csv (e.g., add tags like "MMD", "艦これ", or mark duplicate_of for reuploaded videos).
Future Extensions:
Add GUI for easier CSV editing.
Schedule runs with Windows Task Scheduler.
Auto-detect reuploaded videos via title search.
Contact for additional features.



License
This script is for personal use. Ensure compliance with YouTube's Terms of Service when downloading videos.