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
    """Tìm kiếm từ khóa trên blog - LINH HOẠT HƠN"""
    search_url = f"{BLOG_URL}/search?q={quote(keyword)}"
    
    try:
        print(f"🔎 Đang tìm kiếm: {search_url}")
        
        response = requests.get(search_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm TẤT CẢ các thẻ <a> có chứa từ khóa
        all_links = soup.find_all('a', href=True)
        
        found_posts = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Kiểm tra link có phải là bài viết không
            if BLOG_URL in href and '/20' in href and '.html' in href:
                # Kiểm tra từ khóa có trong tiêu đề không
                keyword_clean = keyword.lower().replace('-', '').replace('_', '')
                text_clean = text.lower().replace('-', '').replace('_', '')
                
                if keyword_clean in text_clean and len(text) > 10:
                    found_posts.append({
                        'url': href,
                        'title': text
                    })
                    print(f"📄 Tìm thấy: {text}")
        
        print(f"📊 Tìm thấy {len(found_posts)} bài viết")
        
        # Trả về bài viết đầu tiên
        if found_posts:
            return {
                'found': True,
                'url': found_posts[0]['url'],
                'title': found_posts[0]['title']
            }
        
        # Nếu không tìm thấy, thử tìm kiếm rộng hơn
        print("🔄 Thử tìm kiếm rộng hơn...")
        
        # Tìm tất cả các link bài viết
        post_links = []
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if BLOG_URL in href and '/20' in href and '.html' in href and len(text) > 10:
                post_links.append({
                    'url': href,
                    'title': text
                })
        
        if post_links:
            print(f"⚠️ Không tìm thấy khớp chính xác, trả về link search")
            return {
                'found': True,
                'url': search_url,
                'title': f'Kết quả tìm kiếm "{keyword}" ({len(post_links)} bài viết)'
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
