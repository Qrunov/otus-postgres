# config_vector.py
# Конфигурация для скрипта вычисления эмбеддингов

# Параметры подключения к PostgreSQL
PG_CONFIG = {
    "port": 5433,
    "database": "postgres",
    "user": "postgres",
}

# Настройки модели
MODEL_CONFIG = {
    "name": "intfloat/multilingual-e5-large",  # название модели
    "device": "cuda",  # "cpu" или "cuda" (если есть GPU)
    "batch_size": 256   # размер батча для обработки

}

# Настройки таблицы и столбцов
TABLE_CONFIG = {
    "table_name": "news",
    "source_column": "article",   # столбец с текстом
    "target_column": "embedding"      # столбец для сохранения эмбеддингов (тип vector или jsonb/text)
}

# Дополнительные опции
OPTIONS = {
    "skip_existing": True,   # пропускать строки, где target_column уже заполнен
    "id_column": "id"        # первичный ключ для обновления (опционально)
}