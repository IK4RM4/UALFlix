#!/usr/bin/env python3
"""
MongoDB Connection Manager REAL com Replica Set
FUNCIONALIDADE 5: ESTRATÉGIAS DE REPLICAÇÃO DE DADOS - IMPLEMENTAÇÃO REAL
"""

from pymongo import MongoClient, ReadPreference
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
import os
import logging
from functools import wraps
from datetime import datetime
from bson import ObjectId
import time

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
            self._setup_config()
            self.client = None
            self.write_client = None
            self.read_client = None
            self._initialize_connection()
    
    def _setup_config(self):
        """Configuração para conectar ao replica set real"""
        self.config = {
            'replica_set': os.environ.get('MONGODB_REPLICA_SET', 'ualflix-replica-set'),
            'database': os.environ.get('MONGODB_DATABASE', 'ualflix'),
            'username': os.environ.get('MONGODB_USERNAME', 'admin'),
            'password': os.environ.get('MONGODB_PASSWORD', 'password'),
            'auth_source': os.environ.get('MONGODB_AUTH_SOURCE', 'admin'),
        }
        
        # Configuração dos hosts do replica set
        primary_host = os.environ.get('MONGODB_PRIMARY_HOST', 'ualflix_db_primary')
        secondary_host = os.environ.get('MONGODB_SECONDARY_HOST', 'ualflix_db_secondary')
        arbiter_host = os.environ.get('MONGODB_ARBITER_HOST', 'ualflix_db_arbiter')
        
        primary_port = os.environ.get('MONGODB_PRIMARY_PORT', '27017')
        secondary_port = os.environ.get('MONGODB_SECONDARY_PORT', '27017')
        arbiter_port = os.environ.get('MONGODB_ARBITER_PORT', '27017')
        
        # Lista de hosts do replica set
        self.hosts = [
            f"{primary_host}:{primary_port}",
            f"{secondary_host}:{secondary_port}",
            f"{arbiter_host}:{arbiter_port}"
        ]
        
        # Connection string para replica set
        self.connection_string = os.environ.get(
            'MONGODB_CONNECTION_STRING',
            f"mongodb://{self.config['username']}:{self.config['password']}@{','.join(self.hosts)}/{self.config['database']}?replicaSet={self.config['replica_set']}&authSource={self.config['auth_source']}"
        )
        
        logger.info(f"Configurado para replica set: {self.config['replica_set']}")
        logger.info(f"Hosts: {self.hosts}")
    
    def _initialize_connection(self):
        """Inicializa conexões ao replica set"""
        try:
            # CONEXÃO PRINCIPAL (para operações gerais)
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                maxPoolSize=50,
                retryWrites=True,
                retryReads=True
            )
            
            # CONEXÃO PARA ESCRITA (primary preferred)
            self.write_client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                maxPoolSize=50,
                readPreference=ReadPreference.PRIMARY,
                retryWrites=True
            )
            
            # CONEXÃO PARA LEITURA (secondary preferred)
            self.read_client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                maxPoolSize=50,
                readPreference=ReadPreference.SECONDARY_PREFERRED,
                retryReads=True
            )
            
            # Testar todas as conexões
            self._test_connections()
            
            logger.info("✅ MongoDB Replica Set conectado com sucesso!")
            logger.info(f"   - Primary: {self._get_primary_host()}")
            logger.info(f"   - Replica Set: {self.config['replica_set']}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao replica set: {e}")
            # Fallback para conexão simples se replica set falhar
            self._fallback_to_simple_connection()
    
    def _test_connections(self):
        """Testa todas as conexões"""
        # Testar conexão principal
        self.client.admin.command('ping')
        
        # Testar conexão de escrita
        self.write_client.admin.command('ping')
        
        # Testar conexão de leitura
        self.read_client.admin.command('ping')
        
        logger.info("🔍 Todas as conexões testadas com sucesso")
    
    def _fallback_to_simple_connection(self):
        """Fallback para conexão simples se replica set falhar"""
        logger.warning("⚠️ Tentando fallback para conexão simples...")
        try:
            primary_host = os.environ.get('MONGODB_PRIMARY_HOST', 'ualflix_db_primary')
            primary_port = os.environ.get('MONGODB_PRIMARY_PORT', '27017')
            
            simple_uri = f"mongodb://{self.config['username']}:{self.config['password']}@{primary_host}:{primary_port}/{self.config['database']}?authSource={self.config['auth_source']}"
            
            self.client = MongoClient(simple_uri, serverSelectionTimeoutMS=15000)
            self.write_client = self.client
            self.read_client = self.client
            
            self.client.admin.command('ping')
            logger.warning("⚠️ Conectado em modo fallback (single instance)")
            
        except Exception as e2:
            logger.error(f"❌ Falha total na conexão: {e2}")
            raise
    
    def get_database(self):
        """Retorna database com conexão principal"""
        if not self.client:
            self._initialize_connection()
        return self.client[self.config['database']]
    
    def get_write_database(self):
        """Retorna database otimizada para ESCRITA (primary)"""
        if not self.write_client:
            self._initialize_connection()
        return self.write_client[self.config['database']]
    
    def get_read_database(self):
        """Retorna database otimizada para LEITURA (secondary preferred)"""
        if not self.read_client:
            self._initialize_connection()
        return self.read_client[self.config['database']]
    
    def check_replica_set_status(self):
        """IMPLEMENTAÇÃO REAL do status do replica set"""
        try:
            # Usar conexão principal para verificar status
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
                'date': status.get('date'),
                'my_state': status.get('myState'),
                'total_members': len(members),
                'healthy_members': len([m for m in members if m['health'] == 1]),
                'source': 'real_replica_set'
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar status do replica set: {e}")
            return {
                'set_name': self.config['replica_set'],
                'status': 'error',
                'error': str(e),
                'members': [],
                'source': 'error'
            }
    
    def test_replication_lag(self):
        """TESTE REAL de lag de replicação"""
        try:
            test_id = f"replication_test_{int(time.time())}"
            start_time = time.time()
            
            # 1. ESCREVER no primary
            write_db = self.get_write_database()
            test_doc = {
                'test_id': test_id,
                'write_time': datetime.utcnow(),
                'test_type': 'replication_lag'
            }
            write_db.replication_test.insert_one(test_doc)
            
            # 2. AGUARDAR e tentar LER do secondary
            max_attempts = 10
            lag_seconds = None
            
            for attempt in range(max_attempts):
                try:
                    read_db = self.get_read_database()
                    found_doc = read_db.replication_test.find_one({'test_id': test_id})
                    
                    if found_doc:
                        lag_seconds = time.time() - start_time
                        logger.info(f"🔄 Replicação detectada em {lag_seconds:.3f}s")
                        break
                    
                    time.sleep(0.5)  # Aguardar 500ms entre tentativas
                    
                except Exception as e:
                    logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                    time.sleep(0.5)
            
            # 3. LIMPAR documento de teste
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
                'max_lag_acceptable': 5.0,
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
        """Métricas REAIS da base de dados por instância"""
        try:
            # Métricas do PRIMARY
            write_db = self.get_write_database()
            write_stats = write_db.command('dbStats')
            
            primary_metrics = {
                'data_size_mb': round(write_stats.get('dataSize', 0) / (1024 * 1024), 2),
                'storage_size_mb': round(write_stats.get('storageSize', 0) / (1024 * 1024), 2),
                'index_size_mb': round(write_stats.get('indexSize', 0) / (1024 * 1024), 2),
                'collections': write_stats.get('collections', 0),
                'objects': write_stats.get('objects', 0),
                'users_count': write_db.users.count_documents({}) if 'users' in write_db.list_collection_names() else 0,
                'videos_count': write_db.videos.count_documents({}) if 'videos' in write_db.list_collection_names() else 0,
                'views_count': write_db.video_views.count_documents({}) if 'video_views' in write_db.list_collection_names() else 0,
                'avg_obj_size': write_stats.get('avgObjSize', 0),
                'indexes': write_stats.get('indexes', 0),
                'connection_type': 'primary_write',
                'source': 'real_primary_stats'
            }
            
            # Métricas do SECONDARY (se disponível)
            try:
                read_db = self.get_read_database()
                read_stats = read_db.command('dbStats')
                
                secondary_metrics = {
                    'users_count': read_db.users.count_documents({}) if 'users' in read_db.list_collection_names() else 0,
                    'videos_count': read_db.videos.count_documents({}) if 'videos' in read_db.list_collection_names() else 0,
                    'views_count': read_db.video_views.count_documents({}) if 'video_views' in read_db.list_collection_names() else 0,
                    'data_size_mb': round(read_stats.get('dataSize', 0) / (1024 * 1024), 2),
                    'collections': read_stats.get('collections', 0),
                    'objects': read_stats.get('objects', 0),
                    'read_preference': 'secondaryPreferred',
                    'connection_type': 'secondary_read',
                    'source': 'real_secondary_stats'
                }
                
            except Exception as e:
                logger.warning(f"Não foi possível obter métricas do secondary: {e}")
                secondary_metrics = {
                    'error': str(e),
                    'read_preference': 'primary_fallback',
                    'source': 'secondary_error'
                }
            
            return {
                'primary': primary_metrics,
                'secondary': secondary_metrics,
                'replica_set_name': self.config['replica_set'],
                'collection_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter métricas da base de dados: {e}")
            return {
                'primary': {'error': str(e), 'source': 'primary_error'},
                'secondary': {'error': str(e), 'source': 'secondary_error'},
                'replica_set_name': self.config['replica_set']
            }
    
    def _get_primary_host(self):
        """Obtém o host primary atual"""
        try:
            status = self.check_replica_set_status()
            return status.get('primary_name', 'unknown')
        except:
            return 'unknown'
    
    def get_connection_info(self):
        """Informações sobre as conexões ativas"""
        try:
            return {
                'replica_set': self.config['replica_set'],
                'database': self.config['database'],
                'hosts': self.hosts,
                'primary_host': self._get_primary_host(),
                'connection_string_used': self.connection_string.replace(self.config['password'], '***'),
                'client_connected': self.client is not None,
                'write_client_connected': self.write_client is not None,
                'read_client_connected': self.read_client is not None,
                'auth_source': self.config['auth_source']
            }
        except Exception as e:
            return {'error': str(e)}
    
    def create_indexes(self):
        """Cria índices na base de dados (usando primary)"""
        try:
            db = self.get_write_database()
            
            # Criar coleções se não existirem
            collections = db.list_collection_names()
            required_collections = ['users', 'videos', 'video_views', 'replication_test']
            
            for coll in required_collections:
                if coll not in collections:
                    db.create_collection(coll)
                    logger.info(f"📁 Coleção '{coll}' criada")
            
            # Criar índices
            try:
                # Users indexes
                db.users.create_index('username', unique=True)
                db.users.create_index('email', unique=True)
                db.users.create_index('created_at')
                db.users.create_index('is_admin')
                
                # Videos indexes
                db.videos.create_index('user_id')
                db.videos.create_index('status')
                db.videos.create_index('upload_date')
                db.videos.create_index('view_count')
                db.videos.create_index([('title', 'text'), ('description', 'text')])
                
                # Video views indexes
                db.video_views.create_index('video_id')
                db.video_views.create_index('user_id')
                db.video_views.create_index('view_date')
                
                # Replication test indexes
                db.replication_test.create_index('test_id')
                db.replication_test.create_index('write_time')
                
                logger.info("✅ Todos os índices criados com sucesso")
                
            except Exception as e:
                logger.warning(f"Alguns índices já existem: {e}")
                
        except Exception as e:
            logger.error(f"Erro ao criar índices: {e}")
    
    def init_collections(self):
        """Inicializa coleções com dados básicos (usando primary)"""
        try:
            db = self.get_write_database()
            
            # Verificar se admin já existe
            admin_exists = db.users.find_one({'username': 'admin'})
            if not admin_exists:
                from werkzeug.security import generate_password_hash
                
                admin_user = {
                    'username': 'admin',
                    'email': 'admin@ualflix.com',
                    'password': generate_password_hash('admin'),
                    'is_admin': True,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                result = db.users.insert_one(admin_user)
                logger.info(f"✅ Utilizador admin criado: {result.inserted_id}")
            else:
                logger.info("ℹ️ Utilizador admin já existe")
            
            # Criar utilizador de teste se não existir
            test_user_exists = db.users.find_one({'username': 'testuser'})
            if not test_user_exists:
                from werkzeug.security import generate_password_hash
                
                test_user = {
                    'username': 'testuser',
                    'email': 'testuser@ualflix.com',
                    'password': generate_password_hash('testpass'),
                    'is_admin': False,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                result = db.users.insert_one(test_user)
                logger.info(f"✅ Utilizador teste criado: {result.inserted_id}")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar coleções: {e}")
    
    def test_replica_set_operations(self):
        """Teste completo das operações do replica set"""
        try:
            logger.info("🧪 Iniciando teste completo do replica set...")
            
            # 1. Verificar status
            status = self.check_replica_set_status()
            logger.info(f"   Status: {status.get('status')}")
            logger.info(f"   Primary: {status.get('primary_name')}")
            logger.info(f"   Membros saudáveis: {status.get('healthy_members')}/{status.get('total_members')}")
            
            # 2. Teste de replicação
            replication = self.test_replication_lag()
            logger.info(f"   Replicação funcionando: {replication.get('replication_working')}")
            if replication.get('replication_working'):
                logger.info(f"   Lag de replicação: {replication.get('lag_seconds'):.3f}s")
            
            # 3. Teste de escrita/leitura
            write_db = self.get_write_database()
            read_db = self.get_read_database()
            
            test_doc = {
                'test_id': f"operation_test_{int(time.time())}",
                'timestamp': datetime.utcnow(),
                'operation': 'replica_set_test'
            }
            
            # Escrever
            write_result = write_db.replication_test.insert_one(test_doc)
            logger.info(f"   Escrita no primary: {write_result.inserted_id}")
            
            # Aguardar e ler
            time.sleep(1)
            read_result = read_db.replication_test.find_one({'_id': write_result.inserted_id})
            
            if read_result:
                logger.info("   ✅ Leitura do secondary: Sucesso")
            else:
                logger.warning("   ⚠️ Leitura do secondary: Falhou")
            
            # Limpar
            write_db.replication_test.delete_one({'_id': write_result.inserted_id})
            
            # 4. Métricas
            metrics = self.get_database_metrics()
            logger.info(f"   Métricas primary: {metrics['primary'].get('source')}")
            logger.info(f"   Métricas secondary: {metrics['secondary'].get('source')}")
            
            logger.info("🎉 Teste do replica set concluído!")
            
            return {
                'status': 'success',
                'replica_set_status': status,
                'replication_test': replication,
                'write_test': 'success',
                'read_test': 'success' if read_result else 'failed',
                'metrics_test': 'success'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no teste do replica set: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

# Singleton
_mongodb_manager = None

def get_mongodb_manager():
    """Retorna instância singleton do MongoDB Manager"""
    global _mongodb_manager
    if _mongodb_manager is None:
        _mongodb_manager = MongoDBManager()
    return _mongodb_manager

def with_write_db(func):
    """Decorator para operações de ESCRITA (primary)"""
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
    """Decorator para operações de LEITURA (secondary preferred)"""
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