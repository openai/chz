import re

import pytest

import chz
from chz.blueprint import EntrypointHelpException, ExtraneousBlueprintArg


@chz.chz
class Run1:
    name: str

    def launch(self, cluster: str):
        """Launch a job on a cluster."""
        return ("launch", self, cluster)

    def history(self):
        return ("history", self)


@chz.chz
class RunDefault:
    def launch(self, cluster: str):
        return ("launch", self, cluster)


def test_methods_entrypoint():
    assert chz.methods_entrypoint(Run1, argv=["launch", "self.name=job", "cluster=big"]) == (
        "launch",
        Run1(name="job"),
        "big",
    )
    assert chz.methods_entrypoint(Run1, argv=["history", "self.name=job"]) == (
        "history",
        Run1(name="job"),
    )

    assert chz.methods_entrypoint(RunDefault, argv=["launch", "cluster=big"]) == (
        "launch",
        RunDefault(),
        "big",
    )

    with pytest.raises(ExtraneousBlueprintArg, match="Extraneous argument 'self.cluster'"):
        chz.methods_entrypoint(Run1, argv=["launch", "self.name=job", "self.cluster=big"])


def test_methods_entrypoint_help():
    with pytest.raises(
        EntrypointHelpException,
        match="""\
Entry point: methods of test_blueprint_methods:Run1

Available methods:
  history
  launch  Launch a job on a cluster.
""",
    ):
        chz.methods_entrypoint(Run1, argv=[])

    with pytest.raises(
        EntrypointHelpException,
        match=re.escape(
            """\
WARNING: Missing required arguments for parameter(s): self.name, cluster

Entry point: test_blueprint_methods:Run1.launch

  Launch a job on a cluster.

Arguments:
  self       test_blueprint_methods:Run1  -
  self.name  str                          -
  cluster    str"""
        ),
    ):
        chz.methods_entrypoint(Run1, argv=["launch", "--help"])


@chz.chz
class RunAltSelfParam:
    name: str

    def launch(run, cluster: str):
        return ("launch", run, cluster)


def test_methods_entrypoint_self():
    assert chz.methods_entrypoint(
        RunAltSelfParam, argv=["launch", "run.name=job", "cluster=big"]
    ) == ("launch", RunAltSelfParam(name="job"), "big")

    with pytest.raises(ExtraneousBlueprintArg, match="Extraneous argument 'self.name'"):
        chz.methods_entrypoint(RunAltSelfParam, argv=["launch", "self.name=job", "cluster=big"])

    with pytest.raises(ExtraneousBlueprintArg, match="Extraneous argument 'run.name'"):
        chz.methods_entrypoint(Run1, argv=["launch", "run.name=job", "cluster=big"])


@chz.chz
class RunDefaultChild(RunDefault): ...


def test_methods_entrypoint_polymorphic():
    assert chz.methods_entrypoint(
        RunDefault, argv=["launch", "self=RunDefaultChild", "cluster=big"]
    ) == ("launch", RunDefaultChild(), "big")


def test_methods_entrypoint_transform():
    def transform(blueprint, target, method):
        if method == "launch":
            return blueprint.apply({"name": "job"}, subpath="self")
        return blueprint

    assert chz.methods_entrypoint(Run1, argv=["launch", "cluster=big"], transform=transform) == (
        "launch",
        Run1(name="job"),
        "big",
    )
