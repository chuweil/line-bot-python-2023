from flask import Flask, request, abort
from api.chat import route as chat_route
from api.keyword import route as keyword_route
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import dotenv
import os

# Priority use environment variable
if ".env" in os.listdir():
    dotenv.load_dotenv()

# 創建 Flask 伺服器
# __name__ 代表目前執行的模組
# 如果以主程式執行，__name__ 會是 __main__
# 如果是被引用，__name__ 會是模組名稱（也就是檔案名稱）
app = Flask(__name__)
# 註冊另一個模組 chat.py 的藍圖
# 註冊後，chat.py 中的路由就會生效
# 但是 chat.py 中的路由前面都會有 chat/ 的前綴 (url_prefix)
app.register_blueprint(chat_route,url_prefix='/chat')
app.register_blueprint(keyword_route,url_prefix='/keyword')

_access_token = os.environ.get('access_token')
_channel_secret = os.environ.get('channel_secret')

# Line Bot API 需要的驗證資訊
configuration = Configuration(access_token=_access_token)
line_handler = WebhookHandler(_channel_secret)


@app.route("/")
def isAlive():
    return "OK"

# 伺服器在收到 POST 請求 /echo 時，會執行 callback 函式處理
@app.route("/echo/", methods=['POST'])
def callback():
    # 獲取 Header 中 X-Line-Signature 的值
    signature = request.headers['X-Line-Signature']

    # 把請求內容取出
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 處理請求
    try:
        # 把 body 跟 signature 交給 handler 做處理
        line_handler.handle(body, signature)
    # 如果有錯誤，把錯誤內容列印出來
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 透過 handler_message 函式處理 MessageEvent 中的 TextMessageContent
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    # MessageEvent 中的 TextMessageContent 大概會有下面這些內容
    # {
    #   "type": "message",
    #   "message": {
    #     "type": "text",
    #     "id": "14353798921116",
    #     "text": "Hello, world"
    #   },
    #   "timestamp": 1625665242211,
    #   "source": {
    #     "type": "user",
    #     "userId": "U80696558e1aa831..."
    #   },
    #   "replyToken": "757913772c4646b784d4b7ce46d12671",
    #   "mode": "active",
    #   "webhookEventId": "01FZ74A0TDDPYRVKNK77XKC3ZR",
    #   "deliveryContext": {
    #     "isRedelivery": false
    #   }
    # }
    # 有些內容我們用不到，所以只取出我們需要的（像是 event.message.text 和 event.reply_token）

    # 透過 ApiClient 建立一個 LineBotApi
    with ApiClient(configuration) as api_client:
        # 透過 LineBotApi 建立一個 MessagingApi
        line_bot_api = MessagingApi(api_client)
        # 回覆訊息
        line_bot_api.reply_message_with_http_info(
            # 回覆訊息的 request
            ReplyMessageRequest(
                reply_token=event.reply_token, 
                messages=[TextMessage(text=event.message.text)]
            )
        )

# 主程式進入點
if __name__ == "__main__":
    # 啟動網路伺服器
    app.run(debug=True)
