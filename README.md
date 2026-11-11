# Boletim de Jurisprudência

Projeto open source para coleta, organização, consulta e exportação de boletins de jurisprudência relacionados ao Direito Administrativo e Militar.

Objetivo

Desenvolver uma ferramenta acessível a usuários sem conhecimento técnico, capaz de reunir informações de boletins de jurisprudência publicados por fontes oficiais, organizá-las em uma base de dados estruturada e permitir sua consulta e exportação.

Fontes previstas

- Tribunal Regional Federal da 1ª Região (TRF1)
- Tribunal Regional Federal da 5ª Região (TRF5)
- Turma Nacional de Uniformização (TNU)
- Turma Regional de Uniformização da 5ª Região (TRU5)

A disponibilidade e o formato das publicações de cada fonte serão verificados durante o desenvolvimento.

Funcionalidades planejadas

- Coleta de boletins publicados nas fontes oficiais.
- Extração e padronização dos dados.
- Organização e consulta dos registros.
- Filtros por tribunal, período e matéria, conforme a disponibilidade dos dados.
- Exportação integral da base em formato tabular.
- Identificação da fonte original e controle da qualidade dos dados.

Tecnologias previstas

- Python para processamento e coleta de dados.
- Interface web para consulta.
- Banco de dados estruturado.
- Exportação para CSV e Excel.

As tecnologias definitivas serão confirmadas durante a implementação.

Princípios do projeto

- Código aberto e documentação acessível.
- Fidelidade às fontes oficiais.
- Rastreabilidade das informações.
- Transparência sobre limitações e dados não disponíveis.
- Validação das informações extraídas antes de sua utilização.

Estrutura atual

```text
src/
├── app.py                     # composição da aplicação Streamlit
├── modules/
│   ├── noticias.py             # cartões do noticiário
│   ├── jurisprudencia.py       # radar e base tabular
│   ├── importacao.py           # entrada por PDF, texto e link oficial
│   ├── administracao.py        # registro manual e configuração
│   ├── revisao.py              # fluxo de revisão e observação sugerida
│   └── prazos.py               # formatação compartilhada de prazos
├── agents/
│   ├── pdf_reader/             # PDF para texto, sem alterar conteúdo
│   ├── decision_parser/        # texto para candidatos estruturados
│   ├── classifier/             # ramo jurídico e pontuação heurística
│   └── validator/              # avisos de qualidade para revisão humana
├── database/
│   ├── connection.py           # conexão, esquema e migrações SQLite
│   ├── models.py               # contrato tipado dos dados de decisão
│   └── repositories.py         # consultas e operações de persistência
├── services/
│   ├── authentication.py       # verificação de credenciais e hash de senha
│   └── audit.py                # registro de ações administrativas
└── extractor.py                # fachada de compatibilidade para a pipeline
```

Os componentes em `agents/` são funções especializadas e determinísticas. Eles não
pesquisam livremente na web nem gravam decisões na base. A coleta continua limitada
a links oficiais aprovados e PDFs fornecidos; a inclusão definitiva depende da revisão
humana. O validador apenas sinaliza campos incertos e preserva o texto original.

O fluxo de leitura pode ser alterado e testado por etapa: PDF → texto → segmentação
de decisões → classificação → avisos de validação → revisão. `extractor.py` mantém os
nomes antigos de importação e o pacote `database` mantém as funções públicas atuais,
evitando uma migração simultânea da aplicação inteira.

### Leitor de PDF avançado e OCR

O módulo `src/agents/pdf_reader/reader.py` expõe:
- `extrair_texto_pdf_por_pagina(arquivo_bytes)`: decompõe o arquivo página a página retornando `(num_pagina, texto, vazia)`. Isso viabiliza processar seletivamente páginas sem texto digital nativo.
- `extrair_texto_pdf(arquivo_bytes)`: mantém a assinatura tradicional concatenada para retrocompatibilidade.
- `src/agents/pdf_reader/ocr.py`: provê a função stub `ocr_pagina(imagem_bytes)` desenhada para conexão de motor de OCR (ex.: Tesseract) estritamente nas páginas assinaladas como vazias.

### Prevenção de Duplicatas e Sugestão de Relevância

- **Identificação Unívoca via Hash:** cada decisão possui um hash SHA-256 gerado a partir de tribunal, processo de origem, título e tese/conteúdo, com índice único no banco de dados e evento em auditoria na tentativa de reinserção.
- **Sugestão de Relevância Temática:** o classificador (`ClassificadorJurisprudenciaML.sugerir_relevancia`) calcula a aderência e o nível de confiança heurística do julgado, orientando a conferência na tela de importação e na fila de revisão.

Executar a aplicação

```powershell
streamlit run src/app.py
```

O acesso administrativo requer `admin_email` e `admin_password` em
`.streamlit/secrets.toml` (arquivo ignorado pelo Git) ou nas secrets do serviço de
hospedagem. Não reutilize nem publique credenciais de desenvolvimento. Novas senhas
do responsável são armazenadas com hash PBKDF2; registros antigos migram para hash
quando o responsável entra com a senha válida.

Executar os testes

```powershell
python -m pytest
```

O `pyproject.toml` define o diretório de código (`src`) e o modo de importação dos
testes. Os testes de banco usam arquivo temporário e não tocam a base local.

Próximos passos antes da publicação online

1. Configurar autenticação gerenciada por OIDC e papéis de autorização para produção.
   Streamlit oferece `st.login`, `st.user` e `st.logout` integrados ao OIDC; a verificação
   atual por senha fica como transição para desenvolvimento. [Documentação oficial](https://docs.streamlit.io/develop/concepts/connections/authentication).
2. Decidir armazenamento persistente hospedado: o banco atual é SQLite local, que pode
   não persistir em todos os provedores de hospedagem.
3. Completar a trilha de auditoria para todos os caminhos de alteração e manter política
   de retenção dos eventos.
4. Expandir testes para PDFs oficiais representativos, OCR e casos difíceis de segmentação.
5. Só então definir coleta por tribunal, com escopo e limites específicos por fonte.

Status

Em desenvolvimento e validação incremental.

Aviso

Este projeto tem finalidade de pesquisa, organização e consulta de informações jurisprudenciais. Os registros deverão ser conferidos nas respectivas fontes oficiais. Resumos e classificações produzidos pelo sistema não substituem o conteúdo oficial das publicações.

Contribuições

As instruções para instalação, execução e contribuição serão adicionadas conforme o projeto evoluir.
