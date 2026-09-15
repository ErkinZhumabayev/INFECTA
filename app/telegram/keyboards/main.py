# Telegram UI Keyboards

from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main game menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="🧪 Лаборатория", callback_data="menu_lab"),
            InlineKeyboardButton(text="🦠 Вирус", callback_data="menu_virus"),
        ],
        [
            InlineKeyboardButton(text="🛡 Защита", callback_data="menu_defense"),
            InlineKeyboardButton(text="🔬 Исследования", callback_data="menu_research"),
        ],
        [
            InlineKeyboardButton(text="⚔️ Атаковать", callback_data="menu_attack"),
            InlineKeyboardButton(text="📋 Задания", callback_data="menu_quests"),
        ],
        [
            InlineKeyboardButton(text="🏆 Достижения", callback_data="menu_achievements"),
            InlineKeyboardButton(text="🏅 Рейтинг", callback_data="menu_leaderboard"),
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="menu_profile"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def lab_menu_keyboard() -> InlineKeyboardMarkup:
    """Laboratory menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="⚡ Энергоядро", callback_data="lab_energy_core"),
            InlineKeyboardButton(text="🔬 Исц. центр", callback_data="lab_research_center"),
        ],
        [
            InlineKeyboardButton(text="🧬 Лаба мутаций", callback_data="lab_mutation_lab"),
            InlineKeyboardButton(text="🛡 Центр защиты", callback_data="lab_defense_center"),
        ],
        [
            InlineKeyboardButton(text="📦 Хранилище", callback_data="lab_storage"),
        ],
        [
            InlineKeyboardButton(text="💰 Собрать ресурсы", callback_data="lab_collect"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def virus_menu_keyboard() -> InlineKeyboardMarkup:
    """Virus management keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="☣️ Заразность", callback_data="virus_upgrade_infectivity"),
            InlineKeyboardButton(text="🔄 Адаптация", callback_data="virus_upgrade_adaptation"),
        ],
        [
            InlineKeyboardButton(text="💪 Устойчивость", callback_data="virus_upgrade_persistence"),
            InlineKeyboardButton(text="🧬 Мутация", callback_data="virus_upgrade_mutation_rate"),
        ],
        [
            InlineKeyboardButton(text="⚡ Мощность", callback_data="virus_upgrade_potency"),
        ],
        [
            InlineKeyboardButton(text="✏️ Переименовать", callback_data="virus_rename"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def defense_menu_keyboard() -> InlineKeyboardMarkup:
    """Defense management keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="🛡 Иммунитет", callback_data="defense_upgrade_immunity"),
            InlineKeyboardButton(text="🔒 Сопротивление", callback_data="defense_upgrade_resistance"),
        ],
        [
            InlineKeyboardButton(text="💚 Восстановление", callback_data="defense_upgrade_recovery"),
            InlineKeyboardButton(text="📡 Обнаружение", callback_data="defense_upgrade_detection"),
        ],
        [
            InlineKeyboardButton(text="🔵 Активировать щит (200💰)", callback_data="defense_activate_shield"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def attack_menu_keyboard(opponents: list) -> InlineKeyboardMarkup:
    """Attack target selection keyboard"""
    keyboard = []
    
    for opponent in opponents:
        username = opponent.username or f"Player_{opponent.id}"
        power = opponent.virus.power if opponent.virus else 0
        defense = opponent.defense.power if opponent.defense else 0
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"⚔️ @{username} (PWR:{power} DEF:{defense})",
                callback_data=f"attack_select_{opponent.id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_attack"),
    ])
    keyboard.append([
        InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def attack_confirm_keyboard(target_id: int, chance: float) -> InlineKeyboardMarkup:
    """Attack confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"🦠 АТАКОВАТЬ ({int(chance*100)}% шанс)",
                callback_data=f"attack_confirm_{target_id}"
            ),
        ],
        [
            InlineKeyboardButton(text="↩️ Отмена", callback_data="menu_attack"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def profile_keyboard(target_id: Optional[int] = None, is_own: bool = True) -> InlineKeyboardMarkup:
    """Profile view keyboard"""
    keyboard = []
    
    if not is_own and target_id:
        # Viewing another player's profile - show attack option
        keyboard.append([
            InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"attack_select_{target_id}"),
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Leaderboard navigation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="🏆 По уровню", callback_data="leaderboard_level"),
            InlineKeyboardButton(text="⚔️ По силе вируса", callback_data="leaderboard_virus"),
        ],
        [
            InlineKeyboardButton(text="🛡 По защите", callback_data="leaderboard_defense"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def quests_keyboard() -> InlineKeyboardMarkup:
    """Quests menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="📜 Текущие задания", callback_data="quests_current"),
            InlineKeyboardButton(text="📅 Ежедневные", callback_data="quests_daily"),
        ],
        [
            InlineKeyboardButton(text="🎯 Прогресс", callback_data="quests_progress"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def achievements_keyboard() -> InlineKeyboardMarkup:
    """Achievements menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="🏆 Все достижения", callback_data="achievements_all"),
            InlineKeyboardButton(text="✅ Полученные", callback_data="achievements_unlocked"),
        ],
        [
            InlineKeyboardButton(text="🔒 locked", callback_data="achievements_locked"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_keyboard() -> InlineKeyboardMarkup:
    """Simple back button keyboard"""
    keyboard = [
        [InlineKeyboardButton(text="↩️ Назад", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def yes_no_keyboard(yes_callback: str, no_callback: str = "menu_main") -> InlineKeyboardMarkup:
    """Yes/No confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=yes_callback),
            InlineKeyboardButton(text="❌ Нет", callback_data=no_callback),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def rename_virus_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for virus rename flow"""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Введите название", callback_data="virus_rename_input")],
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="menu_virus")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
