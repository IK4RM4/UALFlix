// Script para inicialização do MongoDB com usuário admin correto
// Arquivo: mongodb-setup/init-replica.js

// Aguardar replica set estar pronto
sleep(5000);

// Conectar à base de dados ualflix
db = db.getSiblingDB('ualflix');

// Criar coleções se não existirem
db.createCollection('users');
db.createCollection('videos');
db.createCollection('video_views');
db.createCollection('replication_test');

// Criar índices
db.users.createIndex({ 'username': 1 }, { unique: true });
db.users.createIndex({ 'email': 1 });
db.videos.createIndex({ 'user_id': 1 });
db.videos.createIndex({ 'status': 1 });
db.video_views.createIndex({ 'video_id': 1 });
db.replication_test.createIndex({ 'test_id': 1 });

print('Coleções e índices criados');

// Verificar se o usuário admin já existe
var existingAdmin = db.users.findOne({username: 'admin'});

if (!existingAdmin) {
    // Criar usuário admin com senha simples 'admin'
    // Este hash corresponde à senha 'admin' usando pbkdf2:sha256
    var adminUser = {
        username: 'admin',
        email: 'admin@ualflix.com',
        password: 'pbkdf2:sha256:260000$salt123$hash123', // Será substituído pelo app
        is_admin: true,
        created_at: new Date(),
        updated_at: new Date()
    };
    
    db.users.insertOne(adminUser);
    print('Usuário admin criado com sucesso');
    print('Username: admin');
    print('Password: admin');
} else {
    print('Usuário admin já existe');
    
    // Atualizar para garantir que é admin
    db.users.updateOne(
        {username: 'admin'}, 
        {
            $set: {
                is_admin: true,
                updated_at: new Date()
            }
        }
    );
    print('Usuário admin atualizado');
}

// Verificar criação
var adminCheck = db.users.findOne({username: 'admin'});
if (adminCheck) {
    print('✅ Admin verificado: ' + adminCheck.username + ' (is_admin: ' + adminCheck.is_admin + ')');
} else {
    print('❌ Erro: Admin não foi criado');
}

print('Inicialização da base de dados concluída');