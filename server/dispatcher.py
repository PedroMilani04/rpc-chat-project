# server/dispatcher.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared.protocol import decode, encode, make_response, make_ack, Operations, Mode

class Dispatcher:
    def __init__(self, chat_service):
        # recebe a instância do serviço — vai chamar os métodos dela
        self.service = chat_service

    def handle(self, raw: str, socket_file, usuario_atual: list):
        """
        Ponto de entrada: recebe a mensagem crua do socket e despacha.

        'socket_file' é o arquivo do socket (usado pra escrever de volta).
        'usuario_atual' é uma lista com um elemento — o nome do usuário
        autenticado nessa conexão. Usamos lista pra poder modificar de
        dentro das funções (workaround do Python pra referência mutável).
        """
        try:
            req = decode(raw)
        except Exception:
            self._send(socket_file, make_response("?", "error", {"msg": "JSON inválido."}))
            return

        request_id   = req.get("request_id", "?")
        operation_id = req.get("operation_id")
        payload      = req.get("payload", {})
        mode         = req.get("mode", Mode.RR)

        # ─── monta o writer: função que envia string pro cliente ──────────────
        def writer(mensagem: str):
            """
            Empacota uma mensagem de servidor como notificação e envia.
            Usado pelo ChatService pra mandar broadcasts e privados.
            """
            notificacao = {
                "request_id": "server-push",   # não é resposta a nenhum request
                "status":     "ok",
                "payload":    {"msg": mensagem}
            }
            self._send(socket_file, notificacao)

        # ─── despacha pra operação correta ────────────────────────────────────
        resultado = self._despachar(
            operation_id, payload, usuario_atual, writer
        )

        # ─── modo R: não envia resposta ───────────────────────────────────────
        if mode == Mode.R:
            return

        # ─── modos RR e RRA: envia resposta ──────────────────────────────────
        resposta = make_response(request_id, resultado["status"], resultado)
        self._send(socket_file, resposta)

        # ─── modo RRA: espera ACK do cliente ──────────────────────────────────
        if mode == Mode.RRA:
            try:
                raw_ack = socket_file.readline()
                ack = decode(raw_ack)
                if ack.get("ack") and ack.get("request_id") == request_id:
                    print(f"[ACK recebido] request_id={request_id}")
            except Exception:
                print(f"[ACK não recebido] request_id={request_id}")

    # ─── Despacha para o método certo no ChatService ──────────────────────────
    def _despachar(self, operation_id, payload, usuario_atual, writer):
        """
        Lê o operation_id e chama o método correspondente no serviço.
        Retorna sempre um dict com pelo menos {"status": "ok"} ou {"status": "error"}.
        """

        if operation_id == Operations.LOGIN:
            usuario = payload.get("usuario")
            senha   = payload.get("senha")
            res = self.service.login(usuario, senha, writer)
            if res["status"] == "ok":
                usuario_atual[0] = usuario  # registra quem está nessa conexão
            return res

        # a partir daqui, todas as operações exigem login
        if not usuario_atual[0]:
            return {"status": "error", "msg": "Não autenticado."}

        if operation_id == Operations.BROADCAST:
            mensagem = payload.get("mensagem", "")
            return self.service.broadcast(usuario_atual[0], mensagem)

        if operation_id == Operations.PRIVATE_MSG:
            destinatario = payload.get("destinatario")
            mensagem     = payload.get("mensagem", "")
            return self.service.mensagem_privada(usuario_atual[0], destinatario, mensagem)

        if operation_id == Operations.LIST_USERS:
            return self.service.listar_usuarios()

        if operation_id == Operations.LOGOUT:
            res = self.service.logout(usuario_atual[0])
            usuario_atual[0] = None  # limpa o usuário da conexão
            return res

        return {"status": "error", "msg": f"Operação desconhecida: {operation_id}"}

    # ─── Envia um dict pelo socket ────────────────────────────────────────────
    def _send(self, socket_file, data: dict):
        try:
            socket_file.write(encode(data).decode("utf-8"))
            socket_file.flush()  # garante que os bytes saem imediatamente
        except Exception as e:
            print(f"[Dispatcher] Erro ao enviar: {e}")