import datetime
from db_models import *
from peewee import InternalError
from telebot import logger
import logging
import traceback

logger.setLevel(logging.DEBUG)


def add_user(user_id, user_name):
    now = datetime.datetime.now()
    with conn:
        try:
            usr = User.select().where(User.userid == user_id).get()
            usr.lastseen = now
            usr.username = user_name
            usr.save()
        except DoesNotExist as de:
            User.insert(userid=user_id, username=user_name,
                        regdate=now, lastseen=now).execute()
        except Exception as ex:
            logger.debug('!!!!'+traceback.format_exc())


def get_userinfo(user_id):
    with conn:
        return User.get(User.userid == user_id)


def add_word(name, category_name, user_id, language_name):
    now = datetime.datetime.now()
    with conn:
        try:
            u = User.select().where(User.userid == user_id).get()
        except DoesNotExist as de:
            return 1
        try:
            c = Category.select().where(Category.name == category_name).get()
        except DoesNotExist as de:
            return 1
        try:
            l = Language.select().where(Language.name == language_name).get()
        except DoesNotExist as de:
            return 1
        try:
            w = Word.select().where(Word.name == name).get()
            return 1
        except DoesNotExist as de:
            Word.insert(name=name, createdate=now, categoryid=c.id,
                        createby=u.id, translatedby=1, language=l.id).execute()
        return 0


def add_wordpair(word_name, tranlateby_name, category_name, user_id, language_name1, language_name2):
    resultw = add_word(word_name, category_name, user_id, language_name1)
    if resultw == 1:
        return 1
    resultt = add_word(tranlateby_name, category_name, user_id, language_name2)
    if resultt == 1:
        return 1
    with conn:
        added_word = Word.select().where(Word.name == word_name).get()
        added_transl = Word.select().where(Word.name == tranlateby_name).get()
        added_word.translatedby = added_transl.id
        added_transl.translatedby = added_word.id
        added_word.save()
        added_transl.save()


def get_categories():
    with conn:
        return Category.select()


def get_languages():
    with conn:
        return Language.select()


def get_randomwords(list_id):
    with conn:
        return Word.select().where(Word.id.not_in(list_id)).order_by(fn.Random()).limit(5)


def get_wordbyid(word_id):
    with conn:
        return Word.select().where(Word.id == word_id).get()

def get_userbyid(user_id):
    with conn:
        return User.select().where(User.id == user_id).get()

def get_otherwordbyuserid(user_id, lang_id, cat_id):
    with conn:
        user = User.select().where(User.userid == user_id).get()
        userresultswordids = Result.select(
            Result.wordid).where(Result.userid == user.id)
        usertranslatebywordsids = Word.select(
            Word.translatedby).where(Word.id.in_(userresultswordids))
        query = Word.select().where((Word.id.not_in(userresultswordids)) & (
            Word.language == lang_id) & (
            Word.id.not_in(usertranslatebywordsids)) & (Word.categoryid == cat_id)).order_by(fn.Random()).limit(3)
        return list(query)


def update_usertasks(user_id):
    now = datetime.datetime.now()
    with conn:
        user = User.select().where(User.userid == user_id).get()
        try:
            activetaskcount = Result.select().where(
                (Result.userid == user.id) & (Result.isdone == False)).count()
            if activetaskcount < 5:
                utasksids = Result.select(Result.wordid).where(
                    Result.userid == user.id)
                words = get_randomwords(utasksids)
                for w in words:
                    Result.insert(userid=user.id, changedate=now, count=0,
                                  wordid=w.id).execute()
        except DoesNotExist as de:
            words = get_randomwords([])
            for w in words:
                Result.insert(userid=user.id, changedate=now, count=0,
                              wordid=w.id).execute()


def get_userdonetasks(user_id):
    with conn:
        user = User.select().where(User.userid == user_id).get()
        return Result.select().where((Result.userid == user.id) & (Result.isdone == True)).count()

def get_topusers():
    with conn:
        query = Result.select(Result.userid,fn.Count(Result.wordid).alias('count')).where(Result.isdone == True).group_by(Result.userid).order_by(fn.Count(Result.wordid).desc()).limit(5)
        return list(query)

def get_usertask(user_id):
    with conn:
        user = User.select().where(User.userid == user_id).get()
        return Result.select().where((Result.userid == user.id) & (Result.isdone == False)).order_by(Result.changedate, fn.Random()).limit(1).get()


def set_userresult(user_id, word_id, result, mess_id):
    with conn:
        user = User.select().where(User.userid == user_id).get()
        task = Result.select().where((Result.userid == user.id)
                                     & (Result.wordid == word_id)).get()
        if result == 'success':
            if task.count == 4:
                task.count = 5
                task.isdone = True
            else:
                task.count += 1
        else:
            task.count = 0
        task.changedate = datetime.datetime.now()
        task.messageid = mess_id
        task.save()


def isnew_userresult(user_id, word_id, mess_id):
    with conn:
        user = User.select().where(User.userid == user_id).get()
        task = Result.select().where((Result.userid == user.id)
                                     & (Result.wordid == word_id)).get()
        # minutes_diff = (datetime.datetime.now() - task.changedate).total_seconds() / 60.0
        if task.messageid == str(mess_id):
            return False
        else:
            return True


def save_messageinfo(chat_id, message_id):
    with conn:
        MessageInfo.insert(chatid=chat_id, messageid=message_id,
                           changedate=datetime.datetime.now()).execute()


def del_messageinfo(chat_id, message_id):
    with conn:
        MessageInfo.delete().where((MessageInfo.chatid == chat_id) &
                                   (MessageInfo.messageid == message_id)).execute()


def get_messageinfo(chat_id):
    with conn:
        try:
            m = MessageInfo.select().where(MessageInfo.chatid == chat_id)
        except DoesNotExist as de:
            return 1
        return m
