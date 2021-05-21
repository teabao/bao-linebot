# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from __future__ import unicode_literals

import datetime
import errno
import json
import os
import sys
import tempfile
from argparse import ArgumentParser

import cv2
import numpy as np
from flask import Flask, abort, request, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (AudioMessage, BeaconEvent, BoxComponent,
                            BubbleContainer, ButtonComponent, ButtonsTemplate,
                            CameraAction, CameraRollAction, CarouselColumn,
                            CarouselTemplate, ConfirmTemplate,
                            DatetimePickerAction, FileMessage, FlexSendMessage,
                            FollowEvent, IconComponent, ImageCarouselColumn,
                            ImageCarouselTemplate, ImageComponent,
                            ImageMessage, ImageSendMessage, JoinEvent,
                            LeaveEvent, LocationAction, LocationMessage,
                            LocationSendMessage, MemberJoinedEvent,
                            MemberLeftEvent, MessageAction, MessageEvent,
                            PostbackAction, PostbackEvent, QuickReply,
                            QuickReplyButton, SeparatorComponent, SourceGroup,
                            SourceRoom, SourceUser, StickerMessage,
                            StickerSendMessage, TemplateSendMessage,
                            TextComponent, TextMessage, TextSendMessage,
                            UnfollowEvent, URIAction, VideoMessage)
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1)

channel_secret = '8893c3c1421c8b2121793e3060c24893'
channel_access_token = 'iKKtciUxaXGDNNJAwJeEWyEYjeJP2LX/HUZJFeKTFTZOjtL17KY/3i181F+NO+wSiFINyjnanZfD77I3LfTMslP/L2bUYqsO/xSCd8MKKZqKvo84Dp7Dbn6ftAi9KrtDowO3BgfZsCuMfSDij0PWJQdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# function for create tmp dir for download content


def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise


def end_msg(event, filename, txt):
    bubble_string = """
        {
          "type": "bubble",
          "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
              {
                "type": "image",
                "url": """+'"'+request.url_root + '/static/'+filename+'"'+""",
                "position": "relative",
                "size": "full",
                "aspectMode": "cover",
                "aspectRatio": "1:1",
                "gravity": "center"
              },
              {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                  {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                      {
                        "type": "text",
                        "text": "遊戲結束",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#ffffff"
                      }
                    ]
                  },
                  {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                      {
                        "type": "text",
                        "text": """+'"'+txt+'"'+""",
                        "color": "#ebebeb",
                        "size": "xl",
                        "align": "end"
                      }
                    ]
                  }
                ],
                "position": "absolute",
                "offsetBottom": "0px",
                "offsetStart": "0px",
                "offsetEnd": "0px",
                "backgroundColor": "#00000099",
                "paddingAll": "20px"
              }
            ],
            "paddingAll": "0px"
          }
        }
        """
    message = FlexSendMessage(alt_text="hello", contents=json.loads(bubble_string))
    return message


def intro_msg():
    bubble = BubbleContainer(
        direction='ltr',
        hero=ImageComponent(
            url=request.url_root + '/static/poster.jpg',
            size='full',
            aspect_ratio='20:13',
            aspect_mode='cover'
        ),
        body=BoxComponent(
            layout='vertical',
            contents=[
                TextComponent(text='Tic Tac Toe (井字遊戲)', weight='bold', size='xl'),
                BoxComponent(
                    layout='vertical',
                    margin='lg',
                    spacing='sm',
                    contents=[
                        TextComponent(
                            text='在線上隨機配對玩家，挑戰你的對手！',
                            color='#aaaaaa',
                            size='sm',
                            flex=1
                        )
                    ],
                )
            ],
        ),
        footer=BoxComponent(
            layout='vertical',
            spacing='sm',
            contents=[
                ButtonComponent(
                    style='link',
                    height='sm',
                    action=URIAction(label='Github', uri='https://github.com/teabao/bao-linebot')
                ),
                SeparatorComponent(),
                ButtonComponent(
                    style='link',
                    height='sm',
                    action=MessageAction(label='尋找配對', text='配對')
                )
            ]
        ),
    )
    message = FlexSendMessage(alt_text="hello", contents=bubble)
    return message


# ! user_information
user_waiting = []

user = {}


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        print("Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            print("  %s: %s" % (m.property, m.message))
        print("\n")
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text.strip()

    if text == '配對':

        if user_waiting and user_waiting[0]['user_id'] == event.source.user_id:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='配對中...'))

        elif user_waiting:
            opponent = user_waiting.pop(0)
            myself = {
                'name': line_bot_api.get_profile(event.source.user_id).display_name,
                'user_id': event.source.user_id,
                'opponent_id': opponent['user_id']
            }
            opponent['opponent_id'] = myself['user_id']

            url = request.url_root + '/static/grid.jpg'
            app.logger.info("url=" + url)
            line_bot_api.reply_message(
                event.reply_token,
                [
                    TextSendMessage(text='你配對到了'+opponent['name']),
                    ImageSendMessage(url, url),
                    TextSendMessage(text='在圖片上畫圈圈叉叉後回傳~')
                ]
            )

            line_bot_api.push_message(opponent['user_id'], [
                TextSendMessage(text='你配對到了'+myself['name']),
                TextSendMessage(text='等待你的對手...')
            ])

            user[myself['user_id']] = myself
            user[myself['user_id']]['is_gaming'] = True
            user[myself['user_id']]['my_turn'] = True
            user[myself['user_id']]['valid_grid'] = np.ones(shape=(3, 3), dtype=bool)

            user[opponent['user_id']] = opponent
            user[opponent['user_id']]['is_gaming'] = True
            user[opponent['user_id']]['my_turn'] = False
            user[opponent['user_id']]['img_backup'] = '/app/static/grid.jpg'
            user[opponent['user_id']]['valid_grid'] = np.ones(shape=(3, 3), dtype=bool)

        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='配對中...'))

            user_waiting.append({
                'name': line_bot_api.get_profile(event.source.user_id).display_name,
                'user_id': event.source.user_id
            })
    elif text == 'qc':
        quota_consumption = line_bot_api.get_message_quota_consumption()
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(text='total usage: ' + str(quota_consumption.total_usage)),
            ]
        )
    else:
        line_bot_api.reply_message(event.reply_token, intro_msg())


@handler.add(MessageEvent, message=ImageMessage)
def handle_content_message(event):
    id = event.source.user_id
    opponent_id = user[id]['opponent_id']

    if not user[id]['is_gaming']:
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage(text='目前還沒有配對~')
        ])
        return
    elif not user[id]['my_turn']:
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage(text='還沒有輪到你哦~')
        ])

    ext = 'jpg'
    message_content = line_bot_api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        filename = tf.name.split('/')[-1]
        user[id]['img_backup'] = tf.name

    url = request.url_root + '/static/tmp/'+filename
    app.logger.info("url=" + url)

    # ! image diff check
    img_new = cv2.imread(user[id]['img_backup'])
    img_new = cv2.resize(img_new, (300, 300), interpolation=cv2.INTER_AREA)
    img_old = cv2.imread(user[opponent_id]['img_backup'])
    img_old = cv2.resize(img_old, (300, 300), interpolation=cv2.INTER_AREA)

    print('img_backup')
    print(user[id]['img_backup'])
    print(user[opponent_id]['img_backup'])
    print(img_new.shape)
    print(img_old.shape)

    # center of diff pixel
    center = [0, 0]

    # ! cut grid and none valid grid
    diff = np.abs(img_new - img_old)
    diff[85:115, :, :] = 0
    diff[185:215, :, :] = 0
    diff[:, 85:115, :] = 0
    diff[:, 185:215, :] = 0

    count_non_zero = 0
    for i in range(3):
        for j in range(3):
            x = i*100+50
            y = j*100+50
            if not user[id]['valid_grid'][i, j] or not user[opponent_id]['valid_grid'][i, j]:
                diff[x-50:x+49, y-50:y+49, :] = 0
            if len(np.where(diff[x-50:x+49, y-50:y+49, :] > 100)[0]) > 0:
                print(i, j, ' : non-zero,   len:', len(np.where(diff[x-50:x+49, y-50:y+49, :] > 100)[0]))
                count_non_zero += 1

    pos = np.where(diff != 0)
    num = len(pos[0])

    if num == 0 or count_non_zero > 1 or count_non_zero == 0:
        line_bot_api.reply_message(event.reply_token, [
            TextSendMessage(text='你畫的位置或顏色有點奇怪喔~'),
            TextSendMessage(text='請重傳~')
        ])
        return

    for k in range(2):
        for i in range(num):
            center[k] += pos[k][i]
        center[k] = center[k]/num

    print("center", center)

    minimum_dis = float('inf')
    minimum_i = 0
    minimum_j = 0

    for i in range(3):
        for j in range(3):
            x = i*100+50
            y = j*100+50
            dis = (x-center[0])**2 + (y-center[1])**2
            print(i, j, dis)
            if dis < minimum_dis:
                minimum_dis = dis
                minimum_i, minimum_j = i, j

    print(minimum_i, minimum_j)
    user[id]['valid_grid'][minimum_i, minimum_j] = False

    # ! end check

    is_end = False
    for i in range(3):
        if np.sum(user[id]['valid_grid'][i, :]) == 0:
            is_end = True
        if np.sum(user[id]['valid_grid'][:, i]) == 0:
            is_end = True
    if not user[id]['valid_grid'][0, 0] and not user[id]['valid_grid'][1, 1] and not user[id]['valid_grid'][2, 2]:
        is_end = True
    if not user[id]['valid_grid'][2, 0] and not user[id]['valid_grid'][1, 1] and not user[id]['valid_grid'][0, 2]:
        is_end = True

    if is_end:
        line_bot_api.reply_message(event.reply_token, [
            end_msg(event, 'win.png', '你贏了'),
            intro_msg()
        ])
        line_bot_api.push_message(opponent_id, [
            ImageSendMessage(url, url),
            end_msg(event, 'cat.jpg', '你輸了'),
            intro_msg()
        ])

    count = 0
    for i in range(3):
        for j in range(3):
            if not user[id]['valid_grid'][i, j] or not user[opponent_id]['valid_grid'][i, j]:
                count += 1
    if count == 9 and not is_end:
        line_bot_api.reply_message(event.reply_token, [
            end_msg(event, 'hand.jpg', '平手'),
            intro_msg()
        ])
        line_bot_api.push_message(opponent_id, [
            ImageSendMessage(url, url),
            end_msg(event, 'hand.jpg', '平手'),
            intro_msg()
        ])
        is_end = True

    if count == 9 or is_end:
        user[id]['is_gaming'] = False
        user[opponent_id]['is_gaming'] = False

    #! ======

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text='等待你的對手...'))

    # cv2.imwrite('/app/static/tmp/diff.jpg', diff)
    # url2 = request.url_root + '/static/tmp/diff.jpg'
    # app.logger.info("url2=" + url2)

    line_bot_api.push_message(opponent_id, [

        # ImageSendMessage(url2, url2),
        ImageSendMessage(url, url),
        TextSendMessage(text='輪到你了'),
        TextSendMessage(text='在圖片上畫圈圈叉叉後回傳~')
    ])

    user[id]['my_turn'] = False
    user[opponent_id]['my_turn'] = True


@ handler.add(FollowEvent)
def handle_follow(event):
    app.logger.info("Got Follow event:" + event.source.user_id)
    line_bot_api.reply_message(event.reply_token, intro_msg())


@ app.route('/static/<path:path>')
def send_static_content(path):
    return send_from_directory('static', path)


if __name__ == "__main__":
    make_static_tmp_dir()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
