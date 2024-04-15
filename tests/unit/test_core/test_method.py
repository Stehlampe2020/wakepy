from __future__ import annotations

import re
import sys

import pytest

from wakepy.core import DBusMethodCall
from wakepy.core.activation import has_enter, has_exit, has_heartbeat
from wakepy.core.method import Method, MethodOutcome, MethodOutcomeValue, select_methods
from wakepy.core.registry import MethodRegistryError, get_method, get_methods

if sys.version_info < (3, 8):  # pragma: no-cover-if-py-gte-38
    import typing_extensions as typing
else:  # pragma: no-cover-if-py-lt-38
    import typing

if typing.TYPE_CHECKING:
    from wakepy.core import DBusMethod


class TestMethod(Method):
    __test__ = False  # for pytest
    mode = "_test"


def test_overridden_methods_autodiscovery():
    """The enter_mode, heartbeat and exit_mode methods by default do nothing
    (on the Method base class). In subclasses, these are usually overriden.
    Check that detecting the overridden methods works correctly
    """

    class WithEnterAndExit(TestMethod):
        def enter_mode(self):
            return

        def exit_mode(self):
            return

    method1 = WithEnterAndExit()

    assert has_enter(method1)
    assert has_exit(method1)
    assert not has_heartbeat(method1)

    class WithJustHeartBeat(TestMethod):
        def heartbeat(self):
            return

    method2 = WithJustHeartBeat()

    assert not has_enter(method2)
    assert not has_exit(method2)
    assert has_heartbeat(method2)

    class WithEnterExitAndHeartBeat(TestMethod):
        def heartbeat(self):
            return

        def enter_mode(self):
            return

        def exit_mode(self):
            return

    method3 = WithEnterExitAndHeartBeat()

    assert has_enter(method3)
    assert has_exit(method3)
    assert has_heartbeat(method3)

    class SubWithEnterAndHeart(WithJustHeartBeat):
        def enter_mode(self):
            return

    method4 = SubWithEnterAndHeart()
    assert has_enter(method4)
    assert has_heartbeat(method4)
    assert not has_exit(method4)

    class SubWithEnterAndExit(WithEnterAndExit):
        def enter_mode(self):
            return 123

    method5 = SubWithEnterAndExit()
    assert has_enter(method5)
    assert has_exit(method5)
    assert not has_heartbeat(method5)


@pytest.mark.usefixtures("empty_method_registry")
def test_not_possible_to_define_two_methods_with_same_name(testutils, monkeypatch):
    somename = "Some name"

    class SomeMethod(TestMethod):
        name = somename

    # It is not possible to define two methods if same name
    with pytest.raises(
        MethodRegistryError, match=re.escape('Duplicate Method name "Some name"')
    ):

        class SomeMethod(TestMethod):  # type: ignore # noqa:F811
            name = somename

    testutils.empty_method_registry(monkeypatch)

    # Now as the registry is empty it is possible to define method with
    # the same name again
    class SomeMethod(TestMethod):  # type: ignore # noqa:F811
        name = somename


@pytest.mark.usefixtures("provide_methods_a_f")
def test_select_methods():
    (MethodB, MethodD, MethodE) = get_methods(["B", "D", "E"])

    methods = [MethodB, MethodD, MethodE]

    # These can also be filtered with a blacklist
    assert select_methods(methods, omit=["B"]) == [MethodD, MethodE]
    assert select_methods(methods, omit=["B", "E"]) == [MethodD]
    # Extra 'omit' methods do not matter
    assert select_methods(methods, omit=["B", "E", "foo", "bar"]) == [
        MethodD,
    ]

    # These can be filtered with a whitelist
    assert select_methods(methods, use_only=["B", "E"]) == [MethodB, MethodE]

    # If a whitelist contains extra methods, raise exception
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Methods ['bar', 'foo'] in `use_only` are not part of `methods`!"
        ),
    ):
        select_methods(methods, use_only=["foo", "bar"])

    # Cannot provide both: omit and use_only
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Can only define omit (blacklist) or use_only (whitelist), not both!"
        ),
    ):
        select_methods(methods, use_only=["B"], omit=["E"])


def test_method_defaults():
    """tests the Method enter_mode, exit_mode and heartbeat defaults"""
    m = Method()
    assert m.enter_mode() is None  # type: ignore
    assert m.heartbeat() is None  # type: ignore
    assert m.exit_mode() is None  # type: ignore


@pytest.mark.usefixtures("provide_methods_a_f")
def test_method_string_representations():
    MethodB = get_method("B")
    method = MethodB()
    assert method.__str__() == "<wakepy Method: MethodB>"
    assert method.__repr__() == f"<wakepy Method: MethodB at {hex(id(method))}>"


def test_process_dbus_call(dbus_method: DBusMethod):
    method = Method()
    # when there is no dbus adapter..
    assert method.dbus_adapter is None
    # we get RuntimeError
    with pytest.raises(
        RuntimeError,
        match=".*cannot process dbus method call.*as it does not have a DBusAdapter",
    ):
        assert method.process_dbus_call(DBusMethodCall(dbus_method))


def test_methodoutcome(assert_strenum_values):
    assert_strenum_values(MethodOutcome, MethodOutcomeValue)
