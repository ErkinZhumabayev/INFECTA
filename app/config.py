# Game Configuration and Balance Settings
# All game balance parameters are centralized here for easy tuning

from pydantic_settings import BaseSettings
from pydantic import Field


class EnergyConfig(BaseSettings):
    """Energy system configuration"""
    MAX_ENERGY: int = 100
    REGEN_RATE: int = 5  # Energy per hour
    REGEN_INTERVAL_SECONDS: int = 3600  # 1 hour
    ATTACK_COST: int = 10
    MIN_ENERGY_FOR_ATTACK: int = 10


class PvPConfig(BaseSettings):
    """PvP and infection configuration"""
    ATTACK_COOLDOWN_SECONDS: int = 300  # 5 minutes
    PROTECTION_WINDOW_SECONDS: int = 1800  # 30 minutes after infection
    MATCHMAKING_POWER_RANGE: int = 50  # Initial power range for matchmaking
    MATCHMAKING_MAX_RANGE: int = 200  # Maximum power range expansion
    DIMINISHING_RETURNS_FACTOR: float = 0.5  # Reward reduction per repeat attack
    MAX_REPEAT_ATTACKS: int = 3  # Max attacks on same player before heavy penalty
    
    # Infection chance limits (prevents pure RNG)
    MIN_INFECTION_CHANCE: float = 0.15  # 15% minimum
    MAX_INFECTION_CHANCE: float = 0.85  # 85% maximum
    BASE_INFECTION_CHANCE: float = 0.50  # 50% base chance
    
    # Power influence on chance
    POWER_DIFF_FACTOR: float = 0.02  # 2% per power point difference
    
    # Level difference modifier
    LEVEL_DIFF_FACTOR: float = 0.03  # 3% per level difference
    MAX_LEVEL_DIFF_BONUS: float = 0.30  # Max 30% from level difference


class RewardConfig(BaseSettings):
    """Reward configuration"""
    BASE_WIN_REWARD_CREDITS: int = 50
    BASE_WIN_REWARD_XP: int = 30
    BASE_LOSS_REFUND_CREDITS: int = 5  # Consolation prize
    ENERGY_REFUND_ON_LOSS: int = 5  # Partial energy refund on loss
    
    # Reward scaling
    POWER_SCALING_FACTOR: float = 0.1  # Extra reward per power point of target
    LEVEL_SCALING_FACTOR: float = 5  # Extra reward per level of target
    
    # Diminishing returns
    FIRST_ATTACK_MULTIPLIER: float = 1.0
    SECOND_ATTACK_MULTIPLIER: float = 0.7
    THIRD_PLUS_ATTACK_MULTIPLIER: float = 0.4


class ProductionConfig(BaseSettings):
    """Idle production configuration"""
    BASE_CREDITS_PER_HOUR: int = 100
    BASE_SAMPLES_PER_HOUR: int = 10
    OFFLINE_CAP_HOURS: int = 8  # Max offline production hours
    LAB_LEVEL_PRODUCTION_BONUS: float = 0.1  # 10% per lab level


class ProgressionConfig(BaseSettings):
    """Level and XP configuration"""
    BASE_XP_FOR_LEVEL: int = 100
    XP_GROWTH_FACTOR: float = 1.5  # XP needed grows by 50% per level
    MAX_LEVEL: int = 100
    
    # Starting values
    STARTING_CREDITS: int = 500
    STARTING_SAMPLES: int = 50
    STARTING_ENERGY: int = 80


class UpgradeConfig(BaseSettings):
    """Upgrade costs configuration"""
    # Virus upgrade base costs
    VIRUS_UPGRADE_BASE_COST: int = 100
    VIRUS_UPGRADE_COST_MULTIPLIER: float = 1.3
    
    # Defense upgrade base costs
    DEFENSE_UPGRADE_BASE_COST: int = 100
    DEFENSE_UPGRADE_COST_MULTIPLIER: float = 1.3
    
    # Lab upgrade base costs
    LAB_UPGRADE_BASE_COST: int = 200
    LAB_UPGRADE_COST_MULTIPLIER: float = 1.5
    
    # Research costs
    RESEARCH_BASE_COST_CREDITS: int = 150
    RESEARCH_BASE_COST_SAMPLES: int = 20
    RESEARCH_COST_MULTIPLIER: float = 1.4


class RecoveryConfig(BaseSettings):
    """Recovery and healing configuration"""
    BASE_RECOVERY_TIME_SECONDS: int = 3600  # 1 hour base recovery
    RECOVERY_CREDIT_COST: int = 100  # Cost to instant heal
    INFECTION_DEBUFF_PRODUCTION: float = 0.2  # 20% production reduction when infected
    INFECTION_DEBUFF_ENERGY_REGEN: float = 0.3  # 30% energy regen reduction when infected


class MutationConfig(BaseSettings):
    """Mutation system configuration"""
    MUTATION_SLOT_COUNT: int = 3
    MUTATION_DISCOVER_CHANCE: float = 0.1  # 10% chance on level up
    MAX_MUTATIONS_PER_PLAYER: int = 10


class QuestConfig(BaseSettings):
    """Quest system configuration"""
    DAILY_QUESTS_COUNT: int = 3
    QUEST_REFRESH_HOURS: int = 24
    TUTORIAL_QUESTS_COUNT: int = 5


class AntiAbuseConfig(BaseSettings):
    """Anti-abuse configuration"""
    MIN_ACCOUNT_AGE_DAYS_FOR_PVP: int = 0  # Can be increased later
    MAX_ATTACKS_PER_DAY: int = 50
    RATE_LIMIT_ATTACKS_PER_MINUTE: int = 5
    FLOOD_WINDOW_SECONDS: int = 60
    FLOOD_MAX_REQUESTS: int = 20


class GameConfig(BaseSettings):
    """Main game configuration aggregator"""
    energy: EnergyConfig = Field(default_factory=EnergyConfig)
    pvp: PvPConfig = Field(default_factory=PvPConfig)
    reward: RewardConfig = Field(default_factory=RewardConfig)
    production: ProductionConfig = Field(default_factory=ProductionConfig)
    progression: ProgressionConfig = Field(default_factory=ProgressionConfig)
    upgrade: UpgradeConfig = Field(default_factory=UpgradeConfig)
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)
    mutation: MutationConfig = Field(default_factory=MutationConfig)
    quest: QuestConfig = Field(default_factory=QuestConfig)
    anti_abuse: AntiAbuseConfig = Field(default_factory=AntiAbuseConfig)
    
    # Bot settings
    BOT_TOKEN: str = ""
    ADMIN_IDS: list[int] = Field(default_factory=list)
    
    class Config:
        env_file = ".env"
        extra = "ignore"


# Global config instance
config = GameConfig()
