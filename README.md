# Forense ⚖

Uma plataforma análoga ao Doctoralia, mas para o setor jurídico: conecta
**clientes** a **advogados** e **escritórios de advocacia**.

Este repositório contém o primeiro milestone, focado na **visão do cliente**:
buscar e filtrar advogados e escritórios por área de atuação. O cadastro dos três
tipos de conta (cliente, advogado e escritório) também está implementado. O
painel do advogado/escritório está intencionalmente marcado como
*"to be implemented"*.

## Stack

| Camada    | Tecnologia                                                   |
| --------- | ------------------------------------------------------------ |
| Backend   | FastAPI · SQLAlchemy 2 (async) · Pydantic v2 · JWT           |
| Frontend  | React 18 · TypeScript · Vite · React Router · Axios          |
| Banco     | SQLite (dev, zero infra) · Postgres-ready via `DATABASE_URL` |

## Arquitetura (backend)

Arquitetura em camadas com fronteiras explícitas, pensada para escalar:

```
api/         Controllers (routers) + injeção de dependência (composition root)
  └── depende de →
services/    Regras de negócio / casos de uso (sem detalhes de HTTP nem de SQL)
  └── depende de →
repositories/ Acesso a dados (Repository pattern, troca de persistência isolada)
  └── opera sobre →
models/      Entidades ORM (SQLAlchemy)
schemas/     DTOs de entrada/saída (Pydantic) — desacoplam API ↔ domínio
core/        Configuração, banco, segurança, exceções de domínio
```

**Padrões de design empregados**

- **Repository pattern** (`repositories/`) — isola persistência; serviços nunca
  tocam SQL diretamente, facilitando testes e troca de storage.
- **Service layer** (`services/`) — regras de negócio centralizadas (email único,
  OAB única, "escritório exige ≥ 1 advogado") fora de controllers e ORM.
- **Strategy** (`services/oab_validation.py`) — a validação da OAB é uma
  interface plugável. Hoje usa um `NoopOABValidator` (validação adiada, perfil
  fica "OAB pendente"); um validador real entra sem tocar no fluxo de cadastro.
- **DTO / mapeamento** (`schemas/`) — separa o contrato da API do modelo de dados.
- **Dependency Injection** (`api/dependencies.py`) — único ponto que monta o
  grafo de objetos; trivial de sobrescrever em testes.
- **Factory** (`create_app`, `get_oab_validator`, `get_settings`).
- **Unit of Work** — a sessão async é a unidade transacional; cadastros de
  escritório (com advogados novos) commitam atomicamente.

### Modelo de domínio

- `User` é a raiz de autenticação (email, senha, `role`). Cada papel tem um
  perfil 1:1: `Client`, `Lawyer` ou `Firm`.
- `Lawyer` guarda a OAB em **dois campos** (`oab_uf` + `oab_number`), além de
  `LawyerEducation` (formações/pós), `LawyerLanguage` (idiomas), tempo de
  atuação, e N:N com `PracticeArea` (áreas de atuação).
- `Firm` guarda razão social, CNPJ e registro OAB do escritório, e é **composto
  por ≥ 1 advogado** (`firm_lawyers`), que podem já existir ou ser criados no
  cadastro.

## Como rodar

### Backend (porta 8000)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Na primeira execução o banco SQLite é criado e populado (áreas de atuação +
dados demo). Docs interativas em http://localhost:8000/docs.

### Frontend (porta 5173)

```bash
cd frontend
npm install
npm run dev
```

Acesse http://localhost:5173. O Vite faz proxy de `/api` para o backend, então
não há configuração de CORS necessária em dev.

## Contas de demonstração

| Papel     | Email                              | Senha      |
| --------- | ---------------------------------- | ---------- |
| Advogada  | ana.advogada@forense.dev           | senha1234  |
| Advogado  | carlos.tributario@forense.dev      | senha1234  |
| Escritório| contato@martinssouza.adv.br        | senha1234  |

## API principal

| Método | Rota                                  | Descrição                              |
| ------ | ------------------------------------- | -------------------------------------- |
| GET    | `/api/v1/practice-areas`              | Lista áreas de atuação                 |
| GET    | `/api/v1/lawyers?practice_area_id=&q=`| Busca advogados (filtro + texto)       |
| GET    | `/api/v1/lawyers/{id}`                | Perfil detalhado do advogado           |
| GET    | `/api/v1/firms?practice_area_id=&q=`  | Busca escritórios                      |
| GET    | `/api/v1/firms/{id}`                  | Perfil detalhado do escritório         |
| POST   | `/api/v1/register/client`             | Cadastro de cliente                    |
| POST   | `/api/v1/register/lawyer`             | Cadastro de advogado (com OAB)         |
| POST   | `/api/v1/register/firm`               | Cadastro de escritório (com advogados) |
| POST   | `/api/v1/auth/login`                  | Login (retorna JWT)                    |
| GET    | `/api/v1/auth/me`                     | Usuário autenticado                    |

## Próximos passos

- Validação real da OAB (implementar uma `OABValidator` concreta).
- Painel do advogado/escritório (edição de perfil, gestão de advogados, leads).
- Migrações com Alembic (substituir o `create_all` de startup).
- Paginação na UI e ordenação/relevância na busca.
- Testes (pytest + httpx) — a arquitetura desacoplada já está pronta para mocks.
