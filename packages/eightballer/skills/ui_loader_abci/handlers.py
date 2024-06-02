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

"""This module contains the handlers for the skill of ComponentLoadingAbciApp."""

import json
from typing import Optional, cast
from aea.protocols.base import Message
from packages.valory.skills.abstract_round_abci.handlers import (
    ABCIRoundHandler as BaseABCIRoundHandler,
)
from packages.valory.skills.abstract_round_abci.handlers import (
    ContractApiHandler as BaseContractApiHandler,
)
from packages.valory.skills.abstract_round_abci.handlers import (
    HttpHandler as BaseHttpHandler,
)
from packages.valory.skills.abstract_round_abci.handlers import (
    IpfsHandler as BaseIpfsHandler,
)
from packages.valory.skills.abstract_round_abci.handlers import (
    LedgerApiHandler as BaseLedgerApiHandler,
)
from packages.valory.skills.abstract_round_abci.handlers import (
    SigningHandler as BaseSigningHandler,
)
from packages.valory.skills.abstract_round_abci.handlers import (
    TendermintHandler as BaseTendermintHandler,
)
from aea.protocols.base import Message
from aea.skills.base import Handler


from packages.eightballer.protocols.websockets.dialogues import (
    WebsocketsDialogue,
    WebsocketsDialogues,
)
from packages.eightballer.protocols.websockets.message import WebsocketsMessage

from packages.eightballer.protocols.http.message import HttpMessage as UiHttpMessage

from packages.eightballer.skills.ui_loader_abci.models import UserInterfaceClientStrategy


class BaseHandler(BaseHttpHandler):
    """Base handler for logging."""

    @property
    def strategy(self) -> Optional[str]:
        """Get the strategy."""
        return cast(UserInterfaceClientStrategy, self.context.user_interface_client_strategy)


class UserInterfaceHttpHandler(BaseHandler):
    """Handler for the HTTP requests of the ui_loader_abci skill."""
    SUPPORTED_PROTOCOL = UiHttpMessage.protocol_id


    def handle(self, message: Message) -> None:

        self.context.logger.debug("Handling new http connection message in skill")
        message = cast(UiHttpMessage, message)
        dialogue = self.context.user_interface_http_dialogues.update(message)
        if dialogue is None:
            self.context.logger.error(
                "Could not locate dialogue for message={}".format(message)
            )
            return
        self.handle_http_request(message, dialogue)

    def handle_http_request(self, message: UiHttpMessage, dialogue) -> None:
        """
        We handle the http request to return the necessary files.
        """
        if self.is_api_route(message.url):
            headers, content = self.handle_api_request(message, dialogue)
        elif self.is_websocket_request(message):
            return self.handle_websocket_request(message, dialogue)
        else:
            headers, content = self.handle_frontend_request(message, dialogue)
        return self.send_http_response(message, dialogue, headers, content)

    def is_api_route(self, url: str) -> bool:
        """
        Check if the url is an api route.
        """
        parts = url.split("/")
        if "api" in parts:
            return True
        return False
    
    def is_websocket_request(self, message: UiHttpMessage) -> bool:
        if "Upgrade: websocket" in message.headers:
            return True
        return False
    
    def handle_websocket_request(self, message: UiHttpMessage, dialogue) -> None:
        """
        Handle the websocket request.
        """
        self.strategy.clients[
            dialogue.incomplete_dialogue_label.get_incomplete_version().dialogue_reference[
                0
            ]
        ] = dialogue
        self.context.logger.debug(f"Total clients: {len(self.strategy.clients)}")


    def handle_api_request(self, message: UiHttpMessage, dialogue) -> bytes:
        """
        Handle the api request.
        """
        parts = message.url.split("/")
        headers = "Content-Type: application/json; charset=utf-8\n"
        data = {}
        if len(parts) < 4:
            # in a later iteration we should return the open-api spec here.
            return headers, json.dumps(content).encode("utf-8")
        
        if parts[-1] == "agent-info":
            data = {
                "service-id": self.context.params.on_chain_service_id,
                "safe-address": self.context.params.setup_params['safe_contract_address'],
                "agent-address": self.context.agent_address,
                "agent-status": "active" if self.context.is_active else "inactive",
            }
        content = json.dumps(data).encode("utf-8")
        return headers, content

    def handle_frontend_request(self, message: UiHttpMessage, dialogue) -> bytes:
        """
        Handle the frontend request.
        """

        routes = self.context.shared_state.get("routes")
        path = "/".join(message.url.split("/")[3:])
        if path == "":
            path = "index.html"

        if routes is None:
            content = None
        else:
            content = routes.get(path, None)
        # we want to extract the path from the url
        self.context.logger.info("Received request for path: {}".format(path))

        if path is None or content is None:
            self.context.logger.warning("Context not found for path: {}".format(path))
            content = b"Not found!"
        # as we are serving the frontend, we need to set the headers accordingly
        # X-Content-Type-Options: nosniff
        # we now set headers for the responses
        if path.endswith(".html"):
            headers = "Content-Type: text/html; charset=utf-8\n"
        elif path.endswith(".js"):
            headers = "Content-Type: application/javascript; charset=utf-8\n"
        elif path.endswith(".css"):
            headers = "Content-Type: text/css; charset=utf-8\n"
        elif path.endswith(".png"):
            headers = "Content-Type: image/png\n"

        return headers, content
    

    def send_http_response(self, message: UiHttpMessage, dialogue, headers: str, content: bytes) -> None:
        """
        Send the http response.
        """
        response_msg = dialogue.reply(
            performative=UiHttpMessage.Performative.RESPONSE,
            target_message=message,
            status_code=200,
            headers=headers,
            version=message.version,
            status_text="OK",
            body=content,
        )
        self.context.outbox.put_message(message=response_msg)

class UserInterfaceWsHandler(UserInterfaceHttpHandler):
    """This class scaffolds a handler."""

    SUPPORTED_PROTOCOL = WebsocketsMessage.protocol_id

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to an envelope.

        :param message: the message
        """
        if message.performative == WebsocketsMessage.Performative.CONNECT:
            return self._handle_connect(message)

        dialogue = self.websocket_dialogues.get_dialogue(message)

        if message.performative == WebsocketsMessage.Performative.DISCONNECT:
            return self._handle_disconnect(message, dialogue)
        # it is an existing dialogue
        if dialogue is None:
            self.context.logger.error(
                "Could not locate dialogue for message={}".format(message)
            )
            return None
        if message.performative == WebsocketsMessage.Performative.SEND:
            return self._handle_send(message, dialogue)
        self.context.logger.warning(
            "Cannot handle websockets message of performative={}".format(
                message.performative
            )
        )
        return None

    def _handle_disconnect(
        self, message: Message, dialogue: WebsocketsDialogue
    ) -> None:
        """
        Implement the reaction to an envelope.

        :param message: the message
        """
        self.context.logger.info(
            "Handling disconnect message in skill: {}".format(message)
        )
        ws_dialogues_to_connections = {
            v.incomplete_dialogue_label: k for k, v in self.strategy.clients.items()
        }
        if dialogue.incomplete_dialogue_label in ws_dialogues_to_connections:
            del self.strategy.clients[
                ws_dialogues_to_connections[dialogue.incomplete_dialogue_label]
            ]
            self.context.logger.info(f"Total clients: {len(self.strategy.clients)}")
        else:
            self.context.logger.warning(
                f"Could not find dialogue to disconnect: {dialogue.incomplete_dialogue_label}"
            )

    def _handle_send(self, message: Message, dialogue) -> None:
        """
        Implement the reaction to an envelope.

        :param message: the message
        """
        # we here need to basically literate all of the handlers from the custom component
        # and then call the handle method on them.

        for handler_func in self.strategy.handlers:
            response_data = handler_func.handle(message)
            if response_data is not None:
                self.context.logger.info(
                    "Handling message in skill: {}".format(message.data)
                )
                response_message = dialogue.reply(
                    performative=WebsocketsMessage.Performative.SEND,
                    target_message=dialogue.last_message,
                    data=response_data,
                )
                self.context.outbox.put_message(message=response_message)

    @property
    def websocket_dialogues(self) -> "WebsocketsDialogues":
        """Get the http dialogues."""
        return cast(WebsocketsDialogues, self.context.user_interface_ws_dialogues)

    def _handle_connect(self, message: Message) -> None:
        """
        Implement the reaction to the connect message.
        """

        dialogue: WebsocketsDialogue = self.websocket_dialogues.get_dialogue(message)

        if dialogue is not None:
            self.context.logger.debug(
                "Already have a dialogue for message={}".format(message)
            )
            return
        else:
            client_reference = message.url
            dialogue = self.websocket_dialogues.update(message)
            response_msg = dialogue.reply(
                performative=WebsocketsMessage.Performative.CONNECTION_ACK,
                success=True,
                target_message=message,
            )
            self.context.logger.info(
                "Handling connect message in skill: {}".format(client_reference)
            )
            self.strategy.clients[client_reference] = dialogue
            self.context.outbox.put_message(message=response_msg)


ABCIHandler = BaseABCIRoundHandler
HttpHandler = BaseHttpHandler
SigningHandler = BaseSigningHandler
LedgerApiHandler = BaseLedgerApiHandler
ContractApiHandler = BaseContractApiHandler
TendermintHandler = BaseTendermintHandler
IpfsHandler = BaseIpfsHandler
