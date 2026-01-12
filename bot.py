import re
import os
import threading
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from http.server import HTTPServer, BaseHTTPRequestHandler

# ===== CẤU HÌNH =====
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
BLOG_URL = "https://blogvnpt.blogspot.com"
PORT = int(os.environ.get('PORT', 10000))

# Pattern để phát hiện mã sản phẩm
PRODUCT_PATTERN = re.compile(r'\b[A-Z0-9]{5,10}\b', re.IGNORECASE)


# ===== HTTP SERVER (để Render không báo lỗi) =====
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Telegram Bot is Running!</h1>')
    
    def log_message(self, format, *args):
        # Tắt log của HTTP server để không spam
        pass


def run_http_server():
    """Chạy HTTP server để Render không báo lỗi port"""
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    print(f"🌐 HTTP Server đang chạy trên port {PORT}")
    server.serve_forever()


def search_blogspot(keyword):
    """Tìm kiếm từ khóa trên blog"""
    search_url = f"{BLOG_URL}/search?q={quote(keyword)}"
    
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        first_post = soup.find('h3', class_='post-title entry-title')
        
        if first_post and first_post.find('a'):
            post_url = first_post.find('a')['href']
            post_title = first_post.get_text(strip=True)
            
            if keyword.lower() in post_title.lower():
                return {
                    'found': True,
                    'url': post_url,
                    'title': post_title
                }
            
            return {
                'found': True,
                'url': search_url,
                'title': f'Kết quả tìm kiếm "{keyword}"'
            }
        
        return {'found': False}
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return {'found': False}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn trong group"""
    if not update.message or not update.message.text:
        return
    
    message_text = update.message.text
    matches = PRODUCT_PATTERN.findall(message_text)
    
    if not matches:
        return
    
    keyword = matches[0]
    print(f"🔍 Phát hiện từ khóa: {keyword}")
    
    result = search_blogspot(keyword)
    
    if result['found']:
        reply_text = (
            f"🔍 Tìm thấy: {keyword}\n"
            f"📝 {result['title']}\n"
            f"🔗 {result['url']}"
        )
        await update.message.reply_text(reply_text, disable_web_page_preview=False)
        print(f"✅ Đã gửi link cho: {keyword}")
    else:
        print(f"❌ Không tìm thấy: {keyword}")


def main():
    """Khởi động bot"""
    print("=" * 50)
    print("🤖 TELEGRAM BOT - TỰ ĐỘNG TÌM KIẾM BLOG")
    print("=" * 50)
    print(f"📱 Blog: {BLOG_URL}")
    print(f"🔌 Port: {PORT}")
    print("=" * 50)
    
    # Chạy HTTP server trong thread riêng
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Khởi động bot
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot đang chạy...")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
