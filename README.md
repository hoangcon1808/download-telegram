# 🤖 Telegram Universal Video Downloader Bot

Một bot Telegram mạnh mẽ được thiết kế để tự động bóc tách và trích xuất link tải video gốc từ các nền tảng mạng xã hội và các trang web phim trực tuyến. Bot được tối ưu hóa để chạy liên tục 24/7 trên môi trường Serverless (GitHub Actions).

## 🌟 Tính Năng Nổi Bật

- **Hỗ trợ đa nền tảng:** Lấy link gốc từ YouTube, Facebook, Instagram, X (Twitter),... thông qua `yt-dlp`.
- **Tải Playlist/Carousel:** Có khả năng tự động quét và bóc tách toàn bộ video trong một Playlist hoặc Instagram Carousel (giới hạn an toàn chống spam Telegram).
- **TikTok No Watermark:** Tích hợp API chuyên dụng (TikWM) để qua mặt tường lửa TikTok và lấy video không dính logo.
- **Trích xuất IPTV/M3U8:** Tự động thu thập token và luồng phim chuẩn `m3u8` cho các nền tảng web phim đặc thù. Trả về format sẵn sàng cho file M3U.
- **Bảo mật mạng (Proxy):** Điều hướng traffic qua Proxy cá nhân để chống block IP từ các máy chủ lưu trữ nền tảng.
- **Zero-Downtime:** Tự động hồi sinh (Long Polling recovery) kết hợp cùng GitHub Actions Workflow, loại bỏ hoàn toàn lỗi *409 Conflict*.

---

## 📂 Cấu Trúc Dự Án

```text
📦 Telegram-Downloader-Bot
┣ 📂 .github
┃ ┗ 📂 workflows
┃   ┗ 📜 run-bot.yml       # Cấu hình tự động chạy CI/CD trên GitHub Actions
┣ 📜 main.py               # Mã nguồn chính chứa logic bóc link
┣ 📜 requirements.txt      # Thư viện Python cần thiết
┣ 📜 cookies.txt           # (Tùy chọn) File Netscape Cookies cho nội dung Private
┗ 📜 README.md             # Tài liệu dự án
