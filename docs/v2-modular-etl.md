# DAI-26 — Separar extração, transformação e carga em módulos

Esta tarefa **refatora o migrador funcional da DAI-23**, mantendo a mesma interface do terminal e a mesma política de segurança: **prévia sem escrita por padrão**. O conjunto de 127 vagas já migradas permanece intocado.

## Fluxo de responsabilidades

```text
data/processed/jobs_analysis.csv
             |
             v
src/ingestion/csv_reader.py        EXTRAÇÃO
- Abre CSV; verifica colunas
- Contabiliza linhas e rejeições
             |
             v
src/processing/job_transform.py    TRANSFORMAÇÃO
- Normaliza campos
- Valida URL, empresa, salário, datas
- Identifica duplicações no CSV
             |
             v
src/database/migrate_v1.py         ORQUESTRAÇÃO
- Mostra prévia
- Só chama a carga se houver --apply
             |
             v
src/database/job_loader.py         CARGA
- Conecta ao PostgreSQL com .env
- Insere empresas, vagas, publicações
- Evita duplicação por fonte+URL/ID
- Registra execução e garante transação
```

Não foi adicionada coleta em uma API nesta etapa: o extrator existente lê o **CSV da v1**. Criar novas fontes e etapas de coleta será trabalho das DAI-28 e seguintes.

## Teste no Windows (VS Code, PowerShell)

Com o ambiente virtual `(.venv)` ativo, na raiz do projeto:

1. Atualizar a branch:

```powershell
git fetch origin
git switch feat/dai-26-modular-etl
```

2. Rodar os testes unitários (não precisam do Docker):

```powershell
python -m unittest discover -s tests -p "test_etl_v1.py" -v
```

3. Verificar a prévia com os 128 registros originais:

```powershell
python -m src.database.migrate_v1
```

A prévia esperada é: **128 lidos; 127 válidos; 0 duplicados no CSV; 1 rejeitado por empresa ausente; 127 candidatos**, sem escrita no banco.

4. Confirmar que o modo somente de leitura não mexeu no PostgreSQL:

```powershell
docker compose exec db psql -U jobmarket -d jobmarket -c "SELECT COUNT(*) AS vagas FROM jobs;"
```

Esperado, se nenhuma outra importação foi realizada: `127`.

**Não execute `--apply` nesta primeira validação.** A refatoração deve ser conferida sem alterar dados. Um teste idempotente de carga poderá ocorrer depois, mediante revisão, mantendo o mesmo comando da DAI-23.

## Limites

- A transformação mantém as regras de validação da DAI-23. Não inventa empresa nem habilidade.
- O extrator CSV não é uma coleta automatizada online.
- O loader PostgreSQL mantém gravações com transação e checagem de duplicação; o banco não é alterado durante testes unitários ou prévia.
- Os testes foram **executados no computador da desenvolvedora** em ambiente virtual Python: 4 testes aprovados em 0,108 s. A prévia também foi confirmada; o caminho de escrita da carga modular não foi reexecutado nesta tarefa.
- A arquitetura dos módulos é preparada para extensões, sem afirmar que já existe agendamento, integração API, NLP ou ML.

## Critérios de aceite
- [x] Código de extração, transformação e carga separado, com orquestrador preservado.
- [x] Testes unitários e instruções preparados.
- [x] Testes unitários executados no ambiente local (4/4 aprovados).
- [x] Prévia com mesmas contagens da DAI-23 confirmada.
- [x] Resultados de validação documentados; PR pronto para integração.

## Evidências de validação local (desenvolvedora)

- `python -m unittest discover -s tests -p "test_etl_v1.py" -v`: **4 testes passaram**, saída `Ran 4 tests in 0.108s — OK`.
- `python -m src.database.migrate_v1` (sem `--apply`): **128 lidas, 127 válidas, 0 duplicatas no CSV, 1 rejeitada (linha 124, empresa ausente)**; prévia indicou **127 candidatas e nenhuma gravação**.
- Consulta SQL no PostgreSQL: `SELECT COUNT(*) AS vagas FROM jobs;` retornou **127**.
- Limitação de cobertura: a refatoração do módulo de **carga** ainda não foi testada por nova gravação nesta tarefa; preservação dos dados e prévia foram verificadas.
