import subprocess
import os
import re
import difflib
import pandas as pd
import argparse
import shutil
import csv
from config import *

def clean_title(title):
    """Cleanup title/filename: remove prefixes, suffixes, special chars"""
    title = re.sub(r'^y2mate\.com - ', '', title)
    title = re.sub(r'_\d+p.*$', '', title)
    title = re.sub(r'[\n\r]', '', title)  # Remove newlines
    return title.strip()

def clean_for_csv(text):
    """Clean text for CSV: remove problematic chars"""
    if isinstance(text, str):
        return re.sub(r'[\n\r]', '', text).strip()
    return text

def get_playlist_videos(url):
    """Get playlist metadata: return list of dicts {id, title, channel_id, uploader}"""
    if not url.startswith("https://www.youtube.com/playlist?list="):
        raise ValueError("Invalid playlist URL. Must start with 'https://www.youtube.com/playlist?list='")
    
    cmd = [
        'yt-dlp', '--cookies-from-browser', BROWSER,
        '--flat-playlist', '--print', '%(id)s\t%(title)s\t%(channel_id)s\t%(uploader)s',
        '--extractor-args', 'youtubetab:skip=authcheck', url
    ]
    for attempt in range(3):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=60)
            if result.returncode != 0:
                print(f"Attempt {attempt + 1} failed: {result.stderr}")
                continue
            
            videos = []
            for line in result.stdout.splitlines():
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        videos.append({
                            'video_id': parts[0],
                            'title': clean_for_csv(parts[1]),
                            'channel_id': clean_for_csv(parts[2]),
                            'uploader': clean_for_csv(parts[3])
                        })
            if not videos:
                print("Warning: No videos found in playlist.")
            return videos
        except subprocess.TimeoutExpired:
            print(f"Attempt {attempt + 1} timed out.")
        except Exception as e:
            print(f"Attempt {attempt + 1} error: {str(e)}")
    raise ValueError(f"Failed to get playlist after 3 attempts: {url}")

def init_archive():
    """Initialize archive.csv with fuzzy matching"""
    print("Initializing archive.csv...")
    
    try:
        remote_videos = get_playlist_videos(PLAYLIST_URL)
        remote_df = pd.DataFrame(remote_videos)
        remote_df['clean_title'] = remote_df['title'].apply(clean_title)
        
        local_files = []
        for root, _, files in os.walk(FINAL_DOWNLOAD_PATH):
            for file in files:
                if file.lower().endswith(VIDEO_EXTS):
                    full_path = os.path.join(root, file)
                    clean_local = clean_title(file)
                    folder_name = os.path.basename(root)
                    match = re.match(r'@(.+?)\s*\[(.+?)\]', folder_name)
                    inferred_channel_id = match.group(1) if match else ''
                    inferred_uploader = match.group(2) if match else ''
                    local_files.append({
                        'file_path': full_path,
                        'clean_title': clean_local,
                        'inferred_channel_id': inferred_channel_id,
                        'inferred_uploader': inferred_uploader
                    })
        
        local_df = pd.DataFrame(local_files)
        
        matched = []
        unmatched_remote = remote_df.copy()
        for _, local in local_df.iterrows():
            candidates = difflib.get_close_matches(local['clean_title'], remote_df['clean_title'], n=1, cutoff=MATCH_THRESHOLD)
            if candidates:
                match_title = candidates[0]
                remote_row = remote_df[remote_df['clean_title'] == match_title].iloc[0]
                matched.append({
                    'video_id': remote_row['video_id'],
                    'title': remote_row['title'],
                    'channel_id': remote_row['channel_id'] or local['inferred_channel_id'],
                    'uploader': remote_row['uploader'] or local['inferred_uploader'],
                    'download_date': pd.Timestamp.now().date(),
                    'file_path': local['file_path'],
                    'status': 'active',
                    'duplicate_of': '',
                    'tags': 'MMD' if 'MMD' in remote_row['title'] else '',
                    'notes': ''
                })
                unmatched_remote = unmatched_remote[unmatched_remote['clean_title'] != match_title]
        
        archive_df = pd.DataFrame(matched)
        archive_df = archive_df.apply(lambda x: x.apply(clean_for_csv))  # Clean all fields
        archive_df.to_csv(ARCHIVE_CSV, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)
        unmatched_remote.to_csv('unmatched_remote.csv', index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)
        
        # Print sample for verification
        print("\nSample archive.csv content:")
        print(archive_df.head().to_string())
        print(f"\nInitialized {len(matched)} matches. Check unmatched_remote.csv and edit {ARCHIVE_CSV} if needed.")
    except Exception as e:
        print(f"Initialization failed: {str(e)}")

def rename_files():
    """Rename existing files to include [video_id]"""
    print("Renaming existing files...")
    archive_df = pd.read_csv(ARCHIVE_CSV, encoding='utf-8-sig')
    
    for idx, row in archive_df.iterrows():
        old_path = row['file_path']
        if f"[{row['video_id']}]" not in old_path:
            folder = os.path.dirname(old_path)
            old_filename = os.path.basename(old_path)
            new_filename = re.sub(r'(\.mp4|\.mkv|\.webm)$', f' [{row["video_id"]}].\\1', old_filename, flags=re.IGNORECASE)
            new_path = os.path.join(folder, new_filename)
            try:
                os.rename(old_path, new_path)
                archive_df.at[idx, 'file_path'] = new_path
                print(f"Renamed: {old_path} -> {new_path}")
            except Exception as e:
                print(f"Error renaming {old_path}: {str(e)}")
    
    archive_df.to_csv(ARCHIVE_CSV, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)
    print("Rename complete.")

def sync_download():
    """Sync download: download new videos to temp, then move to final"""
    print("Syncing downloads...")
    
    if not os.path.exists(ARCHIVE_CSV):
        raise FileNotFoundError("Run init mode first!")
    archive_df = pd.read_csv(ARCHIVE_CSV, encoding='utf-8-sig')
    
    try:
        remote_videos = get_playlist_videos(PLAYLIST_URL)
        existing_ids = set(archive_df['video_id'])
        missing = [v for v in remote_videos if v['video_id'] not in existing_ids]
        
        if not missing:
            print("No new videos.")
            return
        
        os.makedirs(TEMP_DOWNLOAD_PATH, exist_ok=True)
        for video in missing:
            video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
            author_folder = f"@{video['channel_id']} [{video['uploader']}]"
            output_template = os.path.join(TEMP_DOWNLOAD_PATH, author_folder, '%(title)s [%(id)s].%(ext)s')
            
            # 构建下载命令 - 添加网络控制参数
            cmd = [
                'yt-dlp', '--cookies-from-browser', BROWSER,
                '-f', FORMAT,
                '--write-subs', '--no-write-auto-subs', '--sub-langs', SUB_LANGS,
                '--embed-thumbnail', '--add-metadata',
                '--limit-rate', LIMIT_RATE,  # 限速
                '--retries', str(RETRIES),  # 重试次数
                '--sleep-requests', str(RETRY_SLEEP),  # 请求间隔
                '--sleep-interval', str(RETRY_SLEEP),  # 下载间隔
                '--buffer-size', BUFFER_SIZE,  # 缓冲区大小
                '--concurrent-fragments', str(CONCURRENT_FRAGMENTS),  # 并发控制
                '--continue',  # 断点续传
                '--no-part',  # 不使用 .part 文件（避免残留）
                '-o', output_template,
                '--extractor-args', 'youtubetab:skip=authcheck',
                video_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                downloaded_files = [f for f in os.listdir(os.path.join(TEMP_DOWNLOAD_PATH, author_folder)) if f.endswith(VIDEO_EXTS)]
                if downloaded_files:
                    temp_path = os.path.join(TEMP_DOWNLOAD_PATH, author_folder, downloaded_files[0])
                    final_author_path = os.path.join(FINAL_DOWNLOAD_PATH, author_folder)
                    os.makedirs(final_author_path, exist_ok=True)
                    final_path = os.path.join(final_author_path, downloaded_files[0])
                    shutil.move(temp_path, final_path)
                    
                    new_row = {
                        'video_id': video['video_id'],
                        'title': clean_for_csv(video['title']),
                        'channel_id': clean_for_csv(video['channel_id']),
                        'uploader': clean_for_csv(video['uploader']),
                        'download_date': pd.Timestamp.now().date(),
                        'file_path': final_path,
                        'status': 'active',
                        'duplicate_of': '',
                        'tags': 'MMD' if 'MMD' in video['title'] else '',
                        'notes': ''
                    }
                    archive_df = pd.concat([archive_df, pd.DataFrame([new_row])], ignore_index=True)
                    archive_df.to_csv(ARCHIVE_CSV, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)
                    print(f"Downloaded and moved: {video['title']}")
            else:
                print(f"Error downloading {video['title']}: {result.stderr}")
    except Exception as e:
        print(f"Sync failed: {str(e)}")

def refresh_metadata():
    """Refresh metadata: check for deleted videos, update titles"""
    print("Refreshing metadata...")
    archive_df = pd.read_csv(ARCHIVE_CSV, encoding='utf-8-sig')
    
    for idx, row in archive_df.iterrows():
        video_url = f"https://www.youtube.com/watch?v={row['video_id']}"
        cmd = ['yt-dlp', '--cookies-from-browser', BROWSER, '--get-title', '--get-url', '--extractor-args', 'youtubetab:skip=authcheck', video_url]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0 or not result.stdout.strip():
            archive_df.at[idx, 'status'] = 'deleted'
        else:
            lines = result.stdout.splitlines()
            if lines:
                new_title = clean_for_csv(lines[0].strip())
                if new_title != row['title']:
                    archive_df.at[idx, 'title'] = new_title
                    archive_df.at[idx, 'notes'] += f" Title updated on {pd.Timestamp.now().date()}"
    
    archive_df.to_csv(ARCHIVE_CSV, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)
    print("Refresh complete.")

def generate_report():
    """Generate report: e.g., deleted videos"""
    archive_df = pd.read_csv(ARCHIVE_CSV, encoding='utf-8-sig')
    deleted = archive_df[archive_df['status'] == 'deleted']
    deleted.to_csv('deleted_videos.csv', index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)
    print(f"Generated deleted_videos.csv with {len(deleted)} entries.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['init', 'sync', 'refresh', 'report', 'rename'], required=True)
    parser.add_argument('--url', default=PLAYLIST_URL, help="Override playlist URL")
    args = parser.parse_args()
    
    PLAYLIST_URL = args.url
    
    if args.mode == 'init':
        init_archive()
    elif args.mode == 'sync':
        sync_download()
    elif args.mode == 'refresh':
        refresh_metadata()
    elif args.mode == 'report':
        generate_report()
    elif args.mode == 'rename':
        rename_files()