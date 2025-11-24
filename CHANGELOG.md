# Changelog

## November 2025

- fix most tests on Python 3.14
- support cast to `datetime.datetime`
- improve `is_subtype` for `TypedDict`s
- add `Computed` reference type, thanks sfitzgerald!
- support int dict keys in blueprint, thanks hessam!
- fix subparam mutation in the "template thing", thanks tz!
- improve docs, thanks awei!
- require newer `typing-extensions`

## September 2025

- add `dispatch_entrypoint`
- several changes to optimise argmap lookups by collapsing and consolidating layers
  - this is >10x speedup for some use cases
- always print additional diagnostics for extraneous args, thanks camillo!
- add `skip_default` arg to `beta_to_blueprint_values`, thanks charlieb!
- add special casing for tuples in `beta_argv_arg_to_string`, thanks tz!
- testing improvements

## August 2025

- mention the value of the closest ancestor for extraneous args to help with polymorphism confusion
- improve extraneous arg error message
- add `exclude` param to `asdict`, thanks andrey!
- fix subtype check in the "template thing", thanks tz!
- some cleanup of the "template thing"

## July 2025

- changes to add the "template thing" to blueprint, thanks xintao!
  - this feature is not available in the open source version and I plan to attempt to remove it from the internal version
- differentiate between untyped and zero length tuple in sequence param collection, thanks elwong!
- fix `beta_argv_arg_to_string` behaviour for list elements that are strings containing commas

## June 2025

- better error if annotation eval fails, thanks jelle!
- add `ge` and `le` validators, thanks cassirer!
- special casing to make `beta_argv_arg_to_string` handle dicts, thanks yjiao!

## May 2025

- error for duplicate class when name is ambiguous
- fix defaulting special case for nested args
- add `chz.traverse`, thanks hessam!
- better handling of type variables and meta factory casting
- special casing to make `beta_argv_arg_to_string` involving lists more compact
- improve `freeze_dict` munger static typing for optionals, thanks camillo!
- add `include_type` param to `asdict`, thanks wenda and andrei!
- internal refactoring

## March 2025

Improvements:
- add "universal CLI" via `python -m chz.universal`
- add `shallow` param to `asdict` to prevent deep copying, thanks wenda!
- look at `builtins` and `__main__` to find object factories
- support `*args` and `**kwargs` collection in blueprint
- support type variables in `is_subtype`
- fix variadics that match wildcards in more than one literal location
- fix blueprint apply to subpath with empty key, thanks hessam!
- suppert converter argument in field, thanks camillo!
- refactor param collection in blueprint
- various docs improvements, thanks andrey, csh, mtli!

Error messages:
- better error for a value with subparams specified
- improve error for blueprint type mismatch
- fix bug in `simplistic_type_of_value`
- include Python's native suggestions for `AttributeError` in blueprint attribute access, thanks yifan!

## February 2025

Improvements:
- revamp the docs
- improve casting for callables
- blindly trust explicit inheritance from protocol
- record `meta_factory_value` for non castable factory
- add `__eq__` to `castable`
- fix quoting in the `beta_blueprint_to_argv` thing
- expose the `beta_argv_arg_to_string` thing

Performance:
- add an optimisation when constructing large variadics for 6x speedup on some workloads
- rewrite the `beta_blueprint_to_argv` thing so it's now 40x faster
- make it easier to reuse `MakeResult` to save repeated blueprint make
- lru cache `inspect.getmembers_static` to speed up repeated construction
- refactoring to make optimisation easier

Error messages:
- show the full path more often when errors occur during blueprint construction, thanks mlim and gross!
- add error for case where you have duplicate classes due to `__main__` confusion
- improve error message when constructing ambiguous or mistyped callables
- minor improvements to error messages

## January 2025

Improvements:
- add basic support for functools.partial in blueprints
- allow parametrising the entrypoint in chz blueprints. this allows for a "universal" cli
- rewrie `beta_to_blueprint_values` to better support nesting and polymorphism
- improve interaction between type checking and munger
- ignore self references more consistently when there is a default value available
- better error when self references are missing a default value
- add `freeze_dict` munger, thanks camillo!
- use post init field value in hash, thanks camillo!
- prevent parameterisation of enum classes
- colourise and improve alignment of `--help` output
- various refactoring

Typing improvements:
- implement callable subtyping (especially useful for substructural typing)
- improve `is_subtype_instance` of protocols
- improve `is_subtype_instance` of None, thanks tongzhou!
- improve `is_subtype` handling of unions, thanks tongzhou!
- improve `is_subtype` handling of literals and `types.NoneType`
- better signature subtyping
- better casting for dict

## December 2024

Improvements:
- expand the error for wildcard matching variadic defaults, preventing a footgun
- optimise blueprint construction with large variadics, making a use case 2.7x faster
- add support for protocol subtyping for vitchyr use case
- pass field metadata through blueprint, for use in custom tools
- allow custom root for consistency in tree, thanks ignasi!
- fix `beta_blueprint_to_argv` with None args, thanks tongzhou!
- add test for unspecified `type(None)` trick to avoid instantiating defaulted class
- simplify some `meta_factory` logic
- fix standard `meta_factory` for `type[specialform]`

Error messages:
- mention layer name for extraneous arguments, so you know where the arg comes from
- reorder logic in cast for better errors
- more helpful error message when disallowing `__init__`, `__post_init__`, etc. thanks ebrevdo!
- other misc error message improvements
- misc internal docs

## November 2024

Two headline features for this month: references and `meta_factory` unification:
- references allow for deduplication of parameters and allow introducing indirection where some config is controlled by other teams
- `meta_factory` unification makes chz’s polymorphism more consistent and more powerful

Features:
- core of `meta_factory` unification, change default `meta_factory`
- infra for references, expose references
- use `X_values` from pre-init in `beta_to_blueprint_values`, thanks guillaume!
- give users access to methods_entrypoint blueprint
- add strict option to `Blueprint.apply`, thanks menick!
- add subpath to apply
- add override validators, thanks vineet!
- allow default values in nested_entrypoint
- make (wildcard) references not self-reference when defaulted
- recurse into dict in pretty_format
- make `meta_factory` lambda logic more robust
- support for python3.12 and 3.13

Typing features:
- basic pep 692 support
- add typeddict total=False and pep 655 support, thanks alec!
- add subtype support for pep 655 / required
- parse objects as literals
- allow casting to iterable
- allow ast eval of tuple for sequence
- better casting rules for list
- support casting pathlib
- add typeddict and callable tests

Error messages:
- improve two issues with `--help` in polymorphic command lines
- better error when we choose not to cast due to subparams
- batch errors for invalid ref targets
- improve error with reference cycles
- improve error message during blueprint evaluation
- include previous valid parent for non wildcard extraneous
- improve error mentioning closest matching parent for extraneous argument
- improve error messages on failure to interpret argument
- special case representation of objects from typing module

Internal:
- many refactoring changes and clean up, including large refactor of blueprint and changes for open source

## October 2024

- finally land support for variadic typeddicts
- add ability to attach user metadata to fields
- add better support for NewType, LiteralString, NamedTuple and other niche typing features
- add some support for PEP 646 unpacking of tuples
- add native support for casting fractions
- steps towards `meta_factory` unification. these changes make chz's polymorphism more powerful and more consistent
- allow disallowing `meta_factory`, useful in niche cases
- fix static typing of runtime typing to allow better downstream type checking

## September 2024

- add `blueprint_unspecified` to field, as generalisation of `chz.field(meta_factory=chz.factories.subclass(annot, default_cls=...))`. thanks to vitchyr for helping with this
- use `__orig_class__` to type check user defined generics, if possible
- add `chz.chz_fields` helper to access `__chz_fields__` attribute
- better error if there are no params and extraneous args

## August 2024

- add `check_field_consistency_in_tree` validator, as a way to help ensure your wildcards are doing what you want them to do
- use stdout for `--help`
- allow parsing empty tuple
- add a `const_default` validator for constant fields

## July 2024

- improvements to static types, thanks lmetz and wenda
- quick follow ups to `beta_blueprint_to_argv`, thanks hunter and noah
- improve `type_repr`, thanks davis
- minor error improvements

## June 2024

- support for polymorphic variadic generics
- fix some issues with pydantic support
- add `x_type` to improve static type checking of mungers
- add `beta_blueprint_to_argv`, thanks hunter
- fix callable subtyping with future annotations
- various improvements to `pretty_repr`, make dunder pure
- allow use of chz with abc
- add some special casing to avoid false positives with the conservative check against wildcard default factory interaction
- improve error message when validating types against a `Literal`
- improve error message when hashing chz class with unhashable fields, thanks alexk
- improve error message for unparseable type, thanks andmis
- fix typo in error message, thanks sean
- make various error messages more concise

## May 2024

- show default values in `--help`, includes some fancy logic around lambdas
- show values from unspecified_factory in `--help`, to make polymorphic construction easier to understand
- add `chz.methods_entrypoint` for easily make cli's from classes
- support mapping and sequence variadics
- basic support for pydantic validation during runtime type checking, thanks camillo
- better handling of runtime contexts for future annotations support
- support for nested classes when `meta_factory` turns strings into classes
- better support for polymorphism in `beta_blueprint_to_values`, thanks wenda
- only error for variadic failure if variadic param specified
- more docs, more tests, cleaner help output, cleaner tracebacks

## ???

Established in 2022
