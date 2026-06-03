import os
import re
import requests
import telebot
import yt_dlp
import time
import zipfile
import glob
import random

# Cấu hình cơ bản
TOKEN = os.getenv('BOT_TOKEN')
PROXY_URL = os.getenv('PROXY_URL', 'http://ZalMQa:BRQrEd@14.250.212.38:36428')

if not TOKEN:
    raise Exception("Lỗi: BOT_TOKEN chưa được thiết lập!")

bot = telebot.TeleBot(TOKEN)

# ==========================================
# CƠ CHẾ QUẢN LÝ POOL COOKIES TỪ FILE ZIP
# ==========================================
COOKIE_DIR = './cookies_extracted'
COOKIE_ZIP = 'cookies.zip'

def init_cookie_pool():
    """Giải nén file zip và trả về danh sách các file cookie"""
    if os.path.exists(COOKIE_ZIP):
        print("📦 Tìm thấy cookies.zip, đang giải nén để tạo Pool Cookie...")
        try:
            with zipfile.ZipFile(COOKIE_ZIP, 'r') as zip_ref:
                zip_ref.extractall(COOKIE_DIR)
        except Exception as e:
            print(f"Lỗi giải nén cookies.zip: {e}")
            
    # Lấy tất cả các file .txt trong thư mục giải nén
    if os.path.exists(COOKIE_DIR):
        cookies = glob.glob(f"{COOKIE_DIR}/*.txt")
        print(f"✅ Đã nạp {len(cookies)} file cookie vào hệ thống.")
        return cookies
    # Tương thích ngược nếu chỉ có 1 file cookies.txt rời ở ngoài
    elif os.path.exists('cookies.txt'):
        return ['cookies.txt']
    
    return []

# Khởi tạo danh sách cookie ngay khi chạy code
COOKIE_FILES = init_cookie_pool()

def get_ydl_opts(cookie_path=None):
    """Tùy chọn yt-dlp tích hợp Cookie động"""
    opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': False,
        'extract_flat': 'in_playlist',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        },
        'proxy': PROXY_URL,
        'extractor_args': {
            'youtube': ['client=android', 'client=ios']
        }
    }
    
    # Gắn đường dẫn file cookie live được chỉ định vào options
    if cookie_path and os.path.exists(cookie_path):
        opts['cookiefile'] = cookie_path
        
    return opts

def custom_web_scraper(url):
    """Xử lý TikTok không logo và quét M3U8 cho web phim"""
    if 'tiktok.com' in url:
        try:
            api_url = f"https://www.tikwm.com/api/?url={url}"
            res = requests.get(api_url, timeout=10).json()
            if res.get('code') == 0:
                return res['data']['play']
        except Exception as e:
            print(f"Lỗi API TikTok: {e}")
            return None 

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    proxies = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else None

    try:
        res = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        if res.status_code == 200:
            m3u8_match = re.search(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\']*)', res.text)
            if m3u8_match:
                return m3u8_match.group(1).replace('\\/', '/')
    except Exception as e:
        print(f"Lỗi Crawler M3U8: {e}")
        
    return None 

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, f"👋 **Bot tải video đa nền tảng đang chạy.**\n📦 Đang có sẵn: `{len(COOKIE_FILES)}` cookie dự phòng.\n\nGửi link cho tôi để tải!", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.reply_to(message, "⚠️ Vui lòng gửi một link hợp lệ.")
        return

    msg = bot.reply_to(message, "⏳ Đang kết nối mạng và trích xuất dữ liệu...")

    custom_direct_link = custom_web_scraper(url)
    if custom_direct_link:
        if '.m3u8' in custom_direct_link:
            text_response = f"🎬 **Đã tìm thấy luồng trực tiếp (M3U8)**\n\n📥 [Bấm vào đây để tải/xem]({custom_direct_link})\n\n`#EXTM3U`\n`#EXTINF:-1, Luồng Video`\n`{custom_direct_link}`"
        else:
            text_response = f"🎬 **Video trực tiếp (Không Logo)**\n\n📥 [Bấm vào đây để tải/xem]({custom_direct_link})"
            
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=text_response, parse_mode='Markdown', disable_web_page_preview=True)
        return

    # ==========================================
    # CƠ CHẾ AUTO THỬ NGHIỆM COOKIE (FAILOVER)
    # ==========================================
    
    # Xáo trộn danh sách cookie để tránh dùng 1 file quá nhiều lần
    pool = list(COOKIE_FILES)
    random.shuffle(pool)
    
    # Nếu không có cookie nào, vẫn cho phép chạy 1 lần không dùng cookie
    if not pool:
        pool = [None]
        
    info = None
    success = False
    last_error = ""

    for cookie_path in pool:
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts(cookie_path)) as ydl:
                info = ydl.extract_info(url, download=False)
                success = True
                break # Lấy link thành công, thoát khỏi vòng lặp tìm cookie
                
        except Exception as e:
            last_error = str(e).split('\n')[0][:150]
            # Kiểm tra xem lỗi có phải do YouTube block bot hoặc chết cookie không
            if "Sign in" in last_error or "bot" in last_error.lower() or "cookie" in last_error.lower():
                print(f"⚠️ Cookie {cookie_path} đã chết hoặc bị block. Đang đổi sang cookie khác...")
                continue # Bỏ qua cookie hiện tại, lặp sang cookie tiếp theo
            else:
                # Nếu lỗi khác (VD: sai link, video bị xóa), thì không cần thử cookie khác làm gì
                break
                
    # ==========================================

    if not success:
        error_display = last_error or "❌ Tất cả Cookie đều đã chết hoặc không tìm thấy video hợp lệ."
        try:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"❌ Trích xuất thất bại.\n\n*Log:* `{error_display}`", parse_mode='Markdown')
        except:
            bot.send_message(message.chat.id, f"❌ Trích xuất thất bại.\n\n*Log:* `{error_display}`", parse_mode='Markdown')
        return

    # Tiến hành xả link nếu thành công
    try:
        entries = info.get('entries') if 'entries' in info else [info]
        bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
        
        extracted_count = 0
        MAX_VIDEOS = 5 
        
        for entry in entries:
            if not entry: continue
            
            if extracted_count >= MAX_VIDEOS:
                bot.send_message(message.chat.id, f"⚠️ **Cảnh báo Spam:** Đã chạm ngưỡng {MAX_VIDEOS} video. Vui lòng gửi link lẻ để tải thêm.", parse_mode='Markdown')
                break
                
            video_url = entry.get('url')
            title = entry.get('title', 'Video không tên')
            
            if video_url:
                bot.send_message(
                    chat_id=message.chat.id, 
                    text=f"🎬 **{title}**\n\n📥 [Bấm vào đây để tải/xem]({video_url})", 
                    parse_mode='Markdown'
                )
                extracted_count += 1
                time.sleep(1.5) 
                
        if extracted_count == 0:
            bot.send_message(message.chat.id, "❌ Không tìm thấy URL tải xuống từ trang web này.")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi xuất dữ liệu: `{str(e)[:150]}`", parse_mode='Markdown')

if __name__ == '__main__':
    print("🚀 Bot đang khởi động chế độ Polling...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Lỗi mạng, khởi động lại sau 15s... Log: {e}")
            time.sleep(15)
