import os
from urllib.request import urlopen
import urllib.parse
import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class TelegramUtil:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.chat_test_id = os.getenv('TELEGRAM_CHAT_TEST_ID')

    def send_message(self, message):
        """일반 메시지 전송"""
        message = urllib.parse.quote_plus(message)
        urlopen(f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_id}&parse_mode=html&text={message}")

    def send_photo(self, photo_path, caption=""):
        """이미지 전송"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        
        with open(photo_path, 'rb') as photo:
            payload = {
                "chat_id": self.chat_id,
                "caption": caption,
                "parse_mode": "html"
            }
            files = {
                "photo": photo
            }
            response = requests.post(url, data=payload, files=files)
        
        return response.json()

    def send_test_message(self, message):
        """테스트용 채팅방으로 메시지 전송"""
        message = urllib.parse.quote_plus(message)
        urlopen(f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_test_id}&parse_mode=html&text={message}") 