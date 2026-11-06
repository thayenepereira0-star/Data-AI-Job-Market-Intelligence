# DAI-22 — Conectar Python ao PostgreSQL

O módulo `src.database.check_connection` realiza uma consulta SQL **somente de leitura**, confirma a identidade do banco e conta tabelas no schema `public`.

## Preparação no Windows — PowerShell

Na raiz do repositório, com Docker Desktop aberto:

```powershell
docker compose ps
```

O serviço `db` deve estar `running (healthy)`. O arquivo `.env` deve existir e conter `POSTGRES_PASSWORD` real e os valores de `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PORT`. **Não cole a senha no terminal nem no GitHub.**

Opcional: criar ambiente virtual caso ainda não exista:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale somente as dependências novas da v2:

```powershell
python -m pip install -r requirements-v2.txt
```

Execute a verificação:

```powershell
python -m src.database.check_connection
```

Resultado esperado neste ponto da v2, após DAI-21:

```text
Conexão OK! Banco: jobmarket; usuário: jobmarket; tabelas public: 7.
```

O módulo usa `POSTGRES_HOST=127.0.0.1` por padrão, porque a porta do Compose foi exposta apenas ao host local. Caso o Python rode **dentro de outro contêiner** da mesma rede do Compose, o host passará a ser `db` (etapa futura).

## Limites

- Não cria nem altera tabelas, não importa vagas e não executa treinamento de IA.
- Não considera os resultados de consulta como prova de que há dados nas tabelas.
- Falhas de conexão exibem apenas o tipo de erro, sem mensagem detalhada que possa conter segredos.
- Uma consulta bem-sucedida ainda precisa ser verificada no ambiente local da desenvolvedora para concluir DAI-22.
