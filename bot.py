import logging
import telebot
from telebot.async_telebot import AsyncTeleBot
import asyncio
from settings import TOKEN
import db_main
from telebot import asyncio_filters
from telebot import types
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
from antiflood_middleware import AntiFloodMiddleware
import random
import re
import time


logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)


class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        logger.error(exception)


bot = AsyncTeleBot(TOKEN,
                   exception_handler=ExceptionHandler(),
                   state_storage=StateMemoryStorage())


class WordAddStates(StatesGroup):
    addedword = State()
    translateword = State()
    category = State()
    languageadded = State()
    languagetransl = State()


""" class WordLearnStates(StatesGroup):
    asknext = State()
    showword = State() """


class WordLearnStates(StatesGroup):
    iscancel = State()


@bot.message_handler(commands=['start'])
async def send_welcome(message):
    u = message.from_user.first_name
    if str(u) == "":
        u = 'user_' + message.from_user.id
    db_main.add_user(message.from_user.id, u)
    db_main.update_usertasks(message.from_user.id)
    await bot.send_message(
        message.chat.id,
        'Greetings! I can help you learn words.\n' +
        'To get help press /help.\n')


@bot.message_handler(commands=['help'])
async def help_command(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            'Message to the developer', url='telegram.me/oldboa'
        )
    )
    await bot.send_message(
        message.chat.id,
        'To start learning press /words.\n' +
        'To get statistic press /stat.',
        reply_markup=keyboard
    )


@bot.message_handler(commands=['stat'])
async def send_stat(message):
    userinfo = db_main.get_userinfo(message.from_user.id)
    userdonetasks = db_main.get_userdonetasks(message.from_user.id)
    msg = await bot.send_message(
        message.chat.id,
        'Name: ' + str(userinfo.username) + '\n' +
        'Regdate: ' + str(userinfo.regdate) + '\n' +
        'Lastseen: ' + str(userinfo.lastseen) + '\n' +
        'Words learned: ' + str(userdonetasks) + '\n' +
        'UserId: ' + str(message.from_user.id))
    db_main.save_messageinfo(msg.chat.id, msg.message_id)
    db_main.save_messageinfo(message.chat.id, message.message_id)


@bot.message_handler(commands=['top'])
async def send_top(message):
    usertoplist = db_main.get_topusers()
    strlist = 'Top users:\n'
    i = 1
    for u in usertoplist:
        userinfo = db_main.get_userbyid(u.userid)
        #logger.debug('!!!!!!!!!!!!!!!!!!!!!!!! u.userid ' + str(u.userid))
        strlist += str(i) + '. ' + str(userinfo.userid) + ' ' + str(userinfo.username) + \
            ' : ' + str(u.count) + '\n'
        i += 1
    msg = await bot.send_message(
        message.chat.id,
        str(strlist))
    db_main.save_messageinfo(msg.chat.id, msg.message_id)
    db_main.save_messageinfo(message.chat.id, message.message_id)


@bot.message_handler(commands=['cancel'])
async def command_cancel(message):
    await bot.set_state(message.from_user.id, WordLearnStates.iscancel, message.chat.id)
    markup = types.ReplyKeyboardMarkup(
        one_time_keyboard=True, resize_keyboard=True)
    markup.add('Cancel')
    markup.add('Continue')
    msg = await bot.send_message(message.chat.id, "What'll we do now?", reply_markup=markup)
    db_main.save_messageinfo(msg.chat.id, msg.message_id)
    db_main.save_messageinfo(message.chat.id, message.message_id)


@bot.message_handler(state=WordLearnStates.iscancel)
async def check_cancel(message):
    try:
        if len(message.text) > 10:
            await bot.delete_state(message.from_user.id, message.chat.id)
        else:
            input_string = re.sub(r'[\W_]+', '', message.text)
            commands = ['Cancel']
            if input_string not in commands:
                await bot.delete_state(message.from_user.id, message.chat.id)
            elif input_string == 'Cancel':
                return
    except Exception as e:
        pass


@bot.message_handler(commands=['words'])
async def command_words(message):
    u = message.from_user.first_name
    if str(u) == "":
        u = 'user_' + message.from_user.id
    db_main.add_user(message.from_user.id, u)
    user_id = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    await show_word(user_id, chat_id, message_id)


async def show_word(user_id, chat_id, message_id):
    db_main.update_usertasks(user_id)
    task = db_main.get_usertask(user_id)
    mainword = db_main.get_wordbyid(task.wordid)
    translateword = db_main.get_wordbyid(mainword.translatedby)
    otherwords = db_main.get_otherwordbyuserid(
        user_id, translateword.language, translateword.categoryid)
    otherwords.append(translateword)
    random.shuffle(otherwords)
    keyboard = telebot.types.InlineKeyboardMarkup()
    i = 1
    for w in otherwords:
        if i % 2 == 0:
            keyboard.row(
                btn,
                telebot.types.InlineKeyboardButton(
                    w.name, callback_data='word-'+str(mainword.id)+'-'+str(w.id)+'-'+','.join(str(x) for x in otherwords))
            )
        else:
            btn = telebot.types.InlineKeyboardButton(
                w.name, callback_data='word-'+str(mainword.id)+'-'+str(w.id)+'-'+','.join(str(x) for x in otherwords))
        i += 1
    prevmessages = db_main.get_messageinfo(chat_id)
    if prevmessages != 1:
        try:
            for pm in prevmessages:
                await bot.delete_message(pm.chatid, pm.messageid)
        except Exception as ex:
            pass
        try:
            for pm in prevmessages:
                db_main.del_messageinfo(pm.chatid, pm.messageid)
        except Exception as ex:
            pass
    cancel_state = await bot.get_state(user_id, chat_id)
    if str(cancel_state) == 'WordLearnStates:iscancel':
        await bot.delete_state(user_id, chat_id)
        msg = await bot.send_message(chat_id, "Training was cancelled")
    else:
        msg = await bot.send_message(
            chat_id,
            'What is the correct word to translate:\n' +
            str(mainword.name),
            reply_markup=keyboard
        )
    db_main.save_messageinfo(msg.chat.id, msg.message_id)
    db_main.save_messageinfo(chat_id, message_id)


@bot.callback_query_handler(func=lambda call: True)
async def iq_callback(query):
    data = query.data
    if data.startswith('word-'):
        await get_callback(query)


async def get_callback(query):
    user_id = query.from_user.id
    mainword_id = query.data.split('-')[1]
    translword_id = query.data.split('-')[2]
    orderedwordsid = query.data.split('-')[3]
    if db_main.isnew_userresult(user_id, mainword_id, query.message.message_id) == False:
        await bot.answer_callback_query(query.id, text="❗ You have already answered this question!")
        return
    mainword = db_main.get_wordbyid(mainword_id)
    if str(mainword.translatedby) == translword_id:
        emoji = '✅'
    else:
        emoji = '❌'
    keyboard = telebot.types.InlineKeyboardMarkup()
    i = 1
    for w in orderedwordsid.split(','):
        currentword = db_main.get_wordbyid(w)
        if w == translword_id:
            buttonname = emoji + ' ' + currentword.name
        else:
            buttonname = currentword.name
        if i % 2 == 0:
            keyboard.row(
                btn,
                telebot.types.InlineKeyboardButton(
                    buttonname, callback_data='word-'+str(mainword.id)+'-'+w+'-'+orderedwordsid)
            )
        else:
            btn = telebot.types.InlineKeyboardButton(
                buttonname, callback_data='word-'+str(mainword.id)+'-'+w+'-'+orderedwordsid)
        i += 1

    if str(mainword.translatedby) == translword_id:
        db_main.set_userresult(user_id, mainword_id,
                               'success', query.message.message_id)
        await bot.answer_callback_query(query.id, text="✅ The answer is correct!")
    else:
        db_main.set_userresult(user_id, mainword_id,
                               'failure', query.message.message_id)
        await bot.answer_callback_query(query.id, text="❌ Wrong. Try again later...")
    await bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id, text='What is the correct word to translate:\n' + str(mainword.name), reply_markup=keyboard)
    time.sleep(5)
    await show_word(user_id, query.message.chat.id, query.message.message_id)


@bot.message_handler(commands=['addword'])
async def start_ex(message):
    if str(message.from_user.id) == '500208977':
        await bot.set_state(message.from_user.id, WordAddStates.addedword, message.chat.id)
        await bot.send_message(message.chat.id, 'Hi, write me the word')
    else:
        await bot.send_message(message.chat.id, 'Admin access only')


@bot.message_handler(state="*", commands=['Cancel'])
async def any_state(message):
    await bot.send_message(message.chat.id, "Your state was cancelled.")
    await bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(state=WordAddStates.addedword)
async def addedword_get(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    languages = db_main.get_languages()
    for lang in languages:
        markup.add(lang.name)
    await bot.send_message(message.chat.id, f'What language is this word?', reply_markup=markup)
    await bot.set_state(message.from_user.id, WordAddStates.languageadded, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['addedword'] = message.text


@bot.message_handler(state=WordAddStates.languageadded)
async def language_get(message):
    await bot.send_message(message.chat.id, f'Now write me translation of the word')
    await bot.set_state(message.from_user.id, WordAddStates.translateword, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['languageadded'] = message.text


@bot.message_handler(state=WordAddStates.translateword)
async def translateword_get(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    languages = db_main.get_languages()
    for lang in languages:
        markup.add(lang.name)
    await bot.send_message(message.chat.id, f'What language is this translation?', reply_markup=markup)
    await bot.set_state(message.from_user.id, WordAddStates.languagetransl, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['translateword'] = message.text


@bot.message_handler(state=WordAddStates.languagetransl)
async def ask_category(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    categories = db_main.get_categories()
    for cat in categories:
        markup.add(cat.name)
    await bot.send_message(message.chat.id, "What will be the category?", reply_markup=markup)
    await bot.set_state(message.from_user.id, WordAddStates.category, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['languagetransl'] = message.text


@bot.message_handler(state=WordAddStates.category)
async def ready_for_answer(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        await bot.send_message(message.chat.id, "Ready, take a look:\n<b>addedword: {addedword}\nlanguageadded: {languageadded}\ntranslateword: {translateword}\nlanguagetransl: {languagetransl}\ncategory: {category}</b>".format(addedword=data['addedword'], translateword=data['translateword'], languagetransl=data['languagetransl'], languageadded=data['languageadded'], category=message.text), parse_mode="html")
        result = db_main.add_wordpair(
            data['addedword'], data['translateword'], message.text, message.from_user.id,  data['languageadded'],  data['languagetransl'])
    if result == 1:
        await bot.send_message(message.chat.id, "Error save data")
    else:
        await bot.send_message(message.chat.id, "Data saved")
    await bot.delete_state(message.from_user.id, message.chat.id)


bot.setup_middleware(AntiFloodMiddleware(limit=2, bot=bot))
bot.add_custom_filter(asyncio_filters.StateFilter(bot))

asyncio.run(bot.polling(none_stop=True))
