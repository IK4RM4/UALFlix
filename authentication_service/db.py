#!/usr/bin/env python3
"""
Database Connection Manager - Authentication Service
Suporte para replicação Master-Slave PostgreSQL

FUNCIONALIDADE 5: Estratégias de Replicação de Dados
- Master: Operações de escrita (registro, atualizações de perfil)
- Slave: Operações de leitura (login, validação de sessão)
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
            maxconn=8,  # Menos conexões que catalog (menos escritas)
            **MASTER_CONFIG
        )
        logger.info("✅ Pool Master inicializado (Auth Service)")
        
        # Pool para Slave (leituras)
        slave_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=15,  # Mais conexões para validações/logins
            **SLAVE_CONFIG
        )
        logger.info("✅ Pool Slave inicializado (Auth Service)")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar pools: {e}")
        # Fallback: usar apenas master
        if not master_pool:
            master_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
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
                # Usar slave para leituras (login, validação)
                conn = slave_pool.getconn()
                if conn:
                    conn.set_session(readonly=True, autocommit=True)
                    logger.debug("🔵 Conexão obtida: SLAVE (readonly) - Auth")
                    return conn
                else:
                    logger.warning("⚠️ Slave pool esgotado, tentando master...")
                    raise Exception("Slave pool exhausted")
            
            # Usar master para escritas (registro, updates) ou como fallback
            conn = master_pool.getconn()
            if conn:
                conn.set_session(readonly=readonly, autocommit=False)
                logger.debug(f"🔴 Conexão obtida: MASTER ({'readonly' if readonly else 'read/write'}) - Auth")
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
                    logger.info(f"✅ Conexão direta estabelecida ({'SLAVE' if readonly else 'MASTER'}) - Auth")
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
    """Obter conexão específica para leitura (slave) - Login/Validação"""
    return get_db_connection(readonly=True)

def get_write_connection():
    """Obter conexão específica para escrita (master) - Registro/Updates"""
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
        logger.info("✅ Master conectado (Auth)")
    except Exception as e:
        status['error'] = f"Master: {str(e)}"
        logger.error(f"❌ Erro Master (Auth): {e}")
    
    # Testar Slave
    try:
        conn = get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        return_db_connection(conn, readonly=True)
        status['slave'] = True
        logger.info("✅ Slave conectado (Auth)")
    except Exception as e:
        if not status['error']:
            status['error'] = f"Slave: {str(e)}"
        logger.error(f"❌ Erro Slave (Auth): {e}")
    
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
    """Decorator para conexões de leitura (slave) - Login/Validação"""
    return with_db_connection(readonly=True)(func)

def with_write_connection(func):
    """Decorator para conexões de escrita (master) - Registro/Updates"""
    return with_db_connection(readonly=False)(func)

# ================================================================
# FUNÇÕES ESPECÍFICAS DE AUTENTICAÇÃO
# ================================================================

@with_read_connection
def get_user_by_username(conn, username):
    """
    Obter utilizador por username (operação de leitura - usa slave)
    
    Args:
        username (str): Nome de utilizador
    
    Returns:
        dict: Dados do utilizador ou None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, password, is_admin, created_at, updated_at
        FROM users 
        WHERE username = %s;
    """, (username,))
    
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password': result[3],
            'is_admin': result[4],
            'created_at': result[5],
            'updated_at': result[6]
        }
    return None

@with_read_connection
def get_user_by_email(conn, email):
    """
    Obter utilizador por email (operação de leitura - usa slave)
    
    Args:
        email (str): Email do utilizador
    
    Returns:
        dict: Dados do utilizador ou None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, password, is_admin, created_at, updated_at
        FROM users 
        WHERE email = %s;
    """, (email,))
    
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password': result[3],
            'is_admin': result[4],
            'created_at': result[5],
            'updated_at': result[6]
        }
    return None

@with_read_connection
def get_user_by_id(conn, user_id):
    """
    Obter utilizador por ID (operação de leitura - usa slave)
    
    Args:
        user_id (int): ID do utilizador
    
    Returns:
        dict: Dados do utilizador ou None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, password, is_admin, created_at, updated_at
        FROM users 
        WHERE id = %s;
    """, (user_id,))
    
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password': result[3],
            'is_admin': result[4],
            'created_at': result[5],
            'updated_at': result[6]
        }
    return None

@with_write_connection
def create_user(conn, username, email, password_hash, is_admin=False):
    """
    Criar novo utilizador (operação de escrita - usa master)
    
    Args:
        username (str): Nome de utilizador
        email (str): Email
        password_hash (str): Hash da password
        is_admin (bool): Se é administrador
    
    Returns:
        int: ID do utilizador criado
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (username, email, password, is_admin)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """, (username, email, password_hash, is_admin))
    
    user_id = cursor.fetchone()[0]
    cursor.close()
    
    logger.info(f"✅ Utilizador criado: {username} (ID: {user_id}) - Master DB")
    return user_id

@with_write_connection
def update_user_password(conn, user_id, new_password_hash):
    """
    Atualizar password do utilizador (operação de escrita - usa master)
    
    Args:
        user_id (int): ID do utilizador
        new_password_hash (str): Nova hash da password
    
    Returns:
        bool: True se atualizado com sucesso
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET password = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s;
    """, (new_password_hash, user_id))
    
    rows_affected = cursor.rowcount
    cursor.close()
    
    success = rows_affected > 0
    if success:
        logger.info(f"✅ Password atualizada para user ID: {user_id} - Master DB")
    
    return success

@with_write_connection
def update_user_email(conn, user_id, new_email):
    """
    Atualizar email do utilizador (operação de escrita - usa master)
    
    Args:
        user_id (int): ID do utilizador
        new_email (str): Novo email
    
    Returns:
        bool: True se atualizado com sucesso
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET email = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s;
    """, (new_email, user_id))
    
    rows_affected = cursor.rowcount
    cursor.close()
    
    success = rows_affected > 0
    if success:
        logger.info(f"✅ Email atualizado para user ID: {user_id} - Master DB")
    
    return success

@with_read_connection
def check_username_exists(conn, username):
    """
    Verificar se username já existe (operação de leitura - usa slave)
    
    Args:
        username (str): Nome de utilizador
    
    Returns:
        bool: True se existe
    """
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = %s;", (username,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None

@with_read_connection
def check_email_exists(conn, email):
    """
    Verificar se email já existe (operação de leitura - usa slave)
    
    Args:
        email (str): Email
    
    Returns:
        bool: True se existe
    """
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE email = %s;", (email,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None

@with_read_connection
def get_user_count(conn):
    """Obter contagem total de utilizadores (slave)"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

@with_read_connection
def get_admin_count(conn):
    """Obter contagem de administradores (slave)"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = TRUE;")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_auth_stats():
    """Obter estatísticas de autenticação usando ambos os servidores"""
    stats = {}
    
    try:
        # Usar slave para estatísticas (leitura)
        stats['total_users'] = get_user_count()
        stats['admin_users'] = get_admin_count()
        stats['regular_users'] = stats['total_users'] - stats['admin_users']
        
        # Verificar saúde das conexões
        master_health, slave_health = check_db_connection()
        stats['db_health'] = {
            'master': master_health,
            'slave': slave_health
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        stats['error'] = str(e)
    
    return stats

# ================================================================
# INICIALIZAÇÃO
# ================================================================

# Inicializar pools na importação do módulo
try:
    init_connection_pools()
except Exception as e:
    logger.error(f"Erro na inicialização do módulo db.py (Auth): {e}")

# Para compatibilidade com código existente
def get_db_connection_legacy():
    """Função legacy para compatibilidade"""
    logger.warning("⚠️ Usando função legacy get_db_connection() - Auth Service")
    return get_write_connection()#!/usr/bin/env python3
"""
Database Connection Manager - Authentication Service
Suporte para replicação Master-Slave PostgreSQL

FUNCIONALIDADE 5: Estratégias de Replicação de Dados
- Master: Operações de escrita (registro, atualizações de perfil)
- Slave: Operações de leitura (login, validação de sessão)
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
            maxconn=8,  # Menos conexões que catalog (menos escritas)
            **MASTER_CONFIG
        )
        logger.info("✅ Pool Master inicializado (Auth Service)")
        
        # Pool para Slave (leituras)
        slave_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=15,  # Mais conexões para validações/logins
            **SLAVE_CONFIG
        )
        logger.info("✅ Pool Slave inicializado (Auth Service)")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar pools: {e}")
        # Fallback: usar apenas master
        if not master_pool:
            master_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
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
                # Usar slave para leituras (login, validação)
                conn = slave_pool.getconn()
                if conn:
                    conn.set_session(readonly=True, autocommit=True)
                    logger.debug("🔵 Conexão obtida: SLAVE (readonly) - Auth")
                    return conn
                else:
                    logger.warning("⚠️ Slave pool esgotado, tentando master...")
                    raise Exception("Slave pool exhausted")
            
            # Usar master para escritas (registro, updates) ou como fallback
            conn = master_pool.getconn()
            if conn:
                conn.set_session(readonly=readonly, autocommit=False)
                logger.debug(f"🔴 Conexão obtida: MASTER ({'readonly' if readonly else 'read/write'}) - Auth")
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
                    logger.info(f"✅ Conexão direta estabelecida ({'SLAVE' if readonly else 'MASTER'}) - Auth")
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
    """Obter conexão específica para leitura (slave) - Login/Validação"""
    return get_db_connection(readonly=True)

def get_write_connection():
    """Obter conexão específica para escrita (master) - Registro/Updates"""
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
        logger.info("✅ Master conectado (Auth)")
    except Exception as e:
        status['error'] = f"Master: {str(e)}"
        logger.error(f"❌ Erro Master (Auth): {e}")
    
    # Testar Slave
    try:
        conn = get_read_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        cursor.close()
        return_db_connection(conn, readonly=True)
        status['slave'] = True
        logger.info("✅ Slave conectado (Auth)")
    except Exception as e:
        if not status['error']:
            status['error'] = f"Slave: {str(e)}"
        logger.error(f"❌ Erro Slave (Auth): {e}")
    
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
    """Decorator para conexões de leitura (slave) - Login/Validação"""
    return with_db_connection(readonly=True)(func)

def with_write_connection(func):
    """Decorator para conexões de escrita (master) - Registro/Updates"""
    return with_db_connection(readonly=False)(func)

# ================================================================
# FUNÇÕES ESPECÍFICAS DE AUTENTICAÇÃO
# ================================================================

@with_read_connection
def get_user_by_username(conn, username):
    """
    Obter utilizador por username (operação de leitura - usa slave)
    
    Args:
        username (str): Nome de utilizador
    
    Returns:
        dict: Dados do utilizador ou None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, password, is_admin, created_at, updated_at
        FROM users 
        WHERE username = %s;
    """, (username,))
    
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password': result[3],
            'is_admin': result[4],
            'created_at': result[5],
            'updated_at': result[6]
        }
    return None

@with_read_connection
def get_user_by_email(conn, email):
    """
    Obter utilizador por email (operação de leitura - usa slave)
    
    Args:
        email (str): Email do utilizador
    
    Returns:
        dict: Dados do utilizador ou None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, password, is_admin, created_at, updated_at
        FROM users 
        WHERE email = %s;
    """, (email,))
    
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password': result[3],
            'is_admin': result[4],
            'created_at': result[5],
            'updated_at': result[6]
        }
    return None

@with_read_connection
def get_user_by_id(conn, user_id):
    """
    Obter utilizador por ID (operação de leitura - usa slave)
    
    Args:
        user_id (int): ID do utilizador
    
    Returns:
        dict: Dados do utilizador ou None
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, password, is_admin, created_at, updated_at
        FROM users 
        WHERE id = %s;
    """, (user_id,))
    
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password': result[3],
            'is_admin': result[4],
            'created_at': result[5],
            'updated_at': result[6]
        }
    return None

@with_write_connection
def create_user(conn, username, email, password_hash, is_admin=False):
    """
    Criar novo utilizador (operação de escrita - usa master)
    
    Args:
        username (str): Nome de utilizador
        email (str): Email
        password_hash (str): Hash da password
        is_admin (bool): Se é administrador
    
    Returns:
        int: ID do utilizador criado
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (username, email, password, is_admin)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """, (username, email, password_hash, is_admin))
    
    user_id = cursor.fetchone()[0]
    cursor.close()
    
    logger.info(f"✅ Utilizador criado: {username} (ID: {user_id}) - Master DB")
    return user_id

@with_write_connection
def update_user_password(conn, user_id, new_password_hash):
    """
    Atualizar password do utilizador (operação de escrita - usa master)
    
    Args:
        user_id (int): ID do utilizador
        new_password_hash (str): Nova hash da password
    
    Returns:
        bool: True se atualizado com sucesso
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET password = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s;
    """, (new_password_hash, user_id))
    
    rows_affected = cursor.rowcount
    cursor.close()
    
    success = rows_affected > 0
    if success:
        logger.info(f"✅ Password atualizada para user ID: {user_id} - Master DB")
    
    return success

@with_write_connection
def update_user_email(conn, user_id, new_email):
    """
    Atualizar email do utilizador (operação de escrita - usa master)
    
    Args:
        user_id (int): ID do utilizador
        new_email (str): Novo email
    
    Returns:
        bool: True se atualizado com sucesso
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET email = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s;
    """, (new_email, user_id))
    
    rows_affected = cursor.rowcount
    cursor.close()
    
    success = rows_affected > 0
    if success:
        logger.info(f"✅ Email atualizado para user ID: {user_id} - Master DB")
    
    return success

@with_read_connection
def check_username_exists(conn, username):
    """
    Verificar se username já existe (operação de leitura - usa slave)
    
    Args:
        username (str): Nome de utilizador
    
    Returns:
        bool: True se existe
    """
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = %s;", (username,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None

@with_read_connection
def check_email_exists(conn, email):
    """
    Verificar se email já existe (operação de leitura - usa slave)
    
    Args:
        email (str): Email
    
    Returns:
        bool: True se existe
    """
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE email = %s;", (email,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None

@with_read_connection
def get_user_count(conn):
    """Obter contagem total de utilizadores (slave)"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users;")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

@with_read_connection
def get_admin_count(conn):
    """Obter contagem de administradores (slave)"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = TRUE;")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_auth_stats():
    """Obter estatísticas de autenticação usando ambos os servidores"""
    stats = {}
    
    try:
        # Usar slave para estatísticas (leitura)
        stats['total_users'] = get_user_count()
        stats['admin_users'] = get_admin_count()
        stats['regular_users'] = stats['total_users'] - stats['admin_users']
        
        # Verificar saúde das conexões
        master_health, slave_health = check_db_connection()
        stats['db_health'] = {
            'master': master_health,
            'slave': slave_health
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        stats['error'] = str(e)
    
    return stats

# ================================================================
# INICIALIZAÇÃO
# ================================================================

# Inicializar pools na importação do módulo
try:
    init_connection_pools()
except Exception as e:
    logger.error(f"Erro na inicialização do módulo db.py (Auth): {e}")

# Para compatibilidade com código existente
def get_db_connection_legacy():
    """Função legacy para compatibilidade"""
    logger.warning("⚠️ Usando função legacy get_db_connection() - Auth Service")
    return get_write_connection()