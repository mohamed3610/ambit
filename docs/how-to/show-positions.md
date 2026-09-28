# Show roles as positions

Leadership is often modelled as a field ("this team's lead") — but that
duplicates what a grant already says. `ambit` lets a role *be* the title:
mark it a **position**, and read it back on the pages its scope applies to.

## Mark a role as a position

```python
from ambit.models import Role

Role.objects.create(name="Team Lead", is_position=True)
```

Now "Team Lead" isn't just permission to do things in a team — it's a title
displayed on that team's page, sourced from the grant, not a separate field.

## Read the positions on a page

`positions_for(model, objects)` returns the positions held on each of a set of
objects — for a list or a detail page:

```python
from ambit.services.positions import positions_for

teams = Team.objects.all()
positions = positions_for(Team, teams)
# -> for each team, who holds a position there and under what title
```

Use it to render "Team Lead · Heba Adel" on each team without a
`lead` column anywhere.

## Read a person's own titles

`positions_of(user)` lists the titles a login holds and where — for a
person's own profile page:

```python
from ambit.services.positions import positions_of

for position in positions_of(request.user):
    ...  # e.g. "Regional manager — North"
```

## Why this instead of a field

- One source of truth: the grant *is* the leadership. No `lead_id` to keep in
  sync with who actually has access.
- Reassign by re-granting: move the role to someone else and the title moves
  with the access, atomically.
- Scope-aware: a position narrower than the page is qualified ("North" on a
  department that spans regions).
