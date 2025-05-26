#!/usr/bin/env python3
"""
Database Connection Manager - Catalog Service
Suporte para replicação Master-Slave PostgreSQL

FUNCIONALIDADE 5: Estratégias de Replicação de Dados
- Master: Operações de escrita (INSERT, UPDATE, DELETE)
- Slave: Operações de leitura (SELECT)
- Failover automático em caso de falha
"""

import psycopg2
import psycopg2.pool
import os
import logging
import time
from functools import wraps

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================================================
# CONFIGURAÇÕES DE CONEXÃO
# ================================================================

# Configuração Master (escritas)
MASTER_CONFIG = {
    'host': os.environ.get('DB_MASTER_HOST', 'ualflix_db_master'),
    'port': int(os.environ.get('DB_MASTER_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'ualflix'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
    'sslmode': 'prefer'
}

# Configuração Slave (leituras)
SLAVE_CONFIG = {
    'host': os.environ.get('DB_SLAVE_HOST', 'ualflix_db_slave'),
    'port': int(os.environ.get('DB_SLAVE_PORT', '5432')),
    'database': os.environ.get('DB_NAME', 'ualflix'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
    'sslmode': 'prefer'
}

# Pool de conexões
master_pool = None
slave_pool = None

def init_connection_pools():
    """Inicializar pools de conexão"""
    global master_pool, slave_pool
    
    try:
        # Pool para Master (escritas)
        master_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            **MASTER_CONFIG
        )
        logger.info("✅ Pool Master inicializado")
        
        # Pool para Slave (leituras)
        slave_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,  # Mais conexões para leituras
            **SLAVE_CONFIG
        )
        logger.info("✅ Pool Slave inicializado")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar pools: {e}")
        # Fallback: usar apenas master
        if not master_pool:
            master_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=15,
                **MASTER_CONFIG
            )
        slave_pool = master_pool
        logger.warning("⚠️ Usando apenas Master (modo fallback)")

def get_db_connection(readonly=False, retries=3):
    """
    Obter conexão com a base de dados
    
    Args:
        readonly (bool): True para operações de leitura (usa slave)
        retries (int): Número de tentativas em caso de falha
    
    Returns:
        psycopg2.connection: Conexão com a base de dados
    """
    global master_pool, slave_pool
    
    # Inicializar pools se necessário
    if not master_pool or not slave_pool:
        init_connection_pools()
    
    for attempt in range(retries):
        try:
            if readonly and slave_pool != master_pool:
                # Usar slave para leituras
                conn = slave_pool.getconn()
                if conn:
                    # Verificar se a conexão está válida
                    conn.set_session(readonly=True, autocommit=True)
                    logger.debug("🔵 Conexão obtida: SLAVE (readonly)")
                    return conn
                else:
                    logger.warning("⚠️ Slave pool esgotado, tentando master...")
                    raise Exception("Slave pool exhausted")
            
            # Usar master para escritas ou como fallback
            conn = master_pool.getconn()
            if conn:
                conn.set_session(readonly=readonly, autocommit=False)
                logger.debug(f"🔴 Conexão obtida: MASTER ({'readonly' if readonly else 'read/write'})")
                return conn
            else:
                raise Exception("Master pool exhausted")
                
        except Exception as e:
            logger.warning(f"Tentativa {attempt + 1}/{retries} falhou: {e}")
            if attempt == retries - 1:
                # Última tentativa: tentar conexão direta
                try:
                    config = SLAVE_CONFIG if readonly else MASTER_CONFIG
                    conn = psycopg2.connect(**config)
                    logger.info(f"✅ Conexão direta estabelecida ({'SLAVE' if readonly else 'MASTER'})")
                    return conn
                except Exception as direct_error:
                    logger.error(f"❌ Falha na conexão direta: {direct_error}")
                    raise
            
            time.sleep(0.5 * (attempt + 1))  # Backoff exponencial
    
    raise Exception("Não foi possível estabelecer conexão com a base de dados")

def return_db_connection(conn, readonly=False):
    """
    Retornar conexão para o pool
    
    Args:
        conn: Conexão a ser retornada
        readonly (bool): Se a conexão era readonly
    """
    global master_pool, slave_pool
    
    try:
        if readonly and slave_pool != master_pool:
            slave_pool.putconn(conn)
        else:
            master_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Erro ao retornar conexão: {e}")

def get_read_connection():
    """Obter conexão específica para leitura (slave)"""
    return get_db_connection(readonly=True)

def get_write_connection():
    """Obter conexão específica para escrita (master)"""
    return get_db_connection(readonly=False)

def check_db_connection():
    """Verificar conectividade com ambas as bases de dados"""
    status = {
        'master': False,
        'slave': False,
        'error': None
    }
    
    # Testar Master
    try:
        conn = get_write_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        return_db_connection(conn, readonly=False)
        status['master'] = True
        logger.info("✅ Master conectado")
    except Exception as e:
        status['error'] = f"Master: {str(e)}"
        logger.error(f"❌ Erro Master: {e}")
    
    # Testar Slave
    try:
        conn = get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        return_db_connection(conn, readonly=True)
        status['slave'] = True
        logger.info("✅ Slave conectado")
    except Exception as e:
        if not status['error']:
            status['error'] = f"Slave: {str(e)}"
        logger.error(f"❌ Erro Slave: {e}")
    
    return status['master'] or status['slave'], status

# ================================================================
# DECORATORS PARA GESTÃO DE CONEXÕES
# ================================================================

def with_db_connection(readonly=False):
    """
    Decorator para gestão automática de conexões
    
    Args:
        readonly (bool): True para operações de leitura
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            conn = None
            try:
                conn = get_db_connection(readonly=readonly)
                result = func(conn, *args, **kwargs)
                if not readonly:
                    conn.commit()
                return result
            except Exception as e:
                if conn and not readonly:
                    conn.rollback()
                logger.error(f"Erro na função {func.__name__}: {e}")
                raise
            finally:
                if conn:
                    return_db_connection(conn, readonly=readonly)
        return wrapper
    return decorator

def with_read_connection(func):
    """Decorator para conexões de leitura (slave)"""
    return with_db_connection(readonly=True)(func)

def with_write_connection(func):
    """Decorator para conexões de escrita (master)"""
    return with_db_connection(readonly=False)(func)

# ================================================================
# FUNÇÕES DE CONVENIÊNCIA
# ================================================================

@with_read_connection
def execute_read_query(conn, query, params=None):
    """
    Executar query de leitura no slave
    
    Args:
        query (str): SQL query
        params (tuple): Parâmetros da query
    
    Returns:
        list: Resultados da query
    """
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    results = cursor.fetchall()
    cursor.close()
    return results

@with_write_connection  
def execute_write_query(conn, query, params=None):
    """
    Executar query de escrita no master
    
    Args:
        query (str): SQL query
        params (tuple): Parâmetros da query
    
    Returns:
        int: ID do registro inserido (se aplicável)
    """
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    
    # Tentar obter ID inserido
    try:
        if cursor.description:
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
    except:
        pass
    
    cursor.close()
    return cursor.rowcount

@with_read_connection
def get_table_count(conn, table_name):
    """Obter contagem de registros de uma tabela (slave)"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_replication_status():
    """Obter status de replicação"""
    status = {}
    
    # Status do Master
    try:
        conn = get_write_connection()
        cursor = conn.cursor()
        
        # Verificar se é master
        cursor.execute("SELECT pg_is_in_recovery();")
        is_master = not cursor.fetchone()[0]
        
        # Obter informações de réplicas
        cursor.execute("""
            SELECT 
                application_name,
                client_addr,
                state,
                sync_state
            FROM pg_stat_replication;
        """)
        
        replicas = cursor.fetchall()
        
        status['master'] = {
            'is_master': is_master,
            'replicas_count': len(replicas),
            'replicas': [
                {
                    'name': r[0],
                    'ip': str(r[1]) if r[1] else None,
                    'state': r[2],
                    'sync': r[3]
                } for r in replicas
            ]
        }
        
        cursor.close()
        return_db_connection(conn, readonly=False)
        
    except Exception as e:
        status['master'] = {'error': str(e)}
    
    # Status do Slave
    try:
        conn = get_read_connection()
        cursor = conn.cursor()
        
        # Verificar se é slave
        cursor.execute("SELECT pg_is_in_recovery();")
        is_slave = cursor.fetchone()[0]
        
        # Informações do WAL receiver
        cursor.execute("""
            SELECT 
                status,
                last_msg_receipt_time
            FROM pg_stat_wal_receiver;
        """)
        
        wal_info = cursor.fetchone()
        
        status['slave'] = {
            'is_slave': is_slave,
            'wal_status': wal_info[0] if wal_info else None,
            'last_message': str(wal_info[1]) if wal_info and wal_info[1] else None
        }
        
        cursor.close()
        return_db_connection(conn, readonly=True)
        
    except Exception as e:
        status['slave'] = {'error': str(e)}
    
    return status

# ================================================================
# INICIALIZAÇÃO
# ================================================================

# Inicializar pools na importação do módulo
try:
    init_connection_pools()
except Exception as e:
    logger.error(f"Erro na inicialização do módulo db.py: {e}")

# Para compatibilidade com código existente
def get_db_connection_legacy():
    """Função legacy para compatibilidade"""
    logger.warning("⚠️ Usando função legacy get_db_connection()")
    return get_write_connection()
