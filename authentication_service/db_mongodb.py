#!/usr/bin/env python3
"""
MongoDB Connection Manager com REPLICA SET
Versão corrigida - Estratégia Single Node First
"""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
import os
import logging
from functools import wraps
from datetime import datetime
import time

# Importação condicional de ReadPreference para evitar erros
try:
    from pymongo.read_preferences import ReadPreference
    READPREFERENCE_AVAILABLE = True
except ImportError:
    try:
        from pymongo import ReadPreference
        READPREFERENCE_AVAILABLE = True
    except ImportError:
        READPREFERENCE_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.client = None
            self.write_client = None
            self.read_client = None
            self.is_replica_set = False
            self._initialize_connection()
    
    def _initialize_connection(self):
        """Inicializa conexões com estratégia Single Node First"""
        # ESTRATÉGIA 1: Sempre tentar single node primeiro (mais confiável)
        if self._try_single_node_connection():
            logger.info("Conexão single node estabelecida - sistema operacional")
            self._setup_database()
            return
            
        # ESTRATÉGIA 2: Se single node falhar, tentar replica set
        if self._try_replica_set_connection():
            logger.info("Conexão replica set estabelecida após fallback")
            self._setup_database()
            return
            
        # ESTRATÉGIA 3: Conexão básica como último recurso
        if self._try_basic_connection():
            logger.info("Conexão básica estabelecida como último recurso")
            self._setup_database()
            return
        
        raise Exception("Todas as estratégias de conexão falharam")
    
    def _try_single_node_connection(self):
        """Primeira tentativa: conexão direta ao primary (mais confiável)"""
        logger.info("Tentando conexão single node ao primary...")
        
        try:
            primary_uri = "mongodb://ualflix_db_primary:27017/ualflix"
            
            self.client = MongoClient(
                primary_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=3000,
                directConnection=True  # Força conexão direta
            )
            
            # Testar conexão
            self.client.admin.command('ping')
            
            # Para single node, todos os clientes são o mesmo
            self.write_client = self.client
            self.read_client = self.client
            
            self.is_replica_set = False
            logger.info("Conexão single node bem-sucedida")
            return True
            
        except Exception as e:
            logger.warning(f"Conexão single node falhou: {e}")
            return False
    
    def _try_replica_set_connection(self):
        """Segunda tentativa: conexão ao replica set (só se ReadPreference disponível)"""
        if not READPREFERENCE_AVAILABLE:
            logger.warning("ReadPreference não disponível - pulando tentativa de replica set")
            return False
            
        logger.info("Tentando conexão ao replica set...")
        
        try:
            connection_string = os.environ.get(
                'MONGODB_CONNECTION_STRING',
                'mongodb://ualflix_db_primary:27017,ualflix_db_secondary:27017,ualflix_db_arbiter:27017/ualflix?replicaSet=ualflix-replica-set'
            )
            
            # Cliente principal
            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=8000,
                connectTimeoutMS=4000,
                retryWrites=True,
                retryReads=True
            )
            
            # Testar conexão principal
            self.client.admin.command('ping')
            
            # Cliente para escrita (primary)
            self.write_client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=8000,
                connectTimeoutMS=4000,
                read_preference=ReadPreference.PRIMARY,
                retryWrites=True
            )
            
            # Cliente para leitura (secondary preferred)
            self.read_client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=8000,
                connectTimeoutMS=4000,
                read_preference=ReadPreference.SECONDARY_PREFERRED,
                retryReads=True
            )
            
            # Testar todas as conexões
            self.write_client.admin.command('ping')
            self.read_client.admin.command('ping')
            
            self.is_replica_set = True
            logger.info("Conexão ao replica set bem-sucedida")
            return True
            
        except Exception as e:
            logger.warning(f"Conexão ao replica set falhou: {e}")
            return False
    
    def _try_simple_primary_connection(self):
        """Terceira tentativa: conexão simples sem directConnection"""
        logger.info("Tentando conexão simples ao primary...")
        
        try:
            primary_uri = "mongodb://ualflix_db_primary:27017/ualflix"
            
            self.client = MongoClient(
                primary_uri,
                serverSelectionTimeoutMS=6000,
                connectTimeoutMS=3000
            )
            
            # Testar conexão
            self.client.admin.command('ping')
            
            # Todos os clientes apontam para o mesmo
            self.write_client = self.client
            self.read_client = self.client
            
            self.is_replica_set = False
            logger.info("Conexão simples estabelecida")
            return True
            
        except Exception as e:
            logger.warning(f"Conexão simples falhou: {e}")
            return False
    
    def _try_basic_connection(self):
        """Quarta tentativa: conexão mais básica possível"""
        logger.info("Tentando conexão básica...")
        
        try:
            basic_uri = "mongodb://ualflix_db_primary:27017"
            
            self.client = MongoClient(
                basic_uri,
                serverSelectionTimeoutMS=3000
            )
            
            # Testar conexão
            self.client.admin.command('ping')
            
            # Todos os clientes são o mesmo
            self.write_client = self.client
            self.read_client = self.client
            
            self.is_replica_set = False
            logger.info("Conexão básica estabelecida")
            return True
            
        except Exception as e:
            logger.warning(f"Conexão básica falhou: {e}")
            return False
    
    def _setup_database(self):
        """Setup inicial da base de dados"""
        try:
            db = self.get_write_database()
            
            # Criar coleções se não existirem
            collections = ['users', 'videos', 'video_views', 'replication_test']
            existing_collections = db.list_collection_names()
            
            for collection_name in collections:
                if collection_name not in existing_collections:
                    db.create_collection(collection_name)
                    logger.info(f"Coleção '{collection_name}' criada")
            
            # Criar índices
            self._create_indexes(db)
            
            # Configurar utilizador admin
            self._setup_admin_user(db)
            
        except Exception as e:
            logger.error(f"Erro no setup da base de dados: {e}")
    
    def _create_indexes(self, db):
        """Cria índices necessários"""
        try:
            # Índices para users
            try:
                db.users.create_index('username', unique=True)
                db.users.create_index('email')
            except Exception:
                pass  # Índices já podem existir
            
            # Índices para videos
            try:
                db.videos.create_index('user_id')
                db.videos.create_index('status')
                db.videos.create_index('upload_date')
            except Exception:
                pass
            
            # Índices para video_views
            try:
                db.video_views.create_index('video_id')
                db.video_views.create_index('user_id')
                db.video_views.create_index('view_date')
            except Exception:
                pass
            
            # Índices para replication_test
            try:
                db.replication_test.create_index('test_id')
                db.replication_test.create_index('write_time')
            except Exception:
                pass
            
            logger.info("Índices configurados")
            
        except Exception as e:
            logger.warning(f"Erro ao criar índices: {e}")
    
    def _setup_admin_user(self, db):
        """Configura utilizador administrador"""
        try:
            # Verificar se admin já existe
            admin_user = db.users.find_one({'username': 'admin'})
            
            if not admin_user:
                # Importar aqui para evitar dependências circulares
                try:
                    from werkzeug.security import generate_password_hash
                    password_hash = generate_password_hash('admin', method='pbkdf2:sha256')
                except ImportError:
                    # Fallback se werkzeug não estiver disponível
                    import hashlib
                    password_hash = hashlib.sha256('admin'.encode()).hexdigest()
                
                admin_doc = {
                    'username': 'admin',
                    'email': 'admin@ualflix.com',
                    'password': password_hash,
                    'is_admin': True,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                result = db.users.insert_one(admin_doc)
                logger.info(f"Utilizador admin criado com ID: {result.inserted_id}")
                
            else:
                # Garantir que o admin tem privilégios corretos
                db.users.update_one(
                    {'username': 'admin'},
                    {
                        '$set': {
                            'is_admin': True,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                logger.info("Utilizador admin verificado e atualizado")
            
        except Exception as e:
            logger.error(f"Erro ao configurar utilizador admin: {e}")
    
    def get_database(self):
        """Retorna a base de dados principal"""
        if not self.client:
            self._initialize_connection()
        return self.client[os.environ.get('MONGODB_DATABASE', 'ualflix')]
    
    def get_write_database(self):
        """Retorna base de dados para operações de escrita"""
        if not self.write_client:
            self._initialize_connection()
        return self.write_client[os.environ.get('MONGODB_DATABASE', 'ualflix')]
    
    def get_read_database(self):
        """Retorna base de dados para operações de leitura"""
        if not self.read_client:
            self._initialize_connection()
        return self.read_client[os.environ.get('MONGODB_DATABASE', 'ualflix')]
    
    def check_replica_set_status(self):
        """Verifica status do replica set"""
        if not self.is_replica_set:
            return {
                'set_name': 'single_node',
                'status': 'single_mode',
                'primary_name': 'ualflix_db_primary:27017',
                'members': [
                    {
                        'name': 'ualflix_db_primary:27017',
                        'state': 1,
                        'health': 1,
                        'is_primary': True,
                        'is_secondary': False,
                        'is_arbiter': False
                    }
                ],
                'total_members': 1,
                'healthy_members': 1,
                'source': 'single_node_simulation'
            }
        
        try:
            status = self.client.admin.command("replSetGetStatus")
            
            members = []
            primary_name = None
            
            for member in status.get('members', []):
                member_info = {
                    'name': member.get('name'),
                    'state': member.get('state'),
                    'health': member.get('health'),
                    'is_primary': member.get('state') == 1,
                    'is_secondary': member.get('state') == 2,
                    'is_arbiter': member.get('state') == 7
                }
                
                if member_info['is_primary']:
                    primary_name = member_info['name']
                
                members.append(member_info)
            
            return {
                'set_name': status.get('set'),
                'status': 'healthy',
                'primary_name': primary_name,
                'members': members,
                'total_members': len(members),
                'healthy_members': len([m for m in members if m['health'] == 1]),
                'source': 'real_replica_set'
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar replica set: {e}")
            return {
                'set_name': 'error',
                'status': 'error',
                'error': str(e),
                'members': [],
                'source': 'error'
            }
    
    def test_replication_lag(self):
        """Testa lag de replicação"""
        if not self.is_replica_set:
            return {
                'replication_working': True,
                'lag_seconds': 0.0,
                'test_id': 'single_node',
                'attempts_made': 1,
                'status': 'single_node_mode',
                'source': 'single_node_simulation'
            }
        
        try:
            test_id = f"replication_test_{int(time.time())}"
            start_time = time.time()
            
            # Escrever no primary
            write_db = self.get_write_database()
            test_doc = {
                'test_id': test_id,
                'write_time': datetime.utcnow(),
                'test_type': 'replication_lag'
            }
            write_db.replication_test.insert_one(test_doc)
            
            # Tentar ler do secondary
            max_attempts = 10
            lag_seconds = None
            
            for attempt in range(max_attempts):
                try:
                    read_db = self.get_read_database()
                    found_doc = read_db.replication_test.find_one({'test_id': test_id})
                    
                    if found_doc:
                        lag_seconds = time.time() - start_time
                        break
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                    time.sleep(0.5)
            
            # Limpar documento de teste
            try:
                write_db.replication_test.delete_one({'test_id': test_id})
            except:
                pass
            
            replication_working = lag_seconds is not None
            
            return {
                'replication_working': replication_working,
                'lag_seconds': lag_seconds if lag_seconds else 999.0,
                'test_id': test_id,
                'attempts_made': attempt + 1 if replication_working else max_attempts,
                'status': 'healthy' if replication_working and lag_seconds < 5.0 else 'warning',
                'source': 'real_replication_test'
            }
            
        except Exception as e:
            logger.error(f"Erro no teste de replicação: {e}")
            return {
                'replication_working': False,
                'lag_seconds': 999.0,
                'test_id': 'error',
                'error': str(e),
                'source': 'error'
            }
    
    def get_database_metrics(self):
        """Obtém métricas da base de dados"""
        try:
            # Métricas do primary/write database
            write_db = self.get_write_database()
            write_stats = write_db.command('dbStats')
            
            primary_metrics = {
                'data_size_mb': round(write_stats.get('dataSize', 0) / (1024 * 1024), 2),
                'storage_size_mb': round(write_stats.get('storageSize', 0) / (1024 * 1024), 2),
                'index_size_mb': round(write_stats.get('indexSize', 0) / (1024 * 1024), 2),
                'collections': write_stats.get('collections', 0),
                'objects': write_stats.get('objects', 0),
                'connection_type': 'primary_write',
                'source': 'real_primary_stats'
            }
            
            # Contar documentos por coleção
            try:
                collections = write_db.list_collection_names()
                if 'users' in collections:
                    primary_metrics['users_count'] = write_db.users.count_documents({})
                if 'videos' in collections:
                    primary_metrics['videos_count'] = write_db.videos.count_documents({})
                if 'video_views' in collections:
                    primary_metrics['views_count'] = write_db.video_views.count_documents({})
            except Exception as e:
                logger.warning(f"Erro ao contar documentos: {e}")
            
            # Métricas do secondary (se disponível)
            secondary_metrics = {}
            if self.is_replica_set:
                try:
                    read_db = self.get_read_database()
                    read_stats = read_db.command('dbStats')
                    
                    secondary_metrics = {
                        'data_size_mb': round(read_stats.get('dataSize', 0) / (1024 * 1024), 2),
                        'collections': read_stats.get('collections', 0),
                        'objects': read_stats.get('objects', 0),
                        'read_preference': 'secondaryPreferred',
                        'connection_type': 'secondary_read',
                        'source': 'real_secondary_stats'
                    }
                    
                    # Contar documentos no secondary
                    collections = read_db.list_collection_names()
                    if 'users' in collections:
                        secondary_metrics['users_count'] = read_db.users.count_documents({})
                    if 'videos' in collections:
                        secondary_metrics['videos_count'] = read_db.videos.count_documents({})
                    if 'video_views' in collections:
                        secondary_metrics['views_count'] = read_db.video_views.count_documents({})
                        
                except Exception as e:
                    logger.warning(f"Não foi possível obter métricas do secondary: {e}")
                    secondary_metrics = {
                        'error': str(e),
                        'read_preference': 'primary_fallback',
                        'source': 'secondary_error'
                    }
            else:
                secondary_metrics = {
                    'note': 'Single node mode - no secondary available',
                    'source': 'single_node_mode'
                }
            
            return {
                'primary': primary_metrics,
                'secondary': secondary_metrics,
                'replica_set_name': os.environ.get('MONGODB_REPLICA_SET', 'ualflix-replica-set'),
                'collection_timestamp': datetime.utcnow().isoformat(),
                'is_replica_set': self.is_replica_set
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter métricas: {e}")
            return {
                'primary': {'error': str(e), 'source': 'primary_error'},
                'secondary': {'error': str(e), 'source': 'secondary_error'},
                'replica_set_name': 'error',
                'is_replica_set': False
            }
    
    def _get_primary_host(self):
        """Obtém o host primary atual"""
        try:
            if self.is_replica_set:
                status = self.check_replica_set_status()
                return status.get('primary_name', 'unknown')
            else:
                return 'ualflix_db_primary:27017'
        except:
            return 'unknown'
    
    def create_indexes(self):
        """Método público para criar índices"""
        try:
            db = self.get_write_database()
            self._create_indexes(db)
        except Exception as e:
            logger.error(f"Erro ao criar índices: {e}")
    
    def init_collections(self):
        """Método público para inicializar coleções"""
        try:
            self._setup_database()
        except Exception as e:
            logger.error(f"Erro ao inicializar coleções: {e}")

# Singleton global
_mongodb_manager = None

def get_mongodb_manager():
    """Retorna instância singleton do MongoDB Manager"""
    global _mongodb_manager
    if _mongodb_manager is None:
        _mongodb_manager = MongoDBManager()
    return _mongodb_manager

def with_write_db(func):
    """Decorator para operações de escrita na base de dados"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            db_manager = get_mongodb_manager()
            db = db_manager.get_write_database()
            return func(db, *args, **kwargs)
        except Exception as e:
            logger.error(f"Erro na operação de escrita {func.__name__}: {e}")
            raise
    return wrapper

def with_read_db(func):
    """Decorator para operações de leitura na base de dados"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            db_manager = get_mongodb_manager()
            db = db_manager.get_read_database()
            return func(db, *args, **kwargs)
        except Exception as e:
            logger.error(f"Erro na operação de leitura {func.__name__}: {e}")
            raise
    return wrapper