"""Hooks HTTP executados após criação do backup

- Executa um GET na API de assinaturas da FortePlus para obter detalhes da
  assinatura correspondente (usa `FORTEPLUS_TOKEN` do ambiente).
- Executa um POST no endpoint interno para propagar os dados obtidos
  (usa `FORTEPLUS_REMOTE_TOKEN` do ambiente, se presente).

Observação: assume que a biblioteca `httpx` está disponível no ambiente.
"""

import os
import re
from typing import Optional, Any

import httpx

from pg_mirror.logger import setup_logger
from pg_mirror.jwt_utils import modificar_db_no_token
from pg_mirror.exceptions import ImproperlyConfiguredException

logger = setup_logger()

FORTEPLUS_TOKEN = os.environ.get("FORTEPLUS_TOKEN")

PROD_ENVIRONMENT_URL = "https://assinaturas.forteplus.com.br/api/v1/"
DEV_ENVIRONMENT_URL = "http://192.168.200.68:8031/api/v1/"
DEV_ENVIRONMENT_URL_2 = "http://192.168.200.68:8032/api/v1/"
DEFAULT_TIMEOUT = 10


def extrair_id_assinatura_do_nome_banco(nome_banco: str) -> Optional[str]:
    """Extrai o ID da assinatura do nome do banco de dados.
    
    Dado um nome de banco no formato {uf}_d1_{id}_{nome_fantasia},
    extrai e retorna o ID da assinatura.
    
    Exemplos:
        - "sp_d1_123_acme" → "123"
        - "rj_d1_456_empresa" → "456"
        - "banco_invalido" → None
    
    Args:
        nome_banco: Nome do banco de dados a ser analisado
    
    Returns:
        O ID da assinatura como string, ou None se o formato não corresponder
    """
    # Padrão: {uf}_d1_{id}_{nome_fantasia}
    # Usamos regex para extrair o ID que está entre _d1_ e o próximo _
    pattern = r'^[a-z]{2}_d1_(\d+)_'
    match = re.match(pattern, nome_banco.lower())
    
    if match:
        assinatura_id = match.group(1)
        logger.info(f"ID da assinatura extraído do nome do banco '{nome_banco}': {assinatura_id}")
        return assinatura_id
    
    logger.debug(f"Não foi possível extrair ID da assinatura do nome do banco '{nome_banco}'")
    return None


def obter_dados_assinatura_producao(assinatura_id: str) -> Optional[dict[str, Any]]:
    if not FORTEPLUS_TOKEN:
        logger.warning("Token env var 'FORTEPLUS_TOKEN' não encontrado")
        raise ImproperlyConfiguredException(
            "FORTEPLUS_TOKEN não configurado no ambiente"
        )

    url = f"{PROD_ENVIRONMENT_URL}assinaturas/{assinatura_id}/"
    headers = {
        "Authorization": FORTEPLUS_TOKEN,
        "Accept": "application/json",
    }

    logger.info(f"GET {url}")

    resp = httpx.get(url, headers=headers, timeout=DEFAULT_TIMEOUT, verify=False)
    logger.info(f"GET {url} -> {resp.status_code}")
    logger.debug(f"Response body: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def clonar_assinatura_desenvolvimento(payload: dict) -> Any:
    print("PAYLOAD:", payload)

    if not FORTEPLUS_TOKEN:
        logger.warning("Token env var 'FORTEPLUS_TOKEN' não encontrado")
        raise ImproperlyConfiguredException(
            "FORTEPLUS_TOKEN não configurado no ambiente"
        )

    logger.info(f"POST {DEV_ENVIRONMENT_URL} payload keys={list(payload.keys())}")
    logger.debug(f"Payload completo: {payload}")

    url = f"{DEV_ENVIRONMENT_URL}assinaturas/"
    headers = {
        "Authorization": FORTEPLUS_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    resp = httpx.post(url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT, verify=False)
    logger.info(f"POST {url} -> {resp.status_code}")
    logger.debug(f"Response body: {resp.text}")
    logger.debug(f"Request body: {resp.request.content}")
    resp.raise_for_status()
    return resp.json()


def criar_assinante_usuario_desenvolvimento(
    assinatura_id: int, email_assinante: str, email_usuario: str
) -> Any:
    if not FORTEPLUS_TOKEN:
        logger.warning("Token env var 'FORTEPLUS_TOKEN' não encontrado")
        raise ImproperlyConfiguredException(
            "FORTEPLUS_TOKEN não configurado no ambiente"
        )

    url = f"{DEV_ENVIRONMENT_URL}assinantes_usuarios/"
    headers = {
        "Authorization": FORTEPLUS_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "usss_assinatura": assinatura_id,
        "usss_email_assinante": email_assinante,
        "usss_email_usuario": email_usuario,
    }

    logger.info(f"POST {url} payload keys={list(payload.keys())}")

    resp = httpx.post(url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT, verify=False)
    logger.info(f"POST {url} -> {resp.status_code}")
    logger.debug(f"Response body: {resp.text}")
    resp.raise_for_status()
    return resp.json()


def atualizar_email_usuario_admin_desenvolvimento(novo_email: str, nome_banco_destino: str) -> Any:
    """Atualiza o email do usuário admin no ambiente de desenvolvimento.
    
    Modifica o JWT para apontar para o banco de dados correto antes de fazer a requisição.
    
    Args:
        novo_email: Novo email para o usuário admin
        nome_banco_destino: Nome do banco de dados de destino (para multitenancy via JWT)
    
    Raises:
        ImproperlyConfiguredException: Se FORTEPLUS_TOKEN ou JWT_SECRET não estiverem configurados
        ValueError: Se o token não contiver a chave 'db'
    """
    if not FORTEPLUS_TOKEN:
        logger.warning("Token env var 'FORTEPLUS_TOKEN' não encontrado")
        raise ImproperlyConfiguredException(
            "FORTEPLUS_TOKEN não configurado no ambiente"
        )

    try:
        token_modificado = modificar_db_no_token(FORTEPLUS_TOKEN, nome_banco_destino)
    except Exception as e:
        logger.error(f"Erro ao modificar token JWT: {e}")
        raise ImproperlyConfiguredException(str(e)) from e
    
    headers = {
        "Authorization": token_modificado,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # 1. GET para buscar o usuário pelo email antigo
    email_admin = "erika.neri@forteplus.com.br"
    get_url = f"{DEV_ENVIRONMENT_URL_2}usuarios/"
    params = {"us_email": email_admin}

    logger.info(f"GET {get_url} com query us_email={email_admin}")

    get_resp = httpx.get(
        get_url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT, verify=False
    )
    logger.info(f"GET {get_url} -> {get_resp.status_code}")
    logger.debug(f"Response body: {get_resp.text}")
    get_resp.raise_for_status()

    usuarios = get_resp.json()

    # Extrai o ID do usuário (assumindo que retorna lista ou dict com results)
    if isinstance(usuarios, dict) and "results" in usuarios:
        usuarios = usuarios["results"]

    if not usuarios:
        raise ValueError(f"Usuário com email {email_admin} não encontrado")

    if len(usuarios) > 1:
        logger.warning(
            f"Múltiplos usuários encontrados com email {email_admin}, usando o primeiro"
        )

    usuario_id = usuarios[0].get("id") or usuarios[0].get("us_id")
    if not usuario_id:
        raise ValueError("ID do usuário não encontrado na resposta")

    logger.info(f"Usuário encontrado com ID: {usuario_id}")

    # 2. PATCH para atualizar o email
    patch_url = f"{DEV_ENVIRONMENT_URL_2}usuarios/{usuario_id}/"
    payload = {"us_email": novo_email}

    logger.info(f"PATCH {patch_url} com novo email: {novo_email}")

    patch_resp = httpx.patch(
        patch_url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT, verify=False
    )
    logger.info(f"PATCH {patch_url} -> {patch_resp.status_code}")
    logger.debug(f"Response body: {patch_resp.text}")
    patch_resp.raise_for_status()

    return patch_resp.json()


def gerar_nome_banco_dados(
    pk: str, nome: str, uf: str
) -> str:
    # Pega primeiro nome e converte para lowercase
    nome_fantasia = nome.split(" ")[0].lower()

    # Monta nome do banco: {uf}_d1_{id}_{nome_fantasia}
    nome_banco_dados = f"{uf.lower()}_d1_{pk}_{nome_fantasia}"

    # Sanitiza: remove tudo que não for letra, número ou underscore
    nome_sanitizado = re.sub(r"[^a-zA-Z0-9_]", "", nome_banco_dados)

    logger.info(f"Nome do banco gerado: {nome_sanitizado}")
    return nome_sanitizado
