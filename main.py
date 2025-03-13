# Amir Roox
import asyncio
import json
import os
import random
import re
import sys
import time

# from datetime import timedelta, datetime

# from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client, enums, filters, types
from pyrogram.types import (ReplyKeyboardMarkup as Keyboard, InlineKeyboardMarkup as InlineKeyboard,
                            InlineKeyboardButton as Button, CallbackQuery)

import static.config as config
from static.helpers import create_connection
import pytz
import requests
from bs4 import BeautifulSoup

# Initial Client
app = Client("my_bot", api_id=config.API_ID, api_hash=config.API_HASH,
             bot_token=config.BOT_TOKEN, parse_mode=enums.ParseMode.DEFAULT)
existing_users = set()  # for Cache
limit_user_message = {}  # For Limit Message
step_admin = {}
step_user = {}
COUNT_USER_NOW = 0  # For Limit Users
USER_NOW_IDS = set()  # For Limit Users

# First Run Bot
with app:
    country_time_zone = pytz.timezone('Asia/Tehran')
    # Connect To DataBase
    try:
        with create_connection() as database:
            with database.cursor(dictionary=True) as con:
                con.execute("SELECT * from config WHERE TRUE")
                results_h = con.fetchall()
                for res_h in results_h:
                    if res_h['name'] == 'timeout_delete':
                        config.TIMEOUT_DELETE = int(res_h['value'])
                    elif res_h['name'] == 'chanels':
                        chanels_this = json.loads(res_h['value'])
                        config.CHANELS = chanels_this
                    elif res_h['name'] == 'limit_user':
                        config.LIMIT_USERS = int(res_h['value'])
                con.execute("SELECT * FROM users")
                results_h = con.fetchall()

        # Tester Start
        # con = database.cursor(buffered=True)
        # con.execute("TRUNCATE TABLE media")
        # con.execute("TRUNCATE TABLE search")
        # con.execute("TRUNCATE TABLE users")
        # database.commit()
        # con.close()
        # Tester End

        if results_h:
            COUNT_USER_NOW = len(results_h)
            for res_h in results_h:
                USER_NOW_IDS.add(res_h['user_id'])
        print("Bot is running :) ")
    except Exception as er:
        print(f'SQL Error: {er}')
        exit()

# Admin
admin_panel = Keyboard(
    resize_keyboard=True,
    placeholder="📍 انتخاب کنید :",
    keyboard=[
        ['سرچ در دیتابیس | ⚙️', 'تعداد مشترکین | 👤'],
        ['ری استارت ربات | 🔌', 'خاموش کردن ربات | 🔌'],
        ['تنظیم کانال اسپانسری | 💵'],
        ['تنظیم تایم اوت کپی رایت | ⏳'],
        ['اطلاع رسانی کلی | 🔔', 'تنظیم تایم اوت | ⏰'],
        ['تنظیم تعداد کاربران | 🙋🏻‍♂️']
    ]
)
# Back Panel
back_panel = Keyboard(
    resize_keyboard=True,
    placeholder="بازگشت ...",
    keyboard=[
        ['بازگشت | ◀️'],
    ]
)

# Guest User
users_panel = Keyboard(
    resize_keyboard=True,
    placeholder="📍 انتخاب کنید :",
    keyboard=[
        ['سرچ بر اساس اسم | ❤️', 'سرچ بر اساس نویسنده | 🙍‍♂️'],
        ['سرچ بر اساس ناشر | 🖊️', 'سرچ بر اساس ژانر | 🎨'],
        ['راهنمای ربات | ❓', 'ارتباط با سازنده | 🖥️'],
    ]
)


# Handler Start Bot For User
@app.on_message(filters.incoming & filters.private & filters.text & filters.command('start') & ~filters.user(config.ADMINS_ID))
async def on_start_bot(client_p: Client, message: types.Message):
    user_id = message.from_user.id
    # full_command = message.command  # Embed Start

    # For Limit Request User
    current_time = time.time()  # Curent Time
    if user_id in limit_user_message:
        user_info = limit_user_message[user_id]
        time_since_last_message = current_time - user_info["last_message_time"]

        if time_since_last_message < config.COOLDOWN_TIME:
            await message.reply(f"لطفاً {config.COOLDOWN_TIME} ثانیه بین هر پیام صبر کنید.")
            return
        if time_since_last_message > config.TIME_WINDOW:
            user_info["message_count"] = 1
        else:
            user_info["message_count"] += 1

        if user_info["message_count"] > config.MAX_MESSAGES:
            await message.reply(f"شما بیش از حد پیام ارسال کرده‌اید. لطفاً {config.TIME_WINDOW} ثانیه صبر کنید.")
            return

        user_info["last_message_time"] = current_time
    else:
        limit_user_message[user_id] = {"last_message_time": current_time, "message_count": 1}

    # For Limit Users
    if (COUNT_USER_NOW >= config.LIMIT_USERS) and (user_id not in USER_NOW_IDS):  # 2 >= 15000
        await message.reply(
            '**سلام دوست من ، متاسفانه تعداد زیادی کاربر داریم و استفاده از ربات برای اعضای جدید محدوده!**')
        return

    status = await check_join_member(client_p, message, message.from_user, config.CHANELS, config.BOT_TOKEN)
    list_heart = ['🩷', '❤️', '🧡', '💛', '💚', '🩵', '🩵', '💙', '💜', '❤️‍🔥']
    if not status:
        panel_chanels = []
        for url in config.CHANELS:
            heart_this = random.choice(list_heart)
            chat = await app.get_chat(url)
            panel_chanels.append([Button(f'{heart_this} {chat.title} {heart_this}', url=f't.me/{url}')])
        panel_chanels.append([Button(f'عضو شدم', callback_data=f'channel_member')])
        panel_chanels = InlineKeyboard(panel_chanels)
        await message.reply(
            "اول که امیدوارم خوب باشی، برای استفاده از ربات یه وقت بذار و توی کانال های زیر عضو شو چون خیلی بهمون کمک میکنه.\n\n"
            "First, I hope you are well, take some time to use the robot and subscribe to the following channels because it will help us a lot.",
            reply_markup=panel_chanels)
        return

    st_msg = await message.reply("برای دریافت لینک های دانلود"
                                 " فقط کافیه که **اسم انگلیسی**"
                                 " رو برای من ارسال کنی تا کتاب های مرتبط رو براتون بفرستم."
                                 "\n"
                                 "بعدش با استفاده از کد کتاب میتونی لینک دانلود رو ازمون بگیری.",
                                 reply_markup=users_panel)
    await message.reply('**راهنمای استفاده:**'
                        'وقتی **اسم** یه کتاب رو برامون ارسال کنید، لیستی از کتاب های مرتبط براتون ارسال میشه.'
                        ' اگه روی کد کتاب کلیک کنید براتون کپی میشه'
                        ' و میتونید با ارسال اون کد برای ربات، لینک دانلود رو هم دریافت کنید.\n'
                        'همچنین میتونید لینک هارو کپی کنید و از برنامه های جانبی دانلود منیجر استفاده کنید.\n'
                        '**فقط توجه کنید که باید اسم کتاب رو به تنهایی ارسال کنید**\n\n'
                        'Usage guide: When you send us the name of a book, a list of related books will be sent to you.'
                        '\ncopied for you and you can send the code to the robot to get the download link.\n'
                        'You can also copy the links and use download manager side programs.\n'
                        '**Just note that you have to send the name of the book alone**',
                        reply_to_message_id=st_msg.id)


# Handler Msg for User
@app.on_message(filters.incoming & filters.private & filters.text & ~filters.user(config.ADMINS_ID))
async def handler_text_user(client_p: Client, message: types.Message):
    text = message.text.lower()
    user_id = message.from_user.id

    # For Limit Request User
    current_time = time.time()  # Curent Time
    if user_id in limit_user_message:
        user_info = limit_user_message[user_id]
        time_since_last_message = current_time - user_info["last_message_time"]

        if time_since_last_message < config.COOLDOWN_TIME:
            await message.reply(f"لطفاً {config.COOLDOWN_TIME} ثانیه بین هر پیام صبر کنید.")
            return
        if time_since_last_message > config.TIME_WINDOW:
            user_info["message_count"] = 1
        else:
            user_info["message_count"] += 1

        if user_info["message_count"] > config.MAX_MESSAGES:
            await message.reply(f"شما بیش از حد پیام ارسال کرده‌اید. لطفاً {config.TIME_WINDOW} ثانیه صبر کنید.")
            return

        user_info["last_message_time"] = current_time
    else:
        limit_user_message[user_id] = {"last_message_time": current_time, "message_count": 1}

    # For Limit Users
    if (COUNT_USER_NOW >= config.LIMIT_USERS) and (user_id not in USER_NOW_IDS):  # 2 >= 15000
        await message.reply(
            '**سلام دوست من ، متاسفانه تعداد زیادی کاربر داریم و استفاده از ربات برای اعضای جدید محدوده!**')
        return

    chat_id = message.chat.id
    msg_id = message.id
    if user_id not in existing_users:
        status = await check_join_member(client_p, message, message.from_user, config.CHANELS, config.BOT_TOKEN)
        list_heart = ['🩷', '❤️', '🧡', '💛', '💚', '🩵', '🩵', '💙', '💜', '❤️‍🔥']
        if not status:
            panel_chanels = []
            for url in config.CHANELS:
                heart_this = random.choice(list_heart)
                chat = await app.get_chat(url)
                panel_chanels.append([Button(f'{heart_this} {chat.title} {heart_this}', url=f't.me/{url}')])
            panel_chanels.append([Button(f'عضو شدم', callback_data=f'channel_member')])
            panel_chanels = InlineKeyboard(panel_chanels)
            await message.reply(
                "اول که امیدوارم خوب باشی، برای استفاده از ربات یه وقت بذار و توی کانال های زیر عضو شو چون خیلی بهمون کمک میکنه.\n\n"
                "First, I hope you are well, take some time to use the robot and subscribe to the following channels because it will help us a lot.",
                reply_markup=panel_chanels)
            return
    if re.search(r'[@$%^*]', text):
        await message.reply('دوست من از کارکتر های غیر مجاز تو سرچ استفاده نکن!', reply_markup=users_panel)
        return
    elif text == 'سرچ بر اساس اسم | ❤️':
        step_user[user_id] = {'search': 'title'}
        await message.reply('تمامی مورادی که سرچ میکنید بر اساس اسم کتاب ها لیست میشه!', reply_markup=users_panel)
        return
    elif text == 'سرچ بر اساس نویسنده | 🙍‍♂️':
        step_user[user_id] = {'search': 'author'}
        await message.reply('تمامی مورادی که سرچ میکنید بر اساس نویسنده کتاب لیست میشه!', reply_markup=users_panel)
        return
    elif text == 'سرچ بر اساس ناشر | 🖊️':
        step_user[user_id] = {'search': 'publisher'}
        await message.reply('تمامی مورادی که سرچ میکنید بر اساس ناشر کتاب ها لیست میشه!', reply_markup=users_panel)
        return
    elif text == 'سرچ بر اساس ژانر | 🎨':
        step_user[user_id] = {'search': 'series'}
        await message.reply('تمامی مورادی که سرچ میکنید بر اساس ژانر و تگ کتاب ها لیست میشه!', reply_markup=users_panel)
        return
    elif text == 'راهنمای ربات | ❓':
        await message.reply('**راهنمای استفاده:**'
                            'وقتی **اسم** یه کتاب رو برامون ارسال کنید، لیستی از کتاب های مرتبط براتون ارسال میشه.'
                            ' اگه روی کد کتاب کلیک کنید براتون کپی میشه'
                            ' و میتونید با ارسال اون کد برای ربات، لینک دانلود رو هم دریافت کنید.\n'
                            'همچنین میتونید لینک هارو کپی کنید و از برنامه های جانبی دانلود منیجر استفاده کنید.\n'
                            '**فقط توجه کنید که باید اسم کتاب رو به تنهایی ارسال کنید**\n\n'
                            'Usage guide: When you send us the name of a book, a list of related books will be sent to you.'
                            '\ncopied for you and you can send the code to the robot to get the download link.\n'
                            'You can also copy the links and use download manager side programs.\n'
                            '**Just note that you have to send the name of the book alone**')
        return
    elif text == 'ارتباط با سازنده | 🖥️':
        panel_this = InlineKeyboard(
            [
                [Button('ارتباط', url=f't.me/{config.MAIN_ADMIN}')]
                # [Button('پرداخت', url=f'{config.MAIN_DOMAIN}/request/{user_id}')]
            ]
        )
        await message.reply("برای ارتباط با سازنده کلیک کنید.",
                            reply_to_message_id=msg_id,
                            reply_markup=panel_this)
        return
    if not text.isascii():  # Check English Search
        await message.reply('لطفا فقط به صورت انگلیسی سرچ کنید!', reply_to_message_id=msg_id)
        return
    if re.fullmatch(r'CODE__\w+', text, flags=re.IGNORECASE):
        status = await check_join_member(client_p, message, message.from_user, config.CHANELS, config.BOT_TOKEN)
        if not status:
            list_heart = ['🩷', '❤️', '🧡', '💛', '💚', '🩵', '🩵', '💙', '💜', '❤️‍🔥']
            panel_chanels = []
            for url in config.CHANELS:
                heart_this = random.choice(list_heart)
                chat = await app.get_chat(url)
                panel_chanels.append([Button(f'{heart_this} {chat.title} {heart_this}', url=f't.me/{url}')])
            panel_chanels.append([Button(f'عضو شدم', callback_data=f'channel_member')])
            panel_chanels = InlineKeyboard(panel_chanels)
            await message.reply(
                "اول که امیدوارم خوب باشی، برای استفاده از ربات یه وقت بذار و توی کانال های زیر عضو شو چون خیلی بهمون کمک میکنه.\n\n"
                "First, I hope you are well, take some time to use the robot and subscribe to the following channels because it will help us a lot.",
                reply_markup=panel_chanels)
            return
        md5 = text.replace('CODE__', '').replace('code__', '')
        this_msg = await message.reply("صبر کنید تا اطلاعات رو بروز رسانی کنیم ...", reply_to_message_id=msg_id)
        result = await main_scrapper(md5)
        if result['check'] == 'Not Found':
            await app.edit_message_text(chat_id, this_msg.id, 'موردی با این کلید پیدا نشد :(')
            return
        if result['check'] == 'Error':
            await app.edit_message_text(chat_id, this_msg.id,
                                        'در ارسال لینک به مشکل خوردیم! لطفا چند ساعت بعد دوباره امتحان کنید!')
            return
        name_unique = str(result["title"])
        content = (f'🦋 Name: {name_unique}\n\n'
                   f'📚 Code: {result["md5"]}\n\n'
                   f'🎨 Series: {result["series"]}\n\n'
                   f'🖊️ Authors: {result["authors"]}\n\n'
                   f'📓 Publisher: {result["publisher"]}\n\n'
                   f'👅 Language: {result["language"]}\n\n'
                   f'⏱ Year of publication: {result["year"]}\n\n'
                   f'📃 Number of pages available: {result["pages"]}\n\n'
                   f'💾 Size: {result["size"]}\n\n'
                   # f'🔖 توضیحات: {result["description"]}\n\n'
                   f'📖 File Format: {result["extension"]}\n')
        try:
            this_msg1 = await message.reply_photo(result['path_img'], caption=content, reply_to_message_id=msg_id)
            await app.delete_messages(chat_id, this_msg.id)
        except Exception as ex:
            print(ex)
            this_msg1 = await app.edit_message_text(chat_id, this_msg.id, content)
        # content = ''
        temp_list = []
        i_temp = 0
        for link in result['download_link']:
            if i_temp < 2:
                temp_list.append([Button(f'لینک اصلی', url=link)])
            else:
                temp_list.append([Button(f'لینک کمکی', url=link)])
            i_temp += 1
        link_panel = InlineKeyboard(temp_list)
        # gg = InlineKeyboard([[Button(f'حذف از مورد علاقه', url=f'https://ro-ox.com')]])
        copy_right = await message.reply('میتونید از طریق پنل زیر کتاب خودتون رو دانلود کنید :) ',
                                         reply_to_message_id=this_msg1.id, reply_markup=link_panel)
        await asyncio.sleep(1.3)
        notif_msg = await message.reply(
            '**لطفا لینک هارو توی سیو مسیج ذخیره کنید، چون برای موارد کپی رایت تا یه دقیقه دیگه پاک میشن!**',
            reply_to_message_id=this_msg1.id)
        await asyncio.sleep(config.TIMEOUT_DELETE)
        await app.delete_messages(chat_id, [notif_msg.id, copy_right.id])  # Delete Copy Right Content
        return
    else:
        if len(text) < 3:
            await message.reply('لطفا از کارکتر های بیشتری استفاده کنید!', reply_to_message_id=msg_id)
            return
        this_msg1 = await message.reply("لطفا صبر کنید تا بگردیم ...", reply_to_message_id=msg_id)
        try:
            data, flag = check_query_search(text, step_user[user_id]['search'])  # str
        except Exception as ex:
            print(f'Set Default Value User: {ex}')
            step_user[user_id] = {'search': 'title'}
            data, flag = check_query_search(text, step_user[user_id]['search'])
        if len(data) == 0:
            if flag:
                await app.edit_message_text(chat_id, this_msg1.id, 'متاسفانه کتاب مورد نظر شما پیدا نشد!')
            else:
                await app.edit_message_text(chat_id, this_msg1.id, 'متاسفانه سرور مناسبی پیدا نکردیم :(')
            return
        text_list = data_seperator(data)  # list
        for te in text_list:
            await message.reply(te, reply_to_message_id=msg_id)
        await app.delete_messages(chat_id, this_msg1.id)
        return


# handler Start Bot For Admin
@app.on_message(filters.private & filters.text & filters.regex('^/start$') & filters.user(config.ADMINS_ID))
async def on_start_bot_admin(client_p: Client, message: types.Message):
    await message.reply("سلام مدیر عزیز، به ربات خودت خوش اومدی :)", reply_markup=admin_panel)
    return


# Handler Msg For Admin
@app.on_message(filters.private & filters.text & filters.user(config.ADMINS_ID))
async def handler_text_admin(client_p: Client, message: types.Message):
    global users_panel
    text = message.text.lower()
    user_id = message.from_user.id
    # chat_id = message.chat.id
    msg_id = message.id
    if text == 'خاموش کردن ربات | 🔌':
        await message.reply('ربات خاموش شد: برای شروع مجدد از هاست یا سرور اقدام فرمایید.')
        sys.exit()
    elif text == 'ری استارت ربات | 🔌':
        await message.reply('ربات ریستارت شد: برای شروع 5 ثانیه صبر کنید.')
        os.execl(sys.executable, sys.executable, *sys.argv)
    elif text == 'بازگشت | ◀️':
        step_admin[user_id] = ''
        await message.reply('به پنل اصلی برگشتید!', reply_markup=admin_panel)
        return
    elif text == 'تعداد مشترکین | 👤':

        with create_connection() as connection:
            with connection.cursor() as cursor_db:
                cursor_db.execute('SELECT COUNT(*) FROM users')
                result = cursor_db.fetchone()

        if not result:
            result = [0]
        text = f'کل مشترکین شما: {result[0]}'
        await message.reply(text, reply_to_message_id=msg_id)
        return
    elif text == 'سرچ در دیتابیس | ⚙️':
        await message.reply('برای سرچ کردن فیلم های موجود در دیتابیس ، فقط اسم را سرچ کنید:'
                            ' (تمامی موارد در دیتابیس ذخیره شدن و اسکرپ جداگانه ایی ندارند!)',
                            reply_to_message_id=msg_id, reply_markup=back_panel)
        step_admin[user_id] = 'searchDB'
        return
    elif text == 'تنظیم کانال اسپانسری | 💵':
        this_msg = await message.reply(
            'برای تنظیم اسپانسر از الگو زیر استفاده کنید: (حتما ربات را در کانال عضو و **ادمین** کنید)',
            reply_to_message_id=msg_id)
        await message.reply('@selfbotpro,@roox_text', reply_to_message_id=this_msg.id)
        await message.reply('لطفا فاصله اضافه نزارید، و لینک ها را با یک کاما از هم جدا کنید :)',
                            reply_markup=back_panel)
        step_admin[user_id] = 'editSponser'
        return
    elif text == 'تنظیم تایم اوت | ⏰':
        this_msg = await message.reply('برای تنظیم تایم اوت یک عدد وارد کنید. برای مثال: 10.2 (ده و دو دهم ثانیه)',
                                       reply_to_message_id=msg_id)
        await message.reply('لطفا فاصله اضافه نزارید، و فقط عدد وارد کنید :)')
        await message.reply(f'در حال حاضر تایم اوت برابر است با: {config.COOLDOWN_TIME}',
                            reply_to_message_id=this_msg.id, reply_markup=back_panel)
        step_admin[user_id] = 'editTimeout'
        return
    elif text == 'تنظیم تایم اوت کپی رایت | ⏳':
        this_msg = await message.reply('برای تنظیم تایم اوت کپی رایت یک عدد وارد کنید. برای مثال: 60 (شصت ثانیه)',
                                       reply_to_message_id=msg_id)
        await message.reply('لطفا فاصله اضافه نزارید، و فقط عدد صحیح وارد کنید :)')
        await message.reply(f'در حال حاضر تایم اوت برابر است با: {config.TIMEOUT_DELETE}',
                            reply_to_message_id=this_msg.id, reply_markup=back_panel)
        step_admin[user_id] = 'editTimeoutDeleteMsg'
        return
    elif text == 'اطلاع رسانی کلی | 🔔':
        await message.reply('متنی که میخواهید برای تمامی کاربران بفرستید را اینجا ارسال کنید :)',
                            reply_markup=back_panel)
        step_admin[user_id] = 'sendAll'
        return
    elif text == 'تنظیم تعداد کاربران | 🙋🏻‍♂️':
        this_msg = await message.reply('برای تنظیم تعداد کاربران یک عدد وارد کنید. برای مثال: 15000 (15 هزار کاربر)',
                                       reply_to_message_id=msg_id)
        await message.reply('لطفا فاصله اضافه نزارید، و فقط عدد وارد کنید :)')
        await message.reply(f'در حال حاضر حداکثر تعداد کاربران برابر است با: {config.LIMIT_USERS}',
                            reply_to_message_id=this_msg.id, reply_markup=back_panel)
        step_admin[user_id] = 'editLimitUsers'
        return

    if user_id not in step_admin:
        return
    elif step_admin[user_id] == 'searchDB':
        step_admin[user_id] = ''

        with create_connection() as connection:
            with connection.cursor(dictionary=True) as cursor_db:
                cursor_db.execute(f"SELECT * FROM books WHERE title LIKE %s LIMIT 10",
                                  (str(f'%{text}%'),))
                result = cursor_db.fetchall()

        # content = ''
        for res in result:
            content = (f'🦋 Name: {res["title"]}\n\n'
                       f'📚 Code: {res["md5"]}\n\n'
                       f'🎨 Series: {res["series"]}\n\n'
                       f'🖊️ Authors: {res["authors"]}\n\n'
                       f'📓 Publisher: {res["publisher"]}\n\n'
                       f'👅 Language: {res["language"]}\n\n'
                       f'⏱ Year of publication: {res["year"]}\n\n'
                       f'📃 Number of pages available: {res["pages"]}\n\n'
                       f'💾 Size: {res["size"]}\n\n'
                       # f'🔖 توضیحات: {result["description"]}\n\n'
                       f'📖 File Format: {res["extension"]}\n')
            await message.reply(content, reply_to_message_id=msg_id, reply_markup=admin_panel)

        return
    elif step_admin[user_id] == 'editSponser':
        global existing_users
        all_link = text.strip().replace(' ', '').replace('@', '').split(',')  # Seperator Link
        config.CHANELS = []
        for link in all_link:
            config.CHANELS.append(link)
        await message.reply('چنل های اسپانسرینگ آپدیت شدند.', reply_to_message_id=msg_id, reply_markup=admin_panel)
        step_admin[user_id] = ''
        existing_users = set()
        value = json.dumps(config.CHANELS)

        with create_connection() as connection:
            with connection.cursor() as cursor_db:
                cursor_db.execute("UPDATE config SET value = %s WHERE name = %s", (value, 'chanels'))
                connection.commit()

        return
    elif step_admin[user_id] == 'editTimeout':
        try:
            timeout = float(text.strip())
        except Exception as ex:
            await message.reply('لطفا فقط عدد وارد کنید!', reply_to_message_id=msg_id)
            print(ex)
            return
        config.COOLDOWN_TIME = timeout
        await message.reply('تایم اوت درخواست ها تغییر کرد ✔️', reply_to_message_id=msg_id, reply_markup=admin_panel)
        step_admin[user_id] = ''
        return
    elif step_admin[user_id] == 'editTimeoutDeleteMsg':
        try:
            timeout_del = int(text.strip())
        except Exception as ex:
            await message.reply('لطفا فقط عدد صحیح وارد کنید!', reply_to_message_id=msg_id)
            print(ex)
            return
        config.TIMEOUT_DELETE = timeout_del

        with create_connection() as connection:
            with connection.cursor() as cursor_db:
                cursor_db.execute("UPDATE config SET value = %s WHERE name = %s", (timeout_del, 'timeout_delete'))
                connection.commit()

        await message.reply('تایم اوت کپی رایت تغییر کرد ✔️', reply_to_message_id=msg_id, reply_markup=admin_panel)
        step_admin[user_id] = ''
        return
    elif step_admin[user_id] == 'sendAll':
        this_msg = await message.reply('در حال ارسال برای کاربران هستیم ...')
        step_admin[user_id] = ''

        with create_connection() as connection:
            with connection.cursor(dictionary=True) as cursor_db:
                cursor_db.execute(f"SELECT * FROM users")
                result = cursor_db.fetchall()

        for res in result:
            try:
                await app.send_message(res['user_id'], text)
            except Exception as ex:
                print(ex)
                continue
        await message.reply('تمامی پیام ها ارسال شد!', reply_to_message_id=this_msg.id, reply_markup=admin_panel)

        return
    elif step_admin[user_id] == 'editLimitUsers':
        try:
            limit_user = int(text.strip())
        except Exception as ex:
            await message.reply('لطفا فقط عدد صحیح وارد کنید!', reply_to_message_id=msg_id)
            print(ex)
            return
        config.LIMIT_USERS = limit_user

        with create_connection() as connection:
            with connection.cursor() as cursor_db:
                cursor_db.execute("UPDATE config SET value = %s WHERE name = %s", (limit_user, 'limit_user'))
                connection.commit()

        await message.reply('تعداد حداکثر کاربران تغییر کرد ✔️', reply_to_message_id=msg_id, reply_markup=admin_panel)
        step_admin[user_id] = ''
        return
    await message.reply('دستور شما شناسایی نشد :(', reply_to_message_id=msg_id)


# Need Function (Helper)
# Check Join Members To Channel
async def check_join_member(client_p: Client, message: types.Message, user: types.User, chanels: list, bot_token: str):
    """
    user : The member telegram
    channls : list channls Joined
    BOT_TOKEN : Bot Token
    """
    user_id = user.id
    states = ['administrator', 'creator', 'member', 'restricted']  # Method Member in Telegram
    # Start Loop
    for chanel in chanels:
        try:
            api_tel = f"https://api.telegram.org/bot{bot_token}/getChatMember?chat_id=@{chanel}&user_id={user_id}"
            response = requests.get(api_tel).json()
            # Check Status
            if response['result']['status'] not in states:
                if user_id in existing_users:
                    existing_users.remove(user_id)
                return False
        except Exception as ex:
            print(ex)
            if user_id in existing_users:
                existing_users.remove(user_id)
            return False

    # Load data for Admins
    with create_connection() as connection:
        with connection.cursor() as cursor_db:
            cursor_db.execute("SELECT * FROM users WHERE user_id = %s", (int(user_id),))
            is_new_user = True if cursor_db.fetchone() else False  # Find User
            if not is_new_user:
                global COUNT_USER_NOW, USER_NOW_IDS
                cursor_db.execute("INSERT INTO users (user_id, username, first_name) VALUES (%s, %s, %s)",
                                  (int(user_id), user.username, user.first_name))
                connection.commit()
                cursor_db.execute("SELECT COUNT(*) FROM users")
                all_user = int(cursor_db.fetchone()[0])
                COUNT_USER_NOW = all_user
                USER_NOW_IDS.add(user_id)
                for admin_id in config.ADMINS_ID:
                    try:
                        if not user.username:
                            username = 'Nothing (Without UserName)'
                        else:
                            username = f'@{user.username}'
                        await app.send_message(
                            chat_id=admin_id,
                            text=f"↫︙New User Join The Bot .\n\n  "
                                 f"↫ id :  ❲ {user_id} ❳\n  "
                                 f"↫ username :  ❲ {username} ❳\n  "
                                 f"↫ firstname :  ❲ {user.first_name} ❳\n\n"
                                 f"↫︙members Count Now : ❲{all_user}❳"
                        )
                    except Exception as ex:
                        print(f'Admin Start Bot: {ex}')

    existing_users.add(user_id)
    return True  # Member In Channel


# Handler Query For Users
@app.on_callback_query(~filters.user(config.ADMINS_ID))
async def callback_query_update(client_p: Client, callback_query: "CallbackQuery"):
    from_id = callback_query.from_user.id
    message_id = callback_query.message.id
    callback_data = callback_query.data
    # text = callback_query.message.text

    if callback_data == 'channel_member':  # Checker Member
        status = await check_join_member(client_p, callback_query.message, callback_query.from_user,
                                       config.CHANELS, config.BOT_TOKEN)
        if status:
            await app.delete_messages(from_id, message_id)
            st_msg = await app.send_message(from_id, "برای دریافت لینک های دانلود"
                                                     " فقط کافیه که **اسم انگلیسی**"
                                                     " رو برای من ارسال کنی تا کتاب های مرتبط رو براتون بفرستم."
                                                     "\n"
                                                     "بعدش با استفاده از کد کتاب میتونی لینک دانلود رو ازمون بگیری.",
                                            reply_markup=users_panel)
            await app.send_message(from_id, '**راهنمای استفاده:**'
                                            'وقتی **اسم** یه کتاب رو برامون ارسال کنید، لیستی از کتاب های مرتبط براتون ارسال میشه.'
                                            ' اگه روی کد کتاب کلیک کنید براتون کپی میشه'
                                            ' و میتونید با ارسال اون کد برای ربات، لینک دانلود رو هم دریافت کنید.\n'
                                            'همچنین میتونید لینک هارو کپی کنید و از برنامه های جانبی دانلود منیجر استفاده کنید.\n'
                                            '**فقط توجه کنید که باید اسم کتاب رو به تنهایی ارسال کنید**\n\n'
                                            'Usage guide: When you send us the name of a book, a list of related books will be sent to you.'
                                            '\ncopied for you and you can send the code to the robot to get the download link.\n'
                                            'You can also copy the links and use download manager side programs.\n'
                                            '**Just note that you have to send the name of the book alone**',
                                   reply_to_message_id=st_msg.id)
        else:
            await app.send_message(from_id, 'لطفا داخل چنل ها عضو بشید و سپس عضو شدم رو کلیک کنید!')
        await callback_query.answer()
    return


# Check Query In DB or Not (For Scrapping)
def check_query_search(query_inp: str, category_search='title'):  # Query For Search Movie Or Series (Return Data Str)
    query = query_inp.strip().lower()

    with create_connection() as connection:
        with connection.cursor(dictionary=True) as cursor_db:
            cursor_db.execute("SELECT data FROM search WHERE query = %s and category = %s",
                              (query, category_search))
            is_query = cursor_db.fetchone()

    if is_query:
        data = json.loads(is_query['data'])  # Fetch Data
        return data, True

    data_list = {}  # All Book Link Title
    maximum_page_search = 50  # Dafault 100 Per Page

    checker_here = False
    response = ''
    for main_site_here in config.MAIN_SITE:
        try:
            response = requests.get(
                f'{main_site_here}index.php?req={query}&res={maximum_page_search}&columns%5B%5D={category_search}',
                headers=config.HEADERS)
            if 200 <= response.status_code <= 300:
                checker_here = True
                break
        except Exception as ex:
            print(f'Next URL: {ex}')
            continue
    if not checker_here:
        return [], False

    html_content = response.content.decode('utf-8')
    soup = BeautifulSoup(html_content, "html.parser")
    all_book_list = soup.find('table', class_='c').find_all('tr')
    not_found = True if len(all_book_list) < 2 else False
    if not not_found:
        ii = 0
        for book in all_book_list:
            if ii == 0:
                ii += 1
                continue

            id_book = book.find('td').text.strip()
            author_book = book.find_all('td')[1].text.strip()
            title_column = book.find_all('td')[2].find_all('a')
            publisher_book = book.find_all('td')[3].text.strip()
            year_book = book.find_all('td')[4].text.strip()
            lang_book = book.find_all('td')[6].text.strip()
            extension_book = book.find_all('td')[8].text.strip()
            size_book = book.find_all('td')[7].text.strip()

            # link_book = ''
            if len(title_column) > 1:
                row = -1
            else:
                row = 0

            jj = False
            for font in title_column[row].find_all('font'):
                if len(title_column[row].find_all('font')) < 2:
                    font.extract()
                    break
                if not jj:
                    jj = True
                    continue
                font.extract()
            title_book = title_column[row].text.strip()
            link_book = re.findall(r'\?md5=(\w+)$', title_column[row].get('href'))[0]  # MD5 FILE LINK

            data_list[title_book] = {
                'id': id_book,
                'author': author_book,
                'publisher': publisher_book,
                'md5': link_book,
                'year': year_book,
                'lang': lang_book,
                'size': size_book,
                'extension': extension_book,
            }

    data_str = json.dumps(data_list)

    with create_connection() as connection:
        with connection.cursor(dictionary=True) as cursor_db:
            cursor_db.execute("INSERT INTO search (category, query, data) VALUES (%s, %s, %s)",
                              (category_search, query, data_str))
            connection.commit()

    return data_list, True


# Data To Best String (List)
def data_seperator(data_dict: dict) -> list:
    content = '🔸️ نتایج جستجو بر اساس سرچ انگلیسی' + '\n\n'
    result = []
    j = 0
    for d in data_dict:
        j += 1
        name = d  # Name
        code = data_dict[d]['md5']  # MD5 Link
        info = (
            f'Author: **{data_dict[d]["author"]}** - Publisher: **{data_dict[d]["publisher"]}** - Lang: **{data_dict[d]["lang"]}**\n'
            f'Format File: **{data_dict[d]["extension"]}** - Size: **{data_dict[d]["size"]}**')
        code = f'`CODE__{code}`'
        text = (f"🔹️ Name: {name}\n\n"
                f"⭐️ Quick code copy: {code}\n\n"
                f"ℹ️ {info}\n\n - * - \n\n")
        content += text
        if j == 13:
            result.append(content)
            content = ''
            j = 0
    if content != '':
        result.append(content)
    return result


# Scrapper
async def main_scrapper(md5_: str) -> dict:

    with create_connection() as connection:
        with connection.cursor(dictionary=True) as cursor_db:
            cursor_db.execute("SELECT * FROM books WHERE md5=%s", (md5_,))
            is_find: dict = cursor_db.fetchone()

    if is_find:
        is_find['check'] = True
        is_find['download_link'] = json.loads(is_find['download_link'])
        return is_find  # Return Dic

    response = ''
    for main_site in config.MAIN_SITE:
        link = f'{main_site}book/index.php?md5={md5_}'  # For Get Link
        response = requests.get(link, headers=config.HEADERS)
        if 200 <= response.status_code <= 300:
            break
    my_dict = {
        'check': False
    }
    if response.status_code == requests.codes.ok:
        html_content = response.content.decode('utf-8')
        soup = BeautifulSoup(html_content, "html.parser")
        for s in soup.select('table.hashes'):
            s.extract()
        details_box = soup.select_one('body > table')
        name = details_box.find_all('tr')[1].find_all('td')[2].find('a').text.strip()

        try:
            author = details_box.find_all('tr')[2].find_all('td')[1].text.strip()
        except Exception as ex:
            print('Author Not Found: ', ex)
            author = ''

        try:
            series = details_box.find_all('tr')[3].find_all('td')[1].text.strip()
        except Exception as ex:
            print('Series Not Found: ', ex)
            series = ''

        try:
            publisher = details_box.find_all('tr')[4].find_all('td')[1].text.strip()
        except Exception as ex:
            print('Publisher Not Found: ', ex)
            publisher = ''

        try:
            year = details_box.find_all('tr')[5].find_all('td')[1].text.strip()
        except Exception as ex:
            print('Year Not Found: ', ex)
            year = ''

        try:
            language = details_box.find_all('tr')[6].find_all('td')[1].text.strip()
        except Exception as ex:
            print('Lang Not Found: ', ex)
            language = ''

        try:
            pages = details_box.find_all('tr')[6].find_all('td')[3].text.strip()
        except Exception as ex:
            print('Pages Not Found: ', ex)
            pages = ''

        try:
            size = details_box.find_all('tr')[10].find_all('td')[1].text.strip()
        except Exception as ex:
            print('Size Not Found: ', ex)
            size = ''

        try:
            extension = details_box.find_all('tr')[10].find_all('td')[3].text.strip()
        except Exception as ex:
            print('Extention Not Found: ', ex)
            extension = ''

        try:
            path_img = f'downloads/{md5_}_temp.jpg'
            img_url = str(details_box.find_all('tr')[1].find_all('td')[0].find('a').find('img').get('src').strip())
            img_data = requests.get(f'{config.MAIN_SITE}{img_url}').content
            with open(path_img, 'wb') as handler:
                handler.write(img_data)
        except Exception as ex:
            print('Image Not Found: ', ex)
            path_img = ''

        try:
            links_download_str = details_box.find_all('tr')[1].find_all('td')[0].find('a').get('href').strip()
        except Exception as ex:
            print('Links Download Not Found: ', ex)
            for admin_id in config.ADMINS_ID:
                try:
                    await app.send_message(chat_id=admin_id, text=f"Error Site\n"
                                                                  f"Name MDF: {md5_}\n"
                                                                  f"Status: Failed!")
                except Exception as ex:
                    print(f'Admin Start Bot: {ex}')
            my_dict['check'] = 'Error'
            return my_dict

        link_download = []
        response = requests.get(links_download_str, headers=config.HEADERS)
        if response.status_code == requests.codes.ok:
            html_content = response.content.decode('utf-8')
            soup = BeautifulSoup(html_content, "html.parser")
            box_download = soup.select_one('div#download')
            link_download.append(box_download.find('h2').find('a').get('href'))  # MAIN LINK
            for i in range(0, 3):
                try:
                    link_download.append(box_download.find('ul').find_all('li')[i].find('a').get('href'))
                except Exception as ex:
                    print(f'{ex}')
        else:
            my_dict['check'] = 'Error'
            return my_dict

        link_download_json = json.dumps(link_download)
        my_dict = {
            'title': name,
            'md5': md5_,
            'download_link': link_download,
            'authors': author,
            'year': year,
            'publisher': publisher,
            'language': language,
            'pages': pages,
            'size': size,
            'extension': extension,
            'series': series,
            'path_img': path_img,
            'check': True
        }

        with create_connection() as connection:
            with connection.cursor() as cursor_db:
                cursor_db.execute("INSERT INTO books"
                                  " (title, md5, download_link, authors, publisher, year, pages, language, size, extension, series, path_img) "
                                  "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                  (name, md5_, link_download_json, author, publisher, year, pages, language, size,
                                   extension, series, path_img))
                connection.commit()

        return my_dict
    elif response.status_code == 404:  # Not Found
        my_dict['check'] = 'Not Found'
        return my_dict
    else:
        for admin_id in config.ADMINS_ID:
            try:
                await app.send_message(chat_id=admin_id, text=f"Error Site\n"
                                                              f"Name MDF: {md5_}\n"
                                                              f"Status: Failed!")
            except Exception as ex:
                print(f'Admin Start Bot: {ex}')
        my_dict['check'] = 'Error'
        return my_dict


# Convert Farsi To Fingilsh (EN)
def convert_fa_to_fin(input_str):
    mapping = {
        '۱': '1',
        '۲': '2',
        '۳': '3',
        '۴': '4',
        '۵': '5',
        '۶': '6',
        '۷': '7',
        '۸': '8',
        '۹': '9',
        '۰': '0',
        'آ': 'a',
        'ا': 'a',
        'َ': 'a',
        'ُ': 'o',
        'ِ': 'e',
        'ب': 'b',
        'پ': 'p',
        'ت': 't',
        'ث': 's',
        'ج': 'j',
        'چ': 'ch',
        'ح': 'h',
        'خ': 'kh',
        'د': 'd',
        'ذ': 'z',
        'ر': 'r',
        'ز': 'z',
        'ژ': 'zh',
        'س': 's',
        'ش': 'sh',
        'ص': 's',
        'ض': 'z',
        'ط': 't',
        'ظ': 'z',
        'ع': 'e',
        'غ': 'gh',
        'ف': 'f',
        'ق': 'gh',
        'ک': 'k',
        'گ': 'g',
        'ل': 'l',
        'م': 'm',
        'ن': 'n',
        'و': 'v',
        'ه': 'h',
        'ی': 'y',
        'ئ': 'e',
        ' ': '-'
    }

    output_str = ""
    for char in input_str:
        if char in mapping:
            output_str += mapping[char]
        else:
            if char.isalpha():
                output_str += char

    return output_str


# Delete User For Checker Sponser
# def delete_users():
#     global existing_users
#     existing_users = {}
#
#
# scheduler = AsyncIOScheduler()
# scheduler.add_job(delete_users, "interval", hours=12)
# scheduler.start()

# Run Bot
app.run()
