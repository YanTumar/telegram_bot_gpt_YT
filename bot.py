from http.client import responses

from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler, MessageHandler, filters

from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  default_callback_handler, load_prompt, send_text_buttons)

import credentials

### 3. *"Діалог з відомою особистістю"*
# Телеграм-бот повинен обробляти команду /talk.
# При обробці команди бот надсилає заздалегідь підготовлене зображення та
# пропонує вибір з декількох відомих особистостей,
# використовуючи кнопки. При натисканні кнопки потрібно встановити промпт обраної особистості.
# Подальші текстові повідомлення від користувача потрібно передавати ChatGPT та
# повертати його відповіді користувачеві.
# До них має бути прикріплена кнопка "Закінчити", натискання на яку
# працює так само, як команда /start

TALK_BUTTONS = {
    'talk_cobain': "Курт Кобейн",
    'talk_queen': "Єлизавета II",
    'talk_tolkien': "Джон Толкін",
    'talk_nietzsche': "Фрідріх Ніцше",
    'talk_hawking': "Стівен Гокінг"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт 🧠',
        'gpt': 'Задати питання чату GPT 🤖',
        'talk': 'Поговорити з відомою особистістю 👤',
        'quiz': 'Взяти участь у квізі ❓'
        # Додати команду в меню можна так:
        # 'command': 'button text'

    })


async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'random')
    prompt = load_prompt('random')
    response = await chat_gpt.send_question(prompt, 'Давай рандомний факт')
    await send_text_buttons(
        update, context,
        response,
        {
            'random_finish' : 'Закінчити',
            'random_one_more' :'Хочу ще факт',
        }
    )

async def random_buttons_handler(update: Update, context):
    query = update.callback_query.data
    if query == 'random_finish':
        await start(update, context)
    elif query == 'random_one_more':
        await random(update, context)
    await update.callback_query.answer()

chat_gpt = ChatGptService(credentials.ChatGPT_TOKEN)
app = ApplicationBuilder().token(credentials.BOT_TOKEN).build()

async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_text = update.message.text
    user_prompt = full_text[5:]
    await send_image(update, context, 'gpt')
    gpt_response = await chat_gpt.send_question('', user_prompt)
    # gpt_response = "TestText"
    await send_text(update, context, gpt_response)

async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'talk')
    message = load_message('talk')
    await send_text_buttons(update, context, message, TALK_BUTTONS)

async def talk_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fin = {
        'talk_end': "Закінчити розмову"
    }
    await update.callback_query.answer()
    query = update.callback_query.data
    prompt = load_prompt(query)
    context.user_data['prompt'] = prompt
    await send_image(update, context, query)

    character_name = TALK_BUTTONS[query]
    await send_text_buttons(update, context, f"Привіт, це {character_name}. Про що ти хочеш поговорити?", fin)

async def talk_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fin = {
        'talk_end': "Закінчити розмову"
    }
    if 'prompt' not in context.user_data:
        await send_text(update, context, "Будь ласка, спочатку обери персонажа за допомогою команди /talk")
        return
    character_prompt = context.user_data['prompt']
    user_text = update.message.text
    gpt_response = await chat_gpt.send_question(character_prompt, user_text)
    await send_text_buttons(update, context, gpt_response, fin)

async def talk_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query.data
    if query == 'talk_end':
        del context.user_data['prompt']
        await start(update, context)
    await update.callback_query.answer()

# Зареєструвати обробник команди можна так:
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('random', random))
app.add_handler(CommandHandler('gpt', gpt))
app.add_handler(CommandHandler('talk', talk))
app.add_handler(CallbackQueryHandler(talk_buttons_handler, pattern='^talk_end$'))
app.add_handler(CallbackQueryHandler(talk_button, pattern='^talk_.*$'))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk_message))


# Зареєструвати обробник колбеку можна так:
app.add_handler(CallbackQueryHandler(random_buttons_handler, pattern='^random_.*'))
# app.add_handler(CallbackQueryHandler(default_callback_handler))
app.run_polling()
