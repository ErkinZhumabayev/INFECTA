# Telegram Bot Handlers and Routers

import logging
from typing import Optional
from datetime import datetime, timezone

from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import async_session_maker
from app.game.repositories import PlayerRepository, ResourceRepository
from app.game.services import CombatService, VirusService, DefenseService
from app.telegram.keyboards.main import (
    main_menu_keyboard, lab_menu_keyboard, virus_menu_keyboard,
    defense_menu_keyboard, attack_menu_keyboard, attack_confirm_keyboard,
    profile_keyboard, leaderboard_keyboard, back_keyboard
)
from app.config import config

logger = logging.getLogger(__name__)

# Main router
router = Router()


# FSM States for onboarding and rename
class OnboardingStates(StatesGroup):
    waiting_for_virus_name = State()


class RenameStates(StatesGroup):
    waiting_for_new_name = State()


# Helper function to get database session
async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        return session


def format_player_profile(player, is_own: bool = True) -> str:
    """Format player profile message"""
    username = f"@{player.username}" if player.username else player.first_name or "Игрок"
    
    virus_name = player.virus.name if player.virus else "Неизвестный штамм"
    virus_power = player.virus.power if player.virus else 0
    defense_power = player.defense.power if player.defense else 0
    
    resources = player.resources
    energy = resources.energy if resources else 0
    credits = float(resources.credits) if resources else 0
    samples = float(resources.samples) if resources else 0
    
    infection_state = player.infection_state
    status_text = "🟢 Здоров"
    if infection_state:
        if infection_state.status.value == "infected":
            status_text = "🔴 Заражён"
            if infection_state.recovery_expires_at:
                recovery_time = infection_state.recovery_expires_at - datetime.now(timezone.utc)
                if recovery_time.total_seconds() > 0:
                    hours = int(recovery_time.total_seconds() / 3600)
                    status_text += f" (восст. ~{hours}ч)"
        elif infection_state.status.value == "recovering":
            status_text = "🟡 Восстанавливается"
    
    stats_text = f"""
🧪 <b>ЛАБОРАТОРИЯ</b>

👤 Игрок: {username}
🎯 Уровень: {player.level}

🦠 <b>Вирус:</b>
   Название: {virus_name}
   ⚔️ Сила вируса: {virus_power}

🛡 <b>Защита:</b>
   🛡 Мощность защиты: {defense_power}

⚡ <b>Ресурсы:</b>
   💰 Кредиты: {int(credits)}
   🧬 Образцы: {int(samples)}
   ⚡ Энергия: {energy}/{config.energy.MAX_ENERGY}

📊 <b>Статистика:</b>
   ⚔️ Атак проведено: {player.total_attacks_made}
   ✅ Успешных атак: {player.successful_attacks}
   🛡 Отражено атак: {player.successful_defenses}
   🔥 Лучшая серия: {player.best_streak}

<b>Статус:</b> {status_text}
"""
    return stats_text


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    # Get or create player
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        
        player = await player_repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
        )
        
        # Check if this is a new player (needs onboarding)
        if player.virus and player.virus.name == "Unknown Strain":
            await message.answer(
                "🧬 <b>Добро пожаловать в Virolabs!</b>\n\n"
                "Вы — руководитель секретной лаборатории.\n"
                "Ваша задача: создать собственный вирус и защитить свою лабораторию от других игроков.\n\n"
                "Придумайте название для вашего вируса:",
                parse_mode="HTML"
            )
            await state.set_state(OnboardingStates.waiting_for_virus_name)
            return
        
        # Existing player - show main menu
        await message.answer(
            f"👋 С возвращением, {player.first_name or 'Игрок'}!\n\n"
            "Выберите действие:",
            reply_markup=main_menu_keyboard(),
        )


@router.message(OnboardingStates.waiting_for_virus_name)
async def process_virus_name(message: types.Message, state: FSMContext):
    """Process virus name during onboarding"""
    virus_name = message.text.strip()
    
    if len(virus_name) < 3:
        await message.answer("❌ Название слишком короткое (минимум 3 символа). Попробуйте снова:")
        return
    
    if len(virus_name) > 64:
        await message.answer("❌ Название слишком длинное (максимум 64 символа). Попробуйте снова:")
        return
    
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        player = await player_repo.get_by_id(message.from_user.id)
        
        if player and player.virus:
            player.virus.name = virus_name
            
            # Recalculate power
            virus_service = VirusService(session)
            player.virus.power = virus_service.calculate_virus_power(player.virus)
            
            await session.commit()
    
    await state.clear()
    
    await message.answer(
        f"🦠 Отлично! Ваш вирус назван: <b>{virus_name}</b>\n\n"
        "Теперь вы готовы к игре!\n\n"
        "💡 <b>Совет:</b> Развивайте вирус для атак и защиту для обороны.\n"
        "Но помните: слишком агрессивных игроков могут начать бояться... или объединиться против них.\n\n"
        "Используйте меню ниже для управления лабораторией:",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("lab"))
async def cmd_lab(message: types.Message):
    """Handle .lab or /lab command - show profile"""
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        player = await player_repo.get_by_id(message.from_user.id)
        
        if not player:
            await message.answer("❌ Вы ещё не зарегистрированы. Используйте /start")
            return
        
        # Update production before showing
        resource_repo = ResourceRepository(session)
        await resource_repo.update_pending_production(message.from_user.id)
        
        profile_text = format_player_profile(player, is_own=True)
        
        await message.answer(
            profile_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "menu_main")
async def cb_menu_main(callback: types.CallbackQuery):
    """Show main menu"""
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        player = await player_repo.get_by_id(callback.from_user.id)
        
        if not player:
            await callback.answer("❌ Игрок не найден", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"🧪 <b>Virolabs</b>\n\n"
            f"Игрок: @{player.username or player.first_name}\n"
            f"Уровень: {player.level}\n\n"
            "Выберите действие:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data == "menu_lab")
async def cb_menu_lab(callback: types.CallbackQuery):
    """Show laboratory menu"""
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        resource_repo = ResourceRepository(session)
        player = await player_repo.get_by_id(callback.from_user.id)
        
        if not player or not player.laboratory:
            await callback.answer("❌ Лаборатория не найдена", show_alert=True)
            return
        
        # Update pending production
        await resource_repo.update_pending_production(callback.from_user.id)
        
        lab = player.laboratory
        pending_credits = float(lab.pending_credits or 0)
        pending_samples = float(lab.pending_samples or 0)
        
        text = f"""🔬 <b>ЛАБОРАТОРИЯ</b>

Уровень лаборатории: {lab.level}

🏗 <b>Объекты:</b>
⚡ Энергоядро: ур. {lab.energy_core_level}
🔬 Исследовательский центр: ур. {lab.research_center_level}
🧬 Лаборатория мутаций: ур. {lab.mutation_lab_level}
🛡 Центр защиты: ур. {lab.defense_center_level}
📦 Хранилище: ур. {lab.storage_level}

💰 <b>Ожидают сбора:</b>
Кредиты: {int(pending_credits)}
Образцы: {int(pending_samples)}
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=lab_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data == "menu_virus")
async def cb_menu_virus(callback: types.CallbackQuery):
    """Show virus menu"""
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        player = await player_repo.get_by_id(callback.from_user.id)
        
        if not player or not player.virus:
            await callback.answer("❌ Вирус не найден", show_alert=True)
            return
        
        virus = player.virus
        
        text = f"""🦠 <b>ВИРУС: {virus.name}</b>

Уровень: {virus.level}
⚔️ Общая сила: {virus.power}

📊 <b>Характеристики:</b>
☣️ Заразность: {virus.infectivity}
🔄 Адаптация: {virus.adaptation}
💪 Устойчивость: {virus.persistence}
🧬 Частота мутаций: {virus.mutation_rate}
⚡ Мощность: {virus.potency}

Нажмите на характеристику для улучшения.
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=virus_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data == "menu_defense")
async def cb_menu_defense(callback: types.CallbackQuery):
    """Show defense menu"""
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        player = await player_repo.get_by_id(callback.from_user.id)
        
        if not player or not player.defense:
            await callback.answer("❌ Система защиты не найдена", show_alert=True)
            return
        
        defense = player.defense
        
        shield_info = ""
        if defense.shield > 0 and defense.shield_expires_at:
            remaining = defense.shield_expires_at - datetime.now(timezone.utc)
            if remaining.total_seconds() > 0:
                shield_info = f"\n🔵 <b>Щит активен:</b> {int(remaining.total_seconds() / 60)} мин."
        
        text = f"""🛡 <b>СИСТЕМА ЗАЩИТЫ</b>

Уровень: {defense.level}
🛡 Общая мощность: {defense.power}

📊 <b>Характеристики:</b>
🛡 Иммунитет: {defense.immunity}
🔒 Сопротивление: {defense.resistance}
💚 Восстановление: {defense.recovery}
📡 Обнаружение: {defense.detection}
{shield_info}

Нажмите на характеристику для улучшения.
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=defense_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data == "menu_attack")
async def cb_menu_attack(callback: types.CallbackQuery):
    """Show attack target selection"""
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        combat_service = CombatService(session)
        
        player = await player_repo.get_by_id(callback.from_user.id)
        if not player:
            await callback.answer("❌ Игрок не найден", show_alert=True)
            return
        
        # Find opponents
        opponents = await player_repo.find_matchmaking_opponents(player, limit=5)
        
        if not opponents:
            await callback.answer("❌ Нет доступных целей для атаки", show_alert=True)
            return
        
        text = "⚔️ <b>ВЫБОР ЦЕЛИ</b>\n\nВыберите игрока для атаки:\n"
        
        for i, opp in enumerate(opponents, 1):
            opp_username = f"@{opp.username}" if opp.username else f"Игрок #{opp.id}"
            opp_power = opp.virus.power if opp.virus else 0
            opp_defense = opp.defense.power if opp.defense else 0
            can_attack, reason = await combat_service.can_attack(player.id, opp.id)
            status = "✅" if can_attack else "🔒"
            text += f"{i}. {status} {opp_username} (PWR:{opp_power} DEF:{opp_defense})\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=attack_menu_keyboard(opponents),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("attack_select_"))
async def cb_attack_select(callback: types.CallbackQuery):
    """Show attack confirmation"""
    target_id = int(callback.data.split("_")[-1])
    
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        combat_service = CombatService(session)
        
        attacker = await player_repo.get_by_id(callback.from_user.id)
        target = await player_repo.get_by_id(target_id)
        
        if not attacker or not target:
            await callback.answer("❌ Игрок не найден", show_alert=True)
            return
        
        can_attack, reason = await combat_service.can_attack(attacker.id, target.id)
        if not can_attack:
            await callback.answer(f"❌ {reason}", show_alert=True)
            return
        
        # Calculate chance
        base_chance, final_chance = combat_service.calculate_infection_chance(attacker, target)
        
        target_username = f"@{target.username}" if target.username else f"Игрок #{target.id}"
        target_power = target.defense.power if target.defense else 0
        
        text = f"""⚔️ <b>ПОДТВЕРЖДЕНИЕ АТАКИ</b>

Цель: {target_username}
🛡 Защита цели: {target_power}

📊 <b>Прогноз:</b>
Шанс успеха: ~{int(final_chance * 100)}%
Стоимость: {config.energy.ATTACK_COST} ⚡

💰 <b>Потенциальная награда:</b>
Кредиты: ~{config.reward.BASE_WIN_REWARD_CREDITS}+
XP: ~{config.reward.BASE_WIN_REWARD_XP}+

Вы действительно хотите атаковать?
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=attack_confirm_keyboard(target_id, final_chance),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("attack_confirm_"))
async def cb_attack_confirm(callback: types.CallbackQuery):
    """Execute attack"""
    target_id = int(callback.data.split("_")[-1])
    
    async with async_session_maker() as session:
        combat_service = CombatService(session)
        
        try:
            result = await combat_service.resolve_attack(callback.from_user.id, target_id)
            
            if result['success']:
                emoji = "🦠"
                result_text = "УСПЕХ! Цель заражена!"
                reward_text = f"""+ 💰 {int(result['credits_reward'])} кредитов
+ ⭐ {result['xp_reward']} XP"""
            elif result['result'].value == 'partial':
                emoji = "⚡"
                result_text = "ЧАСТИЧНЫЙ УСПЕХ"
                reward_text = f"+ ⭐ {result['xp_reward']} XP (утешительный приз)"
            else:
                emoji = "❌"
                result_text = "НЕУДАЧА"
                reward_text = f"- ⚡ {config.energy.ATTACK_COST - config.energy.ENERGY_REFUND_ON_LOSS} энергии\n+ 💰 {config.reward.BASE_LOSS_REFUND_CREDITS} (утешение)"
            
            text = f"""{emoji} <b>АТАКА ЗАВЕРШЕНА</b>

Результат: {result_text}

{reward_text}

⚡ Энергия потрачена: {result['energy_cost']}
🎲 Шанс был: {int(result['final_chance'] * 100)}%
📊 Выпало: {int(result['roll'] * 100)}%
"""
            
            if result['leveled_up']:
                text += f"\n🎉 <b>НОВЫЙ УРОВЕНЬ: {result['new_level']}!</b>"
            
            keyboard = [
                [types.InlineKeyboardButton(text="🔬 Моя лаборатория", callback_data="menu_main")],
                [types.InlineKeyboardButton(text="⚔️ Ещё атака", callback_data="menu_attack")],
            ]
            
            await callback.message.edit_text(
                text,
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML",
            )
            
        except ValueError as e:
            await callback.answer(f"❌ {str(e)}", show_alert=True)
        
        await callback.answer()


@router.callback_query(F.data == "menu_leaderboard")
async def cb_menu_leaderboard(callback: types.CallbackQuery):
    """Show leaderboard menu"""
    text = """🏅 <b>РЕЙТИНГ ИГРОКОВ</b>

Выберите категорию для просмотра рейтинга:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=leaderboard_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "leaderboard_level")
async def cb_leaderboard_level(callback: types.CallbackQuery):
    """Show level leaderboard"""
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        players = await player_repo.get_leaderboard(limit=10, offset=0)
        
        text = "🏆 <b>ТОП ПО УРОВНЮ</b>\n\n"
        
        for i, p in enumerate(players, 1):
            username = f"@{p.username}" if p.username else f"Игрок #{p.id}"
            virus_pwr = p.virus.power if p.virus else 0
            text += f"{i}. {username} — ур. {p.level} (сила: {virus_pwr})\n"
        
        await callback.message.edit_text(
            text + "\n↩️ Для возврата нажмите кнопку ниже.",
            reply_markup=leaderboard_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data == "menu_profile")
async def cb_menu_profile(callback: types.CallbackQuery):
    """Show own profile"""
    async with async_session_maker() as session:
        player_repo = PlayerRepository(session)
        resource_repo = ResourceRepository(session)
        
        player = await player_repo.get_by_id(callback.from_user.id)
        
        if not player:
            await callback.answer("❌ Игрок не найден", show_alert=True)
            return
        
        # Update production
        await resource_repo.update_pending_production(callback.from_user.id)
        
        profile_text = format_player_profile(player, is_own=True)
        
        await callback.message.edit_text(
            profile_text,
            reply_markup=profile_keyboard(is_own=True),
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("virus_upgrade_"))
async def cb_virus_upgrade(callback: types.CallbackQuery):
    """Handle virus stat upgrade"""
    stat_name = callback.data.replace("virus_upgrade_", "")
    
    async with async_session_maker() as session:
        virus_service = VirusService(session)
        success, message = await virus_service.upgrade_stat(callback.from_user.id, stat_name)
        
        await callback.answer(message, show_alert=not success)
        
        if success:
            # Refresh virus menu
            await cb_menu_virus(callback)


@router.callback_query(F.data.startswith("defense_upgrade_"))
async def cb_defense_upgrade(callback: types.CallbackQuery):
    """Handle defense stat upgrade"""
    stat_name = callback.data.replace("defense_upgrade_", "")
    
    async with async_session_maker() as session:
        defense_service = DefenseService(session)
        success, message = await defense_service.upgrade_stat(callback.from_user.id, stat_name)
        
        await callback.answer(message, show_alert=not success)
        
        if success:
            # Refresh defense menu
            await cb_menu_defense(callback)


@router.callback_query(F.data == "lab_collect")
async def cb_lab_collect(callback: types.CallbackQuery):
    """Collect laboratory production"""
    async with async_session_maker() as session:
        resource_repo = ResourceRepository(session)
        
        credits_collected, samples_collected = await resource_repo.collect_production(
            callback.from_user.id
        )
        
        if credits_collected > 0 or samples_collected > 0:
            message = f"💰 Собрано ресурсов:\n\n+ 💰 {int(credits_collected)} кредитов\n+ 🧬 {int(samples_collected)} образцов"
            await callback.answer(message, show_alert=True)
            # Refresh lab menu
            await cb_menu_lab(callback)
        else:
            await callback.answer("⏳ Ресурсы ещё не накоплены", show_alert=True)


# Error handler
@router.errors()
async def error_handler(event, exception):
    logger.error(f"Error in handler: {exception}", exc_info=exception)
    return True
