import os
import re
import requests
import telebot
import yt_dlp
import time
import zipfile
import glob
import random
import threading
import datetime

# ==========================================
# CẤU HÌNH HỆ THỐNG
# ==========================================
TOKEN = os.getenv('BOT_TOKEN')
PROXY_URL = os.getenv('PROXY_URL', 'http://ZalMQa:BRQrEd@14.250.212.38:36428')

# ID Telegram của bạn để nhận thông báo hàng giờ. 
# Nếu chạy trên GitHub, hãy thêm biến ADMIN_ID vào phần Secrets.
ADMIN_ID = os.getenv('ADMIN_ID', 'ĐIỀN_ID_CỦA_BẠN_VÀO_ĐÂY') 

if not TOKEN:
    raise Exception("Lỗi: BOT_TOKEN chưa được thiết lập!")

bot = telebot.TeleBot(TOKEN)
START_TIME = time.time() # Ghi nhận thời điểm bot bắt đầu chạy

# ==========================================
# CƠ CHẾ POOL COOKIES
# ==========================================
COOKIE_DIR = './cookies_extracted'
COOKIE_ZIP = 'cookies.zip'

def init_cookie_pool():
    if os.path.exists(COOKIE_ZIP):
        try:
            with zipfile.ZipFile(COOKIE_ZIP, 'r') as zip_ref:
                zip_ref.extractall(COOKIE_DIR)
        except: pass
            
    if os.path.exists(COOKIE_DIR):
        return glob.glob(f"{COOKIE_DIR}/*.txt")
    elif os.path.exists('cookies.txt'):
        return ['cookies.txt']
    return []

COOKIE_FILES = init_cookie_pool()

# ==========================================
# CƠ CHẾ AUTO HEALTH CHECK (1 GIỜ / LẦN)
# ==========================================
def system_health_monitor():
    """Luồng chạy ngầm tự động gửi báo cáo trạng thái mỗi giờ"""
    while True:
        # Tạm dừng 3600 giây (1 giờ) trước khi gửi báo cáo lần tiếp theo
        time.sleep(3600) 
        
        # Tính toán thời gian bot đã hoạt động liên tục
        uptime_seconds = int(time.time() - START_TIME)
        uptime_str = str(datetime.timedelta(seconds=uptime_seconds))
        
        report_msg = (
            "🟢 **BÁO CÁO HỆ THỐNG ĐỊNH KỲ**\n\n"
            "Trạng thái: **Đang hoạt động ổn định** 🚀\n"
            f"⏱ **Uptime:** `{uptime_str}`\n"
            f"📦 **Cookies dự phòng:** `{len(COOKIE_FILES)}` file\n"
            f"🌐 **Proxy:** `{'Đang bật' if PROXY_URL else 'Không dùng'}`"
        )
        
        try:
            if ADMIN_ID and ADMIN_ID != 'ĐIỀN_ID_CỦA_BẠN_VÀO_ĐÂY':
                bot.send_message(chat_id=ADMIN_ID, text=report_msg, parse_mode='Markdown')
            else:
                print("⚠️ Báo cáo hệ thống: Chưa cấu hình ADMIN_ID nên không thể gửi tin nhắn.")
        except Exception as e:
            print(f"Lỗi khi gửi báo cáo Health Check: {e}")

# ==========================================
# LOGIC TRÍCH XUẤT MEDIA
# ==========================================
def get_ydl_opts(cookie_path=None):
    opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': False,
        'extract_flat': 'in_playlist',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        },
        'proxy': PROXY_URL,
        'extractor_args': {'youtube': ['client=android', 'client=ios']}
    }
    if cookie_path and os.path.exists(cookie_path):
        opts['cookiefile'] = cookie_path
    return opts

def custom_web_scraper(url):
    if 'tiktok.com' in url:
        try:
            res = requests.get(f"https://www.tikwm.com/api/?url={url}", timeout=10).json()
            if res.get('code') == 0:
                return {
                    'type': 'tiktok',
                    'video_url': res['data'].get('play'),
                    'audio_url': res['data'].get('music')
                }
        except: return None 

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    proxies = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else None

    try:
        res = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        if res.status_code == 200:
            m3u8_match = re.search(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\']*)', res.text)
            if m3u8_match:
                return {
                    'type': 'm3u8',
                    'video_url': m3u8_match.group(1).replace('\\/', '/'),
                    'audio_url': None
                }
    except: return None 
        
    return None 

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 **Bot tải Video & MP3 đa nền tảng đang chạy.**\n\nGửi link cho tôi để tải!", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.reply_to(message, "⚠️ Vui lòng gửi một link hợp lệ.")
        return

    msg = bot.reply_to(message, "⏳ Đang kết nối mạng và trích xuất dữ liệu...")

    custom_data = custom_web_scraper(url)
    if custom_data:
        if custom_data['type'] == 'm3u8':
            text_response = f"🎬 **Luồng trực tiếp (M3U8)**\n\n📥 [Bấm vào đây để tải/xem]({custom_data['video_url']})\n\n`#EXTM3U`\n`#EXTINF:-1, Luồng Video`\n`{custom_data['video_url']}`"
        else: 
            text_response = f"🎬 **Video (Không Logo)**\n📥 [Tải Video]({custom_data['video_url']})\n\n"
            if custom_data.get('audio_url'):
                text_response += f"🎧 **Nhạc Nền (MP3)**\n📥 [Tải Nhạc]({custom_data['audio_url']})"
            
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=text_response, parse_mode='Markdown', disable_web_page_preview=True)
        return

    pool = list(COOKIE_FILES)
    random.shuffle(pool)
    if not pool: pool = [None]
        
    info = None
    success = False
    last_error = ""

    for cookie_path in pool:
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts(cookie_path)) as ydl:
                info = ydl.extract_info(url, download=False)
                success = True
                break
        except Exception as e:
            last_error = str(e).split('\n')[0][:150]
            if "Sign in" in last_error or "bot" in last_error.lower() or "cookie" in last_error.lower():
                continue
            else:
                break
                
    if not success:
        error_display = last_error or "❌ Tất cả Cookie đều đã chết hoặc không tìm thấy video hợp lệ."
        try:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"❌ Trích xuất thất bại.\n\n*Log:* `{error_display}`", parse_mode='Markdown')
        except:
            bot.send_message(message.chat.id, f"❌ Trích xuất thất bại.\n\n*Log:* `{error_display}`", parse_mode='Markdown')
        return

    try:
        entries = info.get('entries') if 'entries' in info else [info]
        bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
        
        extracted_count = 0
        MAX_VIDEOS = 5 
        
        for entry in entries:
            if not entry: continue
            if extracted_count >= MAX_VIDEOS:
                bot.send_message(message.chat.id, f"⚠️ Đã chạm ngưỡng {MAX_VIDEOS} media. Gửi link lẻ để tải thêm.", parse_mode='Markdown')
                break
                
            title = entry.get('title', 'Media không tên')
            video_url = entry.get('url')
            
            audio_url = None
            if 'formats' in entry:
                audio_formats = [f for f in entry['formats'] if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
                if audio_formats:
                    audio_url = audio_formats[-1].get('url')

            if video_url:
                response = f"🎬 **{title}**\n\n📥 [Tải Video]({video_url})"
                if audio_url:
                    response += f"\n🎧 [Tải Nhạc (Audio)]({audio_url})"
                
                bot.send_message(chat_id=message.chat.id, text=response, parse_mode='Markdown')
                extracted_count += 1
                time.sleep(1.5) 
                
        if extracted_count == 0:
            bot.send_message(message.chat.id, "❌ Không tìm thấy dữ liệu tải xuống.")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi xuất dữ liệu: `{str(e)[:150]}`", parse_mode='Markdown')

if __name__ == '__main__':
    print("🚀 Bot đang khởi động chế độ Polling...")
    
    # 1. Kích hoạt luồng báo cáo định kỳ trước khi bot chạy
    monitor_thread = threading.Thread(target=system_health_monitor)
    monitor_thread.daemon = True # Đảm bảo thread tự tắt khi chương trình chính dừng
    monitor_thread.start()
    
    # 2. Vòng lặp giữ kết nối Telegram
    while True:
        try:
            # Gửi tin nhắn thông báo bot vừa được khởi động lại thành công
            if ADMIN_ID and ADMIN_ID != 'ĐIỀN_ID_CỦA_BẠN_VÀO_ĐÂY':
                try: bot.send_message(ADMIN_ID, "✅ **Hệ thống tải video đã khởi động thành công!**", parse_mode='Markdown')
                except: pass
                
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Lỗi mạng, khởi động lại sau 15s... Log: {e}")
            time.sleep(15)
