# Database Models

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, DateTime, Float, Boolean,
    ForeignKey, Index, UniqueConstraint, Enum, JSON, Numeric
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class InfectionStatus(PyEnum):
    """Player infection status states"""
    HEALTHY = "healthy"
    EXPOSED = "exposed"  # Recently attacked, might get infected
    INFECTED = "infected"
    RECOVERING = "recovering"


class AttackResult(PyEnum):
    """Possible attack outcomes"""
    FAIL = "fail"
    PARTIAL = "partial"  # Partial success - minor debuff
    SUCCESS = "success"  # Full infection


class Player(Base):
    """Main player table - Telegram user info"""
    __tablename__ = "players"
    
    id = Column(BigInteger, primary_key=True)  # Telegram user ID
    username = Column(String(255), nullable=True, index=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), nullable=True)
    
    # Game progression
    level = Column(Integer, default=1, nullable=False)
    experience = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Status
    is_banned = Column(Boolean, default=False, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    laboratory = relationship("Laboratory", back_populates="player", uselist=False, cascade="all, delete-orphan")
    virus = relationship("Virus", back_populates="player", uselist=False, cascade="all, delete-orphan")
    defense = relationship("Defense", back_populates="player", uselist=False, cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="player", uselist=False, cascade="all, delete-orphan")
    infection_state = relationship("InfectionState", back_populates="player", uselist=False, cascade="all, delete-orphan")
    
    # Stats tracking
    total_attacks_made = Column(Integer, default=0)
    total_attacks_received = Column(Integer, default=0)
    successful_attacks = Column(Integer, default=0)
    successful_defenses = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    
    __table_args__ = (
        Index('ix_players_level', 'level'),
        Index('ix_players_created', 'created_at'),
    )


class Laboratory(Base):
    """Player's laboratory - main progression hub"""
    __tablename__ = "laboratories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Lab level and upgrades
    level = Column(Integer, default=1, nullable=False)
    
    # Facility levels (abstract game buildings)
    research_center_level = Column(Integer, default=1)
    energy_core_level = Column(Integer, default=1)
    mutation_lab_level = Column(Integer, default=1)
    defense_center_level = Column(Integer, default=1)
    storage_level = Column(Integer, default=1)
    
    # Production tracking
    last_production_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    pending_credits = Column(Numeric(12, 2), default=0)
    pending_samples = Column(Numeric(12, 2), default=0)
    
    # Relationships
    player = relationship("Player", back_populates="laboratory")
    researches = relationship("PlayerResearch", back_populates="laboratory", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_labs_level', 'level'),
    )


class Virus(Base):
    """Player's virus - attack capabilities"""
    __tablename__ = "viruses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Virus identity
    name = Column(String(64), nullable=False)
    
    # Virus stats (abstract game attributes)
    infectivity = Column(Integer, default=1)  # Chance to infect
    adaptation = Column(Integer, default=1)  # Adaptation to defenses
    persistence = Column(Integer, default=1)  # Resistance to recovery
    mutation_rate = Column(Integer, default=1)  # Mutation chance
    potency = Column(Integer, default=1)  # Effect strength
    
    # Computed power (cached for performance)
    power = Column(Integer, default=5)
    
    # Level
    level = Column(Integer, default=1)
    
    # Relationships
    player = relationship("Player", back_populates="virus")
    mutations = relationship("PlayerMutation", back_populates="virus", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_virus_power', 'power'),
    )


class Defense(Base):
    """Player's defense system"""
    __tablename__ = "defenses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Defense stats (abstract game attributes)
    immunity = Column(Integer, default=1)  # Base resistance
    resistance = Column(Integer, default=1)  # Specific resistance
    recovery = Column(Integer, default=1)  # Recovery speed
    detection = Column(Integer, default=1)  # Detection chance
    shield = Column(Integer, default=0)  # Temporary shield value
    
    # Computed defense power (cached)
    power = Column(Integer, default=5)
    
    # Level
    level = Column(Integer, default=1)
    
    # Shield expiry
    shield_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    player = relationship("Player", back_populates="defense")
    
    __table_args__ = (
        Index('ix_defense_power', 'power'),
    )


class Resource(Base):
    """Player resources/currency"""
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Currencies
    credits = Column(Numeric(12, 2), default=0)  # Main currency
    samples = Column(Numeric(12, 2), default=0)  # Research currency
    energy = Column(Integer, default=80)  # Action energy
    
    # Energy tracking
    last_energy_regen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    player = relationship("Player", back_populates="resources")
    transactions = relationship("ResourceTransaction", back_populates="resource", cascade="all, delete-orphan")


class ResourceTransaction(Base):
    """Audit log for resource changes"""
    __tablename__ = "resource_transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    
    # Transaction details
    resource_type = Column(String(32), nullable=False)  # credits, samples, energy
    amount = Column(Numeric(12, 2), nullable=False)  # Can be negative
    balance_after = Column(Numeric(12, 2), nullable=False)
    
    # Context
    reason = Column(String(64), nullable=False)  # attack_reward, upgrade_cost, production, etc.
    reference_id = Column(String(64), nullable=True)  # Attack ID, upgrade ID, etc.
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    resource = relationship("Resource", back_populates="transactions")
    
    __table_args__ = (
        Index('ix_transactions_player', 'player_id'),
        Index('ix_transactions_created', 'created_at'),
        Index('ix_transactions_reason', 'reason'),
    )


class InfectionState(Base):
    """Current infection state of a player"""
    __tablename__ = "infection_states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Current status
    status = Column(Enum(InfectionStatus), default=InfectionStatus.HEALTHY, nullable=False)
    
    # Infection details
    infected_by_id = Column(BigInteger, ForeignKey("players.id"), nullable=True)
    infected_at = Column(DateTime(timezone=True), nullable=True)
    protection_expires_at = Column(DateTime(timezone=True), nullable=True)
    recovery_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Debuffs
    production_debuff = Column(Float, default=0)
    energy_regen_debuff = Column(Float, default=0)
    
    # Relationships
    player = relationship("Player", back_populates="infection_state", foreign_keys=[player_id])
    infector = relationship("Player", foreign_keys=[infected_by_id])
    
    __table_args__ = (
        Index('ix_infection_status', 'status'),
        Index('ix_infection_expires', 'protection_expires_at'),
    )


class PlayerResearch(Base):
    """Research progress for a player"""
    __tablename__ = "player_researches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    laboratory_id = Column(Integer, ForeignKey("laboratories.id", ondelete="CASCADE"), nullable=False)
    
    research_key = Column(String(64), nullable=False)  # Reference to research definition
    level = Column(Integer, default=1, nullable=False)
    unlocked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    laboratory = relationship("Laboratory", back_populates="researches")
    
    __table_args__ = (
        UniqueConstraint('player_id', 'research_key', name='uq_player_research'),
    )


class PlayerMutation(Base):
    """Discovered mutations for a player"""
    __tablename__ = "player_mutations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    virus_id = Column(Integer, ForeignKey("viruses.id", ondelete="CASCADE"), nullable=False)
    
    mutation_key = Column(String(64), nullable=False)  # Reference to mutation definition
    slot = Column(Integer, nullable=False)  # Which slot (0-2)
    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    virus = relationship("Virus", back_populates="mutations")
    
    __table_args__ = (
        UniqueConstraint('virus_id', 'slot', name='uq_virus_slot'),
    )


class AttackLog(Base):
    """PvP attack history"""
    __tablename__ = "attack_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Participants
    attacker_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    
    # Battle snapshot
    attacker_power = Column(Integer, nullable=False)
    target_defense = Column(Integer, nullable=False)
    attacker_level = Column(Integer, nullable=False)
    target_level = Column(Integer, nullable=False)
    
    # Calculation details
    base_chance = Column(Float, nullable=False)
    final_chance = Column(Float, nullable=False)
    roll_value = Column(Float, nullable=False)
    
    # Result
    result = Column(Enum(AttackResult), nullable=False)
    
    # Rewards/costs
    energy_cost = Column(Integer, nullable=False)
    credits_reward = Column(Numeric(12, 2), default=0)
    xp_reward = Column(Integer, default=0)
    
    # Repeat attack tracking
    repeat_count = Column(Integer, default=1)  # How many times attacker hit this target recently
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('ix_attacks_attacker', 'attacker_id'),
        Index('ix_attacks_target', 'target_id'),
        Index('ix_attacks_created', 'created_at'),
        Index('ix_attacks_result', 'result'),
    )


class Quest(Base):
    """Quest definitions"""
    __tablename__ = "quests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    quest_key = Column(String(64), unique=True, nullable=False)
    
    quest_type = Column(String(32), nullable=False)  # tutorial, daily, progression, pvp
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    # Requirements
    requirement_type = Column(String(64), nullable=False)
    requirement_value = Column(Integer, nullable=False)
    
    # Rewards
    reward_credits = Column(Integer, default=0)
    reward_samples = Column(Integer, default=0)
    reward_xp = Column(Integer, default=0)
    
    is_daily = Column(Boolean, default=False)
    is_repeatable = Column(Boolean, default=False)
    
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class PlayerQuest(Base):
    """Player's quest progress"""
    __tablename__ = "player_quests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    quest_id = Column(Integer, ForeignKey("quests.id", ondelete="CASCADE"), nullable=False)
    
    progress = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    is_claimed = Column(Boolean, default=False)
    
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # For daily quests
    
    __table_args__ = (
        UniqueConstraint('player_id', 'quest_id', name='uq_player_quest'),
        Index('ix_player_quests_expires', 'expires_at'),
    )


class Achievement(Base):
    """Achievement definitions"""
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    achievement_key = Column(String(64), unique=True, nullable=False)
    
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    
    requirement_type = Column(String(64), nullable=False)
    requirement_value = Column(Integer, nullable=False)
    
    reward_credits = Column(Integer, default=0)
    reward_samples = Column(Integer, default=0)
    
    sort_order = Column(Integer, default=0)
    is_hidden = Column(Boolean, default=False)


class PlayerAchievement(Base):
    """Player's unlocked achievements"""
    __tablename__ = "player_achievements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False)
    
    unlocked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_claimed = Column(Boolean, default=False)
    
    __table_args__ = (
        UniqueConstraint('player_id', 'achievement_id', name='uq_player_achievement'),
    )


class DailyReward(Base):
    """Daily login rewards tracking"""
    __tablename__ = "daily_rewards"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    last_claimed_at = Column(DateTime(timezone=True), nullable=True)
    streak_count = Column(Integer, default=0)
    total_claimed = Column(Integer, default=0)
    
    player = relationship("Player")


class Cooldown(Base):
    """Action cooldowns"""
    __tablename__ = "cooldowns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    
    cooldown_type = Column(String(64), nullable=False)  # attack, research, etc.
    reference_id = Column(String(64), nullable=True)  # Target player ID for attack cooldown
    
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('ix_cooldowns_player_type', 'player_id', 'cooldown_type'),
        Index('ix_cooldowns_expires', 'expires_at'),
    )


class GameEvent(Base):
    """Game events for notifications and history"""
    __tablename__ = "game_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    
    event_type = Column(String(64), nullable=False)
    event_data = Column(JSON, nullable=True)
    
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('ix_events_player', 'player_id'),
        Index('ix_events_unread', 'player_id', 'is_read'),
    )
