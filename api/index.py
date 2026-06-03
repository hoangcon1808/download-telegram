import os
import telebot
from flask import Flask, request, jsonify
import yt_dlp
import requests
import re

# Lấy Token từ biến môi trường Vercel. 
# Proxy đã được set mặc định với thông tin bạn cung cấp.
TOKEN = os.getenv('BOT_TOKEN')
PROXY_URL = os.getenv('PROXY_URL', 'http://ZalMQa:BRQrEd@14.250.212.38:36428')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def get_ydl_opts():
    """Cấu hình yt-dlp với Proxy và Cookie để vượt rào"""
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

    # Nếu có file cookies (chuẩn định dạng Netscape) để pass qua các trang yêu cầu login
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'

    return opts

def custom_web_scraper(url):
    """
    Fallback crawler: Bắt các luồng stream động (HLS/M3U8) hoặc xử lý các trang yt-dlp không hỗ trợ.
    Sử dụng proxy mặc định để tránh block IP khi cào dữ liệu.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    proxies = {
        'http': PROXY_URL,
        'https': PROXY_URL
    } if PROXY_URL else None

    # Ví dụ logic tự động dò tìm link .m3u8 trong source HTML của trang web
    # try:
    #     res = requests.get(url, headers=headers, proxies=proxies, timeout=10)
    #     if res.status_code == 200:
    #         # Dùng Regex để tìm các token hoặc file m3u8 sinh động
    #         m3u8_match = re.search(r'(https?://[^\s"\'<>]+?\.m3u8[^\s"\']*)', res.text)
    #         if m3u8_match:
    #             return m3u8_match.group(1)
    # except Exception as e:
    #     print(f"Lỗi cào dữ liệu custom: {e}")
    
    return None 

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Gửi link video cho tôi! Hệ thống đã được cấu hình Proxy ẩn danh và hỗ trợ tải đa nền tảng.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not url.startswith('http'):
        bot.reply_to(message, "⚠️ Vui lòng gửi một link hợp lệ (http/https).")
        return

    msg = bot.reply_to(message, "⏳ Đang kết nối qua Proxy và trích xuất link...")

    # 1. Thử cào bằng logic tự viết (M3U8/HLS/Tokens)
    custom_direct_link = custom_web_scraper(url)
    if custom_direct_link:
        bot.edit_message_text(
            chat_id=message.chat.id, 
            message_id=msg.message_id, 
            text=f"🎬 **Stream Extracted**\n\n📥 [Bấm vào đây để tải/xem luồng M3U8]({custom_direct_link})", 
            parse_mode='Markdown'
        )
        return

    # 2. Xử lý bằng yt-dlp
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]
                
            video_url = info.get('url')
            title = info.get('title', 'Video')
            
            if not video_url:
                raise Exception("Không tìm thấy URL gốc.")

            response_text = f"🎬 **{title}**\n\n📥 [Bấm vào đây để tải/xem]({video_url})"
            bot.edit_message_text(
                chat_id=message.chat.id, 
                message_id=msg.message_id, 
                text=response_text, 
                parse_mode='Markdown'
            )
            
    except Exception as e:
        error_msg = str(e).split('\n')[0][:150]
        bot.edit_message_text(
            chat_id=message.chat.id, 
            message_id=msg.message_id, 
            text=f"❌ Lỗi trích xuất (có thể cần file cookies dạng Netscape). \n\n*Log:* `{error_msg}`", 
            parse_mode='Markdown'
        )

# === VERCEL ROUTES ===

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint nhận dữ liệu từ Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Invalid Request', 403

@app.route('/ping', methods=['GET'])
def ping():
    """Cron job giữ nhịp, chống ngủ đông Vercel"""
    return jsonify({"status": "Bot is awake!"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
