"""Unit tests for game balance and combat mechanics"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# Import config and services
from app.config import config
from app.game.services import CombatService, VirusService, DefenseService


class TestInfectionChanceCalculation:
    """Test the PvP infection chance formula"""
    
    def test_base_chance_equal_players(self):
        """Test base chance when players are equal"""
        # Mock attacker and defender with equal power
        attacker = MagicMock()
        attacker.virus = MagicMock(power=50)
        attacker.level = 10
        
        defender = MagicMock()
        defender.defense = MagicMock(power=50)
        defender.level = 10
        
        service = CombatService.__new__(CombatService)
        base_chance, final_chance = service.calculate_infection_chance(
            attacker, defender, repeat_count=1
        )
        
        assert base_chance == config.pvp.BASE_INFECTION_CHANCE
        assert final_chance == config.pvp.BASE_INFECTION_CHANCE
    
    def test_power_advantage_increases_chance(self):
        """Test that higher virus power increases infection chance"""
        attacker = MagicMock()
        attacker.virus = MagicMock(power=70)
        attacker.level = 10
        
        defender = MagicMock()
        defender.defense = MagicMock(power=30)
        defender.level = 10
        
        service = CombatService.__new__(CombatService)
        base_chance, final_chance = service.calculate_infection_chance(
            attacker, defender, repeat_count=1
        )
        
        # 40 power difference * 2% = 80% increase
        expected = config.pvp.BASE_INFECTION_CHANCE + (40 * config.pvp.POWER_DIFF_FACTOR)
        expected = min(expected, config.pvp.MAX_INFECTION_CHANCE)
        
        assert final_chance <= config.pvp.MAX_INFECTION_CHANCE
        assert final_chance > base_chance
    
    def test_defense_advantage_decreases_chance(self):
        """Test that higher defense decreases infection chance"""
        attacker = MagicMock()
        attacker.virus = MagicMock(power=30)
        attacker.level = 10
        
        defender = MagicMock()
        defender.defense = MagicMock(power=70)
        defender.level = 10
        
        service = CombatService.__new__(CombatService)
        base_chance, final_chance = service.calculate_infection_chance(
            attacker, defender, repeat_count=1
        )
        
        assert final_chance >= config.pvp.MIN_INFECTION_CHANCE
        assert final_chance < base_chance
    
    def test_chance_clamped_to_minimum(self):
        """Test that chance never goes below minimum"""
        attacker = MagicMock()
        attacker.virus = MagicMock(power=1)
        attacker.level = 1
        
        defender = MagicMock()
        defender.defense = MagicMock(power=100)
        defender.level = 20
        
        service = CombatService.__new__(CombatService)
        base_chance, final_chance = service.calculate_infection_chance(
            attacker, defender, repeat_count=1
        )
        
        assert final_chance >= config.pvp.MIN_INFECTION_CHANCE
    
    def test_chance_clamped_to_maximum(self):
        """Test that chance never exceeds maximum"""
        attacker = MagicMock()
        attacker.virus = MagicMock(power=100)
        attacker.level = 20
        
        defender = MagicMock()
        defender.defense = MagicMock(power=1)
        defender.level = 1
        
        service = CombatService.__new__(CombatService)
        base_chance, final_chance = service.calculate_infection_chance(
            attacker, defender, repeat_count=1
        )
        
        assert final_chance <= config.pvp.MAX_INFECTION_CHANCE
    
    def test_diminishing_returns_on_repeat_attacks(self):
        """Test that repeat attacks have reduced chance"""
        attacker = MagicMock()
        attacker.virus = MagicMock(power=50)
        attacker.level = 10
        
        defender = MagicMock()
        defender.defense = MagicMock(power=50)
        defender.level = 10
        
        service = CombatService.__new__(CombatService)
        
        _, chance_1st = service.calculate_infection_chance(attacker, defender, repeat_count=1)
        _, chance_2nd = service.calculate_infection_chance(attacker, defender, repeat_count=2)
        _, chance_3rd = service.calculate_infection_chance(attacker, defender, repeat_count=3)
        
        assert chance_2nd < chance_1st
        assert chance_3rd < chance_2nd
        assert chance_3rd <= chance_1st * config.reward.THIRD_PLUS_ATTACK_MULTIPLIER


class TestVirusPowerCalculation:
    """Test virus power calculation"""
    
    def test_basic_power_calculation(self):
        """Test basic virus power sum"""
        virus = MagicMock()
        virus.infectivity = 5
        virus.adaptation = 5
        virus.persistence = 5
        virus.mutation_rate = 5
        virus.potency = 5
        virus.level = 1
        
        service = VirusService.__new__(VirusService)
        power = service.calculate_virus_power(virus)
        
        # Sum of stats (25) + level bonus (2) = 27
        expected = 25 + 2
        assert power == expected
    
    def test_level_bonus(self):
        """Test level bonus to power"""
        virus = MagicMock()
        virus.infectivity = 1
        virus.adaptation = 1
        virus.persistence = 1
        virus.mutation_rate = 1
        virus.potency = 1
        virus.level = 10
        
        service = VirusService.__new__(VirusService)
        power = service.calculate_virus_power(virus)
        
        # Sum of stats (5) + level bonus (20) = 25
        expected = 5 + 20
        assert power == expected


class TestDefensePowerCalculation:
    """Test defense power calculation"""
    
    def test_basic_power_calculation(self):
        """Test basic defense power sum"""
        defense = MagicMock()
        defense.immunity = 5
        defense.resistance = 5
        defense.recovery = 5
        defense.detection = 5
        defense.shield = 0
        defense.level = 1
        
        service = DefenseService.__new__(DefenseService)
        power = service.calculate_defense_power(defense)
        
        # Sum of stats (20) + level bonus (2) = 22
        expected = 20 + 2
        assert power == expected


class TestEnergySystem:
    """Test energy system configuration"""
    
    def test_energy_regen_rate(self):
        """Test energy regeneration is reasonable"""
        assert config.energy.REGEN_RATE > 0
        assert config.energy.REGEN_RATE <= config.energy.MAX_ENERGY
    
    def test_attack_cost_valid(self):
        """Test attack cost is within valid range"""
        assert config.energy.ATTACK_COST > 0
        assert config.energy.ATTACK_COST <= config.energy.MAX_ENERGY
    
    def test_min_energy_for_attack(self):
        """Test minimum energy requirement"""
        assert config.energy.MIN_ENERGY_FOR_ATTACK > 0
        assert config.energy.MIN_ENERGY_FOR_ATTACK <= config.energy.MAX_ENERGY


class TestAntiSnowballMechanics:
    """Test anti-snowball mechanics"""
    
    def test_protection_window_exists(self):
        """Test protection window is configured"""
        assert config.pvp.PROTECTION_WINDOW_SECONDS > 0
        # Should be at least a few minutes
        assert config.pvp.PROTECTION_WINDOW_SECONDS >= 600
    
    def test_attack_cooldown_exists(self):
        """Test attack cooldown is configured"""
        assert config.pvp.ATTACK_COOLDOWN_SECONDS > 0
        # Should prevent spam but not be too restrictive
        assert config.pvp.ATTACK_COOLDOWN_SECONDS >= 60
    
    def test_matchmaking_range_configured(self):
        """Test matchmaking power range"""
        assert config.pvp.MATCHMAKING_POWER_RANGE > 0
        assert config.pvp.MATCHMAKING_MAX_RANGE > config.pvp.MATCHMAKING_POWER_RANGE
    
    def test_daily_attack_limit(self):
        """Test daily attack limit exists"""
        assert config.anti_abuse.MAX_ATTACKS_PER_DAY > 0
        # Reasonable limit to prevent farming
        assert config.anti_abuse.MAX_ATTACKS_PER_DAY <= 100


class TestEconomyBalance:
    """Test economy balance"""
    
    def test_reward_scaling(self):
        """Test reward scaling factors"""
        assert config.reward.POWER_SCALING_FACTOR > 0
        assert config.reward.LEVEL_SCALING_FACTOR > 0
    
    def test_consolation_prize_exists(self):
        """Test loss consolation prize"""
        assert config.reward.BASE_LOSS_REFUND_CREDITS >= 0
        assert config.energy.ENERGY_REFUND_ON_LOSS >= 0
    
    def test_production_rates(self):
        """Test idle production rates"""
        assert config.production.BASE_CREDITS_PER_HOUR > 0
        assert config.production.BASE_SAMPLES_PER_HOUR > 0
        assert config.production.OFFLINE_CAP_HOURS > 0


class TestProgressionCurve:
    """Test progression curve"""
    
    def test_xp_growth_factor(self):
        """Test XP growth factor is reasonable"""
        assert config.progression.XP_GROWTH_FACTOR > 1.0
        # Shouldn't be too steep
        assert config.progression.XP_GROWTH_FACTOR <= 2.0
    
    def test_max_level_configured(self):
        """Test max level is set"""
        assert config.progression.MAX_LEVEL > 1
        assert config.progression.MAX_LEVEL <= 1000
    
    def test_starting_resources(self):
        """Test starting resources are positive"""
        assert config.progression.STARTING_CREDITS > 0
        assert config.progression.STARTING_SAMPLES > 0
        assert config.progression.STARTING_ENERGY > 0


@pytest.mark.asyncio
class TestCombatServiceIntegration:
    """Integration tests for combat service"""
    
    async def test_can_attack_validation(self):
        """Test can_attack method validation"""
        # This would require a real database session
        # Placeholder for integration test
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
