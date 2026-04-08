# server/chat_service.py
import hashlib
from datetime import datetime

class ChatService:
    def __init__(self):
        # ─── usuários cadastrados: {"nome": "senha_hash"} ─────────────────────
        self.usuarios_cadastrados = {
            "alice": self._hash("1234"),
            "bob":   self._hash("abcd"),
            "carol": self._hash("senha"),
        }

        # ─── clientes conectados: {"nome": socket_writer} ─────────────────────
        # socket_writer é a função que o dispatcher vai registrar pra enviar
        # mensagens de volta pra cada cliente
        self.clientes_conectados = {}

    # ─── Utilitário interno ───────────────────────────────────────────────────
    def _hash(self, senha: str) -> str:
        """Transforma senha em hash SHA256 antes de guardar/comparar."""
        return hashlib.sha256(senha.encode()).hexdigest()

    def _timestamp(self) -> str:
        """Retorna horário atual formatado."""
        return datetime.now().strftime("%H:%M:%S")

    # ─── Autenticação ─────────────────────────────────────────────────────────
    def login(self, usuario: str, senha: str, writer) -> dict:
        """
        Valida usuário e senha.
        'writer' é a função de envio do socket — guardamos pra mandar
        mensagens pra esse cliente no futuro (ex: broadcast recebido).
        """
        if usuario not in self.usuarios_cadastrados:
            return {"status": "error", "msg": "Usuário não encontrado."}

        if self.usuarios_cadastrados[usuario] != self._hash(senha):
            return {"status": "error", "msg": "Senha incorreta."}

        if usuario in self.clientes_conectados:
            return {"status": "error", "msg": "Usuário já está conectado."}

        # registra o cliente com sua função de envio
        self.clientes_conectados[usuario] = writer

        # avisa todo mundo que alguém entrou
        self._notificar_todos(
            remetente="servidor",
            msg=f"[ {usuario} entrou no chat ]"
        )

        print(f"[{self._timestamp()}] {usuario} conectou.")
        return {"status": "ok", "msg": f"Bem-vindo, {usuario}!"}

    def logout(self, usuario: str) -> dict:
        """Remove cliente e avisa os outros."""
        if usuario in self.clientes_conectados:
            del self.clientes_conectados[usuario]
            self._notificar_todos(
                remetente="servidor",
                msg=f"[ {usuario} saiu do chat ]"
            )
            print(f"[{self._timestamp()}] {usuario} desconectou.")

        return {"status": "ok"}

    # ─── Operações do chat ────────────────────────────────────────────────────
    def broadcast(self, remetente: str, mensagem: str) -> dict:
        """Manda mensagem pra todos os clientes conectados."""
        texto = f"[{self._timestamp()}] {remetente}: {mensagem}"
        self._notificar_todos(remetente=remetente, msg=texto)
        return {"status": "ok"}

    def mensagem_privada(self, remetente: str, destinatario: str, mensagem: str) -> dict:
        """Manda mensagem só pra um cliente específico."""
        if destinatario not in self.clientes_conectados:
            return {"status": "error", "msg": "Usuário não encontrado ou offline."}

        texto = f"[{self._timestamp()}] (privado) {remetente} → você: {mensagem}"

        # envia só pro destinatário
        self.clientes_conectados[destinatario](texto)

        # confirmação pro remetente também
        self.clientes_conectados[remetente](
            f"[{self._timestamp()}] (privado) você → {destinatario}: {mensagem}"
        )

        return {"status": "ok"}

    def listar_usuarios(self) -> dict:
        """Retorna lista de quem está online."""
        usuarios = list(self.clientes_conectados.keys())
        return {"status": "ok", "usuarios": usuarios}

    # ─── Utilitário interno ───────────────────────────────────────────────────
    def _notificar_todos(self, remetente: str, msg: str):
        """
        Percorre todos os clientes conectados e envia a mensagem.
        Se um cliente desconectou abruptamente, remove da lista.
        """
        desconectados = []

        for nome, writer in self.clientes_conectados.items():
            try:
                writer(msg)
            except Exception:
                # cliente caiu sem fazer logout — marca pra remover
                desconectados.append(nome)

        for nome in desconectados:
            del self.clientes_conectados[nome]
            print(f"[{self._timestamp()}] {nome} removido por conexão perdida.")