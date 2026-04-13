from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.keyboards.inline import get_back_to_admin_keyboard
from app.core.logging_config import get_logger
from app.services.userbot import UserbotService

logger = get_logger("handlers.userbot")

router = Router()


class UserbotAuthStates(StatesGroup):
    """Состояния для авторизации userbot."""
    waiting_phone = State()
    waiting_code = State()
    waiting_password = State()


@router.callback_query(F.data == "userbot:status")
async def cb_userbot_status(callback: CallbackQuery):
    """Проверить статус userbot."""
    from app.main import userbot
    
    logger.info("Проверка статуса userbot | User: {user}", user=callback.from_user.id)
    
    if not userbot:
        text = "❌ Userbot не инициализирован.\n\nПроверьте API ID/Hash в .env"
    elif userbot.is_authenticated():
        me = userbot.app.me
        text = (
            f"✅ <b>Userbot активен</b>\n\n"
            f"👤 <b>Аккаунт:</b> {me.first_name}\n"
            f"🆔 <b>Username:</b> @{me.username or 'N/A'}\n"
            f"🔢 <b>ID:</b> <code>{me.id}</code>\n\n"
            f"Userbot читает сообщения из чатов."
        )
    else:
        text = (
            f"❌ <b>Userbot не авторизован</b>\n\n"
            f"Для авторизации отправьте номер телефона.\n\n"
            f"<b>Инструкция:</b>\n"
            f"1. Получите API ID/Hash на my.telegram.org\n"
            f"2. Вставьте в .env файл\n"
            f"3. Отправьте номер телефона"
        )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "userbot:auth_start")
async def cb_userbot_auth_start(callback: CallbackQuery, state: FSMContext):
    """Начать авторизацию userbot."""
    logger.info("Начало авторизации userbot | User: {user}", user=callback.from_user.id)
    
    await state.set_state(UserbotAuthStates.waiting_phone)
    
    text = (
        f"🔐 <b>Авторизация Userbot</b>\n\n"
        f"Отправьте номер телефона аккаунта Telegram.\n\n"
        f"<b>Пример:</b> <code>+79991234567</code>\n\n"
        f"⚠️ Аккаунт будет использоваться для чтения сообщений."
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(UserbotAuthStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка номера телефона."""
    from app.main import userbot
    
    phone = message.text.strip()
    logger.info("Авторизация: отправка номера | Phone: {phone}", phone=phone)
    
    try:
        sent_code = await userbot.app.send_code(phone)
        
        await state.set_state(UserbotAuthStates.waiting_code)
        await state.update_data(phone=phone, phone_code_hash=sent_code.phone_code_hash)
        
        await message.answer(
            text=(
                f"✅ Код отправлен на {phone}\n\n"
                f"Введите код из Telegram (например: <code>12345</code>):"
            ),
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error("Ошибка отправки кода: {error}", error=str(e))
        await message.answer(
            text=f"❌ Ошибка: {str(e)}\n\nПопробуйте снова:",
            reply_markup=get_back_to_admin_keyboard()
        )


@router.message(UserbotAuthStates.waiting_code)
async def process_code(message: Message, state: FSMContext):
    """Обработка кода подтверждения."""
    from app.main import userbot
    
    code = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    
    logger.info("Авторизация: ввод кода | Code: {code}", code=code)
    
    try:
        await userbot.app.sign_in(phone, phone_code_hash, code)
        
        await state.clear()
        await message.answer(
            text="✅ <b>Userbot авторизован!</b>\n\nТеперь бот читает сообщения из чатов.",
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="HTML"
        )
        logger.info("Userbot успешно авторизован")
        
    except Exception as e:
        if "2FA" in str(e) or "password" in str(e).lower():
            await state.set_state(UserbotAuthStates.waiting_password)
            await message.answer(
                text="🔒 Введите пароль 2FA:",
                reply_markup=get_back_to_admin_keyboard()
            )
        else:
            logger.error("Ошибка авторизации: {error}", error=str(e))
            await message.answer(
                text=f"❌ Ошибка: {str(e)}",
                reply_markup=get_back_to_admin_keyboard()
            )


@router.message(UserbotAuthStates.waiting_password)
async def process_password(message: Message, state: FSMContext):
    """Обработка 2FA пароля."""
    from app.main import userbot
    
    password = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    
    logger.info("Авторизация: ввод 2FA пароля")
    
    try:
        await userbot.app.sign_in(phone, phone_code_hash, password=password)
        
        await state.clear()
        await message.answer(
            text="✅ <b>Userbot авторизован!</b>\n\nТеперь бот читает сообщения из чатов.",
            reply_markup=get_back_to_admin_keyboard(),
            parse_mode="HTML"
        )
        logger.info("Userbot авторизован с 2FA")
        
    except Exception as e:
        logger.error("Ошибка 2FA: {error}", error=str(e))
        await message.answer(
            text=f"❌ Ошибка 2FA: {str(e)}",
            reply_markup=get_back_to_admin_keyboard()
        )
