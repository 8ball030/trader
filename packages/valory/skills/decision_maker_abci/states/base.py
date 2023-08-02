# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 Valory AG
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

"""This module contains the base functionality for the rounds of the decision-making abci app."""

from enum import Enum
from typing import Optional

from packages.valory.skills.abstract_round_abci.base import (
    CollectSameUntilThresholdRound,
    DeserializedCollection,
    get_name,
)
from packages.valory.skills.decision_maker_abci.payloads import MultisigTxPayload
from packages.valory.skills.market_manager_abci.bets import Bet
from packages.valory.skills.market_manager_abci.rounds import (
    SynchronizedData as MarketManagerSyncedData,
)
from packages.valory.skills.transaction_settlement_abci.rounds import (
    SynchronizedData as TxSettlementSyncedData,
)


class Event(Enum):
    """Event enumeration for the price estimation demo."""

    DONE = "done"
    NONE = "none"
    MECH_RESPONSE_ERROR = "mech_response_error"
    SLOTS_UNSUPPORTED_ERROR = "slots_unsupported_error"
    TIE = "tie"
    UNPROFITABLE = "unprofitable"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"


class SynchronizedData(MarketManagerSyncedData, TxSettlementSyncedData):
    """Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """

    @property
    def sampled_bet_index(self) -> int:
        """Get the sampled bet."""
        return int(self.db.get_strict("sampled_bet_index"))

    @property
    def sampled_bet(self) -> Bet:
        """Get the sampled bet."""
        return self.bets[self.sampled_bet_index]

    @property
    def vote(self) -> Optional[int]:
        """Get the bet's vote index."""
        vote = self.db.get_strict("vote")
        return int(vote) if vote is not None else None

    @property
    def confidence(self) -> float:
        """Get the vote's confidence."""
        return float(self.db.get_strict("confidence"))

    @property
    def is_profitable(self) -> bool:
        """Get whether the current vote is profitable or not."""
        return bool(self.db.get_strict("is_profitable"))

    @property
    def tx_submitter(self) -> str:
        """Get the round that submitted a tx to transaction_settlement_abci."""
        return str(self.db.get_strict("tx_submitter"))

    @property
    def participant_to_decision(self) -> DeserializedCollection:
        """Get the participants to decision-making."""
        return self._get_deserialized("participant_to_decision")

    @property
    def participant_to_sampling(self) -> DeserializedCollection:
        """Get the participants to bet-sampling."""
        return self._get_deserialized("participant_to_sampling")

    @property
    def participant_to_tx_prep(self) -> DeserializedCollection:
        """Get the participants to bet-placement."""
        return self._get_deserialized("participant_to_tx_prep")


class TxPreparationRound(CollectSameUntilThresholdRound):
    """A round for preparing a transaction."""

    payload_class = MultisigTxPayload
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    none_event = Event.NONE
    no_majority_event = Event.NO_MAJORITY
    selection_key = (
        get_name(SynchronizedData.tx_submitter),
        get_name(SynchronizedData.most_voted_tx_hash),
    )
    collection_key = get_name(SynchronizedData.participant_to_tx_prep)