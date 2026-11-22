# Próxima etapa: qualidade, duplicatas e indicadores (V2)

Execução local reportada em 22/11/2026: Adzuna 20 coletados, 19 válidos e 1 rejeitado (título/empresa/URL ausente); Himalayas 20/20, Greenhouse 6/6, Lever 76/76. Total 122 coletados, 121 válidos. Zero grupos com mesma URL entre fontes; um grupo de dois anúncios com mesma empresa+título, **ainda não confirmado como duplicação**.

Histórico informado: 127 vagas, 127 anúncios, 82 empresas, 1 fonte (Adzuna), 2 execuções; competências vazias. Não somar 121 e 127 como vagas únicas.

## Diagnóstico histórico, sem escrita

```powershell
git pull --ff-only origin main
python -m src.database.history_profile
```

O comando define transação READ ONLY e executa somente SELECT. Calcula ausência de descrição, data de publicação, contrato, modalidade, salário, datas futuras, distribuição mensal UTC, top 10 empresas, fontes, grupos de mesma empresa+título e vagas sem publicação associada. Exibe números amostrais, não estimativas de todo o mercado brasileiro.

## Avaliar a coincidência interfontes

O relatório da coleta atual contém um grupo candidato com dois registros; não inclui seus campos individuais. Não há evidência para concluir que sejam a mesma vaga. Conferir manualmente link, empresa, cargo, cidade, descrição e data antes de qualquer deduplicação. Não remover nenhum anúncio automaticamente.

## Portão de autorização para armazenamento

Ver também docs/v2-quality-and-permissions.md. Nenhuma fonte está aprovada automaticamente para carga permanente:

| Fonte | Pendência antes de --apply |
| --- | --- |
| Adzuna | Confirmar retenção, atribuição, finalidade acadêmica e uso continuado |
| Himalayas | Confirmar finalidade, atribuição e implementar remoção de anúncios expirados |
| Greenhouse | Revisar termos da plataforma e do site da empresa, prazo e redistribuição |
| Lever | Revisar termos da plataforma e do site da empresa, prazo e redistribuição |

Consulta HTTP pública não equivale a licença irrestrita de retenção ou redistribuição. Não utilizar --apply sem aprovação documentada por provedor.

## Próximas decisões

Após a saída real de history_profile: analisar taxas de ausência dos campos e o perfil temporal; examinar a dupla suspeita sem excluir registros; priorizar os indicadores SQL de qualidade e preparar regras de expiração e procedência antes da carga de novas APIs.