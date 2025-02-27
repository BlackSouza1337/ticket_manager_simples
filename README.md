# Gerenciador de Chamados Simples

Um sistema de gerenciamento de tickets (chamados) desenvolvido em Python e HTML, voltado para pequenas empresas que não possuem condições de adquirir uma plataforma de gerenciamento de chamados profissional. O sistema é simples, mas funcional, e permite a abertura de tickets normais e prioritários, com notificações por e-mail e gerenciamento de usuários.

## 🚀 Funcionalidades

- **Abertura de Tickets**:
  - Tickets normais e prioritários.
  - Níveis de prioridade para cada ticket.
- **Anexos**:
  - Possibilidade de adicionar arquivos aos tickets.
- **Notificações por E-mail**:
  - Envio de notificações ao abrir ou atualizar um ticket.
- **Gerenciamento de Usuários**:
  - Três níveis de acesso: Usuário comum, Admin e Diretoria.
  - Interface para gerenciar usuários (apenas Admin).
  - Alteração de senha pelo usuário.
- **Tickets Fechados**:
  - Aba específica para tickets resolvidos.

## 📂 Estrutura do Projeto
/static  
│── /img  
│   └── LOGO.PNG  
│── styles.css  

/templates  
│── alterar_senha.html  
│── editar_ticket_prioritario.html  
│── gerenciar_usuarios.html  
│── index.html  
│── login.html  
│── prioritario.html  
│── ticket.html  
│── ticket_prioritario.html  
│── tickets_resolvidos.html  
│── tickets_resolvidos_prioritario.html  

/uploads  

app.py  
database.db  
requirements.txt  



## ⚙️ Como Configurar

1. **Clone o repositório**:
   
   git clone https://github.com/BlackSouza1337/ticket_manager_simples/
   cd nome-do-repositorio

2. Instale as dependências:
    pip install -r requirements.txt

3. Configure o banco de dados
    O banco de dados SQLite (database.db) já está configurado. Se necessário, modifique as configurações no app.py.

4. Configure os e-mails:
    No arquivo app.py, defina as variáveis de ambiente para o e-mail de envio e recebimento.

5. Execute a aplicação
    python app.py

6. Acesse a aplicação:
    Abra o navegador e acesse http://localhost:5000.



👨‍💻 Como Usar
- Login: Acesse a página de login e insira suas credenciais.
- Abrir Ticket: Na página inicial, abra um novo ticket (normal ou prioritário).
- Gerenciar Tickets: Dependendo do seu cargo, você pode responder, finalizar ou mover tickets para a aba de tickets fechados.
- Gerenciar Usuários: Apenas o Admin pode gerenciar usuários.
- Alterar Senha: Cada usuário pode alterar sua própria senha.

🤝 Contribuição
**Contribuições são bem-vindas! Siga os passos abaixo:**
- Faça um fork do projeto.
- Crie uma branch para sua feature (git checkout -b feature/nova-feature).
- Commit suas mudanças (git commit -m 'Adicionando nova feature').
- Faça um push para a branch (git push origin feature/nova-feature).
- Abra um Pull Request.
