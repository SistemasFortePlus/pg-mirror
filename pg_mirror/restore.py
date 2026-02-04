"""Restore operations for PostgreSQL"""
import subprocess
import sys
import os


def restore_backup(backup_file, host, port, database, user, password, 
                   parallel_jobs, logger):
    """
    Restore com paralelização (-j):
    - Múltiplas threads simultâneas
    - Muito mais rápido em bancos grandes
    
    Args:
        backup_file: Caminho do arquivo de backup
        host: Hostname do servidor PostgreSQL
        port: Porta do servidor
        database: Nome do banco de dados
        user: Usuário do PostgreSQL
        password: Senha do usuário
        parallel_jobs: Número de jobs paralelos
        logger: Logger configurado
        
    Returns:
        bool: True se o restore foi bem-sucedido, False caso contrário
    """
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    cmd = [
        'pg_restore',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', database,
        '-j', str(parallel_jobs),  # paralelização
        '--no-owner',
        '--no-acl',
        backup_file
    ]
    
    logger.info(f"Restaurando em '{database}' ({host})...")
    logger.info(f"Usando {parallel_jobs} jobs paralelos")
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            check=False,  # Não levanta exceção automaticamente
            capture_output=True,
            text=True
        )
        
        # Analisa stderr para erros críticos vs warnings aceitáveis
        stderr_output = result.stderr
        
        # Conta erros críticos (linhas com "ERROR:" mas não warnings de permissão/owner)
        critical_errors = []
        warning_count = 0
        
        if stderr_output:
            for line in stderr_output.split('\n'):
                line_lower = line.lower()
                # Erros críticos: falhas de dados, schema, etc
                if 'error:' in line_lower and 'pg_restore: error:' in line_lower:
                    # Ignora erros comuns não-críticos relacionados a permissões
                    if not any(x in line_lower for x in [
                        'must be owner',
                        'permission denied',
                        'role',
                        'does not exist'
                    ]):
                        critical_errors.append(line.strip())
                
                # Captura a linha de warnings ignorados
                if 'warning: errors ignored on restore:' in line_lower:
                    try:
                        warning_count = int(line.split(':')[-1].strip())
                    except:
                        pass
        
        # Log apropriado baseado no resultado
        if critical_errors:
            logger.error(f"Restore falhou com {len(critical_errors)} erro(s) crítico(s):")
            for error in critical_errors[:5]:  # Mostra no máximo 5 erros
                logger.error(f"  • {error}")
            if len(critical_errors) > 5:
                logger.error(f"  ... e mais {len(critical_errors) - 5} erros")
            return False
        
        if warning_count > 0:
            logger.warning(f"Restore concluído com {warning_count} aviso(s) ignorado(s)")
            logger.warning("Avisos geralmente são relacionados a permissões e não afetam os dados")
        
        if result.returncode == 0 or (result.returncode == 1 and warning_count > 0):
            logger.info("✓ Restore concluído com sucesso!")
            return True
        else:
            logger.error(f"Restore falhou com código de retorno: {result.returncode}")
            if stderr_output:
                logger.debug(f"Stderr completo: {stderr_output}")
            return False
    
    except Exception as e:
        logger.error(f"Exceção durante restore: {e}")
        return False
