#!/usr/bin/env python3
"""
Database Manager Service - Gestão de Replicação Master-Slave
"""

from flask import Flask, jsonify, request
import psycopg2
import logging
import time
import threading
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.master_config = {
            'host': 'ualflix_db_master',
            'port': 5432,
            'database': 'ualflix',
            'user': 'postgres',
            'password': 'password'
        }
        
        self.slave_config = {
            'host': 'ualflix_db_slave',
            'port': 5432,
            'database': 'ualflix',
            'user': 'postgres',
            'password': 'password'
        }
        
        self.loadbalancer_config = {
            'host': 'ualflix_db_loadbalancer',
            'port': 5432,
            'database': 'ualflix',
            'user': 'postgres',
            'password': 'password'
        }
        
    def get_connection(self, config, readonly=False):
        """Obter conexão com a base de dados"""
        try:
            conn = psycopg2.connect(**config)
            if readonly:
                conn.set_session(readonly=True)
            return conn
        except Exception as e:
            logger.error(f"Erro ao conectar à BD: {e}")
            return None
    
    def check_master_status(self):
        """Verificar status do master"""
        try:
            conn = self.get_connection(self.master_config)
            if not conn:
                return {"status": "error", "message": "Cannot connect to master"}
            
            cursor = conn.cursor()
            
            # Verificar se é master
            cursor.execute("SELECT pg_is_in_recovery();")
            is_in_recovery = cursor.fetchone()[0]
            
            # Obter informações de replicação
            cursor.execute("""
                SELECT 
                    application_name,
                    client_addr,
                    state,
                    sent_lsn,
                    write_lsn,
                    flush_lsn,
                    replay_lsn,
                    sync_state
                FROM pg_stat_replication;
            """)
            replication_info = cursor.fetchall()
            
            conn.close()
            
            return {
                "status": "active",
                "is_master": not is_in_recovery,
                "replication_slaves": len(replication_info),
                "slaves_info": [
                    {
                        "application_name": row[0],
                        "client_addr": str(row[1]) if row[1] else None,
                        "state": row[2],
                        "sync_state": row[7]
                    } for row in replication_info
                ]
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar master: {e}")
            return {"status": "error", "message": str(e)}
    
    def check_slave_status(self):
        """Verificar status do slave"""
        try:
            conn = self.get_connection(self.slave_config)
            if not conn:
                return {"status": "error", "message": "Cannot connect to slave"}
            
            cursor = conn.cursor()
            
            # Verificar se é slave
            cursor.execute("SELECT pg_is_in_recovery();")
            is_in_recovery = cursor.fetchone()[0]
            
            # Obter informações de WAL receiver
            cursor.execute("""
                SELECT 
                    status,
                    receive_start_lsn,
                    receive_start_tli,
                    received_lsn,
                    received_tli,
                    last_msg_send_time,
                    last_msg_receipt_time,
                    latest_end_lsn,
                    latest_end_time
                FROM pg_stat_wal_receiver;
            """)
            wal_receiver_info = cursor.fetchone()
            
            conn.close()
            
            return {
                "status": "active",
                "is_slave": is_in_recovery,
                "wal_receiver_status": wal_receiver_info[0] if wal_receiver_info else None,
                "last_received": str(wal_receiver_info[6]) if wal_receiver_info and wal_receiver_info[6] else None
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar slave: {e}")
            return {"status": "error", "message": str(e)}
    
    def test_replication_lag(self):
        """Testar lag de replicação"""
        try:
            # Inserir dados no master
            master_conn = self.get_connection(self.master_config)
            if not master_conn:
                return {"error": "Cannot connect to master"}
            
            cursor = master_conn.cursor()
            test_time = datetime.now()
            
            cursor.execute("""
                INSERT INTO replication_test (test_time, test_data) 
                VALUES (%s, %s) RETURNING id;
            """, (test_time, f"Test data {test_time}"))
            
            test_id = cursor.fetchone()[0]
            master_conn.commit()
            master_conn.close()
            
            # Aguardar um pouco para replicação
            time.sleep(2)
            
            # Verificar no slave
            slave_conn = self.get_connection(self.slave_config, readonly=True)
            if not slave_conn:
                return {"error": "Cannot connect to slave"}
            
            cursor = slave_conn.cursor()
            cursor.execute("""
                SELECT test_time, test_data 
                FROM replication_test 
                WHERE id = %s;
            """, (test_id,))
            
            result = cursor.fetchone()
            slave_conn.close()
            
            if result:
                lag_seconds = (datetime.now() - result[0]).total_seconds()
                return {
                    "replication_working": True,
                    "lag_seconds": lag_seconds,
                    "test_id": test_id
                }
            else:
                return {
                    "replication_working": False,
                    "message": "Data not found in slave"
                }
                
        except Exception as e:
            logger.error(f"Erro no teste de replicação: {e}")
            return {"error": str(e)}
    
    def get_database_metrics(self):
        """Obter métricas das bases de dados"""
        metrics = {}
        
        # Métricas do Master
        try:
            conn = self.get_connection(self.master_config)
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        (SELECT count(*) FROM videos) as total_videos,
                        (SELECT count(*) FROM users) as total_users,
                        (SELECT sum(view_count) FROM videos) as total_views;
                """)
                result = cursor.fetchone()
                metrics['master'] = {
                    'active_connections': result[0],
                    'total_videos': result[1],
                    'total_users': result[2],
                    'total_views': result[3]
                }
                conn.close()
        except Exception as e:
            logger.error(f"Erro métricas master: {e}")
            metrics['master'] = {"error": str(e)}
        
        # Métricas do Slave
        try:
            conn = self.get_connection(self.slave_config, readonly=True)
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        (SELECT count(*) FROM videos) as total_videos,
                        (SELECT count(*) FROM users) as total_users;
                """)
                result = cursor.fetchone()
                metrics['slave'] = {
                    'active_connections': result[0],
                    'total_videos': result[1],
                    'total_users': result[2]
                }
                conn.close()
        except Exception as e:
            logger.error(f"Erro métricas slave: {e}")
            metrics['slave'] = {"error": str(e)}
        
        return metrics

# Instância global
db_manager = DatabaseManager()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "service": "database_manager",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/status', methods=['GET'])
def get_status():
    """Obter status completo do sistema de BD"""
    master_status = db_manager.check_master_status()
    slave_status = db_manager.check_slave_status()
    metrics = db_manager.get_database_metrics()
    
    return jsonify({
        "master": master_status,
        "slave": slave_status,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/replication/test', methods=['POST'])
def test_replication():
    """Testar replicação entre master e slave"""
    result = db_manager.test_replication_lag()
    return jsonify(result)

@app.route('/failover/promote-slave', methods=['POST'])
def promote_slave():
    """Promover slave a master (simulação)"""
    try:
        # Em ambiente real, criaria arquivo trigger
        # touch /tmp/promote_to_master no container slave
        return jsonify({
            "message": "Slave promotion initiated",
            "note": "In production, this would trigger failover",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Criar tabela de teste de replicação
    try:
        conn = db_manager.get_connection(db_manager.master_config)
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS replication_test (
                    id SERIAL PRIMARY KEY,
                    test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    test_data TEXT
                );
            """)
            conn.commit()
            conn.close()
            logger.info("Tabela de teste de replicação criada")
    except Exception as e:
        logger.error(f"Erro ao criar tabela de teste: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)