-- Keep the database constraint aligned with the API/frontend bet outcome enum.

alter table public.bet_tracker
    drop constraint if exists bet_tracker_outcome_check;

alter table public.bet_tracker
    add constraint bet_tracker_outcome_check
    check (outcome in ('win', 'loss', 'pending', 'cashed_out'));
