# shared/protocol.py
import json
import uuid

# ─── Operações disponíveis ────────────────────────────────────────────────────
class Operations:
    LOGIN           = "login"
    BROADCAST       = "broadcast"
    PRIVATE_MSG     = "private_msg"
    LIST_USERS      = "list_users"
    LOGOUT          = "logout"

# ─── Modos de comunicação ─────────────────────────────────────────────────────
class Mode:
    R   = "R"    # dispara e esquece
    RR  = "RR"   # espera resposta
    RRA = "RRA"  # espera resposta e manda confirmação

# ─── Monta uma requisição ─────────────────────────────────────────────────────
def make_request(operation_id, payload=None, mode=Mode.RR):
    return {
        "request_id":   str(uuid.uuid4()),  # ID único gerado automaticamente
        "operation_id": operation_id,
        "mode":         mode,
        "payload":      payload or {}
    }

# ─── Monta uma resposta ───────────────────────────────────────────────────────
def make_response(request_id, status="ok", payload=None):
    return {
        "request_id": request_id,   # mesmo ID da requisição original
        "status":     status,       # "ok" ou "error"
        "payload":    payload or {}
    }

# ─── Monta um ACK (confirmação do cliente pro servidor) ───────────────────────
def make_ack(request_id):
    return {
        "request_id": request_id,
        "ack":        True
    }

# ─── Serialização: objeto Python → string pra mandar pelo socket ──────────────
def encode(data: dict) -> bytes:
    return (json.dumps(data) + "\n").encode("utf-8")
    #                          ↑
    #               "\n" serve como separador de mensagens no socket

# ─── Desserialização: string recebida → objeto Python ─────────────────────────
def decode(raw: str) -> dict:
    return json.loads(raw.strip())