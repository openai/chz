# Philosophy

There are a few different ideas in `chz` and not all of them are equally valuable or well designed.

In particular, if you're using `chz` just for the object model, I'm not sure how useful it is
compared to other libraries (see [alternatives](./92_alternatives.md) for many options).

Configuration may never be easy! How you design your configurations may well be a bigger deal
than what configuration system you use. I have seen `chz` used in ways and at a scale that I
never envisioned.

I hope this library is useful to you, and if not, I hope it encourages you to build the tools
you want (because you deserve them!)

The rest of this page is just rambling about things.

## Modularity

We've had some monolithic configuration at OpenAI that made systems painful to work
with. Some ways to avoid this are deeper nested configuration hierarchies (so things can be
self-contained / testable / reusable) and polymorphism (to reduce the cartesian product
explosion of config space).

I hope that the `chz` classes you define can be reused across multiple entrypoints. At some
point, trying to do everything within a single entrypoint makes it hard to create a great
experience for all users. Sharing `chz` classes but specialising your own entrypoint with
partial application seems like a good balance.

As a corollary, this has made me hesitant about adding things to `chz` class definitions that
primarily affect `Blueprint`s that use those classes (e.g. even `blueprint_unspecified`).

One downside of pushing for modularity and self-contained-ness is that it makes situations
where you want to access fields of parents or siblings more awkward. I recommend at least using
validators to ensure consistency. (There are some undocumented features that help with this,
and I'll likely add more things here in the future)

Wildcards are a somewhat controversial feature, but they do at least lower the cost of having
fairly deep configuration hierarchies.

## Partial application

I've seen some users have a bit of a learning curve when first encountering `chz.Blueprint`, but
I'm actually fairly convinced repeated partial application and a one-time initialisation and
validation is a good pattern in a lot of use cases (even if you don't use the command line stuff).

If you find yourself doing `chz.replace` a lot, ask yourself if you should be using `Blueprint`!

## Managing state

`chz` objects are immutable in the sense that you cannot reassign a field. This was a design
choice informed by scars from a previous system (and one that I think has been quite healthy).

Note however that fields on `chz` objects can be mutable objects. It can be convenient to have state
on your configuration objects (e.g. this lets you reuse your polymorphic hierarchy). Currently,
I recommend patterns like:

```python
@chz.chz
class Config:
    state: types.SimpleNamespace

    def get_state(self):
        return self.state

    def set_state(self, state):
        if state is None:
            self.state.value = 0
        else:
            self.state.value = state.value

    def mutate(self):
        self.state.value += 1
```

Not coincidentally, this will remind you of the pattern I use in `fiddle` (OpenAI's dataloader).

Currently, I leave the details of state management to downstream applications, but let me know
if you think I should merge some of these things into `chz`.

### [Next section — Alternatives](./92_alternatives.md)
