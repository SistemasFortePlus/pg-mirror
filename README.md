# 🪞 pg-mirror - PostgreSQL Database Mirroring

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Uma ferramenta Python performática para espelhamento (mirror) de bancos de dados PostgreSQL entre servidores, com suporte a processamento paralelo e gerenciamento inteligente de bancos.

## ✨ Características

- 🚀 **Backup paralelo**: Utiliza formato custom do PostgreSQL com compressão nativa
- ⚡ **Restore multi-threaded**: Restauração até 4x mais rápida com jobs paralelos
- 🔍 **Verificação inteligente**: Detecta se o banco existe antes de restaurar
- 🛡️ **Seguro**: Gerenciamento automático de conexões e arquivos temporários
- 📝 **Logging estruturado**: Acompanhamento detalhado de cada operação
- ⚙️ **Configuração JSON**: Setup simples via arquivo de configuração
- 💻 **CLI moderna**: Interface de linha de comando intuitiva com Click
- ✅ **Verificação automática**: Detecta ferramentas PostgreSQL no sistema

## 📋 Requisitos

- Python 3.8+
- PostgreSQL client tools (`pg_dump`, `pg_restore`, `psql`)
- Acesso aos servidores de origem e destino

## 🔧 Instalação

### Via pip (quando publicado no PyPI)

```bash
pip install pg-mirror
```

### Via clone do repositório

```bash
git clone https://github.com/seu-usuario/pg-mirror.git
cd pg-mirror
pip install -r requirements.txt
```

### Instalar PostgreSQL client tools

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql-client
```

**macOS:**
```bash
brew install postgresql
```

**Windows:**
Baixe do [site oficial do PostgreSQL](https://www.postgresql.org/download/windows/)

**Verificar instalação:**
```bash
pg-mirror check
```

Este comando verifica se `pg_dump`, `pg_restore` e `psql` estão instalados e acessíveis, exibindo versões e caminhos. Caso falte alguma ferramenta, mostra instruções de instalação específicas para seu sistema operacional.

## 🚀 Uso Rápido

### 1. Criar arquivo de configuração

Copie o exemplo e edite com suas credenciais:

```bash
cp examples/config.example.json config.json
```

Edite `config.json`:

```json
{
  "source": {
    "host": "origem.exemplo.com",
    "port": 5432,
    "database": "meu_banco",
    "user": "postgres",
    "password": "senha_segura"
  },
  "target": {
    "host": "destino.exemplo.com",
    "port": 5432,
    "user": "postgres",
    "password": "senha_segura"
  },
  "options": {
    "drop_existing": false,
    "parallel_jobs": 4
  }
}
```

### 2. Executar migração

```bash
pg-mirror mirror --config config.json
```

### Notificações (opcional)

Você pode registrar backups em um banco SQLite local e executar hooks HTTP logo após a criação do backup. Para isso, use a opção `--assinatura-id`:

```bash
pg-mirror mirror --config config.json --assinatura-id 12345
```

Com `--assinatura-id` a ferramenta fará:
- Um GET em `https://assinaturas.forteplus.com.br/api/v1/assinaturas/<id>/` (usa `FORTEPLUS_TOKEN` da env)
- Um POST em `http://192.168.200.68:8031/api/v1/assinaturas/` com o payload retornado

O histórico de backups é salvo em `~/.pg_mirror/pg_mirror.db`.

## 📖 Configuração Detalhada

### Opções do config.json

| Campo | Tipo | Obrigatório | Padrão | Descrição |
|-------|------|-------------|---------|-----------|
| `source.host` | string | ✅ | - | Hostname do servidor de origem |
| `source.port` | integer | ❌ | 5432 | Porta do PostgreSQL |
| `source.database` | string | ✅ | - | Nome do banco a copiar |
| `source.user` | string | ✅ | - | Usuário do PostgreSQL |
| `source.password` | string | ✅ | - | Senha do usuário |
| `target.host` | string | ✅ | - | Hostname do servidor de destino |
| `target.port` | integer | ❌ | 5432 | Porta do PostgreSQL |
| `target.user` | string | ✅ | - | Usuário do PostgreSQL |
| `target.password` | string | ✅ | - | Senha do usuário |
| `options.drop_existing` | boolean | ❌ | false | Se true, recria o banco antes do restore |
| `options.parallel_jobs` | integer | ❌ | 4 | Número de jobs paralelos no restore |

### Comportamento da verificação de banco

A ferramenta implementa lógica inteligente:

1. **Banco não existe**: Cria automaticamente e faz o restore
2. **Banco existe + `drop_existing: false`**: Restaura direto no banco existente
3. **Banco existe + `drop_existing: true`**: Remove e recria o banco antes do restore

## 🎯 Casos de Uso

### Migração entre ambientes

```bash
# Desenvolvimento → Staging
pg-mirror mirror --config config-dev-to-staging.json

# Produção → DR (Disaster Recovery)
pg-mirror mirror --config config-prod-to-dr.json
```

### Refresh de banco de homologação

```json
{
  "source": {"host": "prod.db", "database": "app_prod", ...},
  "target": {"host": "staging.db", ...},
  "options": {
    "drop_existing": true,  // Limpa staging antes
    "parallel_jobs": 8      // Mais rápido em servidores potentes
  }
}
```

### Clone local para desenvolvimento

```json
{
  "source": {"host": "prod.db", "database": "app", ...},
  "target": {"host": "localhost", ...},
  "options": {
    "drop_existing": true,
    "parallel_jobs": 2  // Menos jobs para máquinas locais
  }
}
```

## 🔍 Logs e Debugging

A ferramenta gera logs estruturados:

```
2025-11-05 14:32:10 - PostgresBackupRestore - INFO - ============================================================
2025-11-05 14:32:10 - PostgresBackupRestore - INFO - Configuração carregada:
2025-11-05 14:32:10 - PostgresBackupRestore - INFO -    Origem: meu_banco @ origem.exemplo.com
2025-11-05 14:32:10 - PostgresBackupRestore - INFO -    Destino: meu_banco @ destino.exemplo.com
2025-11-05 14:32:10 - PostgresBackupRestore - INFO -    Jobs paralelos: 4
2025-11-05 14:32:10 - PostgresBackupRestore - INFO -    Drop existing: False
2025-11-05 14:32:10 - PostgresBackupRestore - INFO - ============================================================
2025-11-05 14:32:10 - PostgresBackupRestore - INFO - Criando backup de 'meu_banco' (origem.exemplo.com)...
2025-11-05 14:32:45 - PostgresBackupRestore - INFO - Backup criado com sucesso: 245.67 MB
2025-11-05 14:32:45 - PostgresBackupRestore - INFO - Banco 'meu_banco' não existe. Criando...
2025-11-05 14:32:46 - PostgresBackupRestore - INFO - Banco 'meu_banco' criado com sucesso
2025-11-05 14:32:46 - PostgresBackupRestore - INFO - Restaurando em 'meu_banco' (destino.exemplo.com)...
2025-11-05 14:32:46 - PostgresBackupRestore - INFO - Usando 4 jobs paralelos
2025-11-05 14:35:21 - PostgresBackupRestore - INFO - Restore concluído com sucesso!
2025-11-05 14:35:21 - PostgresBackupRestore - INFO - Backup temporário removido
2025-11-05 14:35:21 - PostgresBackupRestore - INFO - ============================================================
2025-11-05 14:35:21 - PostgresBackupRestore - INFO - Migração concluída com sucesso!
2025-11-05 14:35:21 - PostgresBackupRestore - INFO - ============================================================
```

## 🧪 Testes

O projeto possui uma suíte completa de testes unitários com pytest:

```bash
# Executar todos os testes
pytest tests/

# Com cobertura de código
pytest tests/ --cov=pg_mirror --cov-report=term-missing

# Gerar relatório HTML
pytest tests/ --cov=pg_mirror --cov-report=html
```

### Estatísticas dos Testes

- ✅ **74 testes implementados**
- ✅ **100% de taxa de sucesso**
- ✅ **53% de cobertura de código**
- ✅ **5 módulos com 100% de cobertura** (config, database, logger, restore, __init__)

Veja a [documentação completa dos testes](tests/README.md) e o [resumo da implementação](docs/development/TEST_IMPLEMENTATION_SUMMARY.md).

## 📚 Documentação

A documentação completa está organizada em:

- **[Guia Rápido](docs/guides/QUICKSTART.md)** - Comece em 5 minutos
- **[Referência CLI](docs/reference/README_CLI.md)** - Documentação completa da CLI
- **[Verificação de Sistema](docs/guides/SYSTEM_CHECKS.md)** - Sistema de checks
- **[Instalação](docs/installation.md)** - Guia detalhado de instalação
- **[Estrutura do Projeto](docs/project/PROJECT_STRUCTURE.md)** - Organização do código
- **[Testes](tests/README.md)** - Documentação dos testes unitários

👉 Veja o [índice completo da documentação](docs/README.md)

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia [CONTRIBUTING.md](docs/development/CONTRIBUTING.md) para detalhes sobre nosso código de conduta e processo de submissão de pull requests.

## 📝 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🐛 Reportar Bugs

Encontrou um bug? Por favor, abra uma [issue](https://github.com/seu-usuario/pg-mirror/issues) com:

- Descrição clara do problema
- Passos para reproduzir
- Comportamento esperado vs atual
- Versão do Python e PostgreSQL
- Logs relevantes

## 💡 Roadmap

- [ ] Suporte a backup incremental
- [ ] Interface CLI interativa
- [ ] Suporte a múltiplos bancos em batch
- [ ] Integração com AWS S3 para backups
- [ ] Dashboard web para monitoramento
- [ ] Suporte a Docker

## 👥 Autores

- **Davi SIlva Rafacho** - [davisilvarafacho](https://github.com/davisilvarafacho)

⭐ Se este projeto foi útil, considere dar uma estrela no GitHub!
