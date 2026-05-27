-- Keep public user emails canonical so account bootstrap cannot bypass
-- ownership checks with casing or whitespace variants.

update public.users
    set email = lower(btrim(email))
    where email is not null and email <> lower(btrim(email));

alter table public.users drop constraint if exists users_email_normalized_check;
alter table public.users
    add constraint users_email_normalized_check check (email is null or email = lower(btrim(email)));

create unique index if not exists idx_users_email_normalized
    on public.users (lower(email))
    where email is not null;
