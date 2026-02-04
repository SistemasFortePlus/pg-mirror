"""Utilitários para manipulação de JWT multitenante.

Permite decodificar, modificar e re-assinar tokens JWT para alterar
o banco de dados de destino em ambientes multitenantes.
"""

import jwt
import os
from typing import Any


from pg_mirror.logger import setup_logger

logger = setup_logger()


JWT_SECRET = os.environ.get("JWT_SECRET")


class JWTSecretNaoConfiguradaError(Exception):
    """Exceção lançada quando JWT_SECRET não está configurada no ambiente."""
    pass


class JWTDbAusenteError(Exception):
    """Exceção lançada quando a chave 'db' não existe no payload do token."""
    pass


def decodificar_payload_jwt(token: str) -> dict[str, Any]:
    """Decodifica o payload de um JWT sem verificar a assinatura e expiração.
    
    Args:
        token: Token JWT completo (header.payload.signature)
    
    Returns:
        Dicionário com o payload decodificado
    """
    payload = jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_nbf": False,
            "verify_iat": False,
        }
    )
    
    logger.debug(f"Payload JWT decodificado: {payload}")
    return payload


def modificar_db_no_token(token: str, novo_db: str) -> str:
    """Modifica a chave 'db' no payload do JWT e retorna um novo token assinado.
    
    Args:
        token: Token JWT original
        novo_db: Novo nome do banco de dados
    
    Returns:
        Novo token JWT com a chave 'db' modificada (assinado com HS256)
    
    Raises:
        JWTSecretNaoConfiguradaError: Se JWT_SECRET não estiver configurada
        JWTDbAusenteError: Se a chave 'db' não existir no token original
    """
    if not JWT_SECRET:
        logger.error("JWT_SECRET não configurada no ambiente")
        raise JWTSecretNaoConfiguradaError(
            "Variável de ambiente JWT_SECRET não está configurada"
        )
    
    payload = decodificar_payload_jwt(token)
    
    if "db" not in payload:
        logger.error("Token JWT não contém a chave 'db'")
        raise JWTDbAusenteError(
            "O token JWT não contém a chave 'db' necessária para multitenancy"
        )
    
    db_antigo = payload.get("db")
    payload["db"] = novo_db
    
    logger.info(f"Modificando JWT: db '{db_antigo}' -> '{novo_db}'")
    
    novo_token = jwt.encode(payload, key=JWT_SECRET, algorithm="HS256")
    
    logger.debug("Novo token gerado (assinado com HS256)")
    return novo_token


def obter_db_do_token(token: str) -> str | None:
    """Obtém o valor da chave 'db' do payload do JWT.
    
    Args:
        token: Token JWT completo
    
    Returns:
        Valor da chave 'db' ou None se não existir
    """
    payload = decodificar_payload_jwt(token)
    return payload.get("db")
