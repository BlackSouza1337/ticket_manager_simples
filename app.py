from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


######################################################################################################################################################################
# Configurações do servidor SMTP
SMTP_SERVER = 'mail.mail.com'
SMTP_PORT = 000 
SMTP_USERNAME = 'Seu_Email@Email.com.br'
SMTP_PASSWORD = 'Senha do e-mail'
EMAIL_FROM = 'Seu_Email@Email.com.br'
EMAIL_TO = 'Email_destino@Email.com.br'

#Aqui é configurado e-mail por onde vai passar a notificação de tickets criados. É definido o e-mail padrão que será usado para enviar o chamado e o email destino seria o e-mail
# padrão de recebimento, por exemplo: O setor da TI tem um email padrão TI@dominioempresa.com.br, todo ticket que for aberto será enviado uma mensagem por e-mail ao e-mail padrão destino.
#                         
######################################################################################################################################################################

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Garante que a pasta de uploads exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Classe de usuário
class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role FROM usuarios WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

# Função para validar extensões de arquivos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Função para verificar se o arquivo existe
def file_exists(filename):
    if not filename:
        return False
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return os.path.isfile(file_path)

######################################################################################################################################################################

# Função para criar tabelas no banco de dados
def criar_banco():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # Criando tabela de usuários
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )''')

         # Criando tabela de tickets
        cursor.execute('''CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                setor TEXT NOT NULL,
                tipo_atendimento TEXT NOT NULL,
                descricao TEXT NOT NULL,
                ramal TEXT NOT NULL,
                anexo TEXT,
                status TEXT NOT NULL DEFAULT 'Aberto',
                prioridade TEXT NOT NULL DEFAULT 'Baixo',
                responsavel_id INTEGER,
                FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
            )''')

        # Criando tabela de tickets prioritários
        cursor.execute('''CREATE TABLE IF NOT EXISTS ticketsprioritario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                setor TEXT NOT NULL,
                tipo_atendimento TEXT NOT NULL,
                descricao TEXT NOT NULL,
                ramal TEXT NOT NULL,
                anexo TEXT,
                status TEXT NOT NULL DEFAULT 'Aberto',
                prioridade TEXT NOT NULL DEFAULT 'Baixo',
                responsavel_id INTEGER,
                FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
            )''')

        # Criando tabela de atualizações/respostas de tickets
        cursor.execute('''CREATE TABLE IF NOT EXISTS updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                update_text TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )''')
                
        # Criando tabela de atualizações/respostas de tickets prioritários
        cursor.execute('''CREATE TABLE IF NOT EXISTS updates_prioritario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                update_text TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES ticketsprioritario(id),
                FOREIGN KEY (user_id) REFERENCES usuarios(id)
            )''')

        # Criando usuário admin se não existir
        cursor.execute('SELECT id FROM usuarios WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            senha_hash = generate_password_hash('123')
            cursor.execute('INSERT INTO usuarios (username, password, email, role) VALUES (?, ?, ?, ?)', 
                           ('admin', senha_hash, 'EmailAdmin@Email.com', 'admin'))  # Adicione um e-mail padrão para o admin
            conn.commit()

    except sqlite3.Error as e:
        print(f'Erro ao criar o banco de dados: {str(e)}')
    finally:
        conn.close()


######################################################################################################################################################################

def enviar_email(assunto, mensagem, link=None, email_usuario=None):
    try:
        # Configuração do e-mail
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = email_usuario if email_usuario else EMAIL_TO
        msg['Subject'] = assunto

        # Corpo do e-mail
        if link:
            mensagem += f"\n\nClique aqui para acessar o ticket: {link}"
        msg.attach(MIMEText(mensagem, 'plain'))

        # Conexão com o servidor SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        
        # Envia e-mail para o usuário
        if email_usuario:
            server.sendmail(EMAIL_FROM, email_usuario, text)
        
        # Envia cópia para o e-mail do TI
        server.sendmail(EMAIL_FROM, EMAIL_TO, text)
        
        server.quit()
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

######################################################################################################################################################################

# Rota principal protegida
@app.route('/')
@login_required
def index():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tickets.*, usuarios.username as responsavel_nome
            FROM tickets
            LEFT JOIN usuarios ON tickets.responsavel_id = usuarios.id
            WHERE tickets.status != 'Fechado' 
            ORDER BY 
                CASE 
                    WHEN prioridade = 'Urgente' THEN 1
                    WHEN prioridade = 'Alto' THEN 2
                    WHEN prioridade = 'Médio' THEN 3
                    WHEN prioridade = 'Baixo' THEN 4
                END,
                id ASC
        ''')
        tickets = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()
    
    return render_template('index.html', tickets=tickets)

# Rota para assumir um ticket
@app.route('/assumir_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def assumir_ticket(ticket_id):
    if current_user.role != 'admin':
        flash('Acesso negado. Somente ADMINS podem assumir tickets.', 'error')
        return redirect(url_for('index'))

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE tickets SET responsavel_id = ? WHERE id = ?', (current_user.id, ticket_id))
        conn.commit()
        flash('Ticket assumido com sucesso!', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao assumir o ticket: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('index'))

# Rota para assumir um ticket prioritário
@app.route('/assumir_ticket_prioritario/<int:ticket_id>', methods=['POST'])
@login_required
def assumir_ticket_prioritario(ticket_id):
    if current_user.role != 'admin':
        flash('Acesso negado. Somente ADMINS podem assumir tickets prioritários.', 'error')
        return redirect(url_for('prioritario'))

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE ticketsprioritario SET responsavel_id = ? WHERE id = ?', (current_user.id, ticket_id))
        conn.commit()
        flash('Ticket prioritário assumido com sucesso!', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao assumir o ticket prioritário: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('prioritario'))

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id, password, role FROM usuarios WHERE username = ?', (username,))
            user = cursor.fetchone()
        except sqlite3.Error as e:
            flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
            return redirect(url_for('login'))
        finally:
            conn.close()

        if user and check_password_hash(user[1], password):
            login_user(User(user[0], username, user[2]))
            flash('Login realizado com sucesso!', 'success')

            # Redirecionar com base no papel do usuário
            if user[2] == 'DIRETORIA':
                return redirect(url_for('prioritario'))  # Redireciona para a página de tickets prioritários
            else:
                return redirect(url_for('index'))  # Redireciona para a página inicial
        else:
            flash('Usuário ou senha incorretos.', 'error')

    return render_template('login.html')

# Rota de logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

@app.route('/alterar_senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    if request.method == 'POST':
        nova_senha = request.form['nova_senha']
        confirmar_senha = request.form['confirmar_senha']

        if nova_senha != confirmar_senha:
            flash('As senhas não coincidem. Tente novamente.', 'error')
            return redirect(url_for('alterar_senha'))

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            senha_hash = generate_password_hash(nova_senha)
            cursor.execute('UPDATE usuarios SET password = ? WHERE id = ?', (senha_hash, current_user.id))
            conn.commit()
            flash('Senha alterada com sucesso!', 'success')
        except sqlite3.Error as e:
            flash(f'Erro ao atualizar a senha: {str(e)}', 'error')
        finally:
            conn.close()

        return redirect(url_for('index'))

    return render_template('alterar_senha.html')

# Rota para abrir um novo ticket
@app.route('/abrir_ticket')
@login_required
def abrir_ticket():
    origem = request.args.get('origem', 'index')  # Default para 'index' se não houver origem
    if origem == 'prioritario':
        return render_template('ticket_prioritario.html')
    else:
        return render_template('ticket.html')

# Rota para salvar um novo ticket
@app.route('/salvar_ticket', methods=['POST'])
@login_required
def salvar_ticket():
    usuario = current_user.username
    setor = request.form.get('setor')
    tipo_atendimento = request.form.get('tipo_atendimento')
    descricao = request.form.get('descricao')
    ramal = request.form.get('ramal')
    anexo = request.files.get('anexo')
    prioridade = request.form.get('prioridade', 'Baixo')  # Captura a prioridade
    origem = request.form.get('origem', 'index')  # Captura a origem do formulário

    # Validação dos campos obrigatórios
    if not setor or not tipo_atendimento or not descricao or not ramal:
        flash('Todos os campos obrigatórios devem ser preenchidos.', 'error')
        return redirect(url_for('abrir_ticket', origem=origem))  # Redireciona de volta com a origem

    # Processamento do anexo
    anexo_path = None
    if anexo and allowed_file(anexo.filename):
        filename = secure_filename(anexo.filename)
        anexo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        anexo.save(anexo_path)
        # Salvar apenas o nome do arquivo no banco de dados
        anexo_path = filename  

    # Inserção do ticket no banco de dados
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Verifica se o setor é prioritário
        if setor == 'Prioritário':
            cursor.execute('''
                INSERT INTO ticketsprioritario (usuario, setor, tipo_atendimento, descricao, ramal, anexo, status, prioridade)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (usuario, setor, tipo_atendimento, descricao, ramal, anexo_path, 'Aberto', prioridade))
        else:
            cursor.execute('''
                INSERT INTO tickets (usuario, setor, tipo_atendimento, descricao, ramal, anexo, status, prioridade)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (usuario, setor, tipo_atendimento, descricao, ramal, anexo_path, 'Aberto', prioridade))
        conn.commit()

        # Obter o ID do ticket recém-criado
        ticket_id = cursor.lastrowid

        # Gerar o link para o ticket
        if setor == 'Prioritário':
            link = url_for('editar_ticket_prioritario', id=ticket_id, _external=True)
        else:
            link = url_for('editar_ticket', id=ticket_id, _external=True)

        # Buscar o e-mail do usuário que criou o ticket
        cursor.execute('SELECT email FROM usuarios WHERE username = ?', (usuario,))
        email_usuario = cursor.fetchone()[0]

        assunto = f"Novo Ticket Aberto por {usuario}"
        mensagem = f"""
        Um novo ticket foi aberto:
        Usuário: {usuario}
        Setor: {setor}
        Tipo de Atendimento: {tipo_atendimento}
        Descrição: {descricao}
        Ramal: {ramal}
        Prioridade: {prioridade}
        """
        enviar_email(assunto, mensagem, link, email_usuario)

    except sqlite3.Error as e:
        flash(f'Erro ao salvar o ticket: {str(e)}', 'error')
        return redirect(url_for('abrir_ticket', origem=origem))  # Redireciona de volta com a origem
    finally:
        conn.close()

    flash('Ticket aberto com sucesso!', 'success')

    # Redireciona para a página correta com base na origem
    if origem == 'prioritario':
        return redirect(url_for('prioritario'))
    else:
        return redirect(url_for('index'))

# Rota para editar/responder um ticket existente
@app.route('/editar_ticket/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_ticket(id):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Verificar se o ticket existe
        cursor.execute('SELECT * FROM tickets WHERE id = ?', (id,))
        ticket = cursor.fetchone()
        if not ticket:
            flash('Ticket não encontrado.', 'error')
            return redirect(url_for('index'))
        
        # Buscar ticket
        cursor.execute('SELECT * FROM tickets WHERE id = ?', (id,))
        ticket = cursor.fetchone()

        if not ticket:
            flash('Ticket não encontrado.', 'error')
            return redirect(url_for('index'))

        # Verificar permissões
        if current_user.username != ticket[1] and current_user.role not in ['admin', 'user']:
            flash('Acesso negado. Você não tem permissão para editar este ticket.', 'error')
            return redirect(url_for('index'))
            

        # Buscar atualizações/respostas do ticket com o nome do usuário
        cursor.execute('''
            SELECT updates.id, updates.ticket_id, updates.user_id, updates.update_text, updates.date, usuarios.username
            FROM updates
            JOIN usuarios ON updates.user_id = usuarios.id
            WHERE updates.ticket_id = ?
            ORDER BY updates.date ASC
        ''', (id,))
        updates = cursor.fetchall()

        if request.method == 'POST':
            # Se for uma resposta, adiciona à tabela de atualizações
            resposta = request.form.get('resposta')
            novo_status = request.form.get('status')
            nova_prioridade = request.form.get('prioridade') if current_user.role == 'admin' else None

            if resposta:
                cursor.execute('INSERT INTO updates (ticket_id, user_id, update_text, date) VALUES (?, ?, ?, ?)',
                               (id, current_user.id, resposta, datetime.now()))
                flash('Resposta adicionada com sucesso!', 'success')

            if novo_status:
                cursor.execute('UPDATE tickets SET status = ? WHERE id = ?', (novo_status, id))
                flash('Status atualizado com sucesso!', 'success')

                # Se o status for "Fechado", redireciona para a página de tickets resolvidos
                if novo_status == 'Fechado':
                    conn.commit()
                    return redirect(url_for('tickets_resolvidos'))

            if nova_prioridade:
                cursor.execute('UPDATE tickets SET prioridade = ? WHERE id = ?', (nova_prioridade, id))
                flash('Prioridade atualizada com sucesso!', 'success')

            # Enviar e-mail de atualização
            cursor.execute('SELECT email FROM usuarios WHERE username = ?', (ticket[1],))
            email_usuario = cursor.fetchone()[0]

            assunto = f"Ticket Atualizado: {ticket[0]}"
            mensagem = f"""
            O ticket {ticket[0]} foi atualizado:
            Status: {novo_status if novo_status else ticket[7]}
            Prioridade: {nova_prioridade if nova_prioridade else ticket[8]}
            Resposta: {resposta if resposta else "Nenhuma resposta adicionada."}
            """
            enviar_email(assunto, mensagem, email_usuario=email_usuario)

            conn.commit()
    except sqlite3.Error as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()
    
    # Verificar se o arquivo existe
    file_exists_flag = file_exists(ticket[6]) if ticket[6] else False
    
    return render_template('ticket.html', ticket=ticket, updates=updates, file_exists=file_exists_flag)

# Rota para editar/responder um ticket prioritário
@app.route('/editar_ticket_prioritario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_ticket_prioritario(id):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Buscar ticket da tabela ticketsprioritario
        cursor.execute('SELECT * FROM ticketsprioritario WHERE id = ?', (id,))
        ticket = cursor.fetchone()

        if not ticket:
            flash('Ticket não encontrado.', 'error')
            return redirect(url_for('prioritario'))

        # Verificar permissões
        if current_user.username != ticket[1] and current_user.role not in ['admin', 'diretoria']:
            flash('Acesso negado. Você não tem permissão para editar este ticket.', 'error')
            return redirect(url_for('prioritario'))

        # Buscar atualizações/respostas do ticket com o nome do usuário
        cursor.execute('''
            SELECT updates_prioritario.id, updates_prioritario.ticket_id, updates_prioritario.user_id, updates_prioritario.update_text, updates_prioritario.date, usuarios.username
            FROM updates_prioritario
            JOIN usuarios ON updates_prioritario.user_id = usuarios.id
            WHERE updates_prioritario.ticket_id = ?
            ORDER BY updates_prioritario.date ASC
        ''', (id,))
        updates = cursor.fetchall()

        if request.method == 'POST':
            # Se for uma resposta, adiciona à tabela de atualizações
            resposta = request.form.get('resposta')
            novo_status = request.form.get('status')

            if resposta:
                cursor.execute('INSERT INTO updates_prioritario (ticket_id, user_id, update_text, date) VALUES (?, ?, ?, ?)',
                               (id, current_user.id, resposta, datetime.now()))
                flash('Resposta adicionada com sucesso!', 'success')

            if novo_status:
                cursor.execute('UPDATE ticketsprioritario SET status = ? WHERE id = ?', (novo_status, id))
                flash('Status atualizado com sucesso!', 'success')

                # Se o status for "Fechado", redireciona para a página de tickets resolvidos prioritários
                if novo_status == 'Fechado':
                    conn.commit()
                    return redirect(url_for('tickets_resolvidos_prioritario'))

            conn.commit()
    except sqlite3.Error as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
        return redirect(url_for('prioritario'))
    finally:
        conn.close()
    
    # Verificar se o arquivo existe
    file_exists_flag = file_exists(ticket[6]) if ticket[6] else False
    
    return render_template('editar_ticket_prioritario.html', ticket=ticket, updates=updates, file_exists=file_exists_flag)

# Rota para adicionar um novo usuário
@app.route('/adicionar_usuario', methods=['GET', 'POST'])
@login_required
def adicionar_usuario():
    if current_user.role != 'admin':
        flash('Acesso negado. Somente ADMINS podem adicionar usuários.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']  # Novo campo de e-mail
        role = request.form['role']

        if not username or not password or not email:
            flash('Todos os campos obrigatórios devem ser preenchidos.', 'error')
            return redirect(url_for('adicionar_usuario'))

        senha_hash = generate_password_hash(password)

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO usuarios (username, password, email, role) VALUES (?, ?, ?, ?)', 
                           (username, senha_hash, email, role))
            conn.commit()
        except sqlite3.Error as e:
            flash(f'Erro ao adicionar usuário: {str(e)}', 'error')
            return redirect(url_for('adicionar_usuario'))
        finally:
            conn.close()

        flash('Usuário adicionado com sucesso!', 'success')
        return redirect(url_for('gerenciar_usuarios'))

    return render_template('adicionar_usuario.html')

# Rota para excluir um usuário
@app.route('/excluir_usuario/<int:id>', methods=['POST'])
@login_required
def excluir_usuario(id):
    if current_user.role != 'admin':
        flash('Acesso negado. Somente ADMINS podem excluir usuários.', 'error')
        return redirect(url_for('index'))

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM usuarios WHERE id = ?', (id,))
        conn.commit()
        flash('Usuário excluído com sucesso!', 'success')
    except sqlite3.Error as e:
        flash(f'Erro ao excluir usuário: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('gerenciar_usuarios'))

# Rota para gerenciar usuários
@app.route('/gerenciar_usuarios')
@login_required
def gerenciar_usuarios():
    if current_user.role != 'admin':
        flash('Acesso negado. Somente ADMINS podem gerenciar usuários.', 'error')
        return redirect(url_for('index'))
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, role FROM usuarios')
        usuarios = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()
    
    return render_template('gerenciar_usuarios.html', usuarios=usuarios)

# Rota para download de arquivos
@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Rota para listar tickets prioritários
@app.route('/prioritario')
@login_required
def prioritario():
    if current_user.role not in ['admin', 'DIRETORIA']:
        flash('Acesso negado. Somente ADMINS e DIRETORIA podem visualizar tickets prioritários.', 'error')
        return redirect(url_for('index'))

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Busca tickets da tabela ticketsprioritario com o nome do responsável
        cursor.execute('''
            SELECT ticketsprioritario.*, usuarios.username as responsavel_nome
            FROM ticketsprioritario
            LEFT JOIN usuarios ON ticketsprioritario.responsavel_id = usuarios.id
            WHERE ticketsprioritario.status != 'Fechado'
        ''')
        tickets = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()
    
    return render_template('prioritario.html', tickets=tickets, user_role=current_user.role)

# Rota para abrir/editar tickets prioritários
@app.route('/ticket_prioritario/<int:id>', methods=['GET', 'POST'])
@login_required
def ticket_prioritario(id):
    if current_user.role not in ['admin', 'DIRETORIA']:
        flash('Acesso negado. Somente ADMINS podem editar tickets prioritários.', 'error')
        return redirect(url_for('prioritario'))

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Buscar ticket da tabela ticketsprioritario
        cursor.execute('SELECT * FROM ticketsprioritario WHERE id = ?', (id,))
        ticket = cursor.fetchone()

        if not ticket:
            flash('Ticket não encontrado.', 'error')
            return redirect(url_for('prioritario'))

        # Verificar permissões
        if current_user.username != ticket[1] and current_user.role not in ['admin', 'DIRETORIA']:
            flash('Acesso negado. Você não tem permissão para editar este ticket.', 'error')
            return redirect(url_for('prioritario'))

        # Buscar atualizações/respostas do ticket com o nome do usuário
        cursor.execute('''
            SELECT updates_prioritario.id, updates_prioritario.ticket_id, updates_prioritario.user_id, updates_prioritario.update_text, updates_prioritario.date, usuarios.username
            FROM updates_prioritario
            JOIN usuarios ON updates_prioritario.user_id = usuarios.id
            WHERE updates_prioritario.ticket_id = ?
            ORDER BY updates_prioritario.date ASC
        ''', (id,))
        updates = cursor.fetchall()

        if request.method == 'POST':
            # Se for uma resposta, adiciona à tabela de atualizações
            resposta = request.form.get('resposta')
            novo_status = request.form.get('status')

            if resposta:
                cursor.execute('INSERT INTO updates_prioritario (ticket_id, user_id, update_text, date) VALUES (?, ?, ?, ?)',
                               (id, current_user.id, resposta, datetime.now()))
                flash('Resposta adicionada com sucesso!', 'success')

            if novo_status:
                cursor.execute('UPDATE ticketsprioritario SET status = ? WHERE id = ?', (novo_status, id))
                flash('Status atualizado com sucesso!', 'success')

            conn.commit()
    except sqlite3.Error as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
        return redirect(url_for('prioritario'))
    finally:
        conn.close()
    
    # Verificar se o arquivo existe
    file_exists_flag = file_exists(ticket[6]) if ticket[6] else False
    
    return render_template('ticket_prioritario.html', ticket=ticket, updates=updates, file_exists=file_exists_flag)

# Rota para direcionar tickets fechados
@app.route('/tickets_resolvidos')
@login_required
def tickets_resolvidos():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tickets.*, usuarios.username as responsavel_nome
            FROM tickets
            LEFT JOIN usuarios ON tickets.responsavel_id = usuarios.id
            WHERE tickets.status = 'Fechado'
            ORDER BY 
                CASE 
                    WHEN prioridade = 'Urgente' THEN 1
                    WHEN prioridade = 'Alto' THEN 2
                    WHEN prioridade = 'Médio' THEN 3
                    WHEN prioridade = 'Baixo' THEN 4
                END,
                id ASC
        ''')
        tickets = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()
    
    return render_template('tickets_resolvidos.html', tickets=tickets)

@app.route('/tickets_resolvidos_prioritario')
@login_required
def tickets_resolvidos_prioritario():
    if current_user.role not in ['admin', 'DIRETORIA']:
        flash('Acesso negado. Somente ADMINS e DIRETORIA podem visualizar tickets resolvidos prioritários.', 'error')
        return redirect(url_for('index'))

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ticketsprioritario.*, usuarios.username as responsavel_nome
            FROM ticketsprioritario
            LEFT JOIN usuarios ON ticketsprioritario.responsavel_id = usuarios.id
            WHERE ticketsprioritario.status = 'Fechado'
            ORDER BY 
                CASE 
                    WHEN prioridade = 'Urgente' THEN 1
                    WHEN prioridade = 'Alto' THEN 2
                    WHEN prioridade = 'Médio' THEN 3
                    WHEN prioridade = 'Baixo' THEN 4
                END,
                id ASC
        ''')
        tickets = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f'Erro ao acessar o banco de dados: {str(e)}', 'error')
        return redirect(url_for('prioritario'))
    finally:
        conn.close()
    
    return render_template('tickets_resolvidos_prioritario.html', tickets=tickets)

if __name__ == '__main__':
    criar_banco()
    app.run(host='0.0.0.0', port=5000, debug=True)
