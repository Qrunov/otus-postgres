import os

# Настройки подключения к PostgreSQL (trust authentication)
DB_CONFIG = {
    'port': int(os.getenv('DB_PORT', 5433)),
    'dbname': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'postgres')
    # Без пароля - используется trust authentication
}

# Директория для кэша датасетов HuggingFace
CACHE_DIR = os.getenv('HF_CACHE_DIR', '/var/lib/docker/cache')

# Настройки датасета
DATASET_NAME = os.getenv('DATASET_NAME', 'kaengreg/wikifacts-window_5')
DATASET_QRELS_NAME = os.getenv('DATASET_QRELS_NAME', 'kaengreg/wikifacts-window_5-qrels')

# Настройки загрузки
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 5000))
RESULTS_BATCH_SIZE = int(os.getenv('RESULTS_BATCH_SIZE', 1000))

# Описание эталонного эксперимента
RUN_DESCRIPTION = os.getenv('RUN_DESCRIPTION', 'Wikifacts-window_5 gold standard qrels')

# Настройки очистки данных
CLEAR_TABLES_BEFORE_LOAD = os.getenv('CLEAR_TABLES_BEFORE_LOAD', 'true').lower() == 'true'

# Путь для сохранения примеров
EXAMPLES_OUTPUT_FILE = os.getenv('EXAMPLES_OUTPUT_FILE', 'wikifacts_examples.txt')

# Логирование
VERBOSE = os.getenv('VERBOSE', 'true').lower() == 'true'

# config.py
CORPUS_SPLIT = os.getenv('CORPUS_SPLIT', 'train')
QUERIES_SPLIT = os.getenv('QUERIES_SPLIT', 'train')
QRELS_SPLIT = os.getenv('QRELS_SPLIT', 'dev')
