import subprocess
import os
import re
import difflib
import pandas as pd
import argparse
import shutil
from config import *

def clean_title(title):
    """清理标题/文件名：去前缀、后缀、特殊符"""
    title = re.sub(r'^y2mate\.com - ', '', title)  # 去y2mate前缀
    title = re.sub(r'_\d+p.*$', '', title)  # 去分辨率后缀如_1080pFHR
    title = re.sub(r'[^\w\s]', '', title)  # 去特殊符
    return title.strip().lower()

def get_playlist_videos(url):
    """获取播放列表元数据：返回list of dicts {id, title, channel_id, uploader}"""
    cmd = [
        'yt-dlp', '--cookies-from-browser', BROWSER,
        '--flat-playlist', '--print', '%(id)s\t%(title)s\t%(channel_id)s\t%(uploader)s', url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(f"Error getting playlist: {result.stderr}")
    
    videos = []
    for line in result.stdout.splitlines():
        if line.strip():
            parts = line.split('\t')
            if len(parts) == 4:
                videos.append({
                    'video_id': parts[0],
                    'title': parts[1],
                    'channel_id': parts[2],
                    'uploader': parts[3]
                })
    return videos

def init_archive():
    """初始化模式：半自动化生成archive.csv"""
    print("Initializing archive.csv...")
    
    # 获取远程视频
    remote_videos = get_playlist_videos(PLAYLIST_URL)
    remote_df = pd.DataFrame(remote_videos)
    remote_df['clean_title'] = remote_df['title'].apply(clean_title)
    
    # 扫描本地文件
    local_files = []
    for root, _, files in os.walk(FINAL_DOWNLOAD_PATH):
        for file in files:
            if file.lower().endswith(VIDEO_EXTS):
                full_path = os.path.join(root, file)
                clean_local = clean_title(file)
                # 尝试从文件夹名推断channel_id和uploader
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
    
    # 模糊匹配
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
                'tags': '',
                'notes': ''
            })
            unmatched_remote = unmatched_remote[unmatched_remote['clean_title'] != match_title]
    
    # 保存matched到CSV
    archive_df = pd.DataFrame(matched)
    archive_df.to_csv(ARCHIVE_CSV, index=False)
    
    # 未匹配报告
    unmatched_remote.to_csv('unmatched_remote.csv', index=False)
    print(f"Initialized {len(matched)} matches. Check unmatched_remote.csv and edit {ARCHIVE_CSV} manually if needed.")

def sync_download():
    """同步下载：下载新视频到temp，然后转移到final"""
    print("Syncing downloads...")
    
    # 加载CSV
    if not os.path.exists(ARCHIVE_CSV):
        raise FileNotFoundError("Run init mode first!")
    archive_df = pd.read_csv(ARCHIVE_CSV)
    
    # 获取当前远程视频
    remote_videos = get_playlist_videos(PLAYLIST_URL)
    
    # 找出缺失的（不在CSV的video_id）
    existing_ids = set(archive_df['video_id'])
    missing = [v for v in remote_videos if v['video_id'] not in existing_ids]
    
    if not missing:
        print("No new videos.")
        return
    
    # 下载到temp
    os.makedirs(TEMP_DOWNLOAD_PATH, exist_ok=True)
    for video in missing:
        video_url = f"https://www.youtube.com/watch?v={video['video_id']}"
        author_folder = f"@{video['channel_id']} [{video['uploader']}]"
        output_template = os.path.join(TEMP_DOWNLOAD_PATH, author_folder, '%(title)s [%(id)s].%(ext)s')
        
        cmd = [
            'yt-dlp', '--cookies-from-browser', BROWSER,
            '-f', FORMAT,
            '--write-subs', '--no-write-auto-subs', '--sub-langs', SUB_LANGS,
            '--embed-thumbnail', '--add-metadata',
            '-o', output_template,
            video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            # 找下载的文件（假设单文件）
            downloaded_files = [f for f in os.listdir(os.path.join(TEMP_DOWNLOAD_PATH, author_folder)) if f.endswith(VIDEO_EXTS)]
            if downloaded_files:
                temp_path = os.path.join(TEMP_DOWNLOAD_PATH, author_folder, downloaded_files[0])
                # 转移到final
                final_author_path = os.path.join(FINAL_DOWNLOAD_PATH, author_folder)
                os.makedirs(final_author_path, exist_ok=True)
                final_path = os.path.join(final_author_path, downloaded_files[0])
                shutil.move(temp_path, final_path)
                
                # 添加到CSV
                new_row = {
                    'video_id': video['video_id'],
                    'title': video['title'],
                    'channel_id': video['channel_id'],
                    'uploader': video['uploader'],
                    'download_date': pd.Timestamp.now().date(),
                    'file_path': final_path,
                    'status': 'active',
                    'duplicate_of': '',
                    'tags': '',
                    'notes': ''
                }
                archive_df = pd.concat([archive_df, pd.DataFrame([new_row])], ignore_index=True)
                archive_df.to_csv(ARCHIVE_CSV, index=False)
                print(f"Downloaded and moved: {video['title']}")
        else:
            print(f"Error downloading {video['title']}: {result.stderr}")

def refresh_metadata():
    """刷新元数据：检查删除，更新标题等"""
    print("Refreshing metadata...")
    archive_df = pd.read_csv(ARCHIVE_CSV)
    
    for idx, row in archive_df.iterrows():
        video_url = f"https://www.youtube.com/watch?v={row['video_id']}"
        cmd = ['yt-dlp', '--cookies-from-browser', BROWSER, '--get-title', '--get-url', video_url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout.strip():
            archive_df.at[idx, 'status'] = 'deleted'
        else:
            lines = result.stdout.splitlines()
            if lines:
                new_title = lines[0].strip()
                if new_title != row['title']:
                    archive_df.at[idx, 'title'] = new_title
                    archive_df.at[idx, 'notes'] += f" Title updated on {pd.Timestamp.now().date()}"
    
    archive_df.to_csv(ARCHIVE_CSV, index=False)
    print("Refresh complete.")

def generate_report():
    """生成报告：e.g., deleted videos"""
    archive_df = pd.read_csv(ARCHIVE_CSV)
    deleted = archive_df[archive_df['status'] == 'deleted']
    deleted.to_csv('deleted_videos.csv', index=False)
    print(f"Generated deleted_videos.csv with {len(deleted)} entries.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['init', 'sync', 'refresh', 'report'], required=True)
    parser.add_argument('--url', default=PLAYLIST_URL, help="Override playlist URL")
    args = parser.parse_args()
    
    PLAYLIST_URL = args.url  # 允许动态URL
    
    if args.mode == 'init':
        init_archive()
    elif args.mode == 'sync':
        sync_download()
    elif args.mode == 'refresh':
        refresh_metadata()
    elif args.mode == 'report':
        generate_report()
