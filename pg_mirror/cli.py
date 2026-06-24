#!/usr/bin/env python3
"""
pg-mirror CLI - PostgreSQL Database Mirroring Tool
"""

import os
import sys
import click

from pg_mirror.logger import setup_logger
from pg_mirror.config import load_config
from pg_mirror.database import (
    check_database_exists,
    create_database,
    drop_and_create_database,
    terminate_connections,
)
from pg_mirror import hooks
from pg_mirror.backup import create_backup, cleanup_backup
from pg_mirror.restore import restore_backup
from pg_mirror.system_checks import (
    verify_system_requirements,
    SystemCheckError,
    print_installation_help,
)
from pg_mirror import __version__


@click.group()
@click.version_option(version=__version__, prog_name="pg-mirror")
@click.option(
    "-v", "--verbose", is_flag=True, help="Modo verbose (mostra mensagens DEBUG)"
)
@click.pass_context
def cli(ctx, verbose):
    """
    🪞 pg-mirror - PostgreSQL Database Mirroring Tool

    Ferramenta performática para espelhamento de bancos PostgreSQL
    com processamento paralelo e gerenciamento inteligente.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["logger"] = setup_logger(verbose)


@cli.command()
@click.option(
    "-c",
    "--config",
    default="config.json",
    help="Caminho para arquivo de configuração JSON",
)
@click.option(
    "-j", "--jobs", type=int, help="Número de jobs paralelos (sobrescreve config)"
)
@click.option(
    "--drop-existing",
    is_flag=True,
    help="Recriar banco se já existir (sobrescreve config)",
)
@click.option(
    "--skip-checks", is_flag=True, help="Pular verificação de ferramentas PostgreSQL"
)
@click.pass_context
def mirror(ctx, config, jobs, drop_existing, skip_checks):
    """
    Espelha um banco PostgreSQL de origem para destino.

    Realiza backup do banco de origem e restaura no destino,
    com verificação inteligente e processamento paralelo.
    
    O ID da assinatura é extraído automaticamente do nome do banco de dados.

    Exemplo:

        pg-mirror mirror --config config.json

        pg-mirror mirror -c prod-to-staging.json --jobs 8
    """
    logger = ctx.obj["logger"]
    verbose = ctx.obj["verbose"]

    # Verifica requisitos do sistema
    if not skip_checks:
        logger.info("Verificando ferramentas PostgreSQL...")
        try:
            verify_system_requirements(verbose=verbose)
            logger.info("✓ Todas as ferramentas necessárias estão instaladas")
        except SystemCheckError as e:
            logger.error(f"✗ Verificação do sistema falhou: {e}")
            logger.error("")
            print_installation_help()
            sys.exit(1)

    # Carrega configuração
    cfg = load_config(config, logger)

    # Override de opções via CLI
    if jobs:
        cfg["options"]["parallel_jobs"] = jobs
    if drop_existing:
        cfg["options"]["drop_existing"] = True

    assinatura_id = hooks.extrair_id_assinatura_do_nome_banco(cfg['source']['database'])
    
    if not assinatura_id:
        logger.warning(f"Não foi possível extrair ID da assinatura do nome do banco '{cfg['source']['database']}'")
        logger.warning("O fluxo de hooks HTTP será ignorado")

    logger.info("=" * 60)
    logger.info("Configuração carregada:")
    logger.info(f"   Origem: {cfg['source']['database']} @ {cfg['source']['host']}")
    logger.info(f"   Destino: {cfg['source']['database']} @ {cfg['target']['host']}")
    logger.info(f"   Jobs paralelos: {cfg['options']['parallel_jobs']}")
    logger.info(f"   Drop existing: {cfg['options']['drop_existing']}")
    logger.info(f"   Assinatura ID: {assinatura_id}")
    logger.info("=" * 60)

    backup_file = None
    target_database = cfg["source"]["database"]  # Nome padrão do banco de destino
    hooks_executados_com_sucesso = True  # Flag para controlar se hooks foram bem-sucedidos

    try:
        # 1. BACKUP
        backup_file = create_backup(
            host=cfg["source"]["host"],
            port=cfg["source"]["port"],
            database=cfg["source"]["database"],
            user=cfg["source"]["user"],
            password=cfg["source"]["password"],
            logger=logger,
        )

        # registra histórico em sqlite
        try:
            from pg_mirror import history

            size_mb = 0.0
            try:
                from pathlib import Path

                size_mb = Path(backup_file).stat().st_size / (1024 * 1024)
            except Exception:
                logger.debug("Não foi possível obter tamanho do arquivo de backup")

            record_id = history.record_backup(
                host=cfg["source"]["host"],
                port=cfg["source"]["port"],
                database=cfg["source"]["database"],
                username=cfg["source"]["user"],
                backup_path=backup_file,
                size_mb=size_mb,
                status="created",
            )
            logger.info(f"Registro de backup salvo no sqlite (id={record_id})")

            # Se tiver assinatura_id, executa GET e POST conforme solicitado
            if assinatura_id:
                try:
                    logger.info("=" * 60)
                    logger.info("Iniciando fluxo de hooks HTTP...")
                    logger.info("=" * 60)

                    # 1. Obter dados da assinatura em produção
                    logger.info(
                        f"1/3 - Obtendo dados da assinatura {assinatura_id} em produção..."
                    )
                    dados_assinatura = hooks.obter_dados_assinatura_producao(
                        assinatura_id
                    )

                    if not dados_assinatura:
                        logger.warning("GET de assinatura retornou vazio")
                        history.update_backup(record_id, status="hooks_skipped")
                    else:
                        logger.info(
                            f"✓ Assinatura obtida com sucesso (ID: {dados_assinatura['id']})"
                        )

                        # 2. Clonar assinatura no ambiente de desenvolvimento
                        logger.info(
                            "2/3 - Clonando assinatura no ambiente de desenvolvimento..."
                        )
                        assinatura_clonada = hooks.clonar_assinatura_desenvolvimento(
                            dados_assinatura
                        )
                        assinatura_dev_id = assinatura_clonada.get("id")
                        logger.info(
                            f"✓ Assinatura clonada com sucesso (ID dev: {assinatura_dev_id})"
                        )

                        # Gera nome do banco de dados baseado nos dados da assinatura clonada no DEV
                        target_database = hooks.gerar_nome_banco_dados(
                            pk=str(assinatura_clonada["id"]),
                            nome=assinatura_clonada["ss_nome_fantasia"],
                            uf=assinatura_clonada["ss_uf"],
                        )
                        logger.info(
                            f"Nome do banco de destino definido como: {target_database}"
                        )

                        # 3. Criar assinante_usuario no desenvolvimento
                        logger.info(
                            "3/3 - Criando vínculo assinante_usuario no desenvolvimento..."
                        )
                        email_usuario = os.environ.get("EMAIL_USUARIO")
                        if not email_usuario:
                            logger.warning(
                                "Variável de ambiente 'EMAIL_USUARIO' não definida; não será possível criar vínculo assinante_usuario"
                            )

                        if email_usuario and email_usuario and assinatura_dev_id:
                            assinante_usuario = (
                                hooks.criar_assinante_usuario_desenvolvimento(
                                    assinatura_id=assinatura_dev_id,
                                    email_assinante=email_usuario,
                                    email_usuario=email_usuario,
                                )
                            )
                            logger.info(
                                f"✓ Vínculo assinante_usuario criado com sucesso"
                            )
                        else:
                            logger.warning(
                                f"Dados insuficientes para criar assinante_usuario (assinante={email_usuario}, usuario={email_usuario}, id={assinatura_dev_id})"
                            )

                        logger.info("=" * 60)
                        logger.info("✅ Fluxo de hooks HTTP concluído com sucesso!")
                        logger.info("=" * 60)

                        # Atualiza histórico com sucesso
                        history.update_backup(
                            record_id,
                            status="hooks_completed",
                            extra={
                                "assinatura_id_prod": assinatura_id,
                                "assinatura_id_dev": assinatura_dev_id,
                                "email_assinante": email_usuario,
                                "email_usuario": email_usuario,
                                "target_database": target_database,
                            },
                        )

                except Exception as e:
                    logger.error("=" * 60)
                    logger.error(f"❌ Erro durante fluxo de hooks: {e}")
                    logger.error("=" * 60)
                    history.update_backup(
                        record_id, status="hooks_failed", extra={"error": str(e)}
                    )
                    hooks_executados_com_sucesso = False
                    logger.error("Restauração abortada devido a falha nos hooks HTTP")

        except Exception as e:
            logger.warning(
                f"Não foi possível registrar histórico ou executar hooks: {e}"
            )
            if assinatura_id:
                hooks_executados_com_sucesso = False
                logger.error("Restauração abortada devido a falha no registro de histórico")

        # Verificar se deve continuar com a restauração
        if not hooks_executados_com_sucesso:
            logger.error("=" * 60)
            logger.error("❌ Processo interrompido antes da restauração")
            logger.error("=" * 60)
            sys.exit(1)

        logger.info(f"🎯 Banco de destino para restauração: {target_database}")

        # 2. PREPARAR DESTINO
        db_exists = check_database_exists(
            host=cfg["target"]["host"],
            port=cfg["target"]["port"],
            database=target_database,
            user=cfg["target"]["user"],
            password=cfg["target"]["password"],
            logger=logger,
        )

        terminate_connections(
            host=cfg["target"]["host"],
            port=cfg["target"]["port"],
            database="api_erp",
            user=cfg["target"]["user"],
            password=cfg["target"]["password"],
            logger=logger,
        )

        if db_exists and cfg["options"]["drop_existing"]:
            logger.warning(f"Recriando banco '{target_database}'...")
            drop_and_create_database(
                host=cfg["target"]["host"],
                port=cfg["target"]["port"],
                database=target_database,
                user=cfg["target"]["user"],
                password=cfg["target"]["password"],
                logger=logger,
            )
        elif not db_exists:
            logger.info(f"Banco '{target_database}' não existe. Criando...")
            create_database(
                host=cfg["target"]["host"],
                port=cfg["target"]["port"],
                database=target_database,
                user=cfg["target"]["user"],
                password=cfg["target"]["password"],
                logger=logger,
            )

        # 3. RESTORE
        success = restore_backup(
            backup_file=backup_file,
            host=cfg["target"]["host"],
            port=cfg["target"]["port"],
            database=target_database,
            user=cfg["target"]["user"],
            password=cfg["target"]["password"],
            parallel_jobs=cfg["options"]["parallel_jobs"],
            logger=logger,
        )

        if success:
            # Atualizar email do usuário erika.neri após restauração
            if assinatura_id:
                email_usuario = os.environ.get("EMAIL_USUARIO")
                if email_usuario:
                    try:
                        logger.info("=" * 60)
                        logger.info("⚠️  ATENÇÃO: Verifique se o banco de dados está migrado corretamente!")
                        logger.info(f"   Banco: {target_database}")
                        logger.info("=" * 60)
                        click.pause("Pressione qualquer tecla para continuar após verificar as migrações...")
                        
                        logger.info("Atualizando email do usuário erika.neri no banco restaurado...")
                        hooks.atualizar_email_usuario_admin_desenvolvimento(
                            novo_email=email_usuario,
                            nome_banco_destino=target_database,
                        )
                        logger.info(
                            f"✓ Email do usuário erika.neri atualizado para: {email_usuario}"
                        )
                    except Exception as e:
                        logger.warning(f"Não foi possível atualizar email do usuário: {e}")
                else:
                    logger.warning(
                        "Email do usuário não disponível para atualização pós-restore"
                    )

            logger.info("=" * 60)
            logger.info("✅ Espelhamento concluído com sucesso!")
            logger.info("=" * 60)
        else:
            logger.error("=" * 60)
            logger.error("❌ Espelhamento concluído com erros")
            logger.error("=" * 60)
            sys.exit(1)

    finally:
        # 4. SEMPRE limpa o arquivo temporário
        if backup_file:
            cleanup_backup(backup_file, logger)


@cli.command()
@click.pass_context
def check(ctx):
    """
    Verifica se todas as ferramentas PostgreSQL estão instaladas.

    Verifica a presença de pg_dump, pg_restore e psql no sistema
    e exibe informações sobre versões e caminhos.

    Exemplo:

        pg-mirror check
    """
    logger = ctx.obj["logger"]

    logger.info("Verificando ferramentas PostgreSQL...")
    logger.info("")

    try:
        verify_system_requirements(verbose=True)
        sys.exit(0)
    except SystemCheckError as e:
        logger.error(f"✗ Verificação falhou: {e}")
        logger.error("")
        print_installation_help()
        sys.exit(1)


@cli.command()
@click.option(
    "-c",
    "--config",
    default="config.json",
    help="Caminho para arquivo de configuração JSON",
)
@click.pass_context
def validate(ctx, config):
    """
    Valida arquivo de configuração sem executar o espelhamento.

    Útil para verificar se o arquivo de configuração está correto
    antes de executar o espelhamento.

    Exemplo:

        pg-mirror validate --config config.json
    """
    logger = ctx.obj["logger"]

    try:
        cfg = load_config(config, logger)

        logger.info("✅ Configuração válida!")
        logger.info(
            f"   Origem: {cfg['source']['database']} @ {cfg['source']['host']}:{cfg['source']['port']}"
        )
        logger.info(f"   Destino: {cfg['target']['host']}:{cfg['target']['port']}")
        logger.info(
            f"   Opções: jobs={cfg['options']['parallel_jobs']}, drop_existing={cfg['options']['drop_existing']}"
        )

    except Exception as e:
        logger.error(f"❌ Configuração inválida: {e}")
        sys.exit(1)


@cli.command()
def version():
    """Mostra a versão do pg-mirror."""
    click.echo(f"pg-mirror version {__version__}")


if __name__ == "__main__":
    cli(obj={})
