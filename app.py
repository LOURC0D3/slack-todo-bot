import os
from slack_bolt.async_app import AsyncApp
from prisma import Prisma

import asyncio
import datetime
import random


class App(AsyncApp):
    def __init__(self):
        super().__init__(token="xoxb-3924779483874-4020715904659-1ABd2ayLMGlIBxC4HPJefqlD",
                    signing_secret="6d5cbac7a0f8958c5e834d67356e8631")
        self.prisma = Prisma()
        self.users = []

    async def get_user_by_slack_id(self, slack_id):
        user = await self.prisma.user.find_unique(where={'slack_id': slack_id})

        if user == None:
            user = await self.prisma.user.create(data={'slack_id': slack_id})
            self.users.append(user.slack_id)

        return user

app = App()


@app.command("/todo")
async def todo_command(ack, body, client):
    await ack()

    await open_todo_submit_modal(client, body["trigger_id"], body["user_id"])



async def open_todo_submit_modal(client, trigger_id, user_id):
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
                            "text": "할 일을 입력하세요. (줄바꿈으로 여러개 입력 가능)",
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
                    "type": "divider",
                },
                {
                    "type": "input",
                    "block_id": "input_conversation",
                    "optional": True,
                    "element": {
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
                    },
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
                }
            ]
        }
    )

@app.view("todo_submit")
async def todo_submit(ack, body, client):
    await ack()

    user_id = body["user"]["id"]
    trigger_id = body["trigger_id"]

    title = body["view"]["state"]["values"]["input_title"]["input_title"]["value"]
    due_date = body["view"]["state"]["values"]["input_date"]["input_date"]["selected_date"]
    description = body["view"]["state"]["values"]["input_description"]["input_description"]["value"]
    assignees = body["view"]["state"]["values"]["input_assignee"]["input_assignee"]["selected_users"]
    conversation = body["view"]["state"]["values"]["input_conversation"]["input_conversation"]["selected_conversation"]

    if description == None:
        description = ''
    assignee_description = description + "  |  <@" + user_id + ">님이 추가함"


    for assignee in assignees:
        found = await app.get_user_by_slack_id(assignee)

        tasks = title.splitlines()

        for task in tasks:
            task.strip()

            if assignee != user_id:
                await app.prisma.task.create(
                    data={
                        "title": task,
                        "due_date": due_date,
                        "description": assignee_description,
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
                "type": "mrkdwn",
                "text":  f"• *{task}*"
            })
        for assignee in assignees:
            assignee_post.append({
                "type": "mrkdwn",
                "text": f"<@{assignee}>"
            })
        await client.chat_postMessage(
            channel=conversation,
            text="할 일이 추가되었습니다.",
            attachments=[
                {
                    "color": f"#{''.join([random.choice('0123456789ABCDEF') for x in range(6)])}",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"<@{user_id}>*님이 할 일을 추가했습니다.*"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*{due_date}*   |   {description}",
                                }
                            ]
                        },
                        {
                            "type": "divider",
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "plain_text",
                                "text": "💬 할 일",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": task_post
                        },
                        {
                            "type": "divider",
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "plain_text",
                                "text": "👨 담당자",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "fields": assignee_post
                        },
                        {
                            "type": "divider",
                        }
                    ]
                }
            ]
        )

@app.error
async def error_handler(error, body, say):
    print(error)