# Amir Roox
import asyncio
import json
import os
import random
import re
import sys
import time
from datetime import timedelta, datetime

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
        database = create_connection()
        # Tester Start
        # con = database.cursor(buffered=True)
        # con.execute("TRUNCATE TABLE media")
        # con.execute("TRUNCATE TABLE search")
        # con.execute("TRUNCATE TABLE users")
        # database.commit()
        # con.close()
        # Tester End

        con = database.cursor(buffered=True, dictionary=True)
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
        con.close()
        database.close()
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
        ['راهنمای ربات | ❓', 'ارتباط با سازنده | 🖥️'],
    ]
)


# Handler Start Bot For User
@app.on_message(
    filters.incoming & filters.private & filters.text & filters.command('start') & ~filters.user(config.ADMINS_ID))
async def onStartBot(clientP: Client, message: types.Message):
    user_id = message.from_user.id
    full_command = message.command  # Embed Start

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

    status = await checkJoinMember(clientP, message, message.from_user, config.CHANELS, config.BOT_TOKEN)
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
            "اول که امیدوارم خوب باشی، برای استفاده از ربات یه وقت بذار و توی کانال های زیر عضو شو چون خیلی بهمون کمک میکنه.",
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
                        '**فقط توجه کنید که باید اسم کتاب رو به تنهایی ارسال کنید**',
                        reply_to_message_id=st_msg.id)


# Handler Msg for User
@app.on_message(filters.incoming & filters.private & filters.text & ~filters.user(config.ADMINS_ID))
async def handlerTextUser(clientP: Client, message: types.Message):
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
        status = await checkJoinMember(clientP, message, message.from_user, config.CHANELS, config.BOT_TOKEN)
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
                "اول که امیدوارم خوب باشی، برای استفاده از ربات یه وقت بذار و توی کانال های زیر عضو شو چون خیلی بهمون کمک میکنه.",
                reply_markup=panel_chanels)
            return
    if text == 'بازگشت | ◀️':
        step_user[user_id] = {}
        await message.reply('به صفحه اصلی برگشتید :)', reply_markup=users_panel)
        return
    elif re.search(r'[@$%^*]', text):
        await message.reply('دوست من از کارکتر های غیر مجاز تو سرچ استفاده نکن!', reply_markup=users_panel)
        return
    elif text == 'راهنمای ربات | ❓':
        await message.reply('**راهنمای استفاده:**'
                            'وقتی **اسم** یه کتاب رو برامون ارسال کنید، لیستی از کتاب های مرتبط براتون ارسال میشه.'
                            ' اگه روی کد کتاب کلیک کنید براتون کپی میشه'
                            ' و میتونید با ارسال اون کد برای ربات، لینک دانلود رو هم دریافت کنید.\n'
                            'همچنین میتونید لینک هارو کپی کنید و از برنامه های جانبی دانلود منیجر استفاده کنید.\n'
                            '**فقط توجه کنید که باید اسم کتاب رو به تنهایی ارسال کنید**')
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
    if re.fullmatch(r'.+_\d_[a-zA-Z0-9]+', text):
        status = await checkJoinMember(clientP, message, message.from_user, config.CHANELS, config.BOT_TOKEN)
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
                "اول که امیدوارم خوب باشی، برای استفاده از ربات یه وقت بذار و توی کانال های زیر عضو شو چون خیلی بهمون کمک میکنه.",
                reply_markup=panel_chanels)
            return
        server = int(text.split('_')[1])  # (Midele) DonyayeSerial Or MoboMovies (1, 2)
        name = str(text.split('_')[0])  # (Start)
        model = str(text.split('_')[2])  # (End) Series Or Movie

        connection = create_connection()
        cursor_db = connection.cursor(buffered=True, dictionary=True)
        cursor_db.execute(f"SELECT favorite FROM users WHERE user_id = %s and favorite LIKE %s",
                          (int(user_id), str(f"%{text}%")))
        is_find = cursor_db.fetchone()  # Find Name Favorite
        cursor_db.execute(f"SELECT trial_date FROM users WHERE user_id = %s", (int(user_id),))
        trial_ = cursor_db.fetchone()['trial_date']  # Trial User
        cursor_db.close()
        connection.close()
        if config.IS_PAY and trial_ < datetime.now():  # Test Trial
            trial_panel = InlineKeyboard(
                [
                    [Button(f'اشتراک یک ماهه', callback_data=f'one_month')],
                    [Button(f'اشتراک سه ماهه', callback_data=f'three_month')],
                    [Button(f'اشتراک شش ماهه', callback_data=f'six_month')],
                    [Button(f'اشتراک یک ساله', callback_data=f'one_year')]
                ])
            await message.reply("مدت زمان تریال شما به پایان رسید!",
                                reply_to_message_id=msg_id, reply_markup=trial_panel)
            return
        if is_find:
            add_favorite_panel = InlineKeyboard(
                [[Button(f'حذف از مورد علاقه', callback_data=f'rF__{text}')]])  # Remove Panel Favorite
        else:
            add_favorite_panel = InlineKeyboard(
                [[Button(f'اضافه به مورد علاقه', callback_data=f'aF__{text}')]])  # Add Panel Favorite

        if server == 1:
            this_msg = await message.reply("صبر کنید تا اطلاعات رو بروز رسانی کنیم ...", reply_to_message_id=msg_id)
            result = await scrapperDonyaseryal(name, model)
            if result['check'] == 'Not Found':
                await app.edit_message_text(chat_id, this_msg.id, 'موردی با این کلید پیدا نشد :(')
                return
            if result['check'] == 'Error':
                await app.edit_message_text(chat_id, this_msg.id,
                                            'در ارسال لینک به مشکل خوردیم! لطفا چند ساعت بعد دوباره امتحان کنید!')
                return
            name_unique = str(result["name"]).replace('-', ' ')
            ed = ''
            if model == 'series' and not re.fullmatch(r'.*-.*', result['year']):
                ed = ' (در حال پخش) '
            content = (f'🦋 نام: {name_unique}\n\n'
                       f'🎬 نوع: {result["category"]}\n\n'
                       f'🎨 ژانر: {result["genre"]}\n\n'
                       f'⏰ سال تولید: {result["year"]}{ed}\n\n'
                       f'🪚 محصول: {result["product"]}\n\n'
                       f'👅 زبان: {result["lang"]}\n\n'
                       f'⏱ زمان: {result["time"]}\n\n'
                       f'🔖 توضیحات: {result["description"]}\n\n'
                       f'⚡️ امتیاز: {result["imdb"]}\n')
            await app.delete_messages(chat_id, this_msg.id)
            try:
                this_msg = await message.reply_photo(result['path_img'], caption=content,
                                                     reply_to_message_id=msg_id, reply_markup=add_favorite_panel)
            except Exception as ex:
                print(ex)
                this_msg = await message.reply(content, reply_to_message_id=msg_id, reply_markup=add_favorite_panel)
            this_msg_list = []
            content = ''
            if model == 'series':
                list_encode = result['link']
                ii = 0
                content_list = []
                for i in list_encode.keys():
                    ii += 1
                    content += f'▪️ {i}:\n'  # Num Season
                    for j in list_encode[i].keys():
                        content += f'📥 [{j}]({list_encode[i][j]})\n'
                    content += f'\n\n'
                    if ii == 6:
                        this_msg2 = await message.reply(str(content), reply_to_message_id=this_msg.id)
                        this_msg_list.append(this_msg2.id)
                        content = ''
                        ii = 0
                if content and len(content) >= 3:
                    this_msg2 = await message.reply(str(content), reply_to_message_id=this_msg.id)
                    this_msg_list.append(this_msg2.id)
            else:
                list_encode = result['link']
                for i in list_encode.keys():
                    content += f'▪️ {i}:\n'  # Num Season
                    for j in list_encode[i].keys():
                        content += f'📥 [{j}]({list_encode[i][j]})\n'
                    content += f'\n\n'
                this_msg2 = await message.reply(content, reply_to_message_id=this_msg.id)
                this_msg_list.append(this_msg2.id)
            await asyncio.sleep(1.3)
            notif_msg = await message.reply(
                '**لطفا لینک هارو توی سیو مسیج ذخیره کنید، چون برای موارد کپی رایت تا یه دقیقه دیگه پاک میشن!**',
                reply_to_message_id=this_msg.id)
            this_msg_list.append(notif_msg.id)
            # this_msg_list.append(this_msg.id)
            await asyncio.sleep(config.TIMEOUT_DELETE)
            await app.delete_messages(chat_id, this_msg_list)  # Delete Copy Right Content
            return
        # Turn Off Mobo Movies
        elif server == 2 and False:
            this_msg = await message.reply("صبر کنید تا اطلاعات رو بروز رسانی کنیم ...", reply_to_message_id=msg_id)
            result = await scrapperMoboMovies(name, model)
            if result['check'] == 'Not Found':
                await app.edit_message_text(chat_id, this_msg.id, 'موردی با این کلید پیدا نشد :(')
                return
            if result['check'] == 'Error':
                await app.edit_message_text(chat_id, this_msg.id,
                                            'در ارسال لینک به مشکل خوردیم! لطفا چند ساعت بعد دوباره امتحان کنید!')
                return
            name_unique = str(result["name"]).replace('-', ' ')
            ed = ''
            if model == 'series' and not re.fullmatch(r'.*-.*', result['year']):
                ed = ' (در حال پخش) '
            content = (f'🦋 نام: {name_unique}\n\n'
                       f'🎬 نوع: {result["category"]}\n\n'
                       f'🎨 ژانر: {result["genre"]}\n\n'
                       f'⏰ سال تولید: {result["year"]}{ed}\n\n'
                       f'🪚 محصول: {result["product"]}\n\n'
                       f'👅 زبان: {result["lang"]}\n\n'
                       f'⏱ زمان: {result["time"]}\n\n'
                       f'🔖 توضیحات: {result["description"]}\n\n'
                       f'⚡️ امتیاز: {result["imdb"]}\n')
            await app.delete_messages(chat_id, this_msg.id)
            try:
                this_msg = await message.reply_photo(result['path_img'], caption=content,
                                                     reply_to_message_id=msg_id, reply_markup=add_favorite_panel)
            except Exception as ex:
                print(ex)
                this_msg = await message.reply(content, reply_to_message_id=msg_id, reply_markup=add_favorite_panel)
            this_msg_list = []
            content = ''
            if model == 'series':
                list_encode = result['link']
                for i in list_encode.keys():
                    content += f'▪️ فصل {i}:\n\n'  # Num Season
                    for j in list_encode[i].keys():  # Format Encode
                        content += f'🧩 {j}:\n\n'
                        for e in list_encode[i][j].keys():
                            # content += f'📥 [Episode {e}]({list_encode[i][j][e]})\n'
                            content += f'<a href="{list_encode[i][j][e]}">📥 Episode {e}</a>\n'
                        content += '\n'
                    this_msg2 = await message.reply(str(content), reply_to_message_id=this_msg.id)
                    this_msg_list.append(this_msg2.id)
                    content = ''
            else:  # Movie
                list_encode = result['link']
                for i in list_encode.keys():
                    i_fa = {'dubbed': 'دو زبانه', 'dubbed-sound': 'صدای دوبله', 'soft-sub': 'زیرنویس چسبیده',
                            'subtitle': 'زینویس جدا', 'hard-sub': 'زینویس سخت'}
                    if i in i_fa:
                        fa_dec = i_fa[i]
                    else:
                        fa_dec = i
                    content += f'▪️ {fa_dec}:\n\n'  # Num Season
                    for j in list_encode[i].keys():  # Format Encode
                        # content += f'📥 [{j}]({list_encode[i][j]})\n'
                        content += f'<a href="{list_encode[i][j]}">📥 {j}</a>\n'
                    content += '\n'
                this_msg2 = await message.reply(str(content), reply_to_message_id=this_msg.id)
                this_msg_list.append(this_msg2.id)
            await asyncio.sleep(1.3)
            notif_msg = await message.reply(
                '**لطفا لینک هارو توی سیو مسیج ذخیره کنید، چون برای موارد کپی رایت تا یه دقیقه دیگه پاک میشن!**',
                reply_to_message_id=this_msg.id)
            this_msg_list.append(notif_msg.id)
            # this_msg_list.append(this_msg.id)
            await asyncio.sleep(config.TIMEOUT_DELETE)
            await app.delete_messages(chat_id, this_msg_list)  # Delete Copy Right Content
            return
        else:
            await message.reply("همچین ساختاری برای جستجو فیلم مناسب نیست!", reply_to_message_id=msg_id)
            return
    else:
        if len(text) < 3:
            await message.reply('لطفا از کارکتر های بیشتری استفاده کنید!', reply_to_message_id=msg_id)
            return
        this_msg = await message.reply("لطفا صبر کنید تا بگردیم ...", reply_to_message_id=msg_id)
        data = checkQuerySearch(text)  # str
        if len(data) == 0:
            await app.edit_message_text(chat_id, this_msg.id, 'متاسفانه کتاب مورد نظر شما پیدا نشد!')
            return
        textList = dataSeperator(data)  # list
        for te in textList:
            await message.reply(te, reply_to_message_id=msg_id)
        await app.delete_messages(chat_id, this_msg.id)


# handler Start Bot For Admin
@app.on_message(filters.private & filters.text & filters.regex('^/start$') & filters.user(config.ADMINS_ID))
async def onStartBotAdmin(clientP: Client, message: types.Message):
    await message.reply("سلام مدیر عزیز، به ربات خودت خوش اومدی :)", reply_markup=admin_panel)
    return


# Handler Msg For Admin
@app.on_message(filters.private & filters.text & filters.user(config.ADMINS_ID))
async def handlerTextAdmin(clientP: Client, message: types.Message):
    global users_panel
    text = message.text.lower()
    user_id = message.from_user.id
    chat_id = message.chat.id
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
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True)
        cursor_db.execute('SELECT COUNT(*) FROM users')
        result = cursor_db.fetchone()
        if not result:
            result = [0]
        cursor_db.close()
        connection.close()
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
        text = text.replace(' ', '-').replace(':', '-').strip()

        connection = create_connection()
        cursor_db = connection.cursor(buffered=True, dictionary=True)
        cursor_db.execute(f"SELECT * FROM media WHERE name LIKE %s LIMIT 10",
                          (str(f'%{text}%'),))
        result = cursor_db.fetchall()
        content = ''
        for res in result:
            if res['server'] == 1:
                server = 'دنیای سریال'
            elif res['server'] == 2:
                server = 'موبو موی'
            else:
                server = 'نا شناخته'
            content = (f'🦋 نام: {res["name"]}\n\n'
                       f'🎬 نوع سرور: {server}\n\n'
                       f'🎬 نوع: {res["category"]}\n\n'
                       f'🎨 ژانر: {res["genre"]}\n\n'
                       f'⏰ سال تولید: {res["year"]}\n\n'
                       f'🪚 محصول: {res["product"]}\n\n'
                       f'👅 زبان: {res["lang"]}\n\n'
                       f'⏱ زمان: {res["time"]}\n\n'
                       f'🔖 توضیحات: {res["description"]}\n\n'
                       f'⚡️ امتیاز: {res["imdb"]}\n')
            await message.reply(content, reply_to_message_id=msg_id, reply_markup=admin_panel)
        cursor_db.close()
        connection.close()
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
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True, dictionary=True)
        cursor_db.execute("UPDATE config SET value = %s WHERE name = %s", (value, 'chanels'))
        connection.commit()
        cursor_db.close()
        connection.close()
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
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True)
        cursor_db.execute("UPDATE config SET value = %s WHERE name = %s", (timeout_del, 'timeout_delete'))
        connection.commit()
        cursor_db.close()
        connection.close()
        await message.reply('تایم اوت کپی رایت تغییر کرد ✔️', reply_to_message_id=msg_id, reply_markup=admin_panel)
        step_admin[user_id] = ''
        return
    elif step_admin[user_id] == 'sendAll':
        this_msg = await message.reply('در حال ارسال برای کاربران هستیم ...')
        step_admin[user_id] = ''
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True, dictionary=True)
        cursor_db.execute(f"SELECT * FROM users")
        result = cursor_db.fetchall()
        for res in result:
            try:
                await app.send_message(res['user_id'], text)
            except Exception as ex:
                print(ex)
                continue
        await message.reply('تمامی پیام ها ارسال شد!', reply_to_message_id=this_msg.id, reply_markup=admin_panel)
        cursor_db.close()
        connection.close()
        return
    elif step_admin[user_id] == 'editLimitUsers':
        try:
            limit_user = int(text.strip())
        except Exception as ex:
            await message.reply('لطفا فقط عدد صحیح وارد کنید!', reply_to_message_id=msg_id)
            print(ex)
            return
        config.LIMIT_USERS = limit_user
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True)
        cursor_db.execute("UPDATE config SET value = %s WHERE name = %s", (limit_user, 'limit_user'))
        connection.commit()
        cursor_db.close()
        connection.close()
        await message.reply('تعداد حداکثر کاربران تغییر کرد ✔️', reply_to_message_id=msg_id, reply_markup=admin_panel)
        step_admin[user_id] = ''
        return
    await message.reply('دستور شما شناسایی نشد :(', reply_to_message_id=msg_id)


# Need Function (Helper)
# Check Join Members To Channel
async def checkJoinMember(clientP: Client, message: types.Message, user: types.User, chanels: list, BOT_TOKEN: str):
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
            api_tel = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id=@{chanel}&user_id={user_id}"
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
    connection = create_connection()
    cursor_db = connection.cursor(buffered=True)
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
    cursor_db.close()
    connection.close()
    existing_users.add(user_id)
    return True  # Member In Channel


# Handler Query For Users
@app.on_callback_query(~filters.user(config.ADMINS_ID))
async def callback_query_update(clientP: Client, callback_query: "CallbackQuery"):
    from_id = callback_query.from_user.id
    message_id = callback_query.message.id
    callback_data = callback_query.data
    text = callback_query.message.text

    if callback_data == 'channel_member':  # Checker Member
        status = await checkJoinMember(clientP, callback_query.message, callback_query.from_user,
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
                                            '**فقط توجه کنید که باید اسم کتاب رو به تنهایی ارسال کنید**',
                                   reply_to_message_id=st_msg.id)
        else:
            await app.send_message(from_id, 'لطفا داخل چنل ها عضو بشید و سپس عضو شدم رو کلیک کنید!')
        await callback_query.answer()
    return


# Check Query In DB or Not (For Scrapping)
def checkQuerySearch(queryInp: str) -> dict:  # Query For Search Movie Or Series (Return Data Str)
    query = queryInp.strip().lower()
    connection = create_connection()
    cursor_db = connection.cursor(buffered=True, dictionary=True)
    cursor_db.execute("SELECT data FROM search WHERE query = %s", (query,))
    is_query = cursor_db.fetchone()
    cursor_db.close()
    connection.close()
    if is_query:
        data = json.loads(is_query['data'])  # Fetch Data
        return data

    data_list = {}  # All Book Link Title
    maximum_page_search = 1  # Dafault 100 Per Page

    response = requests.get(f'https://libgen.is/search.php?req={query}&res=100&column=title',
                            headers=config.HEADERS)
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

            title_column = book.find_all('td')[2].find_all('a')
            link_book = ''
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

            data_list[title_book] = link_book

    data_str = json.dumps(data_list)
    connection = create_connection()
    cursor_db = connection.cursor(buffered=True)
    cursor_db.execute("INSERT INTO search (query, data) VALUES (%s, %s)", (query, data_str))
    connection.commit()
    cursor_db.close()
    connection.close()
    return data_list


# Data To Best String (List)
def dataSeperator(data: str) -> list:
    all_data = data.split('__')  # List Of Movie/Series
    content = '🔸️ نتایج جستجو بر اساس سرچ انگلیسی' + '\n\n'
    result = []
    j = 0
    for d in all_data:
        j += 1
        myList = d.split('**')
        name = myList[0]  # Name
        category = myList[1]  # Movie or Series
        link = myList[2]  # Link
        server = myList[3]  # Server Download
        code = f'`{link}_{server}_{category}`'.lower()
        category_fa = 'فیلم' if category == 'movie' else 'سریال'
        text = (f"🔹️ نام انگلیسی: {name}\n"
                f"🍀 نوع: {category_fa}\n"
                f"⭐️ کپی سریع کد: {code}\n\n")
        content += text
        if j == 10:
            result.append(content)
            content = ''
            j = 0
    if content != '':
        result.append(content)
    return result


# Scrapper For Series Or Movies in DonyayeSeryal
async def scrapperDonyaseryal(name_: str, model: str) -> dict:
    name = name_.replace(':', '').replace(' ', '-').replace('’', '').replace("'", '')  # For Get Link
    connection = create_connection()
    cursor_db = connection.cursor(buffered=True, dictionary=True)
    cursor_db.execute("SELECT * FROM media WHERE server=1 and name=%s", (name,))
    is_find: dict = cursor_db.fetchone()
    cursor_db.close()
    connection.close()
    if is_find:
        is_find['check'] = True
        is_find['link'] = strToDict(is_find['link'], model)
        return is_find  # Return Dic
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    myDict = {
        'check': False
    }
    link_str = ''
    if model == 'series':
        response = requests.get(f'https://donyayeserial.com/series/{name}', headers=headers)
    else:
        response = requests.get(f'https://donyayeserial.com/{name}', headers=headers)
    if response.status_code == requests.codes.ok:
        html_content = response.content.decode('utf-8')
        soup = BeautifulSoup(html_content, "html.parser")
        box_download = soup.find('div', id='content-downloads').find('div').find('div')
        current_element = box_download.find('h3', {'style': 'text-align: center;'})
        try:
            genre_all = soup.find('span', class_='pr-item pr-genre').find_all('a')
            genre_all_list = []
            for ge in genre_all:
                genre_all_list.append(ge.text)
            genre = ', '.join(genre_all_list)
        except Exception as ex:
            print('Genre Not Found: ', ex)
            genre = ''
        try:
            if model == 'series':
                try:
                    year = soup.find_all('li', class_='fm-infos')[2]
                    year = year.find_next('strong').next_sibling.get_text().strip()  # 2015 - 2017
                except Exception as ex:
                    print(ex)
                    year = soup.find_all('li', class_='fm-infos')[2].get_text().strip()
                year = year.replace('–', '-').replace('_', '-')
                if not re.fullmatch(r'\d+[–_-]\d+', year):
                    year = year.replace('–', '').replace('_', '').replace('-', '')
            else:
                year = soup.find_all('span', class_='pr-item')[1].find_next('a').text.strip()
        except Exception as ex:
            print('Year Not Found: ', ex)
            year = ''
        try:
            product = str(soup.find_all('span', class_='pr-item')[2].find_next('a').text.strip())
        except Exception as ex:
            print('Product Not Found: ', ex)
            product = ''
        try:
            path_img = f'downloads/{name_}_1.jpg'
            img_url = str(soup.find('div', class_='post-poster').find('img').get('src').strip())
            img_data = requests.get(img_url).content
            with open(path_img, 'wb') as handler:
                handler.write(img_data)
        except Exception as ex:
            print('Image Not Found: ', ex)
            path_img = ''
        try:
            lang = str(soup.find_all('li', class_='fm-infos')[0].find_next('a').text.strip())
        except Exception as ex:
            print('Lang Not Found: ', ex)
            lang = ''
        try:
            time_m = str(soup.find_all('li', class_='fm-infos')[1].strong.next_sibling.text.strip())
        except Exception as ex:
            print('time Not Found: ', ex)
            time_m = ''
        try:
            description = str(
                soup.find('div', class_='position-relative -plot float-right w-100').find('p').text.strip())
        except Exception as ex:
            print('Description Not Found: ', ex)
            description = ''
        try:
            imdb = float(soup.find('span', class_='-rate-value').text.strip())
        except Exception as ex:
            print('IMDB Not Found: ', ex)
            imdb = ''
        title_tag = 'h2'
        subTitle_tag = 'h3'
        if model == 'series':
            title_tag = 'h3'
            subTitle_tag = 'nothing'
            time_m = '-'
        i = 1
        while current_element:
            if current_element.name == title_tag:  # Season Number Or Name Movie
                if i != 1 and model == 'series':  # Just For Series
                    link_str += '^^'
                link_str += f'{current_element.get_text(strip=True).replace("دانلود", "").strip()}__'
            elif current_element.name == subTitle_tag:  # Just For Movies
                link_str += f'{current_element.get_text(strip=True).replace("دانلود", "").strip()}**'
            elif current_element.name == 'p' and current_element.get('style') == 'text-align: center;':  # Get Link
                download_link = current_element.find('a')
                if download_link:
                    repG = (download_link.get_text(strip=True).replace("کلیک کنید", "")
                            .replace("دانلود با", "").strip())
                    link_str += f'{repG}++'
                    link_str += f'{download_link["href"].strip()}%%'
                else:
                    link_str += f'{current_element.get_text(strip=True).replace("دانلود", "").strip()}**'
            elif current_element.name == 'hr':
                link_str += ',,'
            current_element = current_element.find_next_sibling()
            i += 1
        link_dic = strToDict(link_str, model)
        myDict = {
            'server': 1,
            'name': name_,
            'link': link_dic,
            'category': 'سریال' if model == 'series' else 'فیلم',
            'genre': genre,
            'year': year,
            'product': product,
            'lang': lang,
            'time': time_m,
            'description': description,
            'imdb': imdb,
            'path_img': path_img,
            'check': True
        }
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True)
        cursor_db.execute("INSERT INTO media"
                          " (server, name, link, category, genre, year, product, lang, time, description, imdb, path_img) "
                          "VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                          (name_, link_str, model, genre, year, product, lang, time_m, description, imdb, path_img))
        connection.commit()
        cursor_db.close()
        connection.close()
        return myDict
    elif response.status_code == 404:  # Not Found
        myDict['check'] = 'Not Found'
        return myDict
    else:
        for admin_id in config.ADMINS_ID:
            try:
                await app.send_message(chat_id=admin_id, text=f"Error Site: Donyaye Seryal\n"
                                                              f"Name Movie: {name}\n"
                                                              f"Status: Failed!")
            except Exception as ex:
                print(f'Admin Start Bot: {ex}')
        myDict['check'] = 'Error'
        return myDict


# Scrapper For Series Or Movies in MboMovies
async def scrapperMoboMovies(name_: str, model: str) -> dict:
    name = name_.replace(':', '').replace(' ', '-').replace('’', '').replace("'", '')  # For Get Link
    connection = create_connection()
    cursor_db = connection.cursor(buffered=True, dictionary=True)
    cursor_db.execute("SELECT * FROM media WHERE server=2 and name=%s", (name,))
    is_find: dict = cursor_db.fetchone()
    cursor_db.close()
    connection.close()
    if is_find:
        is_find['check'] = True
        is_find['link'] = json.loads(is_find['link'])  # Json to Dict
        return is_find  # Return Dic
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    myDict = {
        'check': False
    }
    link_str = ''
    response = requests.get(f'https://mobomovies.co/post/{name}', headers=headers)
    if response.status_code == requests.codes.ok:
        html_content = response.content.decode('utf-8')
        soup = BeautifulSoup(html_content, "html.parser")
        post_id = int(soup.find('input', {'id': 'post_id'}).get('value').strip())
        try:
            genre_all = soup.find('div', class_='genres').find_all('a')
            genre_all_list = []
            for ge in genre_all:
                genre_all_list.append(ge.text)
            genre = ', '.join(genre_all_list)
        except Exception as ex:
            print('Genre Not Found: ', ex)
            genre = ''
        try:
            year = soup.find('div', class_='items-grow').find_all('section')[0].find_next('b').text.strip()
        except Exception as ex:
            print('Year Not Found: ', ex)
            year = ''
        try:
            product_all = soup.select('section a b.permalink')
            product_all_list = []
            for pro in product_all:
                product_all_list.append(pro.text.strip())
            product = ', '.join(product_all_list)
        except Exception as ex:
            print('Product Not Found: ', ex)
            product = ''
        try:
            path_img = f'downloads/{name_}_2.jpg'
            img_url = str(soup.find('div', class_='post-data').find('img').get('src').strip())
            img_data = requests.get(f'https://mobomovies.co{img_url}').content
            with open(path_img, 'wb') as handler:
                handler.write(img_data)
        except Exception as ex:
            print('Image Not Found: ', ex)
            path_img = ''
        try:
            lang = str(soup.find('div', class_='items-grow').find_all('section')[2].find_next('b').text.strip())
        except Exception as ex:
            print('Lang Not Found: ', ex)
            lang = ''
        try:
            time_m = str(soup.find('div', class_='items-grow').find_all('section')[1].find_next('b').text.strip())
        except Exception as ex:
            print('time Not Found: ', ex)
            time_m = ''
        try:
            description = str(soup.find('summary').text.strip())
        except Exception as ex:
            print('Description Not Found: ', ex)
            description = ''
        try:
            imdb = float(soup.find('div', class_='imdb').find('b').text.strip())
        except Exception as ex:
            print('IMDB Not Found: ', ex)
            imdb = ''

        data = {
            'post_id': post_id
        }
        response = requests.post(f'https://mobomovies.co/api/get-urls', headers=headers, data=data)
        json_content = response.json()
        link_dic = {}
        if json_content and model == 'movie':
            for version in json_content.keys():
                for encode in json_content[version]:
                    format_all = f"{encode['url_quality']} {encode['url_resolution']} {encode['url_size']}"
                    if version not in link_dic:
                        link_dic[version] = {}
                    link_dic[version][format_all] = encode['url_file']
        elif json_content and model == 'series':
            for version in json_content.keys():
                for encode in json_content[version].values():
                    format_all = f"{encode['info']['quality']} {encode['info']['resolution']} {encode['info']['size']}"
                    for episode in encode['urls']:
                        if version not in link_dic:
                            link_dic[version] = {}
                        if format_all not in link_dic[version]:
                            link_dic[version][format_all] = {}
                        link_dic[version][format_all][episode['title']] = episode['file']
        link_str = json.dumps(link_dic)
        myDict = {
            'server': 2,
            'name': name_,
            'link': link_dic,
            'category': 'سریال' if model == 'series' else 'فیلم',
            'genre': genre,
            'year': year,
            'product': product,
            'lang': lang,
            'time': time_m,
            'description': description,
            'imdb': imdb,
            'path_img': path_img,
            'check': True
        }
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True)
        cursor_db.execute("INSERT INTO media"
                          " (server, name, link, category, genre, year, product, lang, time, description, imdb, path_img) "
                          "VALUES (2, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                          (name_, link_str, model, genre, year, product, lang, time_m, description, imdb, path_img))
        connection.commit()
        cursor_db.close()
        connection.close()
        return myDict
    elif response.status_code == 404:  # Not Found
        myDict['check'] = 'Not Found'
        return myDict
    else:
        for admin_id in config.ADMINS_ID:
            try:
                await app.send_message(chat_id=admin_id, text=f"Error Site: Mobo Movies\n"
                                                              f"Name Movie: {name}\n"
                                                              f"Status: Failed!")
            except Exception as ex:
                print(f'Admin Start Bot: {ex}')
        myDict['check'] = 'Error'
        return myDict


# Scrapper For Movies in Digimovies
def scrapperDigimovies(name: str, model='movie'):
    global EXPIRE_MD5_DIGI
    name = name.replace(':', '').replace(' ', '-').replace('’', '').replace("'", '')  # For Get Link
    connection = create_connection()
    cursor_db = connection.cursor(buffered=True, dictionary=True)
    cursor_db.execute("SELECT * FROM media WHERE server=2 and name=%s", (name,))
    is_find: dict = cursor_db.fetchone()
    cursor_db.close()
    connection.close()
    if is_find:
        is_find['link'] = strToDict(is_find['link'], model)
        return is_find  # Return Dic
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    myDict = {}
    link_str = ''
    if model == 'series':
        response = requests.get(f'https://digimoviez.com/serie/{name}', headers=headers)
    else:
        response = requests.get(f'https://digimoviez.com/{name}', headers=headers)
    if response.status_code == requests.codes.ok:
        html_content = response.content
        soup = BeautifulSoup(html_content, "html.parser")
        box_info = soup.find('div', class_='single_holder').find('div', class_='post_holder').find('div', class_='meta')
        try:
            genre = box_info.find('ul').find_all('li')[2].find_next('span', class_='res_item').text.strip()
        except Exception as ex:
            print('Genre Not Found: ', ex)
            genre = ''
        try:
            year = int(re.findall(r'\d{4}', name)[-1])
        except Exception as ex:
            print('Year Not Found: ', ex)
            year = ''
        try:
            product = box_info.find('ul').find_all('li')[5].find_next('span', class_='res_item').text.strip()
        except Exception as ex:
            print('Product Not Found: ', ex)
            product = ''
        lang = 'انگلیسی'
        try:
            time_m = box_info.find('ul').find_all('li')[1].find_next('span', class_='res_item').text.strip()
        except Exception as ex:
            print('time Not Found: ', ex)
            time_m = ''
        try:
            description = box_info.find('div', class_='plot_text').text.strip()
        except Exception as ex:
            print('Description Not Found: ', ex)
            description = ''
        try:
            imdb = float(box_info.find('div', class_='num_holder').find('strong').text.strip())
        except Exception as ex:
            print('IMDB Not Found: ', ex)
            imdb = ''
        movie_type = soup.find_all('div', class_='dllink_holder_ham')  # Model Decode
        expire_md5 = soup.find('div', class_='dllinks').find('a', class_='btn_row btn_dl')  # expire and MD5
        EXPIRE_MD5_DIGI = str(expire_md5.get('href').split('?')[-1])
        with open('EXPIRE_DIGI.txt', 'w') as fileW:
            fileW.write(EXPIRE_MD5_DIGI)
        link_str += f'{name}__'
        for type_m in movie_type:
            title_movie = type_m.find_next('div', class_='right_title').get_text()
            link_str += f'{title_movie}**'  # Text Encode
            limit = type_m.findChildren('div', class_='itemdl parent_item')
            movies_link = type_m.find_all_next('div', class_='row_data', limit=len(limit))
            for movie in movies_link:
                title = movie.find_next('h3').get_text()
                link = movie.find_next('a').get('href').split('?')[0]
                size = movie.find_next('div', class_='item_meta size_dl').get_text()
                all_title = f'{title} ({size})'
                link_str += f"{all_title}++{link}%%"
            link_str += ',,'
        link_dic = strToDict(link_str, model)
        myDict = {
            'server': 1,
            'name': name,
            'link': link_dic,
            'category': 'سریال' if model == 'series' else 'فیلم',
            'genre': genre,
            'year': year,
            'product': product,
            'lang': lang,
            'time': time_m,
            'description': description,
            'imdb': imdb
        }
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True)
        cursor_db.execute("INSERT INTO media"
                          " (server, name, link, category, genre, year, product, lang, time, description, imdb) "
                          "VALUES (2, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                          (name, link_str, model, genre, year, product, lang, time_m, description, imdb))
        connection.commit()
        cursor_db.close()
        connection.close()
        return myDict
    else:
        return myDict


# Scrapper For Persian Series and Films (benameiran3) Update
async def scrapperBenameiran3AdminUpdate(model='series'):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    if model == 'series':
        response = requests.get(f'https://benameiran3.com/persian-s1/', headers=headers)
        if response.status_code == requests.codes.ok:
            html_content = response.content.decode('utf-8')
            soup = BeautifulSoup(html_content, "html.parser")
            all_series = soup.select('article.hentry')
            connection = create_connection()
            cursor_db = connection.cursor(buffered=True, dictionary=True)
            for serie in all_series:
                try:
                    name = serie.find('div', class_='entry-header').find('a').text.strip()
                    en_name = f'{convert_fa_to_fin(name)}'
                    link = serie.find('div', class_='entry-header').find('a').get('href')
                    number_part = int(serie.find('span', class_='vlog-count').text.strip())
                except Exception as ex:
                    print(ex)
                    continue

                cursor_db.execute("SELECT * FROM search_benameiran3 WHERE name = %s", (name,))
                is_find = cursor_db.fetchone()
                if is_find:
                    if number_part != is_find['number']:
                        cursor_db.execute("UPDATE search_benameiran3 SET number = %s WHERE name = %s",
                                          (number_part, name))
                    else:
                        continue
                else:
                    cursor_db.execute("INSERT INTO search_benameiran3 (name, en_name, number, link, category) "
                                      "VALUES (%s, %s, %s, %s, %s)",
                                      (name, en_name, number_part, link, 'series'))
            connection.commit()
            cursor_db.close()
            connection.close()
        else:
            for admin_id in config.ADMINS_ID:
                try:
                    await app.send_message(chat_id=admin_id, text=f"Error Site: Benameiran\n"
                                                                  f"Status: Failed!")
                except Exception as ex:
                    print(f'Admin Start Bot: {ex}')
    if model == 'movie':
        response = requests.get(f'https://benameiran3.com/category/persian-movie-p1', headers=headers)
        if response.status_code == requests.codes.ok:
            html_content = response.content.decode('utf-8')
            soup = BeautifulSoup(html_content, "html.parser")
            max_page = int(soup.find_all('a', class_='page-numbers')[-2].text.strip())  # Last page Search
            max_page_last = config.MAX_PAGE_MOVIE_IRAN  # 218
            if max_page_last >= max_page:
                return
            connection = create_connection()
            cursor_db = connection.cursor(buffered=True, dictionary=True)
            if max_page_last < max_page:
                cursor_db.execute("UPDATE config SET value = %s WHERE name = %s",
                                  (max_page, 'max_page_movie_iran'))
                connection.commit()
                config.MAX_PAGE_MOVIE_IRAN = max_page
                diffrent = max_page - max_page_last
                range_this = range(1, diffrent + 1)
            else:
                return
            for page in range_this:
                response = requests.get(f'https://benameiran3.com/category/persian-movie-p1/page/{page}',
                                        headers=headers)
                if response.status_code == requests.codes.ok:
                    html_content = response.content.decode('utf-8')
                    soup = BeautifulSoup(html_content, "html.parser")
                    all_movies = soup.select('article.post')
                    for movie in all_movies:
                        try:
                            name = movie.find('div', class_='entry-header').find('h2').find('a').text.strip()
                            en_name = f'{convert_fa_to_fin(name)}'
                            link = movie.find('div', class_='entry-header').find('h2').find('a').get('href')
                        except Exception as ex:
                            print(ex)
                            continue

                        cursor_db.execute("SELECT * FROM search_benameiran3 WHERE name = %s", (name,))
                        is_find = cursor_db.fetchone()
                        if is_find:
                            continue
                        else:
                            cursor_db.execute("INSERT INTO search_benameiran3 (name, en_name, number, link, category) "
                                              "VALUES (%s, %s, %s, %s, %s)",
                                              (name, en_name, 0, link, 'movie'))
                    connection.commit()
                await asyncio.sleep(random.randint(2, 5))
                print(f'Sccrap Page {page} # Perisan Movie')
            cursor_db.close()
            connection.close()
        else:
            for admin_id in config.ADMINS_ID:
                try:
                    await app.send_message(chat_id=admin_id, text=f"Error Site: Benameiran\n"
                                                                  f"Status: Failed!")
                except Exception as ex:
                    print(f'Admin Start Bot: {ex}')


# Persian Series and Films (benameiran3) Get
def searchBenameiran3(name, step=0):
    connection = create_connection()
    cursor_db = connection.cursor(buffered=True, dictionary=True)
    if step == 0:
        cursor_db.execute("SELECT * FROM search_benameiran3 WHERE name LIKE %s",
                          (f'%{name}%',))
        result = cursor_db.fetchall()
    elif step == 1:
        cursor_db.execute("SELECT * FROM search_benameiran3 WHERE en_name = %s", (f'{name}',))
        result = cursor_db.fetchone()
    else:
        result = None
    cursor_db.close()
    connection.close()
    if result:
        return result
    return None


# Persian Series and Films (benameiran3) Get
async def scrapperBenameiran3(result: dict, number=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    }
    if result['category'] == 'series' and number:
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True, dictionary=True)
        cursor_db.execute("SELECT * FROM media_benameiran3 WHERE en_name = %s AND number_part = %s",
                          (result['en_name'], number))
        is_find = cursor_db.fetchone()
        cursor_db.close()
        connection.close()
        if is_find:
            is_find['links'] = json.loads(is_find['links'])  # Return Dict
            return is_find

        all_number = result['number']
        page = ((all_number - number) // 6) + 1
        items_before = all_number - number
        position_in_page = items_before % 6 + 1

        response = requests.get(f'{result["link"]}page/{page}', headers=headers)
        if response.status_code == requests.codes.ok:
            html_content = response.content.decode('utf-8')
            soup = BeautifulSoup(html_content, "html.parser")
            link_serie_part = soup.select('div.entry-image a')[position_in_page - 1].get('href')

            response = requests.get(f'{link_serie_part}', headers=headers)
            if response.status_code == requests.codes.ok:
                html_content = response.content.decode('utf-8')
                soup = BeautifulSoup(html_content, "html.parser")
                try:
                    path_img = f"downloads/{result['en_name']}_3.jpg"
                    try:
                        img_url = str(soup.find('div', {'data-title': 'اطلاعات فیلم'}).find('img').get('src').strip())
                    except Exception as ex:
                        print(ex)
                        img_url = str(soup.find('div', class_="entry-content-single").find('img').get('src').strip())
                    if 'benameiran' not in img_url:
                        img_url = f'https://benameiran3.com/{img_url}'
                    img_data = requests.get(f'{img_url}').content
                    with open(path_img, 'wb') as handler:
                        handler.write(img_data)
                except Exception as ex:
                    print('Image Not Found: ', ex)
                    path_img = ''
                try:
                    description_parts = soup.select('div[data-title]')

                    description_p1 = description_parts[0]
                    try:
                        fig = description_p1.find('figure')
                        fig.extract()
                    except Exception as ex:
                        print(f"Figure Not Found: {ex}")
                    description_p1 = description_p1.get_text().strip()

                    description_p2 = description_parts[1]
                    try:
                        fig = description_p2.find('figure')
                        fig.extract()
                    except Exception as ex:
                        print(f"Figure Not Found: {ex}")
                    description_p2 = description_p2.get_text().strip()

                    description_all = description_p1 + '\n\n' + description_p2
                except Exception as ex:
                    print(ex)
                    description_all = 'بدون توضیحات'
                all_encode = soup.find_all('div', class_='su-button-center')
                link_dict = {}
                for encode in all_encode:
                    link = encode.find_next('a').get('href')
                    title = encode.find_next('span').text.strip()
                    link_dict[title] = link
                link_dict = dict(reversed(link_dict.items()))
                myDict = {
                    'server': 3,
                    'name': result['en_name'],
                    'link_page': link_serie_part,
                    'links': link_dict,
                    'category': 'سریال',
                    'description': description_all,
                    'path_img': path_img
                }
                link_str = json.dumps(link_dict)
                connection = create_connection()
                cursor_db = connection.cursor(buffered=True)
                cursor_db.execute("INSERT INTO media_benameiran3"
                                  " (name, en_name, server, category, link_page, links, number_part, path_img, description) "
                                  "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                  (result['name'], result['en_name'], 3, 'series', link_serie_part, link_str,
                                   number, path_img, description_all))
                connection.commit()
                cursor_db.close()
                connection.close()
                return myDict
        else:
            for admin_id in config.ADMINS_ID:
                try:
                    await app.send_message(chat_id=admin_id, text=f"Error Site: Benameiran\n"
                                                                  f"Status: Failed!")
                except Exception as ex:
                    print(f'Admin Start Bot: {ex}')
    elif result['category'] == 'movie':
        connection = create_connection()
        cursor_db = connection.cursor(buffered=True, dictionary=True)
        cursor_db.execute("SELECT * FROM media_benameiran3 WHERE en_name = %s AND category = %s",
                          (result['en_name'], 'movie'))
        is_find = cursor_db.fetchone()
        if is_find:
            is_find['links'] = json.loads(is_find['links'])  # Return Dict
            cursor_db.close()
            connection.close()
            return is_find

        cursor_db.execute("SELECT * FROM search_benameiran3 WHERE en_name = %s AND category = %s",
                          (result['en_name'], 'movie'))
        is_find = cursor_db.fetchone()
        link = is_find['link']
        cursor_db.close()
        connection.close()

        response = requests.get(f'{link}', headers=headers)
        if response.status_code == requests.codes.ok:
            html_content = response.content.decode('utf-8')
            soup = BeautifulSoup(html_content, "html.parser")
            try:
                path_img = f"downloads/{result['en_name']}_3.jpg"
                try:
                    img_url = str(soup.find('div', {'data-title': 'اطلاعات فیلم'}).find('img').get('src').strip())
                except Exception as ex:
                    print(ex)
                    img_url = str(soup.find('div', class_="entry-content-single").find('img').get('src').strip())
                if 'benameiran' not in img_url:
                    img_url = f'https://benameiran3.com/{img_url}'
                img_data = requests.get(f'{img_url}').content
                with open(path_img, 'wb') as handler:
                    handler.write(img_data)
            except Exception as ex:
                print('Image Not Found: ', ex)
                path_img = ''
            try:
                description_parts = soup.select('div[data-title]')

                description_p1 = description_parts[0]
                try:
                    fig = description_p1.find('figure')
                    fig.extract()
                except Exception as ex:
                    print(f"Figure Not Found: {ex}")
                description_p1 = description_p1.get_text().strip()

                description_p2 = description_parts[1]
                try:
                    fig = description_p2.find('figure')
                    fig.extract()
                except Exception as ex:
                    print(f"Figure Not Found: {ex}")
                description_p2 = description_p2.get_text().strip()

                description_all = description_p1 + '\n\n' + description_p2
            except Exception as ex:
                print(ex)
                description_all = ''
            all_encode = soup.find_all('div', class_='su-button-center')
            link_dict = {}
            for encode in all_encode:
                this_link = encode.find_next('a').get('href')
                title = encode.find_next('span').text.strip()
                link_dict[title] = this_link
            link_dict = dict(reversed(link_dict.items()))
            myDict = {
                'server': 3,
                'name': result['en_name'],
                'link_page': link,
                'links': link_dict,
                'category': 'فیلم',
                'description': description_all,
                'path_img': path_img
            }
            link_str = json.dumps(link_dict)
            connection = create_connection()
            cursor_db = connection.cursor(buffered=True)
            cursor_db.execute("INSERT INTO media_benameiran3"
                              " (name, en_name, server, category, link_page, links, number_part, path_img, description) "
                              "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                              (result['name'], result['en_name'], 3, 'movie', link, link_str, 0, path_img,
                               description_all))
            connection.commit()
            cursor_db.close()
            connection.close()
            return myDict
        else:
            for admin_id in config.ADMINS_ID:
                try:
                    await app.send_message(chat_id=admin_id, text=f"Error Site: Benameiran\n"
                                                                  f"Status: Failed!")
                except Exception as ex:
                    print(f'Admin Start Bot: {ex}')
    return None


# String Link To Dictenory (Modal) [Donyaye Seryal]
def strToDict(string: str, model: str) -> dict:
    list_encode = {}
    if model == 'series':
        all_strs = string.split('^^')  # All String (Num Season)
        all_strs.remove('') if '' in all_strs else ''
        for se in all_strs:
            all_str = se.split('__')  # All String
            name = all_str[0]
            list_part = all_str[-1].split(',,')  # Part Of Link
            list_part.remove('') if '' in list_part else ''
            for part in list_part:
                checker = part.split('**')
                checker.remove('') if '' in checker else ''
                encode = checker[0]
                links = checker[1].split('%%')
                links.remove('') if '' in links else ''
                ch = {}
                for li in links:
                    f = li.split('++')
                    ch[f[0]] = f[1]
                list_encode[encode] = ch
        return list_encode
    all_str = string.split('__')  # All String
    name = all_str[0]
    list_part = all_str[-1].split(',,')  # Part Of Link
    list_part.remove('') if '' in list_part else ''
    for part in list_part:
        checker = part.split('**')
        checker.remove('') if '' in checker else ''
        encode = checker[0]
        links = checker[1].split('%%')
        links.remove('') if '' in links else ''
        ch = {}
        for li in links:
            f = li.split('++')
            ch[f[0]] = f[1]
        list_encode[encode] = ch
    return list_encode


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
