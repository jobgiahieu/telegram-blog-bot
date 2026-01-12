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

# Pattern để phát hiện mã sản phẩm (linh hoạt hơn)
PRODUCT_PATTERN = re.compile(r'\b[A-Z][A-Z0-9]{3,15}\b', re.IGNORECASE)


# ===== HTTP SERVER =====
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Telegram Bot is Running!</h1>')
    
    def log_message(self, format, *args):
        pass


def run_http_server():
    """Chạy HTTP server để Render không báo lỗi port"""
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    print(f"🌐 HTTP Server đang chạy trên port {PORT}")
    server.serve_forever()


def search_blogspot(keyword):
    """Tìm kiếm từ khóa trên blog - CẢI TIẾN"""
    search_url = f"{BLOG_URL}/search?q={quote(keyword)}"
    
    try:
        print(f"🔎 Đang tìm kiếm: {search_url}")
        
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm TẤT CẢ các bài viết
        posts = soup.find_all('h3', class_='post-title')
        if not posts:
            posts = soup.find_all('h3', class_='entry-title')
        
        print(f"📊 Tìm thấy {len(posts)} bài viết")
        
        # Duyệt qua từng bài viết
        for post in posts:
            link = post.find('a')
            if link:
                post_url = link.get('href', '')
                post_title = link.get_text(strip=True)
                
                print(f"📄 Kiểm tra: {post_title}")
                
                # Tìm kiếm linh hoạt hơn (không phân biệt hoa thường, dấu)
                keyword_lower = keyword.lower().replace('-', '').replace('_', '')
                title_lower = post_title.lower().replace('-', '').replace('_', '')
                
                if keyword_lower in title_lower:
                    print(f"✅ Khớp! {post_title}")
                    return {
                        'found': True,
                        'url': post_url,
                        'title': post_title
                    }
        
        # Nếu không tìm thấy bài viết chính xác, trả về link search
        if len(posts) > 0:
            print(f"⚠️ Không khớp chính xác, trả về link search")
            return {
                'found': True,
                'url': search_url,
                'title': f'Kết quả tìm kiếm "{keyword}"'
            }
        
        print(f"❌ Không tìm thấy bài viết nào")
        return {'found': False}
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return {'found': False}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn trong group"""
    if not update.message or not update.message.text:
        return
    
    message_text = update.message.text
    
    print(f"💬 Nhận tin nhắn: {message_text}")
    
    # Tìm tất cả các mã sản phẩm trong tin nhắn
    matches = PRODUCT_PATTERN.findall(message_text)
    
    if not matches:
        print(f"⏭️ Không phát hiện mã sản phẩm")
        return
    
    # Lấy mã đầu tiên tìm được
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
        # Không reply nếu không tìm thấy


def main():
    """Khởi động bot"""
    print("=" * 50)
    print("🤖 TELEGRAM BOT - TỰ ĐỘNG TÌM KIẾM BLOG")
    print("=" * 50)
    print(f"📱 Blog: {BLOG_URL}")
    print(f"🔌 Port: {PORT}")
    print(f"🔍 Pattern: {PRODUCT_PATTERN.pattern}")
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
