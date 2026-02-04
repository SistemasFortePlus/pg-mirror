"""Database operations for PostgreSQL"""
import os
import subprocess
import sys


class DatabaseManager:
    """
    Gerenciador de operações de banco de dados PostgreSQL com reutilização de conexão.
    
    Esta classe encapsula as credenciais de conexão e reutiliza o ambiente
    configurado para múltiplas operações, evitando repetição de código.
    
    Exemplo de uso:
        db_manager = DatabaseManager(
            host='localhost',
            port=5432,
            user='postgres',
            password='secret',
            logger=logger
        )
        
        if db_manager.check_database_exists('mydb'):
            db_manager.drop_and_create_database('mydb')
        else:
            db_manager.create_database('mydb')
    """
    
    def __init__(self, host, port, user, password, logger):
        """
        Inicializa o gerenciador com as credenciais de conexão.
        
        Args:
            host: Hostname do servidor PostgreSQL
            port: Porta do servidor
            user: Usuário do PostgreSQL
            password: Senha do usuário
            logger: Logger configurado
        """
        self.host = host
        self.port = str(port)
        self.user = user
        self.password = password
        self.logger = logger
        self._env = None
    
    @property
    def env(self):
        """Retorna o ambiente configurado com PGPASSWORD, criando apenas uma vez."""
        if self._env is None:
            self._env = os.environ.copy()
            self._env['PGPASSWORD'] = self.password
        return self._env
    
    def _build_psql_cmd(self, sql, target_database='postgres'):
        """
        Constrói o comando psql base.
        
        Args:
            sql: Comando SQL a ser executado
            target_database: Banco de dados alvo para conexão (padrão: postgres)
            
        Returns:
            list: Lista de argumentos do comando psql
        """
        return [
            'psql',
            '-h', self.host,
            '-p', self.port,
            '-U', self.user,
            '-d', target_database,
            '-c', sql
        ]
    
    def _run_psql(self, sql, target_database='postgres', check=True, capture_output=True):
        """
        Executa um comando psql.
        
        Args:
            sql: Comando SQL a ser executado
            target_database: Banco de dados alvo para conexão
            check: Se True, levanta exceção em caso de erro
            capture_output: Se True, captura stdout e stderr
            
        Returns:
            subprocess.CompletedProcess: Resultado da execução
        """
        cmd = self._build_psql_cmd(sql, target_database)
        return subprocess.run(cmd, env=self.env, check=check, capture_output=capture_output, text=True)
    
    def check_database_exists(self, database):
        """
        Verifica se o banco de dados existe.
        
        Args:
            database: Nome do banco de dados
            
        Returns:
            bool: True se o banco existe, False caso contrário
        """
        sql = f"SELECT 1 FROM pg_database WHERE datname='{database}';"
        cmd = [
            'psql',
            '-h', self.host,
            '-p', self.port,
            '-U', self.user,
            '-d', 'postgres',
            '-tAc', sql
        ]
        
        try:
            result = subprocess.run(cmd, env=self.env, capture_output=True, text=True, check=False)
            exists = result.stdout.strip() == '1'
            self.logger.debug(f"Banco '{database}' existe: {exists}")
            return exists
        except Exception as e:
            self.logger.error(f"Erro ao verificar existência do banco: {e}")
            return False
    
    def create_database(self, database):
        """
        Cria o banco de dados.
        
        Args:
            database: Nome do banco de dados
        """
        try:
            self._run_psql(f'CREATE DATABASE "{database}";')
            self.logger.info(f"Banco '{database}' criado com sucesso")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erro ao criar banco: {e.stderr if e.stderr else e}")
            sys.exit(1)
    
    def drop_and_create_database(self, database):
        """
        Recria o banco do zero (remove e cria novamente).
        
        Args:
            database: Nome do banco de dados
        """
        terminate_sql = f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{database}'
            AND pid <> pg_backend_pid();
        """
        
        try:
            # Termina conexões existentes
            self.logger.debug(f"Terminando conexões existentes no banco '{database}'")
            self._run_psql(terminate_sql, check=False)
            
            # Remove o banco
            self.logger.debug(f"Removendo banco '{database}'")
            self._run_psql(f'DROP DATABASE IF EXISTS "{database}";')
            
            # Cria o banco
            self.logger.debug(f"Criando banco '{database}'")
            self._run_psql(f'CREATE DATABASE "{database}";')
            
            self.logger.info(f"Banco '{database}' recriado com sucesso")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erro ao recriar banco: {e.stderr if e.stderr else e}")
            sys.exit(1)


# =============================================================================
# Funções legadas - mantidas para compatibilidade durante migração
# =============================================================================


def check_database_exists(host, port, database, user, password, logger):
    """
    Verifica se o banco de dados existe
    
    Args:
        host: Hostname do servidor PostgreSQL
        port: Porta do servidor
        database: Nome do banco de dados
        user: Usuário do PostgreSQL
        password: Senha do usuário
        logger: Logger configurado
        
    Returns:
        bool: True se o banco existe, False caso contrário
    """
    import os
    
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    check_cmd = [
        'psql',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', 'postgres',
        '-tAc', f"SELECT 1 FROM pg_database WHERE datname='{database}';"
    ]
    
    try:
        result = subprocess.run(
            check_cmd,
            env=env,
            capture_output=True,
            text=True,
            check=False
        )
        exists = result.stdout.strip() == '1'
        logger.debug(f"Banco '{database}' existe: {exists}")
        return exists
    except Exception as e:
        logger.error(f"Erro ao verificar existência do banco: {e}")
        return False


def create_database(host, port, database, user, password, logger):
    """
    Cria o banco de dados
    
    Args:
        host: Hostname do servidor PostgreSQL
        port: Porta do servidor
        database: Nome do banco de dados
        user: Usuário do PostgreSQL
        password: Senha do usuário
        logger: Logger configurado
    """
    import os
    
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    create_cmd = [
        'psql',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', 'postgres',
        '-c', f'CREATE DATABASE "{database}";'
    ]
    
    try:
        subprocess.run(create_cmd, env=env, check=True, capture_output=True)
        logger.info(f"Banco '{database}' criado com sucesso")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao criar banco: {e.stderr.decode() if e.stderr else e}")
        sys.exit(1)


def drop_and_create_database(host, port, database, user, password, logger):
    """
    Recria o banco do zero (remove e cria novamente)
    
    Args:
        host: Hostname do servidor PostgreSQL
        port: Porta do servidor
        database: Nome do banco de dados
        user: Usuário do PostgreSQL
        password: Senha do usuário
        logger: Logger configurado
    """
    import os
    
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    # Termina conexões existentes
    logger.debug(f"Terminando conexões existentes no banco '{database}'")
    terminate_cmd = [
        'psql',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', 'postgres',
        '-c', f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{database}'
            AND pid <> pg_backend_pid();
        """
    ]
    
    drop_cmd = [
        'psql',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', 'postgres',
        '-c', f'DROP DATABASE IF EXISTS "{database}";'
    ]
    
    create_cmd = [
        'psql',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', 'postgres',
        '-c', f'CREATE DATABASE "{database}";'
    ]
    
    try:
        subprocess.run(terminate_cmd, env=env, capture_output=True)
        logger.debug(f"Removendo banco '{database}'")
        subprocess.run(drop_cmd, env=env, check=True, capture_output=True)
        logger.debug(f"Criando banco '{database}'")
        subprocess.run(create_cmd, env=env, check=True, capture_output=True)
        logger.info(f"Banco '{database}' recriado com sucesso")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao recriar banco: {e.stderr.decode() if e.stderr else e}")
        sys.exit(1)
