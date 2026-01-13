import re
import os
import threading
import asyncio
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
MAX_RESULTS = 5  # Số kết quả tối đa

# Pattern linh hoạt: cho phép dấu gạch ngang và gạch dưới
PRODUCT_PATTERN = re.compile(r'\b[A-Z][A-Z0-9\-\_]{2,20}\b', re.IGNORECASE)


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
    """Chạy HTTP server"""
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    print(f"🌐 HTTP Server đang chạy trên port {PORT}")
    server.serve_forever()


def search_blogspot(keyword):
    """Tìm kiếm và trả về NHIỀU kết quả"""
    search_url = f"{BLOG_URL}/search?q={quote(keyword)}"
    
    try:
        print(f"🔎 Đang tìm kiếm: {search_url}")
        
        response = requests.get(search_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        all_links = soup.find_all('a', href=True)
        
        found_posts = []
        seen_urls = set()
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Chỉ lấy link bài viết
            if BLOG_URL in href and '/20' in href and '.html' in href:
                if href in seen_urls or len(text) < 10:
                    continue
                seen_urls.add(href)
                
                # So khớp linh hoạt
                keyword_clean = keyword.lower().replace('-', '').replace('_', '').replace(' ', '')
                text_clean = text.lower().replace('-', '').replace('_', '').replace(' ', '')
                
                if keyword_clean in text_clean:
                    found_posts.append({
                        'url': href,
                        'title': text
                    })
                    print(f"📄 Tìm thấy: {text[:50]}...")
                    
                    # Giới hạn số kết quả
                    if len(found_posts) >= MAX_RESULTS:
                        break
        
        print(f"📊 Tổng cộng tìm thấy {len(found_posts)} bài viết")
        
        if found_posts:
            return {
                'found': True,
                'posts': found_posts  # Trả về LIST thay vì 1 bài
            }
        
        # Nếu không tìm thấy khớp chính xác
        print("⚠️ Không tìm thấy bài viết khớp")
        
        # Đếm tổng số bài viết trong kết quả search
        post_count = len([l for l in all_links if BLOG_URL in l.get('href', '') and '.html' in l.get('href', '')])
        
        if post_count > 0:
            return {
                'found': True,
                'posts': [{
                    'url': search_url,
                    'title': f'Xem {post_count} kết quả tìm kiếm cho "{keyword}"'
                }]
            }
        
        print(f"❌ Không tìm thấy bài viết nào")
        return {'found': False}
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return {'found': False}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn"""
    if not update.message or not update.message.text:
        return
    
    message_text = update.message.text
    
    print(f"💬 Nhận tin nhắn: {message_text}")
    
    matches = PRODUCT_PATTERN.findall(message_text)
    
    if not matches:
        print(f"⏭️ Không phát hiện mã sản phẩm")
        return
    
    keyword = matches[0]
    print(f"🔍 Phát hiện từ khóa: {keyword}")
    
    result = search_blogspot(keyword)
    
    if result['found']:
        posts = result['posts']
        
        # Gửi tin nhắn header
        header = f"🔍 Tìm thấy {len(posts)} bài viết cho: {keyword}"
        await update.message.reply_text(header)
        
        # Gửi TỪNG bài viết riêng biệt với preview
        for i, post in enumerate(posts, 1):
            # Format: Tiêu đề + Link (Telegram tự hiển thị preview)
            message = f"📝 {post['title']}\n🔗 {post['url']}"
            
            try:
                await update.message.reply_text(
                    message,
                    disable_web_page_preview=False  # BẬT preview!
                )
                # Delay nhỏ tránh spam
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Lỗi gửi tin {i}: {e}")
        
        # Gửi tin nhắn cuối với link blog
        footer = f"🔍 Tìm thêm bài viết hữu ích tại: {BLOG_URL}\n👍 Nhớ lưu lại để tham khảo nhé!"
        await update.message.reply_text(footer, disable_web_page_preview=False)
        
        print(f"✅ Đã gửi {len(posts)} link cho: {keyword}")
    else:
        print(f"❌ Không tìm thấy: {keyword}")


def main():
    """Khởi động bot"""
    print("=" * 50)
    print("🤖 TELEGRAM BOT - TỰ ĐỘNG TÌM KIẾM BLOG")
    print("=" * 50)
    print(f"📱 Blog: {BLOG_URL}")
    print(f"🔌 Port: {PORT}")
    print(f"📊 Max results: {MAX_RESULTS}")
    print(f"🔍 Pattern: {PRODUCT_PATTERN.pattern}")
    print("=" * 50)
    
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot đang chạy...")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
