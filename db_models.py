from peewee import *
from settings import DBNAME, DBUSER, DBPASS

conn = PostgresqlDatabase(DBNAME,
                          user=DBUSER,
                          password=DBPASS,
                          host="localhost",
                          port="5432")


class BaseModel(Model):
    id = PrimaryKeyField(unique=True)

    class Meta:
        database = conn


class User(BaseModel):
    userid = CharField(unique=True)
    username = CharField()
    regdate = DateTimeField()
    lastseen = DateTimeField()

    class Meta:
        table_name = 'users'


class Category(BaseModel):
    name = CharField()
    createdate = DateTimeField()
    createby = ForeignKeyField(User)

    class Meta:
        table_name = 'categories'


class Language(BaseModel):
    name = CharField()
    createdate = DateTimeField()
    createby = ForeignKeyField(User)

    class Meta:
        table_name = 'languages'


class Word(BaseModel):
    name = CharField()
    language = ForeignKeyField(Language)
    categoryid = ForeignKeyField(Category)
    translatedby = ForeignKeyField('self')
    createdate = DateTimeField()
    createby = ForeignKeyField(User)

    class Meta:
        table_name = 'words'


class Result(BaseModel):
    userid = ForeignKeyField(User)
    wordid = ForeignKeyField(Word)
    isdone = BooleanField(default=False)
    count = SmallIntegerField()
    changedate = DateTimeField()
    messageid = CharField(null=True)

    class Meta:
        table_name = 'results'


class MessageInfo(BaseModel):
    chatid = CharField()
    messageid = CharField()
    changedate = DateTimeField()

    class Meta:
        table_name = 'messageinfos'


try:
    with conn:
        conn.create_tables([User, Word, Category, Result, Language, MessageInfo])
except InternalError as px:
    print(str(px))
