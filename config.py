# 播放列表URL（可随时改，支持多个：用逗号分隔，或命令行传入）
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLsNiJ5ulrY_FB-BWOCLmObaEtg51bu9i6"

# 浏览器 for cookie
BROWSER = "firefox"

# 下载临时路径 (固态盘)
TEMP_DOWNLOAD_PATH = "D:\\Videos\\temp_download"

# 最终保存路径 (机械盘)
FINAL_DOWNLOAD_PATH = "F:\\Videos\\youtube download\\MMD"  # 加\\MMD以匹配你的例子，可改

# Archive CSV路径
ARCHIVE_CSV = "F:\\Videos\\youtube download\\archive.csv"

# 下载质量参数
FORMAT = "bestvideo[height>=720][height<=1440]+bestaudio/best[height>=720][height<=1440]"

# 字幕参数
SUB_LANGS = "zh-CN,zh-*,en-*,ja"

# 文件扩展白名单
VIDEO_EXTS = ('.mp4', '.mkv', '.webm')

# 模糊匹配阈值 (0-1, 越高越严格)
MATCH_THRESHOLD = 0.9
