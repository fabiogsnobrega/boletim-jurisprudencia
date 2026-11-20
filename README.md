# Boletim de Jurisprudência

**Aplicação publicada:** [Acessar o Boletim de Jurisprudência](https://boletim-jurisprudencia.streamlit.app/)

Aplicação em desenvolvimento para organização, consulta e revisão humana de decisões de interesse em Direito Administrativo e Militar. A licença ainda não foi escolhida; o projeto não deve ser apresentado como open source até essa decisão e a inclusão do arquivo de licença.

Objetivo

Desenvolver uma ferramenta acessível a usuários sem conhecimento técnico, capaz de reunir informações de boletins de jurisprudência publicados por fontes oficiais, organizá-las em uma base de dados estruturada e permitir sua consulta e exportação.

Tribunais de interesse

- Tribunal Regional Federal da 1ª Região (TRF1)
- Tribunal Regional Federal da 5ª Região (TRF5)
- Turma Nacional de Uniformização (TNU)
- Turma Regional de Uniformização da 5ª Região (TRU5)

Na inicialização, o sistema registra URLs padrão para TRF1, TRF5 e TNU. O TRU5 está
listado como tribunal de interesse, mas não possui URL padrão cadastrada.

A disponibilidade e o formato das publicações variam. A importação por URL exige link direto ao PDF em domínio oficial; páginas que listam boletins não são coletadas automaticamente. A extração heurística pode errar segmentação, campos e relevância, exige revisão humana, e não foi validada por amostra representativa de PDFs reais. OCR é apenas um stub e não está implementado. A análise Gemini só é solicitada após ação explícita e autorização do usuário; o texto selecionado é enviado ao Google.

Funcionalidades disponíveis

- Cadastro manual e importação de decisões a partir de PDF, texto e links diretos para PDFs oficiais.
- Extração heurística, classificação temática e avisos de validação, com revisão humana antes da inclusão.
- Consulta em cartões, radar de alertas, filtros e base tabular.
- Exportação integral restrita a usuários autenticados.
- Registro da origem, fila de revisão e eventos de auditoria.
- Sugestões de atualização de endereços oficiais sujeitas à aprovação administrativa.

Tecnologias utilizadas

- Python e Streamlit para a aplicação web.
- SQLite para persistência local.
- Pandas e openpyxl para exportação tabular.
- pypdf para leitura de PDFs e requests para requisições HTTP.
- Integração opcional com Gemini, chamada somente por ação explícita do usuário.

Princípios do projeto

- Licença ainda não definida; não apresentar o projeto como open source até a escolha e inclusão de uma licença.
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
│   ├── validator/              # avisos de qualidade para revisão humana
│   └── ai_analyst/             # análise Gemini opcional, chamada explicitamente
├── database/
│   ├── connection.py           # conexão, esquema e migrações SQLite
│   ├── models.py               # contrato tipado dos dados de decisão
│   └── repositories.py         # consultas e operações de persistência
├── services/
│   ├── authentication.py       # verificação de credenciais e hash de senha
│   └── audit.py                # registro de ações administrativas
├── assets/
│   └── style.css               # estilos da interface
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

### Instalação e execução local

Requer Python 3.11 ou superior e Streamlit 1.55 ou superior. No PowerShell, a partir da raiz do repositório:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run src/app.py
```

O banco SQLite local é criado em `data/jurisprudencia.db` ao iniciar. Para uma demonstração local persistida, rode `python src/seed_data.py`; o comando recusa bases não vazias e cria também um usuário de teste para o ciclo mensal. `python src/seed_data.py --reset-demo` apaga decisões locais antes de carregar a demonstração e deve ser usado apenas em uma base descartável. A seed não roda automaticamente na hospedagem.

As credenciais administrativas são configuradas no arquivo `.streamlit/secrets.toml` na raiz do repositório (crie a pasta e o arquivo se ainda não existirem) ou pelas variáveis `BOLETIM_ADMIN_EMAIL` e `BOLETIM_ADMIN_PASSWORD`. O formato do arquivo é `admin_email = "..."` e `admin_password = "..."`. O fluxo de demonstração local mantém uma credencial deliberadamente simples; não execute a seed nem use credenciais de desenvolvimento em produção. A autenticação atual não substitui OIDC nem outros controles operacionais de produção.

### Identidade Visual Editorial e Minimalista

O design da aplicação foi padronizado em alinhamento ao portfólio profissional:
- **Fundo Marfim:** `#F3EFE6`
- **Azul-Marinho Editorial:** `#263D50` para cabeçalhos e títulos serifados (`Playfair Display`)
- **Acentos Sóbrios:** Azul acinzentado (`#B9C9D0`), Verde-sálvia (`#C5CEBA`), Terracota suave (`#D8B9A8`) e Areia (`#D8D0B5`)
- **Tipografia:** Serifada para títulos de precedentes e sem serifa (`Inter`) para textos, filtros e controles
- **Espaçamento Otimizado:** Remoção do padding ocioso no topo para aproveitamento total da tela
- **Acessibilidade:** Suporte nativo à preferência por movimento reduzido (`prefers-reduced-motion`) e foco visível por teclado

### Ferramenta de Comparação e Benchmark (Teste de Fogo)

Para confrontar a seleção manual de decisões com a extração automatizada:
```powershell
python scripts/avaliar_precisao_extracao.py --pdf caminho/boletim.pdf --processos "0801234-56.2026.4.05.0000,0001111-22.2026.4.01.0000"
```
Gera automaticamente a taxa de concordância, recall e aponta eventuais falsos negativos para afinamento cirúrgico dos agentes.

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
testes. Os testes de banco usam arquivos temporários; esses artefatos não devem ser
versionados nem enviados ao GitHub.

### Implantação e persistência

O ponto de entrada é `src/app.py`; o comando deve ser executado na raiz do
repositório: `streamlit run src/app.py`. No Streamlit Community Cloud, selecione
esse arquivo como entrypoint, escolha Python 3.12 e configure os secrets no painel
da hospedagem. `GEMINI_API_KEY` é opcional; credenciais administrativas devem ficar
fora do Git.

O banco `data/jurisprudencia.db` é local e criado automaticamente. Se um visitante
abrir uma instalação cuja base ainda não tem decisões, a interface mostra três exemplos
fictícios em memória, em modo somente leitura. Eles não são gravados no banco, não são
julgados reais e não devem ser citados. Um clone novo não cria automaticamente usuários
de demonstração; o login administrativo depende das credenciais configuradas em secrets.

O Streamlit Community Cloud não garante persistência dos arquivos locais entre
reinicializações ou reconstruções. Portanto, a configuração SQLite local serve apenas
para demonstração descartável; não use dados reais ou que precisem ser preservados até
adotar um banco externo persistente com backup. Arquivos enviados no uploader ficam em
memória durante o fluxo, não são armazenados como arquivos permanentes.

Próximas etapas para uso continuado

1. Configurar autenticação gerenciada por OIDC e papéis de autorização para produção.
   Streamlit oferece `st.login`, `st.user` e `st.logout` integrados ao OIDC; a verificação
   atual por senha fica como transição para desenvolvimento. [Documentação oficial](https://docs.streamlit.io/develop/concepts/connections/authentication).
2. Adotar armazenamento persistente hospedado antes de operar com dados reais; o SQLite
   local não é armazenamento durável no Community Cloud.
3. Revisar cobertura e retenção da trilha de auditoria para todos os caminhos de alteração.
4. Expandir testes para PDFs oficiais representativos, OCR e casos difíceis de segmentação.
5. Só então definir coleta por tribunal, com escopo e limites específicos por fonte.

Status

Em desenvolvimento e validação incremental.

Aviso

Este projeto tem finalidade de pesquisa, organização e consulta de informações jurisprudenciais. Os registros deverão ser conferidos nas respectivas fontes oficiais. Resumos e classificações produzidos pelo sistema não substituem o conteúdo oficial das publicações.

Licença e contribuições

A licença de uso e distribuição ainda precisa ser decidida pelo responsável. Até essa escolha, não há concessão explícita de licença open source. As instruções de contribuição serão definidas após essa decisão.
