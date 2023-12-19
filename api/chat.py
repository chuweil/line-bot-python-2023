# 引入需要的模組
from collections import defaultdict
from flask import request, abort, Blueprint, current_app
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
import google.generativeai as genai
import dotenv
import os
import datetime as dt
import requests

# 如果當前目錄有 .env 檔案，則優先使用 .env 檔案中的環境變數
if ".env" in os.listdir():
    dotenv.load_dotenv()

# 從環境變數中取得需要的資訊
_google_generativeai_token = os.environ.get('google_generativeai_token')
_access_token = os.environ.get('access_token')
_channel_secret = os.environ.get('channel_secret')

# 設定 Google generativeai 的 API 金鑰
genai.configure(api_key=_google_generativeai_token)

# 建立一個新的藍圖
route = Blueprint(name="__chat", import_name=__name__)

# 設定 Line Bot 的設定
configuration = Configuration(access_token=_access_token)
line_handler = WebhookHandler(_channel_secret)

# 從 Google generativeai 中取得所有支援文字生成的模型
models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
print("Available models:")
# Available models:
# models/gemini-pro
# models/gemini-pro-vision
print("\n".join([m.name for m in models]))


# 這些Prompt 對語言模型都算是前文，可以幫助語言模型往更好的方向生成
prompt = """
你是是GDSCxNUK 的 Line 官方帳號
當使用者第一次跟你聊天時，請透過下方資訊介紹你自己
GDSC 是由 Google Developers Student Clubs 的縮寫，是一個由 Google 贊助的學生社群，旨在讓學生學習 Google 技術，並且與其他學生一起建立專案。
而我們是由高雄大學的學生所組成的 GDSC 團隊，我們的目標是讓更多的學生學習到 Google 的技術，並且與其他學生一起建立專案。
https://gdsc.community.dev/national-university-of-kaohsiung/

你也是一個聊天機器人，你可以陪用戶聊天。只能使用繁體中文!
語言模型是由 Google 最近發布的 Gemini 提供技術支持。

請使用不制式的聊天方式(更口語)
你只能根據我所提供的訊息來回覆特定資料的訊息，例如:天氣、時間、日期。
若我沒有告訴你的資料被問到時，請回覆「不知道」或「我不知道」。不要瞎掰，謝謝。
"""

StartMessage = [
    {
        'role': 'user',
        'parts': ["系統 : " + prompt],
    },
    {
        'role': 'model',
        'parts': [
            """
            好我會遵守的!等等用戶跟我說話時，我會先介紹這個官方帳號和GDSCxNUK的資訊。
            """
        ],
    },
]


def getWeather():
    url = "https://opendata.cwb.gov.tw/api/v1/rest/datastore/F-D0047-065?Authorization=CWA-0A877B7D-95C1-4109-A964-8A50A48DBF1B&limit=1&format=JSON&locationName=%E6%A5%A0%E6%A2%93%E5%8D%80&elementName=WeatherDescription"
    res = requests.get(url)
    res = res.json()
    res = res['records']['locations'][0]['location'][0]['weatherElement'][0]['time'][0][
        'elementValue'
    ][0]["value"]
    # EX 陰。降雨機率 30%。溫度攝氏20度。稍有寒意。偏北風 平均風速2-3級(每秒5公尺)。相對濕度77%。
    return res


# 從 Google generativeai 中取得指定的模型
model = genai.GenerativeModel('gemini-pro')
# 建立一個使用者字典，用於儲存不同使用者的歷史訊息
users = defaultdict(lambda: {'history': [msg for msg in StartMessage]})


# 定義一個路由，用於接收 Line Bot 的訊息
@route.route("/", methods=['POST'])
def chat_callback():
    # 取得 Line Bot 的認證資訊
    signature = request.headers['X-Line-Signature']

    # 取得請求的內容
    body = request.get_data(as_text=True)
    current_app.logger.info("Request body: " + body)

    # 處理 webhook 的內容
    # 若驗證失敗，則回傳錯誤訊息 (400)
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        current_app.logger.error(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return 'OK'


# 定義一個處理訊息的函數
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    with ApiClient(configuration) as api_client:
        current_app.logger.debug("User:" + event.source.to_dict()['userId'])
        global users, model
        # 開始聊天，若沒有歷史訊息，則建立一個新的聊天
        history = users[event.source.to_dict()['userId']]['history']

        # 更新天氣資料
        history[0] = StartMessage[0]
        history[0]['parts'][0] = history[0]['parts'][0] + "\n--- 系統訊息 ---\n 楠梓區今天天氣:" + getWeather()

        chat = model.start_chat(history=history)

        # 將使用者的訊息送入Google generativeai中運算
        response = chat.send_message(
            event.message.text + F"\ntime:{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        reply = response.text
        # 使用 Line Bot API 回覆訊息
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=str(reply))]
            )
        )
        # 將聊天的歷史訊息儲存起來
        users[event.source.to_dict()['userId']]['history'] = chat.history
        print("User history:", users[event.source.to_dict()['userId']]['history'])
