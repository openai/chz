## Alternatives

The most common question I get when someone first sees `chz` is "...but have you heard about X?"

Here are some values for X that I have heard of. A lot of these libraries are great; `chz` builds
off of ideas from multiple of them, executes some things differently, and also has some novel
features.

Anyway, here is a list of things `chz` is not:

(data model)

- [dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [attrs](https://www.attrs.org/en/stable/)
- [msgspec](https://jcristharif.com/msgspec/)
- [pydantic](https://docs.pydantic.dev/)
- hyperparams (internal)

(serialisation)

- [msgspec](https://jcristharif.com/msgspec/)
- [cattrs](https://catt.rs/en/stable/readme.html#features)
- [apischema](https://wyfo.github.io/apischema/)
- [marshmallow](https://marshmallow.readthedocs.io/en/stable/)
- [dacite](https://github.com/konradhalas/dacite)
- [dataclasses_json](https://github.com/lidatong/dataclasses-json)
- dump (internal)

(cli)

- [fire](https://github.com/google/python-fire)
- [appeal](https://github.com/larryhastings/appeal)
- [typer](https://typer.tiangolo.com/)
- smokey (internal)
- ein (internal)

(runtime typing)

- [typeguard](https://github.com/agronholm/typeguard)
- [trycast](https://github.com/davidfstr/trycast)
- [runtype](https://github.com/erezsh/runtype)

(config solutions)

- [hydra](https://hydra.cc/docs/intro/)
- [the other fiddle](https://github.com/google/fiddle)
- [gin](https://github.com/google/gin-config)
- [hyperstate](https://github.com/cswinter/hyperstate)

I don't think there's anything on this list that covers the same set of functionality I'm aiming
for here. I also have specific bones to pick with some of these libraries :-)

Let me know if you think there's a feature that would be constructive to add!
