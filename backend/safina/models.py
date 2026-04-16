"""Pydantic models for Safina Pay API."""

from decimal import Decimal
from typing import Any, Optional, Union
from pydantic import BaseModel, field_validator, model_validator


def _to_str(v: Any) -> str:
    """Coerce int/float to str for flexible API responses."""
    if v is None:
        return ""
    return str(v)


class Network(BaseModel):
    network_id: int
    network_name: str
    link: Optional[str] = None
    address_explorer: Optional[str] = None
    tx_explorer: Optional[str] = None
    block_explorer: Optional[str] = None
    info: Optional[str] = None
    status: int


class Wallet(BaseModel):
    wallet_id: Union[int, str]
    network: Union[int, str]
    wallet_type: Optional[Union[int, str]] = None
    name: str
    info: Optional[str] = None
    addr: Optional[str] = ""
    addr_info: Optional[str] = None
    myUNID: Optional[str] = None
    tokenShortNames: Optional[str] = None


class WalletDetail(BaseModel):
    wallet_name: str
    info: Optional[str] = None
    network: Union[int, str]
    wallet_type: Optional[Union[int, str]] = None
    myFlags: Optional[str] = None
    unid: Optional[str] = None
    slist: Optional[dict] = None
    addrs: Optional[str] = None


class Token(BaseModel):
    id: Optional[Union[int, str]] = None
    wallet_id: Optional[Union[int, str]] = None
    network: Optional[Union[int, str]] = None
    token: str
    value: Union[str, int, float]  # Safina may return comma-string or float
    decimals: Optional[Union[int, str]] = None
    value_hex: Optional[str] = None

    @property
    def value_decimal(self) -> Decimal:
        """Convert Safina value to Decimal."""
        v = str(self.value)
        return Decimal(v.replace(",", "."))


class TokenInfo(BaseModel):
    token: str  # "network:::TOKEN" format
    c: Union[str, int, float]  # commission multiplier
    cMin: Union[str, int, float]  # min commission
    cMax: Union[str, int, float]  # max commission

    @property
    def network_id(self) -> str:
        return self.token.split(":::")[0]

    @property
    def token_name(self) -> str:
        return self.token.split(":::")[-1].split("###")[0]


class UserToken(BaseModel):
    network_name: str
    token: str
    value: float


class Transaction(BaseModel):
    model_config = {"extra": "allow"}

    id: Union[int, str]
    tx: Optional[str] = None  # blockchain tx hash, null until broadcast
    token: Optional[str] = None
    token_name: Optional[str] = None
    to_addr: Optional[str] = None
    value: Union[str, int, float] = "0"
    value_hex: Optional[str] = None
    unid: Optional[str] = None
    init_ts: Optional[Union[int, str]] = None
    min_sign: Optional[Union[int, str]] = None
    wait: Optional[list] = None
    signed: Optional[list] = None
    info: Optional[str] = None

    @property
    def value_decimal(self) -> Decimal:
        v = str(self.value)
        return Decimal(v.replace(",", "."))


class SignedTransaction(BaseModel):
    to_addr: str
    tx_value: str
    tx: Optional[str] = None
    init_ts: int
    info: Optional[str] = None
    token: Optional[str] = None


class PendingSignature(BaseModel):
    token: str
    to_addr: str
    tx_value: str
    init_ts: int
    unid: str


class CreateWalletRequest(BaseModel):
    network: str
    info: str = ""
    slist: Optional[dict] = None


class SendTransactionRequest(BaseModel):
    token: str  # "network:::TOKEN###wallet_name"
    to_address: str
    value: str  # decimal value
    info: str = ""
    json_info: Optional[dict] = None


class RejectTransactionRequest(BaseModel):
    reason: str = ""
