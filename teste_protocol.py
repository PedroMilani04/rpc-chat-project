# teste_protocol.py  ← cria esse arquivo na raiz do projeto
import sys
sys.path.append(".")  # garante que o Python acha a pasta shared

from shared.protocol import *

# ─── Testando make_request ────────────────────────────────────────────────────
req = make_request(
    operation_id=Operations.BROADCAST,
    payload={"mensagem": "Olá geral!"},
    mode=Mode.RR
)
print("=== REQUEST ===")
print(req)

# ─── Testando make_response ───────────────────────────────────────────────────
res = make_response(
    request_id=req["request_id"],
    status="ok",
    payload={"info": "mensagem entregue"}
)
print("\n=== RESPONSE ===")
print(res)

# ─── Testando make_ack ────────────────────────────────────────────────────────
ack = make_ack(req["request_id"])
print("\n=== ACK ===")
print(ack)

# ─── Testando encode e decode ─────────────────────────────────────────────────
encoded = encode(req)
print("\n=== ENCODE (bytes que vão pelo socket) ===")
print(encoded)

decoded = decode(encoded.decode("utf-8"))
print("\n=== DECODE (voltou a ser dict) ===")
print(decoded)

# ─── Verificando que request_id bate entre req, res e ack ────────────────────
print("\n=== VERIFICAÇÃO DE IDs ===")
print(f"request_id original : {req['request_id']}")
print(f"request_id na res   : {res['request_id']}")
print(f"request_id no ack   : {ack['request_id']}")
print(f"IDs batem? {req['request_id'] == res['request_id'] == ack['request_id']}")