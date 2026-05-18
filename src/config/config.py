TYPE_TO_MARCKET = {
    'TQBR': 'shares',
    'TQOB': 'bonds',
    'TQTF': 'index'
}

REDIS_URL = "redis://localhost:6379/0"
REDIS_TTL_SECONDS = 60  # Время жизни кеша в секундах