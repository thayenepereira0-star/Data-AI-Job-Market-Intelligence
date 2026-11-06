# V2 — Preparação do PostgreSQL local (DAI-20)

Esta etapa configura **somente o ambiente do banco**. As sete tabelas da DAI-17 serão implementadas na **DAI-21** e a conexão Python na **DAI-22**. Nenhuma credencial real deve ser versionada.

## Pré-requisitos

- Docker Desktop instalado, iniciado e com suporte a Docker Compose.
- Porta local 5432 disponível (ou configure outra com `POSTGRES_PORT`).
- PowerShell, na pasta raiz do repositório.

## Executar no Windows (PowerShell)

1. Criar seu arquivo de configuração local (se ainda não existir):

```powershell
Copy-Item .env.example .env
```

2. Abrir `.env` e substituir `POSTGRES_PASSWORD` por uma **senha local forte**, sem espaços extras, e nunca publicar este arquivo.

3. Validar a configuração e iniciar somente o PostgreSQL:

```powershell
docker compose config --quiet
docker compose up -d db
docker compose ps
```

4. Testar a conexão dentro do contêiner:

```powershell
docker compose exec db psql -U jobmarket -d jobmarket -c "SELECT current_database(), current_user;"
```

5. Ao terminar a sessão:

```powershell
docker compose down
```

Os dados permanecem no volume Docker `postgres_data`. **Não use `docker compose down -v`** a menos que queira apagar intencionalmente o banco local.

## Se algo falhar

- **Docker não reconhecido:** instalar/iniciar Docker Desktop e reabrir o terminal.
- **Porta em uso:** mudar `POSTGRES_PORT` no arquivo `.env` (ex.: `5433`).
- **Senha não configurada:** certificar-se de que `POSTGRES_PASSWORD` está presente em `.env` antes de iniciar.
- **Mudou usuário/senha depois da primeira inicialização:** o volume conserva o banco original. Não excluir o volume para corrigir sem antes entender os dados que ele contém.
- **Não há acesso remoto:** a porta está vinculada apenas a `127.0.0.1`, para desenvolvimento local.

## Critérios de aceite da DAI-20

- [x] Configuração versionada sem senha real.
- [x] Procedimento de inicialização e teste documentado.
- [x] Contêiner PostgreSQL em execução, confirmado como `running (healthy)` no computador de desenvolvimento.
- [x] Consulta SQL de teste executada com resultado `current_database=jobmarket`, `current_user=jobmarket` e PostgreSQL 17.11.
- [ ] Checagem explícita `docker compose config --quiet` ainda não documentada como executada.

A execução e a consulta foram verificadas em saídas de terminal enviadas pela desenvolvedora. O assistente não executou Docker diretamente.\n\n**Segurança:** use `docker compose config --quiet` em vez de `docker compose config` para evitar imprimir a senha do banco no terminal.
