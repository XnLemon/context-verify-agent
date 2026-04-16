create table if not exists contracts (
    id text primary key,
    title text not null,
    type text not null,
    status text not null,
    author text not null,
    owner_username text null,
    content text not null,
    source_file_name text null,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create table if not exists review_records (
    id serial primary key,
    contract_id text not null unique references contracts(id) on delete cascade,
    summary jsonb not null,
    report_overview text not null,
    key_findings jsonb not null default '[]'::jsonb,
    next_actions jsonb not null default '[]'::jsonb,
    generated_at timestamptz not null
);

create table if not exists review_issues (
    id serial primary key,
    review_id int not null references review_records(id) on delete cascade,
    contract_id text not null,
    issue_id text not null,
    type text not null,
    severity text not null,
    message text not null,
    suggestion text not null,
    location text null,
    status text not null,
    start_index int null,
    end_index int null,
    constraint uq_review_issue_id unique(review_id, issue_id)
);

create table if not exists chat_threads (
    id serial primary key,
    contract_id text not null references contracts(id) on delete cascade,
    member_id int not null default 0,
    created_at timestamptz not null,
    updated_at timestamptz not null,
    constraint uq_chat_thread_contract_member unique(contract_id, member_id)
);

create table if not exists chat_messages (
    id serial primary key,
    thread_id int not null references chat_threads(id) on delete cascade,
    contract_id text not null,
    msg_id text not null,
    role text not null,
    content text not null,
    timestamp text not null,
    created_at timestamptz null
);

create table if not exists history_logs (
    id serial primary key,
    contract_id text not null references contracts(id) on delete cascade,
    member_id int not null default 0,
    event_id text not null,
    type text not null,
    title text not null,
    description text not null,
    created_at timestamptz not null,
    metadata_json jsonb not null default '{}'::jsonb
);

create table if not exists members (
    id serial primary key,
    username text not null unique,
    display_name text not null,
    role text not null,
    member_type text not null,
    password_hash text not null,
    password_salt text not null,
    is_active boolean not null default true,
    avatar_url text null,
    theme_preference text not null default 'system',
    font_scale text not null default 'medium',
    notify_enabled boolean not null default true,
    created_at timestamptz not null,
    updated_at timestamptz not null,
    last_login_at timestamptz null
);

create table if not exists auth_sessions (
    id serial primary key,
    member_id int not null references members(id) on delete cascade,
    token text not null unique,
    created_at timestamptz not null,
    expires_at timestamptz not null
);

create table if not exists login_audits (
    id serial primary key,
    member_id int not null references members(id) on delete cascade,
    login_at timestamptz not null,
    ip_address text null,
    user_agent text null
);

create index if not exists idx_contracts_status_updated_at on contracts(status, updated_at);
create index if not exists idx_contracts_owner_updated_at on contracts(owner_username, updated_at);
create index if not exists idx_review_issues_contract_status_severity on review_issues(contract_id, status, severity);
create index if not exists idx_chat_messages_contract_created_at on chat_messages(contract_id, created_at);
create index if not exists idx_history_logs_contract_member_created_at on history_logs(contract_id, member_id, created_at desc);
create index if not exists idx_members_role_active on members(role, is_active);
create index if not exists idx_auth_sessions_member_expires on auth_sessions(member_id, expires_at);
create index if not exists idx_login_audits_member_login_at on login_audits(member_id, login_at desc);
