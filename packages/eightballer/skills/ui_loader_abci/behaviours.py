# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This package contains round behaviours of ComponentLoadingAbciApp."""

from abc import ABC
from glob import glob
from pathlib import Path
import threading
import time
import yaml
from typing import Generator, Optional, Set, Type, cast
import sys
from importlib import import_module

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.eightballer.skills.ui_loader_abci.models import Params, UserInterfaceClientStrategy
from packages.eightballer.skills.ui_loader_abci.rounds import (
    Event,
    SynchronizedData,
    ComponentLoadingAbciApp,
    ErrorRound,
    HealthcheckRound,
    SetupRound,
)
from packages.eightballer.skills.ui_loader_abci.rounds import (
    ErrorPayload,
    HealthcheckPayload,
    SetupPayload,
)


from aea.cli.utils.config import get_ipfs_node_multiaddr
from aea.skills.base import Model
from aea_cli_ipfs.ipfs_utils import DownloadError, IPFSTool


from enum import Enum
import importlib

DEFAULT_FRONTEND_DIR = "frontend"

def dynamic_import(component_name, module_name):
    module = importlib.import_module(component_name)
    sub_module = getattr(module, module_name)
    return sub_module


class HttpStatus(Enum):
    OK = 200
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500

class ComponentLoadingBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the ui_loader_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class ErrorBehaviour(ComponentLoadingBaseBehaviour):
    """ErrorBehaviour"""

    matching_round: Type[AbstractRound] = ErrorRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            #  we check the parameters to see if we should alert the user via apprise.
            error_data = yield from self.get_error_data()
            if self.params.alert_user:
                yield from self.alert_user(error_data)
            payload = ErrorPayload(sender=sender, 
                                   error_data=error_data
                                   )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
        self.set_done()

    def alert_user(self, error_data: str) -> bool:
        """Alert the user of the error."""
        # alert the user via apprise
        raise NotImplementedError
    
    def get_error_data(self) -> str:
        """Get the error data."""
        return f"Warning! Error detected: {self.synchronized_data.error_data} for {self.context.agent_address}"

    


class HealthcheckBehaviour(ComponentLoadingBaseBehaviour):
    """HealthcheckBehaviour"""

    matching_round: Type[AbstractRound] = HealthcheckRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            health_status = yield from self._check_ui_health()
            payload = HealthcheckPayload(sender=sender, 
                                      health_data=health_status
                                   )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
        self.set_done()

    def _check_ui_health(self) -> bool:
        """Check the health of the UI."""
        status = HttpStatus.OK
        if status is HttpStatus.OK:
            yield Event.DONE
        yield Event.ERROR

class SetupBehaviour(ComponentLoadingBaseBehaviour):
    """SetupBehaviour"""

    matching_round: Type[AbstractRound] = SetupRound

    @property
    def strategy(self) -> Optional[str]:
        """Get the strategy."""
        return cast(UserInterfaceClientStrategy, self.context.user_interface_client_strategy)



    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address

            ui_setup_ok = Event.DONE
            if self.params.user_interface_enabled:
                author, component_name, directory, config = self.custom_ui_component
                self.context.logger.info(f"Loading User Interface: {component_name}")
                ui_setup_ok = yield from self.load_ui(directory)
                if config.get("behaviours", False):
                    ui_behaviours_ok = yield from self.load_behaviours(author, component_name, directory, config)
                else:
                    ui_behaviours_ok = Event.DONE
                if config.get("handlers", False):
                    ui_handlers_ok = yield from self.load_handlers(author, component_name, directory, config)
                else:
                    ui_handlers_ok = Event.DONE

                self.context.logger.info(f"UI setup status: {ui_setup_ok}")
                self.context.logger.info(f"UI handlers status: {ui_handlers_ok}")
                self.context.logger.info(f"UI behaviours status: {ui_behaviours_ok}")

            payload = SetupPayload(sender=sender, 
                                   setup_data=Event.Done.value if all([
                                        ui_setup_ok is Event.DONE,
                                        ui_behaviours_ok is Event.DONE,
                                        ui_handlers_ok is Event.DONE]
                                   ) else Event.ERROR.value
                                   )
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
        self.set_done()

    # here we load the UI from the custom parameter passed in the setup payload

    def load_ui(self, directory) -> bool:
        """Load the UI from the setup_data."""
        self.context.logger.info(f"Generating routes for the UI in {directory}...")
        self.strategy.routes = self.generate_routes(directory)
        self.context.logger.info(f"Routes generated: {len(self.strategy.routes)} routes.")
        sys.path += [str(Path(__file__).resolve().parent
                            .parent
                            .parent
                            .parent
                            .parent
        / directory.parent)]
        self.context.logger.info(f"Added {directory} to the path.")
        if not self.strategy.routes:
            return Event.ERROR
        yield Event.DONE

    def generate_routes(self, directory) -> dict:
        """
        We generate a mapping of routes based on all the files found in the frontend directory.
        We read the files into memory and store them in the routes dict.
        """
        routes = {}
        for path in glob(str(Path(directory/ "build") / "**" / "*"), recursive=True):
            data = Path(path)
            if data.is_file():
                route = data.relative_to(str(directory / "build"))
                routes[str(route)] = data.read_bytes()
        return routes

    @property
    def custom_ui_component(self) -> bool:
        """Check laod of custom UI component."""
        author, component_name = self.params.user_interface_name.split("/")
        directory = Path("vendor") / author / "customs" / component_name 
        config = yaml.safe_load((directory / "component.yaml").read_text())
        return author, component_name, directory, config

    
    def load_behaviours(self, author, component_name, directory, config) -> bool:
        """
        load in the behaviours for the ComponentLoadingRoundBehaviour
        """
        def behaviour_runner(behaviour, interval = 1):
            # We need to convert this into a Task to executed by the task runner.
            behaviour.setup()
            while True:
                behaviour.act()
                self.context.logger.debug(f"Behaviour {behaviour} running...")
                time.sleep(interval)

        configs = config['behaviours']
        module = dynamic_import(component_name, "behaviours")
        
        for behaviour_config in configs:
            class_name = behaviour_config["class_name"]
            kwargs = behaviour_config.get("kwargs", {})
            behaviour = getattr(module, class_name)
            behaviour = behaviour(name=class_name,skill_context=self.context, **kwargs)
            self.context.user_interface_client_strategy.behaviours.append(behaviour)
            task = threading.Thread(target=behaviour_runner, args=(behaviour,))
            task.start()
            self.context.logger.info(f"Behaviour {class_name} loaded and running.")
        self.context.logger.info(f"Behaviour {behaviour} started.")
        yield Event.DONE

    def load_handlers(self, author, component_name, directory, config) -> bool:
        """
        load in the handlers for the ComponentLoadingRoundBehaviour
        """

        configs = config['handlers']
        module = dynamic_import(component_name, "handlers")
        
        for handler_config in configs:
            class_name = handler_config["class_name"]
            handler_kwargs = handler_config.get("kwargs", {})
            handler = getattr(module, class_name)
            handler = handler(name=class_name,skill_context=self.context, **handler_kwargs)
            self.context.user_interface_client_strategy.handlers.append(handler)
            self.context.logger.info(f"Handler {class_name} loaded.")
        yield Event.DONE


class ComponentLoadingRoundBehaviour(AbstractRoundBehaviour):
    """ComponentLoadingRoundBehaviour"""

    initial_behaviour_cls = SetupBehaviour
    abci_app_cls = ComponentLoadingAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        ErrorBehaviour,
        HealthcheckBehaviour,
        SetupBehaviour
    ]
