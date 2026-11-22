# Diagnóstico de qualidade e armazenamento da V2

## Uso (sem gravação)

Após atualizar a branch e instalar dependências:

```powershell
python -m src.run_v2 --sources adzuna,himalayas,greenhouse,lever --query "data analyst" --country BR --greenhouse-boards kunumi --lever-sites ciandt
python -m src.database.inspect_v2_db
```

O primeiro comando retorna a seção `quality` com os motivos agregados de rejeição e a quantidade de **candidatos** a duplicatas entre fontes: mesma URL canônica, ou mesmo nome de empresa + título. Os critérios de mesmo nome/título **não demonstram duplicação**; exigem revisão humana. O diagnóstico compara **somente a coleta atual**; não cruza com os registros históricos do banco. Nenhum título, URL ou anúncio bruto é impresso.

O segundo comando faz somente `SELECT` em uma transação `READ ONLY` no PostgreSQL configurado em `.env`, mostrando totais das sete tabelas e contagens por fonte. Não aplica migração, não exclui e não insere nada. Não cole suas credenciais em issues nem relatórios.

**Importante:** nunca use `--apply` enquanto as permissões de armazenamento não estiverem verificadas.

## Condições de uso — revisão de 22/11/2026

| Fonte | Evidência oficial | Situação para retenção no projeto |
| --- | --- | --- |
| Adzuna | https://developer.adzuna.com/docs/terms_of_service | Termos permitem pesquisa pessoal/acadêmica, exigem atribuição quando dados publicados e restringem pesquisa/uso continuado por organizações; não considerar retenção histórica ilimitada automaticamente aprovada. Confirmar o escopo com Adzuna antes da carga. |
| Himalayas | https://himalayas.app/terms | Cache permitido sob condições: manter `applicationLink`, atribuição e link de origem, remoção de anúncios expirados, respeito a limites e proibição de repasse a agregadores/terceiros. O carregador atual **não implementa remoção por expiração**, portanto não ativar retenção até implementá-la e confirmar finalidade do projeto. |
| Greenhouse | https://docs.greenhouse.io/job-board | A API de anúncios públicos documenta consulta sem autenticação. Isso **não é autorização expressa de retenção histórica ou redistribuição**; avaliar finalidade e termos do portal da empresa. |
| Lever | https://github.com/lever/postings-api | API de anúncios publicados documenta consulta e criação de página de carreiras. Isso **não garante autorização de histórico/redistribuição**; avaliar finalidade e termos do portal da empresa. |

**Decisão técnica atual:** a execução em memória para diagnóstico continua habilitada; carga real exige aprovação documentada por provedor. Estes apontamentos não constituem parecer jurídico.

## Critérios para fechar esta etapa

- Entender a rejeição da Adzuna sem capturar dados pessoais ou anúncios no log
- Avaliar grupos candidatos a duplicata e evitar afirmar que `total_valid` = vagas únicas
- Conferir totais do PostgreSQL local (não pressupor que os 127 registros históricos continuam presentes sem consulta)
- Documentar, por fonte, atribuição, expiração, retenção e redistribuição antes de qualquer inserção
