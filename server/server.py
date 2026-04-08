# server/server.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import socket
import threading

from server.chat_service import ChatService
from server.dispatcher import Dispatcher

HOST = "localhost"
PORT = 5000

def tratar_cliente(socket_file, dispatcher):
    """
    Roda em uma thread exclusiva pra cada cliente.
    Fica num loop lendo mensagens e passando pro dispatcher.
    """
    # usuario_atual[0] começa None — vira o nome depois do login
    usuario_atual = [None]

    try:
        while True:
            raw = socket_file.readline()  # trava aqui até chegar uma mensagem

            if not raw:
                # readline() retorna string vazia quando o cliente desconectou
                break

            dispatcher.handle(raw, socket_file, usuario_atual)

    except Exception as e:
        print(f"[Erro na thread] {e}")

    finally:
        # cliente saiu — faz logout se ainda estava conectado
        if usuario_atual[0]:
            dispatcher.service.logout(usuario_atual[0])
            print(f"[Servidor] {usuario_atual[0]} desconectado.")

        socket_file.close()

def main():
    # ─── cria o serviço e o dispatcher uma única vez ──────────────────────────
    service    = ChatService()
    dispatcher = Dispatcher(service)

    # ─── abre o socket do servidor ────────────────────────────────────────────
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #                                               ↑
    #                   permite reusar a porta logo após reiniciar o servidor

    servidor.bind((HOST, PORT))
    servidor.listen()
    print(f"[Servidor] Rodando em {HOST}:{PORT} — aguardando conexões...")

    try:
        while True:
            conn, endereco = servidor.accept()  # trava até alguém conectar
            print(f"[Servidor] Nova conexão de {endereco}")

            # transforma o socket em arquivo de texto linha a linha
            socket_file = conn.makefile(mode="rw", encoding="utf-8")

            # cria thread exclusiva pra esse cliente
            thread = threading.Thread(
                target=tratar_cliente,
                args=(socket_file, dispatcher),
                daemon=True   # thread morre automaticamente se o servidor fechar
            )
            thread.start()

    except KeyboardInterrupt:
        print("\n[Servidor] Encerrando...")

    finally:
        servidor.close()

if __name__ == "__main__":
    main()