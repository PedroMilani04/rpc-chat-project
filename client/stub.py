# client/stub.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import socket
import queue
from shared.protocol import (
    make_request, make_ack, encode, decode,
    Operations, Mode
)

class ChatStub:
    def __init__(self, host="localhost", port=5000):
        self.host = host
        self.port = port
        self.socket_file = None  # começa sem conexão
        # fila usada para roteamento: a thread de recebimento coloca aqui
        # as respostas RPC; a thread principal consome daqui
        self._response_queue = queue.SimpleQueue()

    # ─── Conexão ──────────────────────────────────────────────────────────────
    def conectar(self):
        """Abre o socket e conecta no servidor."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        self.socket_file = s.makefile(mode="rw", encoding="utf-8")
        print(f"[Stub] Conectado em {self.host}:{self.port}")

    def desconectar(self):
        """Fecha o socket."""
        if self.socket_file:
            self.socket_file.close()

    # ─── Métodos públicos (o que o cliente vê) ────────────────────────────────
    def login(self, usuario, senha):
        """RR — precisa saber se o login deu certo."""
        return self._call(
            operation_id=Operations.LOGIN,
            payload={"usuario": usuario, "senha": senha},
            mode=Mode.RR
        )

    def broadcast(self, mensagem):
        """R — dispara e não espera resposta."""
        return self._call(
            operation_id=Operations.BROADCAST,
            payload={"mensagem": mensagem},
            mode=Mode.R
        )

    def mensagem_privada(self, destinatario, mensagem):
        """RR — precisa saber se o destinatário existe."""
        return self._call(
            operation_id=Operations.PRIVATE_MSG,
            payload={"destinatario": destinatario, "mensagem": mensagem},
            mode=Mode.RR
        )

    def listar_usuarios(self):
        """RR — retorna a lista de usuários online."""
        return self._call(
            operation_id=Operations.LIST_USERS,
            payload={},
            mode=Mode.RR
        )

    def logout(self):
        """RR — confirma que saiu."""
        return self._call(
            operation_id=Operations.LOGOUT,
            payload={},
            mode=Mode.RR
        )

    # ─── Motor interno do RPC ─────────────────────────────────────────────────
    def _call(self, operation_id, payload, mode):
        """
        Aqui acontece o RPC de verdade:
        1. monta a requisição
        2. serializa e manda pelo socket
        3. se for RR ou RRA, espera resposta
        4. se for RRA, manda ACK
        5. retorna o resultado
        """
        req = make_request(operation_id, payload, mode)

        # ─── envia a requisição ───────────────────────────────────────────────
        self.socket_file.write(encode(req).decode("utf-8"))
        self.socket_file.flush()

        # ─── modo R: dispara e esquece ────────────────────────────────────────
        if mode == Mode.R:
            return None

        # ─── modos RR e RRA: espera resposta via fila ─────────────────────────
        # A thread de recebimento é a ÚNICA que lê o socket;
        # ela coloca as respostas aqui e a thread principal consome.
        res = self._response_queue.get()

        # ─── modo RRA: manda confirmação de recebimento ───────────────────────
        if mode == Mode.RRA:
            ack = make_ack(req["request_id"])
            self.socket_file.write(encode(ack).decode("utf-8"))
            self.socket_file.flush()
            print(f"[Stub] ACK enviado para request_id={req['request_id'][:8]}...")

        return res