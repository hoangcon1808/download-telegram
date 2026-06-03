import os
import re
import requests
import telebot
import yt_dlp
import time

TOKEN = os.getenv('BOT_TOKEN')
PROXY_URL = os.getenv('PROXY_URL', 'http://ZalMQa:BRQrEd@14.250.212.38:36428')

if not TOKEN:
    raise Exception("Lỗi: BOT_TOKEN chưa được thiết lập!")

bot = telebot.TeleBot(TOKEN)

def get_ydl_opts():
    opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': False, # Cho phép quét playlist
        'extract_flat': 'in_playlist',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
        },
        'proxy': PROXY_URL
    }
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'
    return opts

def custom_web_scraper(url):
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
    bot.reply_to(message, "👋 **Hệ thống tải video đa nền tảng đang chạy.**\n\nGửi link (Video lẻ hoặc Playlist) cho tôi để bắt đầu bóc tách!", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.reply_to(message, "⚠️ Vui lòng gửi một link hợp lệ.")
        return

    msg = bot.reply_to(message, "⏳ Đang kết nối mạng và trích xuất dữ liệu...")

    # 1. Quét Custom API / M3U8
    custom_direct_link = custom_web_scraper(url)
    if custom_direct_link:
        if '.m3u8' in custom_direct_link:
            text_response = f"🎬 **Đã tìm thấy luồng trực tiếp (M3U8)**\n\n📥 [Bấm vào đây để tải/xem]({custom_direct_link})\n\n`#EXTM3U`\n`#EXTINF:-1, Luồng Video`\n`{custom_direct_link}`"
        else:
            text_response = f"🎬 **Video trực tiếp (Không Logo)**\n\n📥 [Bấm vào đây để tải/xem]({custom_direct_link})"
            
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=text_response, parse_mode='Markdown', disable_web_page_preview=True)
        return

    # 2. Xử lý đa nền tảng bằng yt-dlp (Hỗ trợ bóc tách danh sách/playlist)
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Chuẩn hóa info thành dạng List để xử lý đồng nhất cho cả video lẻ và playlist
            entries = info.get('entries') if 'entries' in info else [info]
            
            # Xóa tin nhắn "Đang kết nối..." trước khi xả link
            bot.delete_message(chat_id=message.chat.id, message_id=msg.message_id)
            
            extracted_count = 0
            MAX_VIDEOS = 5 # Đặt giới hạn tải tối đa 5 video từ 1 link để tránh bị Telegram khóa API vì spam
            
            for entry in entries:
                if not entry:
                    continue
                
                if extracted_count >= MAX_VIDEOS:
                    bot.send_message(message.chat.id, f"⚠️ **Cảnh báo Spam:** Đã chạm ngưỡng hiển thị {MAX_VIDEOS} video từ link này. Vui lòng gửi link lẻ để lấy thêm.", parse_mode='Markdown')
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
                    time.sleep(1.5) # Nghỉ 1.5 giây giữa mỗi tin nhắn để chống rate-limit của Telegram
                    
            if extracted_count == 0:
                bot.send_message(message.chat.id, "❌ Không tìm thấy URL tải xuống từ trang web này.")
            
    except Exception as e:
        error_msg = str(e).split('\n')[0][:150]
        try:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"❌ Trích xuất thất bại.\n\n*Log:* `{error_msg}`", parse_mode='Markdown')
        except:
            bot.send_message(message.chat.id, f"❌ Trích xuất thất bại.\n\n*Log:* `{error_msg}`", parse_mode='Markdown')

if __name__ == '__main__':
    print("🚀 Bot đang khởi động chế độ Polling...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Lỗi mạng, khởi động lại sau 15s... Log: {e}")
            time.sleep(15)
