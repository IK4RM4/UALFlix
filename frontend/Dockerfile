FROM node:18
WORKDIR /app
COPY package*.json ./

# Instalar dependências
RUN npm install

COPY . .
RUN npm run build
RUN npm install -g serve

# Comando para iniciar a aplicação
CMD ["serve", "-s", "build", "-l", "3000"]