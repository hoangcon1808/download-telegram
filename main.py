import os
import re
import requests
import telebot
import yt_dlp
import time

# Lấy biến môi trường từ GitHub Secrets, kèm Proxy mặc định làm fallback
TOKEN = os.getenv('BOT_TOKEN')
PROXY_URL = os.getenv('PROXY_URL', 'http://ZalMQa:BRQrEd@14.250.212.38:36428')

# Nếu không tìm thấy Token (chạy local quên set biến), văng lỗi ngay lập tức
if not TOKEN:
    raise Exception("Lỗi: BOT_TOKEN chưa được thiết lập!")

bot = telebot.TeleBot(TOKEN)

def get_ydl_opts():
    """Tùy chọn yt-dlp với Proxy và Netscape Cookies"""
    opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': False,
        'extract_flat': 'in_playlist',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        },
        'proxy': PROXY_URL
    }
    
    # Tự động nạp file cookies chuẩn Netscape để bypass login (FB Private, IG...)
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
        
    return opts

def custom_web_scraper(url):
    """
    Crawler quét và bóc tách dữ liệu trước khi chuyển qua yt-dlp.
    - Xử lý TikTok qua API ngoài để chống block IP và lấy video không logo.
    - Quét luồng HLS/M3U8 cho các trang web phim.
    """
    # 1. Bypass thuật toán TikTok
    if 'tiktok.com' in url:
        try:
            api_url = f"https://www.tikwm.com/api/?url={url}"
            res = requests.get(api_url, timeout=10).json()
            if res.get('code') == 0:
                direct_link = res['data']['play']
                return direct_link
        except Exception as e:
            print(f"Lỗi API TikTok: {e}")
            return None # Fallback về yt-dlp nếu API sập

    # 2. Quét tìm luồng M3U8 cho các trang phim/TV
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
                direct_link = m3u8_match.group(1).replace('\\/', '/')
                return direct_link
    except Exception as e:
        print(f"Lỗi Crawler M3U8: {e}")
        
    return None 

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 **Hệ thống tải video đa nền tảng đang chạy.**\n\nGửi link cho tôi để bắt đầu bóc tách!", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.reply_to(message, "⚠️ Vui lòng gửi một link hợp lệ.")
        return

    msg = bot.reply_to(message, "⏳ Đang kết nối mạng và trích xuất dữ liệu...")

    # 1. Ưu tiên quét Custom API / M3U8 trước
    custom_direct_link = custom_web_scraper(url)
    if custom_direct_link:
        # Nếu là link m3u8 thì xuất thêm định dạng list cho external player
        if '.m3u8' in custom_direct_link:
            text_response = (
                "🎬 **Đã tìm thấy luồng trực tiếp (M3U8)**\n\n"
                f"📥 [Bấm vào đây để tải/xem]({custom_direct_link})\n\n"
                "`#EXTM3U`\n`#EXTINF:-1, Luồng Video`\n"
                f"`{custom_direct_link}`"
            )
        else:
            text_response = f"🎬 **Video trực tiếp (Không Logo)**\n\n📥 [Bấm vào đây để tải/xem]({custom_direct_link})"
            
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=text_response, parse_mode='Markdown', disable_web_page_preview=True)
        return

    # 2. Nếu không thuộc luồng tĩnh hoặc API ngoài, chuyển qua xử lý bằng yt-dlp
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Xử lý nếu link là playlist
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
                
            video_url = info.get('url')
            title = info.get('title', 'Video')
            
            if not video_url:
                raise Exception("Không tìm thấy URL gốc.")

            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"🎬 **{title}**\n\n📥 [Bấm vào đây để tải/xem]({video_url})", parse_mode='Markdown')
            
    except Exception as e:
        error_msg = str(e).split('\n')[0][:150]
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"❌ Trích xuất thất bại.\n\n*Log:* `{error_msg}`", parse_mode='Markdown')

if __name__ == '__main__':
    print("🚀 Bot đang khởi động chế độ Polling...")
    # Polling liên tục, tự động thử lại khi mất kết nối
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Lỗi rớt mạng, đang khởi động lại sau 15s... Chi tiết: {e}")
            time.sleep(15)
