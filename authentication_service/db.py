#!/usr/bin/env python3
"""
Database Connection Manager - Authentication Service - CORRIGIDO
Connection Pool com configurações otimizadas
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

# Pool de conexões
master_pool = None

def init_connection_pools():
    """Inicializar pools de conexão - CORRIGIDO"""
    global master_pool
    
    try:
        # Pool mais conservador para evitar esgotamento
        master_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,   # CORRIGIDO: mínimo 2
            maxconn=5,   # CORRIGIDO: máximo 5 (era 8-15)
            **MASTER_CONFIG
        )
        logger.info("✅ Pool Master inicializado (Auth Service) - 5 conexões máx")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar pool: {e}")
        master_pool = None

def get_db_connection(readonly=False, retries=3):
    """
    Obter conexão com a base de dados - CORRIGIDO
    """
    global master_pool
    
    # Inicializar pool se necessário
    if not master_pool:
        init_connection_pools()
    
    for attempt in range(retries):
        try:
            if master_pool:
                conn = master_pool.getconn()
                if conn:
                    conn.set_session(autocommit=False)  # CORRIGIDO: autocommit sempre False
                    logger.debug("🔴 Conexão obtida: MASTER - Auth")
                    return conn
                else:
                    raise Exception("Pool exhausted")
            
            # Fallback: conexão direta
            conn = psycopg2.connect(**MASTER_CONFIG)
            logger.info("✅ Conexão direta estabelecida (MASTER) - Auth")
            return conn
                
        except Exception as e:
            logger.warning(f"Tentativa {attempt + 1}/{retries} falhou: {e}")
            if attempt == retries - 1:
                # Última tentativa: sempre conexão direta
                try:
                    conn = psycopg2.connect(**MASTER_CONFIG)
                    logger.info("✅ Conexão direta estabelecida (MASTER) - Auth")
                    return conn
                except Exception as direct_error:
                    logger.error(f"❌ Falha na conexão direta: {direct_error}")
                    raise
            
            time.sleep(1)  # CORRIGIDO: Wait mais longo
    
    raise Exception("Não foi possível estabelecer conexão com a base de dados")

def return_db_connection(conn):
    """
    Retornar conexão para o pool - CORRIGIDO
    """
    global master_pool
    
    try:
        if master_pool and conn:
            master_pool.putconn(conn)
            logger.debug("🔄 Conexão retornada ao pool")
    except Exception as e:
        logger.error(f"Erro ao retornar conexão: {e}")
        # Se falhar, fechar conexão diretamente
        try:
            conn.close()
        except:
            pass

def check_db_connection():
    """Verificar conectividade com a base de dados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        return_db_connection(conn)
        logger.info("✅ Database conectado (Auth)")
        return True, {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Erro Database (Auth): {e}")
        return False, {"error": str(e)}

# ================================================================
# DECORATORS PARA GESTÃO DE CONEXÕES - CORRIGIDO
# ================================================================

def with_db_connection(readonly=False):
    """
    Decorator para gestão automática de conexões - CORRIGIDO
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
                    try:
                        conn.rollback()
                    except:
                        pass
                logger.error(f"Erro na função {func.__name__}: {e}")
                raise
            finally:
                if conn:
                    return_db_connection(conn)
        return wrapper
    return decorator

# ================================================================
# INICIALIZAÇÃO
# ================================================================

# Inicializar pool na importação do módulo
try:
    init_connection_pools()
except Exception as e:
    logger.error(f"Erro na inicialização do módulo db.py (Auth): {e}")

# Para compatibilidade com código existente
def get_db_connection_legacy():
    """Função legacy para compatibilidade"""
    return get_db_connection(readonly=False)