from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static


def _parameter_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _coerce_parameter(value: str, template: Any) -> Any:
    if isinstance(template, bool):
        return value == "true"
    if isinstance(template, int) and not isinstance(template, bool):
        return int(value)
    if isinstance(template, float):
        return float(value)
    return value


class ParameterForm(Vertical):
    """Reusable scalar parameter form backed by discovered strategy defaults."""

    def __init__(self, parameters: dict[str, Any], **kwargs: Any):
        super().__init__(**kwargs)
        self.parameters = parameters

    def compose(self) -> ComposeResult:
        if not self.parameters:
            yield Static("No configurable parameters.", id="no-parameters")
            return
        for index, (name, value) in enumerate(self.parameters.items()):
            yield Label(name)
            if isinstance(value, bool):
                yield Select(
                    [("True", "true"), ("False", "false")],
                    value=_parameter_value(value),
                    id=f"parameter-{index}",
                )
            else:
                yield Input(value=_parameter_value(value), id=f"parameter-{index}")

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for index, (name, template) in enumerate(self.parameters.items()):
            widget = self.query_one(f"#parameter-{index}")
            raw = widget.value
            result[name] = _coerce_parameter(str(raw), template)
        return result


class StartDialog(ModalScreen[dict[str, Any] | None]):
    """Collect the operational mode and parameters before starting a strategy."""

    CSS = """
    StartDialog {
        align: center middle;
        background: #000000 55%;
    }

    #start-dialog {
        width: 72;
        height: 24;
        padding: 1 2;
        border: solid #79d6c9;
        background: #162127;
    }

    #dialog-title {
        height: 2;
        text-style: bold;
        color: #79d6c9;
    }

    #parameter-form {
        height: 1fr;
        margin: 1 0;
        overflow-y: auto;
    }

    #mode-select {
        width: 24;
        margin: 0 0 1 0;
    }

    #dialog-error {
        height: 2;
        color: #ff8a80;
    }

    #dialog-actions {
        height: 3;
        align-horizontal: right;
    }

    #dialog-actions Button {
        margin-left: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, strategy: dict[str, Any], default_mode: str = "paper"):
        super().__init__()
        self.strategy = strategy
        self.default_mode = default_mode

    def compose(self) -> ComposeResult:
        with Vertical(id="start-dialog"):
            yield Static("RUN STRATEGY", id="dialog-title")
            yield Static(f"Strategy: {self.strategy['id']}\nBroker: Alpaca")
            yield Label("Mode")
            yield Select(
                [("Paper", "paper"), ("Live", "live")],
                value=self.default_mode,
                id="mode-select",
            )
            yield Label("Parameters")
            yield ParameterForm(self.strategy.get("parameters", {}), id="parameter-form")
            yield Static("", id="dialog-error")
            with Horizontal(id="dialog-actions"):
                yield Button("Cancel", id="cancel")
                yield Button("Continue", id="confirm-start", variant="success")

    def submit(self) -> None:
        try:
            parameters = self.query_one(ParameterForm).values()
        except ValueError as exc:
            self.query_one("#dialog-error", Static).update(str(exc))
            return
        mode = self.query_one("#mode-select", Select).value
        if mode not in {"paper", "live"}:
            self.query_one("#dialog-error", Static).update("Select Paper or Live mode.")
            return
        self.dismiss({"strategy_id": self.strategy["id"], "mode": mode, "parameters": parameters})

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-start":
            self.submit()
        elif event.button.id == "cancel":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ParametersDialog(ModalScreen[dict[str, Any] | None]):
    """Edit persisted strategy configuration without starting a run."""

    CSS = """
    ParametersDialog {
        align: center middle;
        background: #000000 55%;
    }

    #parameters-dialog {
        width: 72;
        height: 24;
        padding: 1 2;
        border: solid #79d6c9;
        background: #162127;
    }

    #parameters-title {
        height: 2;
        text-style: bold;
        color: #79d6c9;
    }

    #parameters-actions {
        height: 3;
        align-horizontal: right;
    }

    #parameters-actions Button {
        margin-left: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, strategy: dict[str, Any]):
        super().__init__()
        self.strategy = strategy

    def compose(self) -> ComposeResult:
        with Vertical(id="parameters-dialog"):
            yield Static(f"EDIT PARAMETERS · {self.strategy['id']}", id="parameters-title")
            yield ParameterForm(self.strategy.get("parameters", {}), id="parameter-form")
            with Horizontal(id="parameters-actions"):
                yield Button("Cancel", id="cancel-parameters")
                yield Button("Save", id="save-parameters", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-parameters":
            self.dismiss(None)
            return
        try:
            self.dismiss({"strategy_id": self.strategy["id"], "parameters": self.query_one(ParameterForm).values()})
        except ValueError:
            return

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmLiveDialog(ModalScreen[bool]):
    """Require an explicit human acknowledgement before launching live trading."""

    CSS = """
    ConfirmLiveDialog {
        align: center middle;
        background: #000000 55%;
    }

    #confirm-live-dialog {
        width: 62;
        height: 15;
        padding: 1 2;
        border: solid #ff8a80;
        background: #162127;
    }

    #confirm-live-title {
        height: 2;
        text-style: bold;
        color: #ff8a80;
    }

    #confirm-live-actions {
        height: 3;
        margin-top: 1;
        align-horizontal: right;
    }

    #confirm-live-actions Button {
        margin-left: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, strategy_id: str):
        super().__init__()
        self.strategy_id = strategy_id

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-live-dialog"):
            yield Static("CONFIRM LIVE TRADING", id="confirm-live-title")
            yield Static(
                f"Start {self.strategy_id} with REAL capital?\n\nBroker: Alpaca\nMode: LIVE"
            )
            with Horizontal(id="confirm-live-actions"):
                yield Button("Cancel", id="cancel-live")
                yield Button("Confirm Live", id="confirm-live", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-live")

    def action_cancel(self) -> None:
        self.dismiss(False)