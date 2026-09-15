# Repository pattern for database access

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from decimal import Decimal
import random

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.game.models.models import (
    Player, Laboratory, Virus, Defense, Resource, ResourceTransaction,
    InfectionState, InfectionStatus, AttackLog, AttackResult,
    PlayerResearch, PlayerMutation, Cooldown, GameEvent,
    Quest, PlayerQuest, Achievement, PlayerAchievement, DailyReward
)
from app.config import config


class PlayerRepository:
    """Repository for player operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create(self, telegram_id: int, username: str = None, 
                           first_name: str = None, last_name: str = None,
                           language_code: str = None) -> Player:
        """Get existing player or create new one with all related entities"""
        
        result = await self.session.execute(
            select(Player).where(Player.id == telegram_id)
        )
        player = result.scalar_one_or_none()
        
        if player:
            # Update user info
            if username:
                player.username = username
            if first_name:
                player.first_name = first_name
            if last_name:
                player.last_name = last_name
            if language_code:
                player.language_code = language_code
            player.last_active_at = datetime.now(timezone.utc)
            await self.session.flush()
            return player
        
        # Create new player with all related entities
        player = Player(
            id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            level=1,
            experience=0,
        )
        self.session.add(player)
        await self.session.flush()  # Get player ID
        
        # Create laboratory
        lab = Laboratory(player_id=telegram_id)
        self.session.add(lab)
        
        # Create virus (placeholder name, will be set during onboarding)
        virus = Virus(
            player_id=telegram_id,
            name="Unknown Strain",
            infectivity=1,
            adaptation=1,
            persistence=1,
            mutation_rate=1,
            potency=1,
            power=5,
            level=1,
        )
        self.session.add(virus)
        
        # Create defense
        defense = Defense(
            player_id=telegram_id,
            immunity=1,
            resistance=1,
            recovery=1,
            detection=1,
            shield=0,
            power=5,
            level=1,
        )
        self.session.add(defense)
        
        # Create resources
        res = Resource(
            player_id=telegram_id,
            credits=config.progression.STARTING_CREDITS,
            samples=config.progression.STARTING_SAMPLES,
            energy=config.progression.STARTING_ENERGY,
            last_energy_regen=datetime.now(timezone.utc),
        )
        self.session.add(res)
        
        # Create infection state
        infection_state = InfectionState(
            player_id=telegram_id,
            status=InfectionStatus.HEALTHY,
        )
        self.session.add(infection_state)
        
        await self.session.flush()
        
        # Reload with relationships
        result = await self.session.execute(
            select(Player)
            .options(
                selectinload(Player.laboratory),
                selectinload(Player.virus),
                selectinload(Player.defense),
                selectinload(Player.resources),
                selectinload(Player.infection_state),
            )
            .where(Player.id == telegram_id)
        )
        player = result.scalar_one()
        
        return player
    
    async def get_by_id(self, telegram_id: int) -> Optional[Player]:
        """Get player by Telegram ID with all relationships"""
        result = await self.session.execute(
            select(Player)
            .options(
                selectinload(Player.laboratory),
                selectinload(Player.virus),
                selectinload(Player.defense),
                selectinload(Player.resources),
                selectinload(Player.infection_state),
            )
            .where(Player.id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[Player]:
        """Get player by username"""
        result = await self.session.execute(
            select(Player)
            .options(
                selectinload(Player.laboratory),
                selectinload(Player.virus),
                selectinload(Player.defense),
                selectinload(Player.resources),
                selectinload(Player.infection_state),
            )
            .where(Player.username == username.lstrip('@'))
        )
        return result.scalar_one_or_none()
    
    async def add_experience(self, player_id: int, xp: int) -> Tuple[int, bool]:
        """Add experience and handle level up. Returns (new_level, leveled_up)"""
        player = await self.get_by_id(player_id)
        if not player:
            return 1, False
        
        player.experience += xp
        leveled_up = False
        
        # Calculate XP needed for next level
        xp_needed = int(
            config.progression.BASE_XP_FOR_LEVEL * 
            (config.progression.XP_GROWTH_FACTOR ** (player.level - 1))
        )
        
        while player.experience >= xp_needed and player.level < config.progression.MAX_LEVEL:
            player.experience -= xp_needed
            player.level += 1
            leveled_up = True
            
            xp_needed = int(
                config.progression.BASE_XP_FOR_LEVEL * 
                (config.progression.XP_GROWTH_FACTOR ** (player.level - 1))
            )
        
        player.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        
        return player.level, leveled_up
    
    async def get_leaderboard(self, limit: int = 20, offset: int = 0) -> List[Player]:
        """Get top players by level and power"""
        result = await self.session.execute(
            select(Player)
            .options(selectinload(Player.virus), selectinload(Player.defense))
            .where(Player.is_banned == False)
            .order_by(Player.level.desc(), Player.virus.power.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def find_matchmaking_opponents(self, player: Player, 
                                         limit: int = 5) -> List[Player]:
        """Find suitable PvP opponents based on power range"""
        player_power = self._calculate_player_power(player)
        
        # Start with narrow range, expand if needed
        current_range = config.pvp.MATCHMAKING_POWER_RANGE
        max_range = config.pvp.MATCHMAKING_MAX_RANGE
        
        while current_range <= max_range:
            min_power = max(1, player_power - current_range)
            max_power = player_power + current_range
            
            result = await self.session.execute(
                select(Player)
                .options(
                    selectinload(Player.virus),
                    selectinload(Player.defense),
                    selectinload(Player.infection_state),
                )
                .where(Player.id != player.id)
                .where(Player.is_banned == False)
                .where(Player.is_blocked == False)
            )
            
            candidates = list(result.scalars().all())
            
            # Filter by power and protection status
            suitable = []
            for p in candidates:
                p_power = self._calculate_player_power(p)
                if min_power <= p_power <= max_power:
                    # Check if not protected
                    if p.infection_state:
                        now = datetime.now(timezone.utc)
                        if p.infection_state.protection_expires_at:
                            if p.infection_state.protection_expires_at > now:
                                continue  # Still protected
                    suitable.append(p)
            
            if suitable:
                return suitable[:limit]
            
            current_range += 20
        
        # If no suitable opponents, return any non-protected players
        result = await self.session.execute(
            select(Player)
            .options(
                selectinload(Player.virus),
                selectinload(Player.defense),
                selectinload(Player.infection_state),
            )
            .where(Player.id != player.id)
            .where(Player.is_banned == False)
            .where(Player.is_blocked == False)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    def _calculate_player_power(self, player: Player) -> int:
        """Calculate total player power for matchmaking"""
        virus_power = player.virus.power if player.virus else 0
        defense_power = player.defense.power if player.defense else 0
        lab_bonus = player.laboratory.level if player.laboratory else 0
        
        return virus_power + defense_power + lab_bonus


class ResourceRepository:
    """Repository for resource operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_resources(self, player_id: int) -> Optional[Resource]:
        """Get player resources"""
        result = await self.session.execute(
            select(Resource).where(Resource.player_id == player_id)
        )
        return result.scalar_one_or_none()
    
    async def regenerate_energy(self, player_id: int) -> int:
        """Regenerate energy based on time passed. Returns current energy."""
        result = await self.session.execute(
            select(Resource).where(Resource.player_id == player_id)
        )
        resource = result.scalar_one_or_none()
        
        if not resource:
            return 0
        
        now = datetime.now(timezone.utc)
        time_diff = now - resource.last_energy_regen.replace(tzinfo=timezone.utc)
        hours_passed = time_diff.total_seconds() / config.energy.REGEN_INTERVAL_SECONDS
        
        if hours_passed >= 1:
            # Get infection debuff
            infection_result = await self.session.execute(
                select(InfectionState).where(InfectionState.player_id == player_id)
            )
            infection_state = infection_result.scalar_one_or_none()
            
            regen_multiplier = 1.0
            if infection_state and infection_state.energy_regen_debuff:
                regen_multiplier = 1.0 - infection_state.energy_regen_debuff
            
            energy_to_add = int(hours_passed * config.energy.REGEN_RATE * regen_multiplier)
            
            if energy_to_add > 0:
                resource.energy = min(
                    config.energy.MAX_ENERGY,
                    resource.energy + energy_to_add
                )
                resource.last_energy_regen = now
        
        await self.session.flush()
        return resource.energy
    
    async def modify_resource(self, player_id: int, resource_type: str,
                             amount: Decimal, reason: str, 
                             reference_id: str = None) -> Decimal:
        """Modify a resource and create transaction log. Returns new balance."""
        result = await self.session.execute(
            select(Resource).where(Resource.player_id == player_id)
        )
        resource = result.scalar_one_or_none()
        
        if not resource:
            raise ValueError(f"Resources not found for player {player_id}")
        
        # Get current balance
        if resource_type == 'credits':
            current_balance = resource.credits
            resource.credits += amount
            new_balance = resource.credits
        elif resource_type == 'samples':
            current_balance = resource.samples
            resource.samples += amount
            new_balance = resource.samples
        elif resource_type == 'energy':
            current_balance = Decimal(resource.energy)
            resource.energy = int(resource.energy + int(amount))
            new_balance = Decimal(resource.energy)
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")
        
        # Ensure non-negative
        if new_balance < 0:
            raise ValueError("Insufficient resources")
        
        # Create transaction record
        transaction = ResourceTransaction(
            resource_id=resource.id,
            player_id=player_id,
            resource_type=resource_type,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            reference_id=reference_id,
        )
        self.session.add(transaction)
        
        await self.session.flush()
        return new_balance
    
    async def calculate_offline_production(self, player: Player) -> Tuple[Decimal, Decimal]:
        """Calculate offline production based on time since last collection"""
        lab = player.laboratory
        if not lab:
            return Decimal(0), Decimal(0)
        
        now = datetime.now(timezone.utc)
        time_diff = now - lab.last_production_at.replace(tzinfo=timezone.utc)
        hours_passed = time_diff.total_seconds() / 3600
        
        # Cap offline production
        capped_hours = min(hours_passed, config.production.OFFLINE_CAP_HOURS)
        
        if capped_hours <= 0:
            return Decimal(0), Decimal(0)
        
        # Calculate production bonuses
        lab_level_bonus = 1 + (lab.level * config.production.LAB_LEVEL_PRODUCTION_BONUS)
        
        # Check infection debuff
        infection_result = await self.session.execute(
            select(InfectionState).where(InfectionState.player_id == player.id)
        )
        infection_state = infection_result.scalar_one_or_none()
        
        production_multiplier = lab_level_bonus
        if infection_state and infection_state.production_debuff:
            production_multiplier *= (1 - infection_state.production_debuff)
        
        credits_produced = Decimal(str(
            config.production.BASE_CREDITS_PER_HOUR * capped_hours * production_multiplier
        ))
        samples_produced = Decimal(str(
            config.production.BASE_SAMPLES_PER_HOUR * capped_hours * production_multiplier
        ))
        
        return credits_produced, samples_produced
    
    async def collect_production(self, player_id: int) -> Tuple[Decimal, Decimal]:
        """Collect pending production and reset timer"""
        player = await PlayerRepository(self.session).get_by_id(player_id)
        if not player or not player.laboratory:
            return Decimal(0), Decimal(0)
        
        lab = player.laboratory
        credits_pending = lab.pending_credits or Decimal(0)
        samples_pending = lab.pending_samples or Decimal(0)
        
        if credits_pending > 0 or samples_pending > 0:
            # Add to actual resources
            if credits_pending > 0:
                await self.modify_resource(
                    player_id, 'credits', credits_pending, 'production_collection'
                )
            if samples_pending > 0:
                await self.modify_resource(
                    player_id, 'samples', samples_pending, 'production_collection'
                )
            
            # Reset pending and update timestamp
            lab.pending_credits = Decimal(0)
            lab.pending_samples = Decimal(0)
            lab.last_production_at = datetime.now(timezone.utc)
            
            await self.session.flush()
        
        return credits_pending, samples_pending
    
    async def update_pending_production(self, player_id: int):
        """Update pending production based on time passed"""
        player = await PlayerRepository(self.session).get_by_id(player_id)
        if not player or not player.laboratory:
            return
        
        credits_to_add, samples_to_add = await self.calculate_offline_production(player)
        
        lab = player.laboratory
        lab.pending_credits = (lab.pending_credits or Decimal(0)) + credits_to_add
        lab.pending_samples = (lab.pending_samples or Decimal(0)) + samples_to_add
        lab.last_production_at = datetime.now(timezone.utc)
        
        await self.session.flush()


class InfectionRepository:
    """Repository for infection state operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_state(self, player_id: int) -> Optional[InfectionState]:
        """Get player's infection state"""
        result = await self.session.execute(
            select(InfectionState).where(InfectionState.player_id == player_id)
        )
        return result.scalar_one_or_none()
    
    async def set_infected(self, player_id: int, infector_id: int,
                          duration_seconds: int = None) -> InfectionState:
        """Set player as infected"""
        result = await self.session.execute(
            select(InfectionState).where(InfectionState.player_id == player_id)
        )
        state = result.scalar_one_or_none()
        
        if not state:
            state = InfectionState(player_id=player_id)
            self.session.add(state)
        
        now = datetime.now(timezone.utc)
        state.status = InfectionStatus.INFECTED
        state.infected_by_id = infector_id
        state.infected_at = now
        
        protection_duration = duration_seconds or config.pvp.PROTECTION_WINDOW_SECONDS
        state.protection_expires_at = now + timedelta(seconds=protection_duration)
        
        # Set recovery time
        recovery_time = config.recovery.BASE_RECOVERY_TIME_SECONDS
        state.recovery_expires_at = now + timedelta(seconds=recovery_time)
        
        # Apply debuffs
        state.production_debuff = config.recovery.INFECTION_DEBUFF_PRODUCTION
        state.energy_regen_debuff = config.recovery.INFECTION_DEBUFF_ENERGY_REGEN
        
        await self.session.flush()
        return state
    
    async def set_recovering(self, player_id: int) -> Optional[InfectionState]:
        """Set player as recovering"""
        result = await self.session.execute(
            select(InfectionState).where(InfectionState.player_id == player_id)
        )
        state = result.scalar_one_or_none()
        
        if state:
            state.status = InfectionStatus.RECOVERING
            await self.session.flush()
        
        return state
    
    async def set_healthy(self, player_id: int) -> Optional[InfectionState]:
        """Set player as healthy"""
        result = await self.session.execute(
            select(InfectionState).where(InfectionState.player_id == player_id)
        )
        state = result.scalar_one_or_none()
        
        if state:
            state.status = InfectionStatus.HEALTHY
            state.infected_by_id = None
            state.infected_at = None
            state.protection_expires_at = None
            state.recovery_expires_at = None
            state.production_debuff = 0
            state.energy_regen_debuff = 0
            await self.session.flush()
        
        return state
    
    async def check_protection(self, player_id: int) -> bool:
        """Check if player is currently protected from attacks"""
        state = await self.get_state(player_id)
        if not state:
            return False
        
        if state.protection_expires_at is None:
            return False
        
        return datetime.now(timezone.utc) < state.protection_expires_at
    
    async def check_recovery_complete(self, player_id: int) -> bool:
        """Check if recovery is complete and auto-heal if so"""
        state = await self.get_state(player_id)
        if not state:
            return True
        
        if state.status != InfectionStatus.INFECTED:
            return True
        
        if state.recovery_expires_at is None:
            return True
        
        if datetime.now(timezone.utc) >= state.recovery_expires_at:
            await self.set_healthy(player_id)
            return True
        
        return False


class AttackRepository:
    """Repository for attack logging and cooldown operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_attack(self, attacker_id: int, target_id: int,
                        attacker_power: int, target_defense: int,
                        attacker_level: int, target_level: int,
                        base_chance: float, final_chance: float,
                        roll_value: float, result: AttackResult,
                        energy_cost: int, credits_reward: Decimal,
                        xp_reward: int, repeat_count: int) -> AttackLog:
        """Log an attack to the database"""
        attack = AttackLog(
            attacker_id=attacker_id,
            target_id=target_id,
            attacker_power=attacker_power,
            target_defense=target_defense,
            attacker_level=attacker_level,
            target_level=target_level,
            base_chance=base_chance,
            final_chance=final_chance,
            roll_value=roll_value,
            result=result,
            energy_cost=energy_cost,
            credits_reward=credits_reward,
            xp_reward=xp_reward,
            repeat_count=repeat_count,
        )
        self.session.add(attack)
        await self.session.flush()
        return attack
    
    async def get_recent_attacks_against(self, attacker_id: int, target_id: int,
                                        limit: int = 10) -> List[AttackLog]:
        """Get recent attacks by attacker against target"""
        result = await self.session.execute(
            select(AttackLog)
            .where(AttackLog.attacker_id == attacker_id)
            .where(AttackLog.target_id == target_id)
            .order_by(AttackLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_attacks_today(self, player_id: int) -> int:
        """Count attacks made by player today"""
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await self.session.execute(
            select(func.count(AttackLog.id))
            .where(AttackLog.attacker_id == player_id)
            .where(AttackLog.created_at >= today)
        )
        return result.scalar() or 0
    
    async def check_cooldown(self, player_id: int, cooldown_type: str,
                            reference_id: str = None) -> Optional[datetime]:
        """Check if cooldown is active. Returns expiry time if active, None otherwise."""
        query = select(Cooldown).where(
            Cooldown.player_id == player_id,
            Cooldown.cooldown_type == cooldown_type,
            Cooldown.expires_at > datetime.now(timezone.utc)
        )
        
        if reference_id:
            query = query.where(Cooldown.reference_id == reference_id)
        
        result = await self.session.execute(query)
        cooldown = result.scalar_one_or_none()
        
        return cooldown.expires_at if cooldown else None
    
    async def set_cooldown(self, player_id: int, cooldown_type: str,
                          duration_seconds: int, reference_id: str = None):
        """Set a cooldown"""
        cooldown = Cooldown(
            player_id=player_id,
            cooldown_type=cooldown_type,
            reference_id=reference_id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=duration_seconds),
        )
        self.session.add(cooldown)
        await self.session.flush()
    
    async def cleanup_expired_cooldowns(self):
        """Remove expired cooldowns"""
        await self.session.execute(
            delete(Cooldown).where(
                Cooldown.expires_at <= datetime.now(timezone.utc)
            )
        )
        await self.session.flush()


class CooldownRepository:
    """Repository for cooldown operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def is_on_cooldown(self, player_id: int, cooldown_type: str,
                            reference_id: str = None) -> Tuple[bool, Optional[timedelta]]:
        """Check if action is on cooldown. Returns (is_on_cooldown, remaining_time)"""
        query = select(Cooldown).where(
            Cooldown.player_id == player_id,
            Cooldown.cooldown_type == cooldown_type,
            Cooldown.expires_at > datetime.now(timezone.utc)
        )
        
        if reference_id:
            query = query.where(Cooldown.reference_id == reference_id)
        
        result = await self.session.execute(query)
        cooldown = result.scalar_one_or_none()
        
        if cooldown:
            remaining = cooldown.expires_at - datetime.now(timezone.utc)
            return True, remaining
        
        return False, None
    
    async def set_cooldown(self, player_id: int, cooldown_type: str,
                          duration_seconds: int, reference_id: str = None):
        """Set a cooldown"""
        # Clean up old cooldowns of same type first
        await self.session.execute(
            delete(Cooldown).where(
                Cooldown.player_id == player_id,
                Cooldown.cooldown_type == cooldown_type,
                Cooldown.reference_id == reference_id,
            )
        )
        
        cooldown = Cooldown(
            player_id=player_id,
            cooldown_type=cooldown_type,
            reference_id=reference_id,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=duration_seconds),
        )
        self.session.add(cooldown)
        await self.session.flush()
