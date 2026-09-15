# Core game logic services

from datetime import datetime, timezone
from decimal import Decimal
from typing import Tuple, Optional
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.game.repositories import (
    PlayerRepository, ResourceRepository, InfectionRepository,
    AttackRepository, CooldownRepository
)
from app.game.models.models import AttackResult, InfectionStatus


class CombatService:
    """PvP combat and infection calculation service"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.player_repo = PlayerRepository(session)
        self.resource_repo = ResourceRepository(session)
        self.infection_repo = InfectionRepository(session)
        self.attack_repo = AttackRepository(session)
        self.cooldown_repo = CooldownRepository(session)
    
    def calculate_infection_chance(self, attacker, defender, 
                                   repeat_count: int = 1) -> Tuple[float, float]:
        """
        Calculate infection chance based on multiple factors.
        Returns (base_chance, final_chance) tuple.
        
        Formula:
        base_chance = BASE_INFECTION_CHANCE
        power_modifier = (attacker_power - defender_power) * POWER_DIFF_FACTOR
        level_modifier = (attacker_level - defender_level) * LEVEL_DIFF_FACTOR
        final = clamp(base + power_modifier + level_modifier, MIN, MAX)
        """
        attacker_power = attacker.virus.power if attacker.virus else 0
        defender_power = defender.defense.power if defender.defense else 0
        attacker_level = attacker.level
        defender_level = defender.level
        
        # Base chance
        base_chance = config.pvp.BASE_INFECTION_CHANCE
        
        # Power difference modifier
        power_diff = attacker_power - defender_power
        power_modifier = power_diff * config.pvp.POWER_DIFF_FACTOR
        
        # Level difference modifier (capped)
        level_diff = attacker_level - defender_level
        level_modifier = max(
            -config.pvp.MAX_LEVEL_DIFF_BONUS,
            min(config.pvp.MAX_LEVEL_DIFF_BONUS, 
                level_diff * config.pvp.LEVEL_DIFF_FACTOR)
        )
        
        # Calculate final chance before caps
        raw_chance = base_chance + power_modifier + level_modifier
        
        # Apply diminishing returns for repeat attacks
        if repeat_count == 2:
            raw_chance *= config.reward.SECOND_ATTACK_MULTIPLIER
        elif repeat_count >= 3:
            raw_chance *= config.reward.THIRD_PLUS_ATTACK_MULTIPLIER
        
        # Clamp to valid range
        final_chance = max(
            config.pvp.MIN_INFECTION_CHANCE,
            min(config.pvp.MAX_INFECTION_CHANCE, raw_chance)
        )
        
        return base_chance, final_chance
    
    async def resolve_attack(self, attacker_id: int, target_id: int) -> dict:
        """
        Resolve a PvP attack between two players.
        Returns attack result dictionary.
        """
        attacker = await self.player_repo.get_by_id(attacker_id)
        target = await self.player_repo.get_by_id(target_id)
        
        if not attacker or not target:
            raise ValueError("Player not found")
        
        # Check energy
        resources = await self.resource_repo.get_resources(attacker_id)
        if not resources or resources.energy < config.energy.ATTACK_COST:
            raise ValueError("Insufficient energy")
        
        # Check cooldown
        is_on_cooldown, remaining = await self.cooldown_repo.is_on_cooldown(
            attacker_id, 'attack', str(target_id)
        )
        if is_on_cooldown:
            raise ValueError(f"Attack on cooldown: {int(remaining.total_seconds())}s remaining")
        
        # Check if target is protected
        is_protected = await self.infection_repo.check_protection(target_id)
        if is_protected:
            raise ValueError("Target is currently protected")
        
        # Check recovery complete (auto-heal if needed)
        await self.infection_repo.check_recovery_complete(target_id)
        
        # Count recent attacks against this target
        recent_attacks = await self.attack_repo.get_recent_attacks_against(
            attacker_id, target_id, limit=config.pvp.MAX_REPEAT_ATTACKS
        )
        repeat_count = len(recent_attacks) + 1
        
        # Deduct energy first (atomic operation start)
        await self.resource_repo.modify_resource(
            attacker_id, 'energy', 
            Decimal(-config.energy.ATTACK_COST), 
            'attack_cost',
            reference_id=f"attack_{target_id}"
        )
        
        # Calculate infection chance
        base_chance, final_chance = self.calculate_infection_chance(
            attacker, target, repeat_count
        )
        
        # Roll for result
        roll = random.random()
        
        # Determine result
        if roll <= final_chance:
            # Success - infect target
            result = AttackResult.SUCCESS
            
            # Apply infection
            await self.infection_repo.set_infected(target_id, attacker_id)
            
            # Calculate rewards with diminishing returns
            reward_multiplier = 1.0
            if repeat_count == 2:
                reward_multiplier = config.reward.SECOND_ATTACK_MULTIPLIER
            elif repeat_count >= 3:
                reward_multiplier = config.reward.THIRD_PLUS_ATTACK_MULTIPLIER
            
            # Base reward scaled by target power and level
            target_power = target.defense.power if target.defense else 0
            credits_reward = Decimal(str(
                (config.reward.BASE_WIN_REWARD_CREDITS + 
                 target_power * config.reward.POWER_SCALING_FACTOR +
                 target.level * config.reward.LEVEL_SCALING_FACTOR) 
                * reward_multiplier
            ))
            xp_reward = int(config.reward.BASE_WIN_REWARD_XP * reward_multiplier)
            
            # Apply rewards
            await self.resource_repo.modify_resource(
                attacker_id, 'credits', credits_reward, 'attack_reward',
                reference_id=f"attack_{target_id}"
            )
            new_level, leveled_up = await self.player_repo.add_experience(
                attacker_id, xp_reward
            )
            
            # Update attacker stats
            attacker.successful_attacks += 1
            attacker.current_streak += 1
            attacker.best_streak = max(attacker.best_streak, attacker.current_streak)
            
            # Update target stats
            target.total_attacks_received += 1
            
        elif roll <= final_chance + (1 - final_chance) * 0.3:
            # Partial success - minor effect, no infection
            result = AttackResult.PARTIAL
            credits_reward = Decimal(0)
            xp_reward = 0
            new_level = attacker.level
            leveled_up = False
            
            # Partial: small XP gain, no credits
            xp_reward = int(config.reward.BASE_WIN_REWARD_XP * 0.3 * 
                           (1.0 if repeat_count == 1 else 0.5))
            if xp_reward > 0:
                new_level, leveled_up = await self.player_repo.add_experience(
                    attacker_id, xp_reward
                )
            
            attacker.current_streak = 0
            target.total_attacks_received += 1
            
        else:
            # Fail - no effect, partial energy refund
            result = AttackResult.FAIL
            credits_reward = Decimal(0)
            xp_reward = 0
            new_level = attacker.level
            leveled_up = False
            
            # Refund some energy on loss
            refund = config.energy.ENERGY_REFUND_ON_LOSS
            await self.resource_repo.modify_resource(
                attacker_id, 'energy', Decimal(refund), 'attack_refund',
                reference_id=f"attack_{target_id}"
            )
            
            # Small consolation prize
            consolation = config.reward.BASE_LOSS_REFUND_CREDITS
            await self.resource_repo.modify_resource(
                attacker_id, 'credits', Decimal(consolation), 'attack_consolation',
                reference_id=f"attack_{target_id}"
            )
            
            attacker.current_streak = 0
            target.successful_defenses += 1
            target.total_attacks_received += 1
        
        # Log the attack
        await self.attack_repo.log_attack(
            attacker_id=attacker_id,
            target_id=target_id,
            attacker_power=attacker.virus.power if attacker.virus else 0,
            target_defense=target.defense.power if target.defense else 0,
            attacker_level=attacker.level,
            target_level=target.level,
            base_chance=base_chance,
            final_chance=final_chance,
            roll_value=roll,
            result=result,
            energy_cost=config.energy.ATTACK_COST,
            credits_reward=credits_reward,
            xp_reward=xp_reward,
            repeat_count=repeat_count,
        )
        
        # Set attack cooldown
        await self.cooldown_repo.set_cooldown(
            attacker_id, 'attack', 
            config.pvp.ATTACK_COOLDOWN_SECONDS,
            reference_id=str(target_id)
        )
        
        # Update last active
        attacker.last_active_at = datetime.now(timezone.utc)
        target.last_active_at = datetime.now(timezone.utc)
        
        await self.session.flush()
        
        return {
            'result': result,
            'success': result == AttackResult.SUCCESS,
            'base_chance': base_chance,
            'final_chance': final_chance,
            'roll': roll,
            'credits_reward': float(credits_reward),
            'xp_reward': xp_reward,
            'energy_cost': config.energy.ATTACK_COST,
            'repeat_count': repeat_count,
            'leveled_up': leveled_up,
            'new_level': new_level,
            'target_protected_until': None if result != AttackResult.SUCCESS 
                                     else (await self.infection_repo.get_state(target_id)).protection_expires_at,
        }
    
    async def can_attack(self, attacker_id: int, target_id: int) -> Tuple[bool, str]:
        """Check if attacker can attack target. Returns (can_attack, reason)"""
        attacker = await self.player_repo.get_by_id(attacker_id)
        target = await self.player_repo.get_by_id(target_id)
        
        if not attacker:
            return False, "Attacker not found"
        
        if not target:
            return False, "Target not found"
        
        if attacker.is_banned:
            return False, "Account is banned"
        
        # Check energy
        resources = await self.resource_repo.get_resources(attacker_id)
        if not resources or resources.energy < config.energy.ATTACK_COST:
            return False, "Insufficient energy"
        
        # Check cooldown
        is_on_cooldown, remaining = await self.cooldown_repo.is_on_cooldown(
            attacker_id, 'attack', str(target_id)
        )
        if is_on_cooldown:
            return False, f"Cooldown: {int(remaining.total_seconds())}s"
        
        # Check protection
        is_protected = await self.infection_repo.check_protection(target_id)
        if is_protected:
            return False, "Target is protected"
        
        # Check daily limit
        attacks_today = await self.attack_repo.count_attacks_today(attacker_id)
        if attacks_today >= config.anti_abuse.MAX_ATTACKS_PER_DAY:
            return False, "Daily attack limit reached"
        
        return True, "OK"


class VirusService:
    """Virus management service"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.player_repo = PlayerRepository(session)
        self.resource_repo = ResourceRepository(session)
    
    def calculate_virus_power(self, virus) -> int:
        """Calculate total virus power from stats"""
        if not virus:
            return 0
        
        # Simple sum of all stats
        power = (
            virus.infectivity +
            virus.adaptation +
            virus.persistence +
            virus.mutation_rate +
            virus.potency
        )
        
        # Level bonus
        power += virus.level * 2
        
        return power
    
    async def upgrade_stat(self, player_id: int, stat_name: str) -> Tuple[bool, str]:
        """Upgrade a virus stat. Returns (success, message)"""
        player = await self.player_repo.get_by_id(player_id)
        if not player or not player.virus:
            return False, "Virus not found"
        
        virus = player.virus
        
        # Validate stat name
        valid_stats = ['infectivity', 'adaptation', 'persistence', 'mutation_rate', 'potency']
        if stat_name not in valid_stats:
            return False, f"Invalid stat. Valid: {valid_stats}"
        
        # Calculate cost
        current_level = getattr(virus, stat_name)
        cost = int(
            config.upgrade.VIRUS_UPGRADE_BASE_COST * 
            (config.upgrade.VIRUS_UPGRADE_COST_MULTIPLIER ** (current_level - 1))
        )
        
        # Check resources
        resources = await self.resource_repo.get_resources(player_id)
        if not resources or resources.samples < cost:
            return False, f"Insufficient samples. Need: {cost}, Have: {resources.samples}"
        
        # Deduct samples
        await self.resource_repo.modify_resource(
            player_id, 'samples', Decimal(-cost), 'virus_upgrade',
            reference_id=f"upgrade_{stat_name}"
        )
        
        # Upgrade stat
        setattr(virus, stat_name, current_level + 1)
        
        # Recalculate power
        virus.power = self.calculate_virus_power(virus)
        
        await self.session.flush()
        
        return True, f"Upgraded {stat_name} to level {current_level + 1}"
    
    async def rename_virus(self, player_id: int, new_name: str) -> Tuple[bool, str]:
        """Rename player's virus"""
        if len(new_name) > 64:
            return False, "Name too long (max 64 characters)"
        
        if len(new_name) < 3:
            return False, "Name too short (min 3 characters)"
        
        player = await self.player_repo.get_by_id(player_id)
        if not player or not player.virus:
            return False, "Virus not found"
        
        player.virus.name = new_name
        await self.session.flush()
        
        return True, f"Virus renamed to '{new_name}'"


class DefenseService:
    """Defense management service"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.player_repo = PlayerRepository(session)
        self.resource_repo = ResourceRepository(session)
    
    def calculate_defense_power(self, defense) -> int:
        """Calculate total defense power from stats"""
        if not defense:
            return 0
        
        # Sum of all stats
        power = (
            defense.immunity +
            defense.resistance +
            defense.recovery +
            defense.detection +
            defense.shield
        )
        
        # Level bonus
        power += defense.level * 2
        
        return power
    
    async def upgrade_stat(self, player_id: int, stat_name: str) -> Tuple[bool, str]:
        """Upgrade a defense stat. Returns (success, message)"""
        player = await self.player_repo.get_by_id(player_id)
        if not player or not player.defense:
            return False, "Defense system not found"
        
        defense = player.defense
        
        # Validate stat name
        valid_stats = ['immunity', 'resistance', 'recovery', 'detection']
        if stat_name not in valid_stats:
            return False, f"Invalid stat. Valid: {valid_stats}"
        
        # Calculate cost
        current_level = getattr(defense, stat_name)
        cost = int(
            config.upgrade.DEFENSE_UPGRADE_BASE_COST * 
            (config.upgrade.DEFENSE_UPGRADE_COST_MULTIPLIER ** (current_level - 1))
        )
        
        # Check resources
        resources = await self.resource_repo.get_resources(player_id)
        if not resources or resources.samples < cost:
            return False, f"Insufficient samples. Need: {cost}, Have: {resources.samples}"
        
        # Deduct samples
        await self.resource_repo.modify_resource(
            player_id, 'samples', Decimal(-cost), 'defense_upgrade',
            reference_id=f"upgrade_{stat_name}"
        )
        
        # Upgrade stat
        setattr(defense, stat_name, current_level + 1)
        
        # Recalculate power
        defense.power = self.calculate_defense_power(defense)
        
        await self.session.flush()
        
        return True, f"Upgraded {stat_name} to level {current_level + 1}"
    
    async def activate_shield(self, player_id: int, duration_hours: int = 2) -> Tuple[bool, str]:
        """Activate temporary shield. Costs credits."""
        player = await self.player_repo.get_by_id(player_id)
        if not player or not player.defense:
            return False, "Defense system not found"
        
        # Shield cost
        shield_cost = 200  # Credits
        
        resources = await self.resource_repo.get_resources(player_id)
        if not resources or resources.credits < shield_cost:
            return False, f"Insufficient credits. Need: {shield_cost}"
        
        # Deduct credits
        await self.resource_repo.modify_resource(
            player_id, 'credits', Decimal(-shield_cost), 'shield_activation'
        )
        
        # Activate shield
        from datetime import timedelta
        player.defense.shield = 10  # Shield value
        player.defense.shield_expires_at = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        
        # Recalculate power
        player.defense.power = self.calculate_defense_power(player.defense)
        
        await self.session.flush()
        
        return True, f"Shield activated for {duration_hours} hours"
