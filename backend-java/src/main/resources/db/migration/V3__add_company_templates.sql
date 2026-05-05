create table if not exists template_tags (
    id serial primary key,
    name text not null unique,
    color text not null default '#2563eb',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null
);

create table if not exists company_templates (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    content text not null default '',
    tags jsonb not null default '[]'::jsonb,
    created_by int references members(id) on delete cascade,
    updated_by int references members(id) on delete cascade,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null,
    is_deleted boolean not null default false
);

create table if not exists template_clauses (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    content text not null default '',
    tags jsonb not null default '[]'::jsonb,
    created_by int references members(id) on delete cascade,
    updated_by int references members(id) on delete cascade,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null,
    is_deleted boolean not null default false
);

create index if not exists idx_company_templates_created_by on company_templates(created_by);
create index if not exists idx_company_templates_updated_by on company_templates(updated_by);
create index if not exists idx_company_templates_created_at on company_templates(created_at);
create index if not exists idx_company_templates_is_deleted on company_templates(is_deleted);
create index if not exists idx_company_templates_tags on company_templates using gin(tags);
create index if not exists idx_template_clauses_created_by on template_clauses(created_by);
create index if not exists idx_template_clauses_updated_by on template_clauses(updated_by);
create index if not exists idx_template_clauses_created_at on template_clauses(created_at);
create index if not exists idx_template_clauses_is_deleted on template_clauses(is_deleted);
create index if not exists idx_template_clauses_tags on template_clauses using gin(tags);
