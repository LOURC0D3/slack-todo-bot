import os
from dotenv import load_dotenv

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.sanic import AsyncSlackRequestHandler

from prisma import Prisma
from prisma.utils import async_run

import asyncio
import datetime
import time
import random
import markdown
from bs4 import BeautifulSoup
import requests
import re

from sanic import Sanic
from sanic.request import Request

from saying import getRandomSaying

load_dotenv()

class App(AsyncApp):
    def __init__(self):
        super().__init__(token=os.environ.get("SLACK_BOT_TOKEN"), signing_secret=os.environ.get("SLACK_SIGNING_SECRET"))
        self.prisma = Prisma()

        self.api = Sanic(__name__)
        self.app_handler = AsyncSlackRequestHandler(self)

    async def get_user_by_slack_id(self, slack_id):
        user = await self.prisma.user.find_unique(where={'slack_id': slack_id})

        if user == None:
            user = await self.prisma.user.create(data={'slack_id': slack_id, 'user_setting': {'create': {}}})

        return user

    async def task_cleaner(self):
        while True:
            set_time_stamp = int(time.mktime(datetime.datetime.strptime(
                f"{str(datetime.datetime.now() + datetime.timedelta(days=1)).split(' ')[0]} 00:00:00", "%Y-%m-%d %H:%M:%S").timetuple()))

            now_date_stamp = int(datetime.datetime.now().timestamp())

            await asyncio.sleep(set_time_stamp - now_date_stamp)

            now_date_stamp = int(datetime.datetime.now().timestamp())

            users = await self.prisma.user.find_many(include={'tasks': True})
            for user in users:
                for task in user.tasks:
                    task_time_stamp = int(time.mktime(datetime.datetime.strptime(
                        f"{task.due_date} 23:59:59", "%Y-%m-%d %H:%M:%S").timetuple()))

                    if task.is_clear:
                        await self.prisma.task.delete(where={'id': task.id})
                    elif task_time_stamp - now_date_stamp <= 0:
                        await self.prisma.task.delete(where={'id': task.id})
                await publish_home_tab(self.client, user.slack_id, user.slack_id)

    async def daily_message_sender(self):
        while True:
            set_time_stamp = int(time.mktime(datetime.datetime.strptime(
                f"{str(datetime.datetime.now() + datetime.timedelta(days=1)).split(' ')[0]} 09:30:00", "%Y-%m-%d %H:%M:%S").timetuple()))

            now_date_stamp = int(datetime.datetime.now().timestamp())

            await asyncio.sleep(set_time_stamp - now_date_stamp)

            news_num = 4
            news_url = 'https://search.naver.com/search.naver?where=news&query=%EA%B2%BD%ED%96%A5%EC%8B%A0%EB%AC%B8&sm=tab_clk.jou&sort=0&photo=0&field=0&pd=0&ds=&de=&docid=&related=0&mynews=0&office_type=&office_section_code=&news_office_checked=&nso=&is_sug_officeid=1'

            req = requests.get(news_url)
            soup = BeautifulSoup(req.text, 'html.parser')

            title_list = []
            url_list = []
            idx = 0

            while idx < news_num:
                table = soup.find('ul', {'class': 'list_news'})
                li_list = table.find_all(
                    'li', {'id': re.compile('sp_nws.*')})
                area_list = [
                    li.find('div', {'class': 'news_area'}) for li in li_list]
                a_list = [area.find('a', {'class': 'news_tit'})
                          for area in area_list]

                for n in a_list[:min(len(a_list), news_num-idx)]:
                    title_list.append(n.get('title'))
                    url_list.append(n.get('href'))

                    idx += 1

            users = await self.prisma.usersetting.find_many(where={'notification_news': True}, include={'user': True})
            for user in users:
                await self.client.chat_postMessage(channel=user.user.slack_id, attachments=[
                    {
                        "color": "#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)]),
                        "blocks": [
                            {
                                "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": "🌞 좋은 아침이에요. <@" + user.user.slack_id + ">님!"
                                        },
                                "accessory": {
                                            "type": "button",
                                            "text": {
                                                "type": "plain_text",
                                                "text": "할 일 생성",
                                                        "emoji": True
                                            },
                                            "style": "primary",
                                            "action_id": "on_click_create_todo"
                                        }
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "section",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "회원님을 위해 오늘의 기사를 준비해왔어요!",
                                            "emoji": True
                                        }
                            },
                            {
                                "type": "section",
                                        "fields": [
                                            {
                                                "type": "mrkdwn",
                                                "text": "- <" + url_list[0] + "|" + title_list[0] + ">"
                                            },
                                            {
                                                "type": "mrkdwn",
                                                "text": "- <" + url_list[1] + "|" + title_list[1] + ">"
                                            },
                                            {
                                                "type": "mrkdwn",
                                                "text": "- <" + url_list[2] + "|" + title_list[2] + ">"
                                            },
                                            {
                                                "type": "mrkdwn",
                                                "text": "- <" + url_list[3] + "|" + title_list[3] + ">"
                                            }
                                        ]
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": "그럼, 오늘도 힘내세요! 👋"
                                        }
                            },
                            {
                                "type": "divider"
                            }
                        ]
                    }
                ]
                )


app = App()


@ app.api.post("/slack/events")
async def events_handler(req: Request):
    return await app.app_handler.handle(req)


@ app.command("/todo")
async def todo_command(ack, body, client):
    await ack()

    await open_todo_submit_modal(client, body["trigger_id"], body["user_id"])


@ app.shortcut("message_shortcut")
async def message_shortcut(ack, body, client):
    await ack()

    user_id = body["user"]["id"]
    user = await app.get_user_by_slack_id(user_id)
    title = body["message"]["text"].replace(
        "\n", " ").replace("\r", " ").replace("\t", " ")
    author_id = body["message"]["user"]

    html = markdown.markdown(title)
    soup = BeautifulSoup(html, features='html.parser')
    title = soup.get_text()

    if len(title) > 100:
        title = title[:100] + "..."

    await app.prisma.task.create(
        data={
            "title": title,
            "due_date": datetime.datetime.now(
            ).strftime('%Y-%m-%d'),
            "description": f"<@{author_id}>님이 작성함",
            "is_personal": False,
            "user": {
                "connect": {
                    "id": user.id
                }
            }
        })


@ app.event("app_home_opened")
async def opened_home_tab(client, event, logger):
    await publish_home_tab(client, event["user"], event["user"])


@ app.action("none")
async def none_action(ack, body, client):
    await ack()


@ app.action("on_click_next_button_in_home_tab")
async def on_click_next_button_in_home_tab(ack, body, client):
    await ack()

    if body["view"]["blocks"][5]["elements"][0]["value"] == "prev":
        page = int(body["view"]["blocks"][5]["elements"][1]["value"])
    else:
        page = int(body["view"]["blocks"][5]["elements"][0]["value"])

    await publish_home_tab(client, body["user"]["id"], body["view"]["blocks"][0]["elements"][0]["initial_user"], page+1)


@ app.action("on_click_prev_button_in_home_tab")
async def on_click_prev_button_in_home_tab(ack, body, client):
    await ack()

    if body["view"]["blocks"][5]["elements"][0]["value"] == "prev":
        page = int(body["view"]["blocks"][5]["elements"][1]["value"])
    else:
        page = int(body["view"]["blocks"][5]["elements"][0]["value"])

    await publish_home_tab(client, body["user"]["id"], body["view"]["blocks"][0]["elements"][0]["initial_user"], page-1)


@ app.action("on_click_task_checkbox_in_home_tab")
async def on_click_task_checkbox_in_home_tab(ack, body, client):
    await ack()

    if body["view"]["blocks"][5]["elements"][0]["value"] == "prev":
        page = int(body["view"]["blocks"][5]["elements"][1]["value"])
    else:
        page = int(body["view"]["blocks"][5]["elements"][0]["value"])

    if body["view"]["blocks"][0]["elements"][0]["initial_user"] != body["user"]["id"]:
        await client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "title": {
                    "type": "plain_text",
                    "text": "권한 없음"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "다른 사람의 할 일을 완료할 수 없습니다."
                        }
                    }
                ]
            }
        )
        await publish_home_tab(client, body["user"]["id"], body["view"]["blocks"][0]["elements"][0]["initial_user"], page)
        return

    user = await app.get_user_by_slack_id(body["user"]["id"])
    tasks = await app.prisma.task.find_many(
        where={
            'user_id': user.id
        },
        take=8,
        skip=(page - 1) * 7,
        order={
            "created_at": "desc"
        }
    )
    if len(tasks) == 8:
        tasks.pop(-1)

    for task in tasks:
        await app.prisma.task.update(
            where={'id': task.id},
            data={'is_clear': False}
        )
        for option in body["actions"][0]["selected_options"]:
            if task.id == int(option["value"].split("-")[1]):
                await app.prisma.task.update(
                    where={'id': task.id},
                    data={'is_clear': True}
                )

    all_tasks = await app.prisma.task.find_many(where={"user_id": user.id})
    all_completed_tasks = await app.prisma.task.find_many(where={"user_id": user.id, "is_clear": True})

    if len(all_tasks) == len(all_completed_tasks):
        user_options = await app.prisma.usersetting.find_unique(
            where={
                'user_id': user.id
            }
        )

        if user_options.conversation != None:
            await client.chat_postMessage(
                channel=user_options.conversation, text='할 일 완료!', blocks=[{
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🎉 <@" + user.slack_id + ">님이 모든 할 일을 완료하였습니다!",
                    }
                }])

        await app.client.chat_postMessage(channel=user.slack_id, text='할 일 완료!', blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "수고하셨습니다. <@" + user.slack_id + ">님!"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "오늘도 고생하셨을 <@" + user.slack_id + ">님을 위해 명언을 준비 해보았습니다. 📚"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "> *" + getRandomSaying() + "*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "제가 준비한 게 도움이 되었으면 좋겠네요. 😁\n그럼, 남은 하루 즐겁게 보내시길 바래요! 👋"
                }
            },
            {
                "type": "divider"
            }
        ])

    await publish_home_tab(client, body["user"]["id"], body["user"]["id"], page)


@ app.action("on_click_create_todo")
@ app.shortcut("global_shortcut")
async def on_click_create_todo(ack, body, client):
    await ack()

    await open_todo_submit_modal(client, body["trigger_id"], body["user"]["id"])


@ app.action("on_click_setting_button_in_home_tab")
async def on_click_setting_button_in_home_tab(ack, body, client):
    await ack()

    await open_setting_home_tab(client, body["user"]["id"])


@ app.action("on_click_back_button_in_setting_home_tab")
async def on_click_back_button_in_setting_home_tab(ack, body, client):
    await ack()

    await publish_home_tab(client, body["user"]["id"], body["user"]["id"])


@ app.action("on_click_save_button_in_setting_home_tab")
async def on_click_save_button_in_setting_home_tab(ack, body, client):
    await ack()

    user_id = body["user"]["id"]

    public_tasks = False
    notification_news = False
    send_quotes = False

    for j in body["view"]["state"]["values"].values():
        for item in j.values():
            if item["type"] == "checkboxes":
                for i in item["selected_options"]:
                    if i["value"] == "set-public-tasks":
                        public_tasks = True
                    elif i["value"] == "set-notification-news":
                        notification_news = True
                    elif i["value"] == "set-send-quotes":
                        send_quotes = True
            elif item["type"] == "conversations_select":
                channel_id = item["selected_conversation"]

    user = await app.get_user_by_slack_id(user_id)
    await app.prisma.usersetting.update(
        where={'user_id': user.id},
        data={
            'public_tasks': public_tasks,
            'notification_news': notification_news,
            'send_quotes': send_quotes,
            'conversation': channel_id
        }
    )

    await open_setting_home_tab(client, user_id)


async def open_setting_home_tab(client, user_id):
    user = await app.get_user_by_slack_id(user_id)
    user_options = await app.prisma.usersetting.find_unique(where={'user_id': user.id})

    if user_options.conversation == None:
        conversation_post = {
            "type": "input",
            "element": {
                "type": "conversations_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "해당 없음",
                    "emoji": True
                },
                "filter": {
                    "include": [
                        "public"
                    ]
                },
            },
            "label": {
                "type": "plain_text",
                "text": "소속 채널 설정",
                "emoji": True
            }
        }
    else:
        conversation_post = {
            "type": "input",
            "element": {
                "type": "conversations_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "해당 없음",
                    "emoji": True
                },
                "initial_conversation": user_options.conversation,
                "filter": {
                    "include": [
                        "public"
                    ]
                },
            },
            "label": {
                "type": "plain_text",
                "text": "소속 채널 설정",
                "emoji": True
            }
        }

    public_tasks = user_options.public_tasks
    notification_news = user_options.notification_news
    send_quotes = user_options.send_quotes

    setting_checked = []
    if public_tasks:
        setting_checked.append({
            "text": {
                "type": "plain_text",
                "text": "작업 목록 공개"
            },
            "description": {
                "type": "plain_text",
                "text": "나의 작업 목록을 공개로 설정합니다."
            },
            "value": "set-public-tasks"
        })
    if notification_news:
        setting_checked.append({
            "text": {
                "type": "plain_text",
                "text": "뉴스 알림 수신"
            },
            "description": {
                "type": "plain_text",
                "text": "아침 9시 30분에 오늘의 뉴스를 받습니다."
            },
            "value": "set-notification-news"
        })
    if send_quotes:
        setting_checked.append({
            "text": {
                "type": "plain_text",
                "text": "작업 완료 메세지 수신"
            },
            "description": {
                "type": "plain_text",
                "text": "작업을 완료하면 메세지를 받거나 받습니다."
            },
            "value": "set-send-quotes"
        })

    if len(setting_checked) != 0:
        checkboxes_post = {
            "type": "checkboxes",
            "initial_options": setting_checked,
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "작업 목록 공개"
                    },
                    "description": {
                        "type": "plain_text",
                        "text": "나의 작업 목록을 공개로 설정합니다."
                    },
                    "value": "set-public-tasks"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "뉴스 알림 수신"
                    },
                    "description": {
                        "type": "plain_text",
                        "text": "아침 9시 30분에 오늘의 뉴스를 받습니다."
                    },
                    "value": "set-notification-news"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "작업 완료 메세지 수신"
                    },
                    "description": {
                        "type": "plain_text",
                        "text": "작업을 완료하면 메세지를 받거나 받습니다."
                    },
                    "value": "set-send-quotes"
                }
            ]
        }
    else:
        checkboxes_post = {
            "type": "checkboxes",
            "options": [
                {
                    "text": {
                        "type": "plain_text",
                        "text": "작업 목록 공개"
                    },
                    "description": {
                        "type": "plain_text",
                        "text": "나의 작업 목록을 공개로 설정합니다."
                    },
                    "value": "set-public-tasks"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "뉴스 알림 수신"
                    },
                    "description": {
                        "type": "plain_text",
                        "text": "아침 9시 30분에 오늘의 뉴스를 받습니다."
                    },
                    "value": "set-notification-news"
                },
                {
                    "text": {
                        "type": "plain_text",
                        "text": "작업 완료 메세지 수신"
                    },
                    "description": {
                        "type": "plain_text",
                        "text": "작업을 완료하면 메세지를 받거나 받습니다."
                    },
                    "value": "set-send-quotes"
                }
            ]
        }

    await client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": [
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "action_id": "on_click_back_button_in_setting_home_tab",
                                "style": "danger",
                                "text": {
                                    "type": "plain_text",
                                    "text": "←"
                                }
                            },
                            {
                                "type": "button",
                                "action_id": "on_click_save_button_in_setting_home_tab",
                                "style": "primary",
                                "text": {
                                    "type": "plain_text",
                                    "text": "저장"
                                }
                            }
                        ]
                    },
                {
                        "type": "divider"
                        },
                {
                        "type": "input",
                        "element": checkboxes_post,
                        "label": {
                            "type": "plain_text",
                            "text": "⚙️ 설정",
                            "emoji": True
                        }
                        },
                conversation_post
            ]
        }
    )


async def publish_home_tab(client, user_id, selected_user, page=1):
    user = await app.get_user_by_slack_id(selected_user)
    req_user = await app.get_user_by_slack_id(user_id)

    user_options = await app.prisma.usersetting.find_unique(where={"user_id": user.id})

    content = []

    if selected_user != user_id and not user_options.public_tasks:
        content.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔒 <@{selected_user}>님의 작업 목록은 비공개입니다."
            }
        })
    else:
        all_tasks = await app.prisma.task.find_many(where={"user_id": user.id})
        all_completed_tasks = await app.prisma.task.find_many(where={"user_id": user.id, "is_clear": True})

        tasks = await app.prisma.task.find_many(
            where={
                "user_id": user.id,
            },
            take=8,
            skip=(page - 1) * 7,
            order={
                "created_at": "desc"
            }
        )

        active_next_page = False
        active_prev_page = False

        if page > 1:
            active_prev_page = True

        if len(tasks) == 8:
            tasks.pop(-1)
            active_next_page = True

        tasks_post = []
        completed_tasks_post = []
        for task in tasks:
            personal_description = ""
            if task.is_personal:
                personal_description = " | 🔒"
                if task.user_id != req_user.id:
                    continue
            tmp = {
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{task.title}*"
                },
                "description": {
                    "type": "mrkdwn",
                    "text": f"*{task.due_date}*\n_{task.description}_{personal_description}"
                },
                "value": f"task-{task.id}"
            }
            tasks_post.append(tmp)

            if task.is_clear:
                completed_tasks_post.append(tmp)

        if len(tasks_post) == 0:
            content.append({
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "🥱 오늘은 예정된 할 일이 없네요.",
                    "emoji": True
                }
            })
        else:
            if len(completed_tasks_post) == 0:
                element = {
                    "type": "checkboxes",
                    "options": tasks_post,
                    "action_id": "on_click_task_checkbox_in_home_tab"
                }
            else:
                element = {
                    "type": "checkboxes",
                    "options": tasks_post,
                    "initial_options": completed_tasks_post,
                    "action_id": "on_click_task_checkbox_in_home_tab"
                }
            content.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<@{selected_user}>님의 오늘 할 일 목록입니다.\n*진행률 - {round(len(all_completed_tasks) / (len(all_tasks)) * 100.0)}%*",
                    }
                },
            )
            content.append({
                "type": "actions",
                "elements": [
                    element
                ]
            })

        pagination_post = []
        if active_prev_page:
            pagination_post.append(
                {
                    "type": "button",
                    "style": "primary",
                    "action_id": f"on_click_prev_button_in_home_tab",
                    "text": {
                        "type": "plain_text",
                        "text": "←"
                    },
                    "value": "prev"
                }
            )
        pagination_post.append(
            {
                "type": "button",
                "action_id": f"none",
                "text": {
                        "type": "plain_text",
                        "text": f"{page}",
                        "emoji": True
                },
                "value": f"{page}",
            },
        )
        if active_next_page:
            pagination_post.append(
                {
                    "type": "button",
                    "style": "primary",
                    "action_id": f"on_click_next_button_in_home_tab",
                    "text": {
                        "type": "plain_text",
                        "text": "→"
                    },
                    "value": "next"
                }
            )

        content.append({
            "type": "divider",
        })
        content.append({
            "type": "actions",
            "elements": pagination_post
        })

    blocks = [
        {
            "type": "actions",
            "elements": [
                {
                    "type": "users_select",
                    "action_id": "select_user_in_home_tab",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "유저를 선택해주세요",
                        "emoji": True
                    },
                    "initial_user": selected_user
                },
                {
                    "type": "button",
                    "action_id": "on_click_create_todo",
                    "style": "primary",
                    "text": {
                        "type": "plain_text",
                        "text": "할 일 생성",
                        "emoji": True
                    },
                    "value": "on_click_create_todo"
                },
                {
                    "type": "button",
                    "action_id": "on_click_setting_button_in_home_tab",
                    "text": {
                        "type": "plain_text",
                        "text": "설정",
                        "emoji": True
                    },
                    "value": "on_click_setting_button_in_home_tab"
                }
            ]
        },
        {
            "type": "divider"
        },
    ]
    blocks.extend(content)

    await client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "blocks": blocks
        }
    )


@ app.action("select_user_in_home_tab")
async def on_click_user_select(ack, body, client):
    await ack()

    selected_user = body["actions"][0]["selected_user"]
    await publish_home_tab(client, body["user"]["id"], selected_user)


async def open_todo_submit_modal(client, trigger_id, user_id):
    user = await app.get_user_by_slack_id(user_id)
    user_options = await app.prisma.usersetting.find_unique(where={"user_id": user.id})

    if user_options.conversation != None:
        conversation_post = {
            "type": "conversations_select",
            "action_id": "input_conversation",
            "placeholder": {
                "type": "plain_text",
                "text": "채널을 선택하세요.",
                "emoji": True
            },
            "initial_conversation": user_options.conversation,
            "filter": {
                "include": ["public"],
                "exclude_bot_users": True,
            }
        }
    else:
        conversation_post = {
            "type": "conversations_select",
            "action_id": "input_conversation",
            "placeholder": {
                "type": "plain_text",
                "text": "채널을 선택하세요.",
                "emoji": True
            },
            "filter": {
                "include": ["public"],
                "exclude_bot_users": True,
            }
        }

    await client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": "todo_submit",
            "title": {
                "type": "plain_text",
                "text": "작업 생성",
                "emoji": True
            },
            "submit": {
                "type": "plain_text",
                "text": "제출",
                "emoji": True
            },
            "close": {
                "type": "plain_text",
                "text": "취소",
                "emoji": True
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "input_title",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "input_title",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "할 일을 입력하세요. (줄바꿈으로 여러개 입력 가능, 최대 10개)",
                            "emoji": True
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "💬 할 일",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "block_id": "input_date",
                    "element": {
                        "type": "datepicker",
                        "action_id": "input_date",
                        "initial_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "placeholder": {
                            "type": "plain_text",
                            "text": "날짜를 선택하세요.",
                            "emoji": True
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "📅 마감일",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "block_id": "input_assignee",
                    "element": {
                        "type": "multi_users_select",
                        "action_id": "input_assignee",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "담당자를 선택하세요.",
                            "emoji": True
                        },
                        "initial_users": [user_id]
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "👨‍👩‍👧‍👦 담당자",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "block_id": "input_conversation",
                    "optional": True,
                    "element": conversation_post,
                    "label": {
                        "type": "plain_text",
                        "text": "🌈 채널",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "block_id": "input_description",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "input_description",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "할 일에 대한 설명을 입력하세요.",
                            "emoji": True
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "📝 노트",
                        "emoji": True
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "block_id": "is_personal_task",
                    "optional": True,
                    "element": {
                        "type": "checkboxes",
                        "action_id": "is_personal_task",
                        "options": [
                            {
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*개인 작업*"
                                },
                                "description": {
                                    "type": "mrkdwn",
                                    "text": "해당 할 일은 본인 이외에는 조회할 수 없습니다."
                                },
                            }
                        ]
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "⚙️ 설정",
                        "emoji": True
                    }
                }
            ]
        }
    )


@ app.view("todo_submit")
async def todo_submit(ack, body, client):

    user_id = body["user"]["id"]
    trigger_id = body["trigger_id"]

    title = body["view"]["state"]["values"]["input_title"]["input_title"]["value"]
    due_date = body["view"]["state"]["values"]["input_date"]["input_date"]["selected_date"]
    description = body["view"]["state"]["values"]["input_description"]["input_description"]["value"]
    assignees = body["view"]["state"]["values"]["input_assignee"]["input_assignee"]["selected_users"]
    conversation = body["view"]["state"]["values"]["input_conversation"]["input_conversation"]["selected_conversation"]
    is_personal_task = len(body["view"]["state"]["values"]
                           ["is_personal_task"]["is_personal_task"]["selected_options"]) != 0

    tasks = title.splitlines()

    if len(tasks) > 10:
        await ack(
            response_action="errors",
            errors={
                "input_title": "할 일은 10개를 초과하여 등록할 수 없습니다."
            }
        )
        return
    await ack()

    if description == None:
        description = ''
    assignee_description = description + "  |  <@" + user_id + ">님이 추가함"

    for assignee in assignees:
        found = await app.get_user_by_slack_id(assignee)

        for task in tasks:
            task = task.strip()

            if assignee != user_id:
                await app.prisma.task.create(
                    data={
                        "title": task,
                        "due_date": due_date,
                        "description": assignee_description,
                        "is_personal": is_personal_task,
                        "user": {
                            "connect": {
                                "id": found.id
                            }
                        }
                    })
            else:
                await app.prisma.task.create(
                    data={
                        "title": task,
                        "due_date": due_date,
                        "description": description,
                        "is_personal": is_personal_task,
                        "user": {
                            "connect": {
                                "id": found.id
                            }
                        }
                    })

    if conversation != None:
        task_post = []
        assignee_post = []

        for task in tasks:
            task_post.append({
                "value":  f"• *{task}*",
                "short": True
            })
        for assignee in assignees:
            assignee_post.append(f"<@{assignee}> ")

        due_date_time_stamp = datetime.datetime.strptime(
            due_date, "%Y-%m-%d").timestamp()
        await client.chat_postMessage(
            channel=conversation,
            attachments=[
                {
                    "mrkdwn_in": [
                        "text"
                    ],
                    "color": f"#{''.join([random.choice('0123456789ABCDEF') for x in range(6)])}",
                    "title": f"<@{user_id}>님이 할 일을 추가했습니다.",
                    "fields": task_post,
                    "footer": f"*담당자*\n{''.join(assignee_post).strip()}\n_{description}_",
                    "ts": due_date_time_stamp,
                    "blocks": []
                }
            ]
        )
    await publish_home_tab(client, user_id, user_id)


@ app.middleware
async def middleware(client, context, logger, payload, next):
    try:
        user_id = payload["user"]
        await app.get_user_by_slack_id(user_id)
    except Exception:
        pass
    # Pass control to the next middleware
    return await next()


@ app.error
async def error_handler(error, body, say, client):
    print(error)

    try:
        trigger_id = body["trigger_id"]
    except KeyError:
        trigger_id = None

    if trigger_id == None:
        await client.views_publish(
            user_id=body["event"]["user"],
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"에러가 발생했습니다. 다시 시도해주세요."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```{error}```"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "action_id": "refresh",
                                "text": {
                                    "type": "plain_text",
                                    "text": "새로고침",
                                    "emoji": True
                                },
                                "value": "refresh"
                            }
                        ]
                    }
                ]
            }
        )
    else:
        await client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "error",
                "title": {
                    "type": "plain_text",
                    "text": "에러가 발생했습니다."
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"에러가 발생했습니다. 다시 시도해주세요."
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```{error}```"
                        }
                    }
                ]
            }
        )


@ app.action("refresh")
async def refresh(client, body, ack, respond):
    await ack()
    await publish_home_tab(client, body["user"]["id"], body["user"]["id"])
