// Aguardar instâncias ficarem prontas
sleep(15000);

try {
    // Configuração do replica set
    var config = {
        _id: "ualflix-replica-set",
        members: [
            { _id: 0, host: "ualflix_db_primary:27017", priority: 2 },
            { _id: 1, host: "ualflix_db_secondary:27017", priority: 1 },
            { _id: 2, host: "ualflix_db_arbiter:27017", arbiterOnly: true }
        ]
    };
    
    print("🔧 Inicializando replica set...");
    var result = rs.initiate(config);
    print("Resultado:", JSON.stringify(result));
    
    // Aguardar eleição do primary
    sleep(10000);
    
    // Criar utilizadores após replica set estar ativo
    print("👤 Criando utilizadores...");
    
    db = db.getSiblingDB('admin');
    try {
        db.createUser({
            user: "admin",
            pwd: "password",
            roles: [{ role: "root", db: "admin" }]
        });
        print(" Utilizador admin criado");
    } catch (e) {
        print("Utilizador admin já existe");
    }
    
    // Configurar base de dados da aplicação
    db = db.getSiblingDB('ualflix');
    
    db.createCollection('users');
    db.createCollection('videos');
    db.createCollection('video_views');
    db.createCollection('replication_test');
    
    // Criar índices
    db.users.createIndex({ "username": 1 }, { unique: true });
    db.users.createIndex({ "email": 1 }, { unique: true });
    db.videos.createIndex({ "user_id": 1 });
    db.videos.createIndex({ "status": 1 });
    
    print(" UALFlix MongoDB Replica Set configurado com sucesso!");
    
} catch (error) {
    print("Erro:", error.message);
    throw error;
}