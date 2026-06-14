# embed_vector.py
import psycopg2
from psycopg2.extras import Json
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
from tqdm import tqdm
from config_vector import PG_CONFIG, MODEL_CONFIG, TABLE_CONFIG, OPTIONS

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingProcessor:
    def __init__(self):
        self.model = None
        self.conn = None
        
    def load_model(self):
        """Загрузка модели эмбеддингов"""
        logger.info(f"Загрузка модели: {MODEL_CONFIG['name']}")
        self.model = SentenceTransformer(MODEL_CONFIG['name'], device=MODEL_CONFIG['device'])
        logger.info("Модель загружена")
        
    def connect_db(self):
        """Подключение к PostgreSQL"""
        logger.info("Подключение к PostgreSQL...")
        self.conn = psycopg2.connect(**PG_CONFIG)
        self.conn.autocommit = False
        logger.info("Подключение установлено")
        
    def get_rows_to_process(self):
        """Получение строк, для которых нужно вычислить эмбеддинги"""
        table = TABLE_CONFIG['table_name']
        source_col = TABLE_CONFIG['source_column']
        target_col = TABLE_CONFIG['target_column']
        id_col = OPTIONS.get('id_column', 'id')
        
        cursor = self.conn.cursor()
        
        if OPTIONS.get('skip_existing', True):
            query = f"""
                SELECT {id_col}, {source_col}
                FROM {table}
                WHERE {source_col} IS NOT NULL 
                AND {source_col} != ''
                AND ({target_col} IS NULL OR vector_dims({target_col}) = 0)
                ORDER BY {id_col}
            """
        else:
            query = f"""
                SELECT {id_col}, {source_col}
                FROM {table}
                WHERE {source_col} IS NOT NULL 
                AND {source_col} != ''
                ORDER BY {id_col}
            """
            
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        
        logger.info(f"Найдено строк для обработки: {len(rows)}")
        return rows
        
    def compute_embeddings(self, texts, batch_size=None):
        """Вычисление эмбеддингов для списка текстов"""
        if batch_size is None:
            batch_size = MODEL_CONFIG.get('batch_size', 32)
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings
    
    def save_embeddings(self, updates):
        """Массовое сохранение эмбеддингов в БД"""
        table = TABLE_CONFIG['table_name']
        target_col = TABLE_CONFIG['target_column']
        id_col = OPTIONS.get('id_column', 'id')
        
        cursor = self.conn.cursor()
        
    
        # Подготавливаем пакетное обновление
        updated_count = 0
        for embedding in updates:
            embedding_str = '[' + ','.join(map(str, embedding[1])) + ']'
            
            query = f"""
                UPDATE {table}
                SET {target_col} = %s
                WHERE {id_col} = %s
            """
            
            cursor.execute(query, (embedding_str, embedding[0]))
            
            updated_count += 1
            
            # Коммитим каждые 1000 строк
            if updated_count % 1000 == 0:
                self.conn.commit()
        
        self.conn.commit()
        cursor.close()
#        logger.info(f"Всего сохранено: {updated_count} строк")
        
    def process(self):
        """Основной процесс"""
        try:
            # Подготовка
            self.load_model()
            self.connect_db()
            
            # Получаем данные
            rows = self.get_rows_to_process()
            
            if not rows:
                logger.info("Нет строк для обработки")
                return
            
            # Разбиваем на батчи для вычисления эмбеддингов
            batch_size = MODEL_CONFIG.get('batch_size', 32)
            all_updates = []
            
            for i in tqdm(range(0, len(rows), batch_size), desc="Вычисление эмбеддингов"):
                batch_rows = rows[i:i+batch_size]
                texts = [row[1] for row in batch_rows]
                ids = [row[0] for row in batch_rows]
                # Вычисляем эмбеддинги
                embeddings = self.compute_embeddings(texts, batch_size=len(texts))
                
                # Сохраняем пары (id, embedding)
                for j, row in enumerate(batch_rows):
                    all_updates.append((ids[j] , embeddings[j]))
            
                # Сохраняем в БД
                if len(all_updates) >= 1000:
                    self.save_embeddings(all_updates)
                    all_updates = []
            
            self.save_embeddings(all_updates)
            logger.info("Обработка завершена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            if self.conn:
                self.conn.close()
                logger.info("Соединение с БД закрыто")

if __name__ == "__main__":
    processor = EmbeddingProcessor()
    processor.process()