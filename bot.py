import re
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# ===== CẤU HÌNH =====
# Lấy token từ biến môi trường (Render sẽ cung cấp)
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
BLOG_URL = "https://blogvnpt.blogspot.com"

# Pattern để phát hiện mã sản phẩm (ví dụ: F6201B, EW12ST)
PRODUCT_PATTERN = re.compile(r'\b[A-Z0-9]{5,10}\b', re.IGNORECASE)


def search_blogspot(keyword):
    """
    Tìm kiếm từ khóa trên blog Blogspot
    Trả về dict với 'found' và thông tin bài viết nếu tìm thấy
    """
    search_url = f"{BLOG_URL}/search?q={quote(keyword)}"
    
    try:
        # Gửi request tìm kiếm
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm bài viết đầu tiên trong kết quả
        first_post = soup.find('h3', class_='post-title entry-title')
        
        if first_post and first_post.find('a'):
            post_url = first_post.find('a')['href']
            post_title = first_post.get_text(strip=True)
            
            # Kiểm tra từ khóa có trong tiêu đề không
            if keyword.lower() in post_title.lower():
                return {
                    'found': True,
                    'url': post_url,
                    'title': post_title
                }
            
            # Nếu có kết quả nhưng không khớp chính xác
            return {
                'found': True,
                'url': search_url,
                'title': f'Kết quả tìm kiếm "{keyword}"'
            }
        
        # Không tìm thấy bài viết nào
        return {'found': False}
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối: {e}")
        return {'found': False}
    except Exception as e:
        print(f"❌ Lỗi xử lý: {e}")
        return {'found': False}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Xử lý tất cả tin nhắn trong group
    Tự động phát hiện mã sản phẩm và tìm kiếm
    """
    # Kiểm tra có tin nhắn text không
    if not update.message or not update.message.text:
        return
    
    message_text = update.message.text
    
    # Tìm tất cả các mã sản phẩm trong tin nhắn
    matches = PRODUCT_PATTERN.findall(message_text)
    
    if not matches:
        return  # Không có mã nào → không làm gì
    
    # Lấy mã đầu tiên tìm được
    keyword = matches[0]
    
    print(f"🔍 Phát hiện từ khóa: {keyword}")
    
    # Tìm kiếm trên blog
    result = search_blogspot(keyword)
    
    # CHỈ trả lời nếu TÌM THẤY
    if result['found']:
        reply_text = (
            f"🔍 Tìm thấy: {keyword}\n"
            f"📝 {result['title']}\n"
            f"🔗 {result['url']}"
        )
        await update.message.reply_text(
            reply_text,
            disable_web_page_preview=False
        )
        print(f"✅ Đã gửi link cho: {keyword}")
    else:
        # KHÔNG tìm thấy → IM LẶNG
        print(f"❌ Không tìm thấy: {keyword}")


def main():
    """Khởi động bot"""
    print("=" * 50)
    print("🤖 TELEGRAM BOT - TỰ ĐỘNG TÌM KIẾM BLOG")
    print("=" * 50)
    print(f"📱 Blog: {BLOG_URL}")
    print(f"🔍 Pattern: {PRODUCT_PATTERN.pattern}")
    print("=" * 50)
    
    # Tạo application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Thêm handler để xử lý TẤT CẢ tin nhắn text
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )
    
    print("✅ Bot đang chạy...")
    print("=" * 50)
    
    # Chạy bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()