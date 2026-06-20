from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler, MessageHandler, filters

from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  default_callback_handler, load_prompt, send_text_buttons)

import credentials
import re

chat_gpt = ChatGptService(credentials.ChatGPT_TOKEN)
app = ApplicationBuilder().token(credentials.BOT_TOKEN).build()

chat_modes = {}

TRANSLATOR_BUTTONS = {
    'translator_en': "Англійська 🇺🇸",
    'translator_uk': "Українська 🇺🇦",
    'translator_fr': "Французька 🇫🇷",
    'translator_de': "Німецька 🇩🇪"
}

RECOMMEND_BUTTONS = {
    'books': "Книги📚",
    'films': "Фільми🎬",
    'music': "Музика🎵"
}

warning_quiz = "Будь ласка, спочатку завершіть поточний квіз."
warning_translator = "Будь-ласка, спочатку завершіть переклад."
quiz_end_session = "Цей квіз уже завершено або він недійсний."

async def is_user_busy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    mode = chat_modes.get(user_id)

    if mode == 'GPT_MODE':
        gpt_warning = "Ця кнопка вже недійсна в поточному режимі."
        if update.message and update.message.text:
            await plain_text_handler(update, context)
            return True
        elif update.callback_query:
            await update.callback_query.answer(gpt_warning)
            return True

    elif mode == 'RANDOM_MODE':
        random_warning = "Будь ласка, спочатку завершіть перегляд факту"
        if update.callback_query:
            if update.callback_query.data.startswith('random_'):
                return False
            else:
                await update.callback_query.answer(random_warning)
                return True
        elif update.message and update.message.text:
            await send_text(update, context, random_warning)
            return True

    elif mode == 'TALK_MODE':
        warning_text = "Будь ласка, спочатку закінчіть розмову з відомою особистістю."
        if update.callback_query:
            await update.callback_query.answer(warning_text)
        else:
            await send_text(update, context, warning_text)
        return True

    elif mode == 'TALK_CHOICE_MODE':
        if update.callback_query:
            if update.callback_query.data.startswith('talk_'):
                return False
            else:
                await update.callback_query.answer("Спочатку оберіть відому особу зі списку.")
                return True
            
        elif update.message:
            await send_text(update, context, "Будь ласка, оберіть співрозмовника, натиснувши на кнопку.")
            return True

    elif mode == 'QUIZ_MODE':
        if update.callback_query:
            if not update.callback_query.data.startswith('quiz_'):
                await update.callback_query.answer(warning_quiz)
                return True

        elif update.message and update.message.text and update.message.text.startswith('/'):
            await send_text(update, context, warning_quiz)
            return True

    elif mode == 'QUIZ_GAME_MODE':
        if update.callback_query:
            await update.callback_query.answer(warning_quiz)
            return True

        elif update.message and update.message.text and update.message.text.startswith('/'):
            await send_text(update, context, warning_quiz)
            return True


    elif mode in ['TRANSLATOR_MODE', 'TRANSLATOR_CHOICE_MODE']:
        if update.callback_query:
            if not update.callback_query.data.startswith('translator_'):
                await update.callback_query.answer(warning_translator)
                return True

        elif update.message and update.message.text and update.message.text.startswith('/'):
            await send_text(update, context, warning_translator)
            return True

    elif mode in ['RECOMMEND_CHOICE_MODE', 'RECOMMEND_GENRE_MODE']:
        warning_recommend = "Будь ласка, спочатку завершіть роботу з рекомендаціями."
        if update.callback_query:
            await update.callback_query.answer(warning_recommend)
            return True

        elif update.message and update.message.text and update.message.text.startswith('/'):
            await send_text(update, context, warning_recommend)
            return True

    return False

TALK_BUTTONS = {
    'talk_cobain': "Курт Кобейн",
    'talk_queen': "Єлизавета II",
    'talk_tolkien': "Джон Толкін",
    'talk_nietzsche': "Фрідріх Ніцше",
    'talk_hawking': "Стівен Гокінг"
}

QUIZ_BUTTONS = {
    'quiz_prog': "Програмування",
    'quiz_math': "Математика",
    'quiz_biology': "Біологія"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_modes[update.effective_user.id] = None
    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт 🧠',
        'gpt': 'Задати питання чату GPT 🤖',
        'talk': 'Поговорити з відомою особистістю 👤',
        'quiz': 'Взяти участь у квізі ❓',
        'translator': 'Перекладач 🌐',
        'recommend': 'Рекомендації книг/фільмів/музики 📚🎬🎵'
    })


async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return

    await send_image(update, context, 'random')
    intro_text = load_message('random')
    chat_modes[update.effective_user.id] = 'RANDOM_MODE'
    await send_text(update, context, intro_text)
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
    if await is_user_busy(update, context):
        return
    query = update.callback_query.data
    if query == 'random_finish':
        await start(update, context)
    elif query == 'random_one_more':
        await random(update, context)
    await update.callback_query.answer()

async def gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    welcome_message = load_message('gpt')
    await send_image(update, context, 'gpt')
    chat_modes[update.effective_user.id] = 'GPT_MODE'
    if update.message and update.message.text:
        full_text = update.message.text
        user_prompt = full_text[len("/gpt "):].strip()
    else:
        user_prompt = ""
    if user_prompt == "":
        await send_text(update, context, welcome_message)
    else:
        prompt = load_prompt('gpt')
        chat_gpt.set_prompt(prompt)
        gpt_response = await chat_gpt.add_message(user_prompt)
        await send_text(update, context, gpt_response)

async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return

    await send_image(update, context, 'talk')
    message = load_message('talk')
    chat_modes[update.effective_user.id] = 'TALK_CHOICE_MODE'
    await send_text_buttons(update, context, message, TALK_BUTTONS)

async def talk_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_mode = chat_modes.get(user_id)
    if current_mode != 'TALK_CHOICE_MODE':
        await update.callback_query.answer("Цей список вже застарів")
        return
    fin = {
        'talk_end': "Закінчити розмову"
    }
    if await is_user_busy(update, context):
        return
    await update.callback_query.answer()
    query = update.callback_query.data
    prompt = load_prompt(query)
    chat_gpt.set_prompt(prompt)
    chat_modes[update.effective_user.id] = 'TALK_MODE'
    await send_image(update, context, query)

    character_name = TALK_BUTTONS[query]
    await send_text_buttons(update, context, f"Привіт, це {character_name}. Про що ти хочеш поговорити?", fin)

async def plain_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    mode = chat_modes.get(user_id)

    user_text = update.message.text

    if mode == "GPT_MODE":
        gpt_response = await chat_gpt.add_message(user_text)
        await send_text_buttons(update, context, gpt_response, {'gpt_end': "Закінчити розмову"})

    elif mode == "TALK_MODE":
        gpt_response = await chat_gpt.add_message(user_text)
        await send_text_buttons(update, context, gpt_response, {'talk_end': "Закінчити розмову"})

    elif mode == "QUIZ_GAME_MODE":
        context.user_data['quiz_questions_count'] += 1
        gpt_response = await chat_gpt.add_message(user_text)

        if "Правильно" in gpt_response:
            context.user_data['quiz_score'] += 1
        await send_text(update, context, gpt_response)

        if context.user_data['quiz_questions_count'] >= 5:
            await send_text_buttons(update,
                                    context,
                                    f"Квіз завершено! Ваш результат: {context.user_data['quiz_score']} з 5",
                                    {
                                        'quiz_continue': "Продовжити квіз",
                                        'quiz_change': "Змінити тему",
                                        'quiz_end': "Закінчити квіз"
                                    })

        else:
            gpt_next_question = await chat_gpt.add_message('quiz_more')
            await send_text(update, context, gpt_next_question)

    elif mode == "TRANSLATOR_MODE":
        await translator_text_handler(update, context)

    elif mode == "RECOMMEND_GENRE_MODE":
        await recommend_text_handler(update, context)

async def gpt_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query.data
    user_id = update.effective_user.id
    current_mode = chat_modes.get(user_id)

    if current_mode != 'GPT_MODE':
        await update.callback_query.answer('Ця команда вже застаріла')
        return

    if query == 'gpt_end':
        chat_modes[update.effective_user.id] = None
        chat_gpt.message_list.clear()
        await start(update, context)
    await update.callback_query.answer()

async def talk_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query.data
    if query == 'talk_end':
        chat_gpt.message_list.clear()
        await start(update, context)
    await update.callback_query.answer()

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    chat_modes[update.effective_user.id] = 'QUIZ_MODE'
    start_message = load_message('quiz')
    await send_image(update, context, 'quiz')
    await send_text_buttons(update, context, start_message, QUIZ_BUTTONS)

async def quiz_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_mode = chat_modes.get(user_id)

    if current_mode != 'QUIZ_MODE':
        await update.callback_query.answer(quiz_end_session)
        return

    if await is_user_busy(update, context):
        return
    chat_modes[update.effective_user.id] = 'QUIZ_GAME_MODE'
    query = update.callback_query.data
    await update.callback_query.answer()
    context.user_data['quiz_questions_count'] = 0
    context.user_data['quiz_score'] = 0
    prompt = load_prompt('quiz')
    chat_gpt.set_prompt(prompt)
    gpt_response = await chat_gpt.add_message(query)
    await send_text(update, context, gpt_response)

async def quiz_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_mode = chat_modes.get(user_id)

    if current_mode != 'QUIZ_GAME_MODE':
        await update.callback_query.answer(quiz_end_session)
        return

    query = update.callback_query.data
    if query == 'quiz_end':
        chat_gpt.message_list.clear()
        await start(update, context)

    elif query == 'quiz_change':
        chat_gpt.message_list.clear()
        chat_modes[update.effective_user.id] = None
        await quiz(update, context)

    elif query == 'quiz_continue':
        context.user_data['quiz_questions_count'] = 0
        context.user_data['quiz_score'] = 0
        gpt_next_question = await chat_gpt.add_message('quiz_more')
        await send_text(update, context, gpt_next_question)
    await update.callback_query.answer()

async def translator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    chat_modes[update.effective_user.id] = 'TRANSLATOR_CHOICE_MODE'
    await send_image(update, context, 'translator')
    start_message = load_message('translator')
    await send_text_buttons(update, context, start_message, TRANSLATOR_BUTTONS)

async def translator_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_mode = chat_modes.get(user_id)

    if current_mode != 'TRANSLATOR_CHOICE_MODE':
        await update.callback_query.answer("Цей список вже застарів")
        return

    query = update.callback_query.data
    context.user_data['target_language'] = query

    await update.callback_query.answer()

    prompt = load_prompt('translator')
    chat_gpt.set_prompt(prompt)

    chat_modes[update.effective_user.id] = 'TRANSLATOR_MODE'
    await send_text(update, context, "Чудово! Тепер напиши текст, який хочеш перекласти.")

async def translator_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    target_language = context.user_data['target_language']

    language_name = TRANSLATOR_BUTTONS.get(target_language, "обрану мову")

    gpt_response = await chat_gpt.add_message(f"Переклади на {language_name}: {user_text}")
    await send_text_buttons(update, context, gpt_response, {
        'translator_end': "Закінчити переклад",
        'translator_change': "Змінити мову"})

async def translator_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query.data
    if query == 'translator_end':
        chat_gpt.message_list.clear()
        chat_modes[update.effective_user.id] = None
        await start(update, context)
    elif query == 'translator_change':
        chat_gpt.message_list.clear()
        await translator(update, context)

    await update.callback_query.answer()

async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_busy(update, context):
        return
    chat_modes[update.effective_user.id] = 'RECOMMEND_CHOICE_MODE'
    start_message = load_message('recommend')
    await send_image(update, context, 'recommend')
    await send_text_buttons(update, context, start_message, RECOMMEND_BUTTONS)

async def recommend_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_mode = chat_modes.get(user_id)

    if current_mode != 'RECOMMEND_CHOICE_MODE':
        await update.callback_query.answer("Ця рекомендація вже застаріла")
        return
    chat_gpt.message_list.clear()

    query = update.callback_query.data
    context.user_data['recommend_category'] = query
    chat_modes[update.effective_user.id] = 'RECOMMEND_GENRE_MODE'

    category_name = RECOMMEND_BUTTONS.get(query)

    await send_text(update, context, f"Чудово! Тепер напиши жанр або настрій для категорії {category_name}:")
    await update.callback_query.answer()

    prompt = load_prompt('recommend')
    chat_gpt.set_prompt(prompt)


async def recommend_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_gpt.message_list.clear()
    chat_gpt.set_prompt(load_prompt('recommend'))
    category = context.user_data.get('recommend_category')

    if update.message and update.message.text:
        genre = update.message.text
        context.user_data['recommend_genre'] = genre
    else:
        genre = context.user_data.get('recommend_genre')

    category_name = RECOMMEND_BUTTONS.get(category)
    await send_text(update, context, "Зачекайте хвилинку, підбираю найкращі варіанти...")
    user_request = f"Категорія: {category_name}, Жанр/Настрій: {genre}. Поверни строго 3 варіанти. "
    if context.user_data.get('ignored_titles'):
        ignored = ". ".join(context.user_data['ignored_titles'])
        user_request += f" Не пропонуй ці варіанти: {ignored}."
    gpt_response = await chat_gpt.add_message(user_request)

    msg = await send_text_buttons(update, context, gpt_response, {
        'recommend_not_like': "Не подобається",
        'recommend_end': "Закінчити"
    })

    context.user_data['last_recommend_msg_id'] = msg.message_id

async def recommend_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_mode = chat_modes.get(user_id)

    if current_mode != 'RECOMMEND_GENRE_MODE':
        await update.callback_query.answer("Ця рекомендація вже застаріла")
        return

    current_msg_id = update.callback_query.message.message_id
    last_msg_id = context.user_data.get('last_recommend_msg_id')

    if current_msg_id != last_msg_id:
        await update.callback_query.answer("Це повідомлення вже застаріле.")
        return

    query = update.callback_query.data
    if query == 'recommend_end':
        chat_gpt.message_list.clear()
        chat_modes[update.effective_user.id] = None
        if 'ignored_titles' in context.user_data:
            del context.user_data['ignored_titles']
        await start(update, context)

    elif query == 'recommend_not_like':
        last_recommendation = update.callback_query.message.text
        if "не зовсім зрозумів" in last_recommendation.lower() or "перепрошую" in last_recommendation.lower():
            chat_gpt.message_list.clear()
            await update.callback_query.edit_message_text(
                "Цей запит не було розпізнано. Будь ласка, введіть інший жанр у поле вводу знизу."
            )
            await update.callback_query.answer()
            return

        if 'ignored_titles' not in context.user_data:
            context.user_data['ignored_titles'] = []

        found_titles = re.findall(r'\*\*"([^"]+)"\*\*', last_recommendation)
        context.user_data['ignored_titles'].extend(found_titles)
        await recommend_text_handler(update, context)
    await update.callback_query.answer()


# Зареєструвати обробник команди можна так:
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('random', random))
app.add_handler(CommandHandler('gpt', gpt))
app.add_handler(CommandHandler('talk', talk))
app.add_handler(CommandHandler('quiz', quiz))
app.add_handler(CommandHandler('translator', translator))
app.add_handler(CommandHandler('recommend', recommend))
app.add_handler(CallbackQueryHandler(talk_buttons_handler, pattern='^talk_end.*$'))
app.add_handler(CallbackQueryHandler(gpt_buttons_handler, pattern='^gpt_.*$'))
app.add_handler(CallbackQueryHandler(talk_button, pattern='^talk_.*$'))
app.add_handler(CallbackQueryHandler(translator_button, pattern='^translator_(en|uk|fr|de)$'))
app.add_handler(CallbackQueryHandler(translator_buttons_handler, pattern='^translator_(end|change)$'))
app.add_handler(CallbackQueryHandler(quiz_buttons_handler, pattern='^quiz_(continue|change|end)$'))
app.add_handler(CallbackQueryHandler(quiz_button, pattern='^quiz_.*$'))
app.add_handler(CallbackQueryHandler(recommend_button, pattern='^(books|films|music)$'))
app.add_handler(CallbackQueryHandler(recommend_buttons_handler, pattern='^recommend_.*$'))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_handler))


# Зареєструвати обробник колбеку можна так:
app.add_handler(CallbackQueryHandler(random_buttons_handler, pattern='^random_.*'))
# app.add_handler(CallbackQueryHandler(default_callback_handler))
app.run_polling()
