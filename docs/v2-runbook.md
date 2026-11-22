# Data AI Job Market Intelligence V2 — Execução segura

## Prévia end-to-end (não grava no PostgreSQL)

Com as dependências instaladas, execute:

```powershell
python -m src.run_v2 --sources himalayas,greenhouse,lever --query "data analyst" --country BR --greenhouse-boards kunumi --lever-sites ciandt
```

Para adicionar a Adzuna, configure `ADZUNA_APP_ID` e `ADZUNA_APP_KEY` no ambiente local e acrescente `adzuna` a `--sources`. Uma fonte que falhar não impede as demais de serem analisadas.

O programa consulta as APIs, transforma os envelopes em memória e imprime somente contagens, status e tipos de erro. **Não salva anúncios, nem chama o banco** no modo padrão.

## Carga opcional — uso restrito

`--apply --approved-storage-sources <fontes>` só deve ser utilizado após validar expressamente a retenção, o processamento e a atribuição exigidos por cada fonte. Fontes não aprovadas podem ser analisadas em memória, mas são excluídas da gravação. Este parâmetro não prova permissão legal.

**IMPORTANTE:** o projeto ainda precisa de teste controlado de carga real e reexecução idempotente com o PostgreSQL local; não considerar a DAI-30 concluída só pelos testes simulados.

## Integração

Conectores DAI-28/65/64/67 → orquestrador DAI-66 → transformação DAI-29 → prévia / carregador DAI-30.

As fontes são independentes. Se uma falhar, o relatório registra a falha sem vazar o texto da exceção. O relatório não imprime dados de vagas ou credenciais.
