# Virolabs - Telegram Game

🧪 **Social Idle/RPG/Strategy Game for Telegram**

Create your own virus, build your laboratory, and compete with other players in this strategic PvP game!

## 🎮 Game Concept

You are both:
- **Virus Creator**: Develop your unique virus strain with different characteristics
- **Laboratory Owner**: Protect your lab from infections by other players

The core dilemma: **Attack or Defend?**

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Telegram Bot Token (from @BotFather)
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd viralabs
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start PostgreSQL** (or use Docker)
```bash
docker-compose up -d postgres
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start the bot**
```bash
python -m app.main --mode polling
```

### Docker Deployment

```bash
# Build and run everything
docker-compose up -d

# View logs
docker-compose logs -f bot
```

## 🎯 Core Features

### Virus Development
- 5 abstract characteristics to upgrade:
  - ☣️ Infectivity (заразность)
  - 🔄 Adaptation (адаптация)
  - 💪 Persistence (устойчивость)
  - 🧬 Mutation Rate (мутации)
  - ⚡ Potency (мощность)

### Defense System
- Upgrade your protection:
  - 🛡 Immunity
  - 🔒 Resistance
  - 💚 Recovery
  - 📡 Detection
- Activate temporary shields

### PvP Combat
- Probabilistic combat system (not pure RNG)
- Chance calculation based on:
  - Virus power vs Defense power
  - Level difference
  - Recent attacks (diminishing returns)
- Three outcomes: Success, Partial, Fail
- Protection window after infection

### Economy
- 💰 Credits: Main currency
- 🧬 Samples: Research currency
- ⚡ Energy: Action resource (regenerates over time)
- Idle production from laboratory

### Progression
- Player levels with XP
- Laboratory upgrades
- Research tree (planned)
- Mutations (planned)
- Achievements (planned)
- Quests (planned)

## 🎲 Game Balance

### Anti-Snowball Mechanics
- Protection window after successful infection (30 min)
- Attack cooldown (5 min per target)
- Diminishing returns on repeat attacks
- Matchmaking within power range
- Daily attack limits

### Fair PvP Formula
```
base_chance = 50%
power_modifier = (attacker_power - defender_power) * 2%
level_modifier = (attacker_level - defender_level) * 3% (capped at ±30%)

final_chance = clamp(
    base + power_modifier + level_modifier,
    min=15%,
    max=85%
)
```

Repeat attack multipliers:
- 1st attack: 100%
- 2nd attack: 70%
- 3rd+ attack: 40%

## 📁 Project Structure

```
app/
├── config.py              # Game configuration & balance
├── main.py                # Bot entry point
├── database/
│   └── database.py        # DB connection & session
├── game/
│   ├── models/
│   │   └── models.py      # SQLAlchemy ORM models
│   ├── repositories.py    # Data access layer
│   └── services.py        # Game logic services
├── telegram/
│   ├── routers/
│   │   └── main.py        # Telegram handlers
│   └── keyboards/
│       └── main.py        # Inline keyboards
└── utils/                 # Utilities

tests/                     # Test files
alembic/                   # Database migrations
```

## 🛠 Development

### Running Tests
```bash
pytest tests/ -v
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Style
```bash
# Format code
black app/ tests/

# Lint
flake8 app/ tests/
```

## 📋 Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the game / Register |
| `/lab` | View your laboratory profile |
| `/help` | Show help information |

## 🔐 Security

- All callbacks validated against user ID
- Rate limiting on attacks
- Transaction-based resource operations
- Input validation
- SQL injection protection via SQLAlchemy
- No secrets in code (use .env)

## 📊 Monitoring

Structured logging enabled. For production:
- Add Sentry for error tracking
- Add Prometheus metrics
- Set up Grafana dashboards

## 🚧 Planned Features

- [ ] Research tree system
- [ ] Mutations discovery
- [ ] Daily quests & achievements
- [ ] Clan/alliance system
- [ ] Seasonal events
- [ ] Trading system
- [ ] Battle Pass
- [ ] Referral program
- [ ] Tournaments

## ⚖️ License

MIT License

## 👥 Contributing

Contributions welcome! Please read our contributing guidelines first.

---

**Remember**: This is a fictional game. All viruses, infections, and mutations are abstract game mechanics only. No real biological content is included.
