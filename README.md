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
| Cliente   | cliente@forense.dev                | senha1234  |
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

## Agendamento flexível (composição de etapas)

Cada advogado/escritório monta seu **próprio fluxo** combinando quatro
configurações independentes — não há "modos" fixos no código:

| Configuração          | Opções                                                        |
| --------------------- | ------------------------------------------------------------- |
| Triagem               | desabilitada · opcional · obrigatória                         |
| Exibição da agenda    | imediata · após a triagem · não exibir                        |
| Aprovação             | automática · manual                                           |
| Pagamento (modelado)  | não cobrar · antes da confirmação · após a confirmação        |

O **motor de fluxo** ([app/services/booking/flow.py](backend/app/services/booking/flow.py))
deriva, a partir dessas configurações, um pipeline ordenado de etapas
(`resolve_steps` — a única fonte da composição/ordem):
`TRIAGE → AGENDA → APPROVAL → PAYMENT(before) → [CONFIRMED] → PAYMENT(after)`.
Cada etapa é um `Step` autocontido ([steps.py](backend/app/services/booking/steps.py));
adicionar uma etapa nova = uma classe `Step` + uma linha no resolvedor. Os
estados do agendamento (`PENDING`, `AWAITING_APPROVAL`, `CONFIRMED`, `REJECTED`,
`CANCELLED`, `COMPLETED`) e as transições de ciclo de vida ficam numa tabela
única. O frontend renderiza o fluxo **dinamicamente** a partir dos descritores
retornados pela API — sem lógica de "modo" no React.

Endpoints principais:

| Método | Rota                                          | Descrição                                  |
| ------ | --------------------------------------------- | ------------------------------------------ |
| GET    | `/api/v1/providers/{user_id}/booking-flow`    | Fluxo resolvido + questionário (público)   |
| GET    | `/api/v1/providers/{user_id}/slots`           | Horários abertos derivados (público)       |
| POST   | `/api/v1/bookings`                            | Cliente inicia uma solicitação             |
| POST   | `/api/v1/bookings/{id}/triage` · `/slot` · `/payment` | Ações do cliente nas etapas        |
| POST   | `/api/v1/bookings/{id}/approve` · `/reject` · `/complete` | Ações do provider               |
| POST   | `/api/v1/bookings/{id}/cancel`                | Cancelamento (qualquer parte)              |
| GET/PUT| `/api/v1/me/booking-configuration`            | Provider configura seu fluxo               |
| CRUD   | `/api/v1/me/booking-configuration/questions`  | Perguntas de triagem (por provider)        |
| GET/PUT| `/api/v1/me/availability` · `/rules`          | Provider edita a grade semanal recorrente  |
| CRUD   | `/api/v1/me/availability/exceptions`          | Bloqueios pontuais (feriados, férias)      |

### Disponibilidade (grade semanal + bloqueios)

A agenda não é cadastrada hora a hora. O provider declara uma **grade semanal
recorrente** (`AvailabilityRule`: dia da semana + faixa de horas) — pintada numa
interface visual em [BookingConfigPage](frontend/src/pages/BookingConfigPage.tsx)
— e **bloqueios pontuais** (`AvailabilityException`: feriados, férias). Os slots
de uma hora oferecidos ao cliente são **derivados** dessas regras menos os
bloqueios menos o que já está reservado, para um horizonte rolante
([availability_service.py](backend/app/services/availability_service.py)); um
`AvailabilitySlot` só é materializado quando o cliente de fato reserva. Convenção
de relógio: as horas da grade são tratadas como **UTC** de ponta a ponta.

Os três demos vêm com configurações distintas: Ana (Doctoralia-like), Carlos
(triagem obrigatória + agenda após triagem + aprovação manual) e o escritório
(triagem opcional + sem agenda pública + aprovação manual). No frontend, abra o
perfil de um provider (como cliente) para ver o fluxo, ou
`/painel/agendamento` (como provider) para configurá-lo.

### Testes

```bash
cd backend && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest          # cobre os 4 fluxos, posicionamento de pagamento, guardas e ciclo de vida
```

## Próximos passos

- Validação real da OAB (implementar uma `OABValidator` concreta).
- Restante do painel do advogado/escritório (gestão de solicitações, leads).
- Integração real de meios de pagamento (hoje apenas modelado).
- Migrações com Alembic (substituir o `create_all` de startup).
- Paginação na UI e ordenação/relevância na busca.
