#!/bin/bash
# Script para iniciar a replicação do PostgreSQL

set -e

# Configurações
MASTER_HOST="ualflix_db_master"
MASTER_PORT="5432"
MASTER_USER="postgres"
MASTER_PASSWORD="password"
MASTER_DB="ualflix"
REPLICA_USER="postgres"
REPLICA_PASSWORD="password"

# Caminho para os dados do PostgreSQL
PG_DATA="/var/lib/postgresql/data"

# Verifica se o diretório de dados já está configurado
if [ -f "$PG_DATA/standby.signal" ]; then
    echo "Este servidor já está configurado como replica."
    exit 0
fi

# Limpa o diretório de dados
rm -rf $PG_DATA/*

# Executa pg_basebackup para criar uma cópia do master
echo "Executando backup inicial do master..."
pg_basebackup -h $MASTER_HOST -p $MASTER_PORT -U $REPLICA_USER -D $PG_DATA -P -v -R

# Cria arquivo de configuração de standby
# Indica que este é um servidor standby


# Configura postgresql.conf para replicação
# Configurações de replicação
primary_conninfo = 'host=$MASTER_HOST port=$MASTER_PORT user=$REPLICA_USER password=$REPLICA_PASSWORD'
hot_standby = on


# Cria arquivo pg_hba.conf para permitir a replicação

# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                trust
host    all             postgres        127.0.0.1/32            md5
host    all             postgres        ::1/128                 md5
host    all             all             0.0.0.0/0               md5
host    replication     postgres        0.0.0.0/0               md5


# Ajusta permissões
chown -R postgres:postgres $PG_DATA
chmod 700 $PG_DATA

echo "Configuração de replicação concluída. O servidor está configurado como replica."