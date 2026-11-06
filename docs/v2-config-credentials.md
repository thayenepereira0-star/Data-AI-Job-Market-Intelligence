# DAI-27 — Configuração centralizada e segurança de credenciais

Agora `src/config.py` é responsável pela leitura/validação das variáveis de ambiente. `src/database/check_connection.py` e, indiretamente, `src/database/job_loader.py`, reutilizam a mesma função `connection_settings()`, sem duplicar regras de autenticação.

## Arquivos e responsabilidade

- `.env.example`: somente nomes das variáveis e exemplos fictícios, versionado.
- `.env`: credenciais reais **somente no computador local**; já está ignorado pelo Git.
- `src/config.py`: `connection_settings()` para PostgreSQL e `adzuna_credentials()` para uso futuro da API.
- `tests/test_config.py`: testes isolados, com credenciais de teste fictícias; sem conexão à rede.

Credenciais da Adzuna são **opcionais** para a migração de CSV e a conexão ao PostgreSQL, pois a coleta via API ainda não foi implementada. A validação dessas credenciais só acontece quando `adzuna_credentials()` é chamada.

**Não compartilhe o conteúdo de `.env`, nem imprima as credenciais retornadas por `connection_settings()`.** Não use `docker compose config` sem `--quiet`, pois ele pode mostrar senhas.

## Testes no VS Code

Com `(.venv)` ativo, na raiz do repositório:

```powershell
git fetch origin
git switch feat/dai-27-config-secrets
python -m unittest discover -s tests -p "test_config.py" -v
python -m unittest discover -s tests -p "test_*.py" -v
python -m src.database.check_connection
python -m src.database.migrate_v1
```

A última linha é **somente a prévia**. Não use `--apply` neste card. O esperado para a prévia é: 128 registros lidos, 127 válidos, 1 rejeitado, 0 duplicados. O teste de conexão deve confirmar banco `jobmarket` e 7 tabelas; consulte o output real.

## Limites e critérios de aceite

- [x] Leitura e validação centralizada de configuração, sem versionar segredos.
- [x] Reutilização da configuração na conexão existente e no loader.
- [x] Testes unitários preparados, com variáveis simuladas.
- [ ] Testes executados no ambiente da desenvolvedora.
- [ ] Conexão real e prévia da migração confirmadas depois da alteração.
- [ ] Documentar os resultados e mesclar o PR.

Esta tarefa não provisiona um gerenciador externo de segredos, não acessa a API da Adzuna e não altera o banco de dados.
