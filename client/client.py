# client/client.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import threading
from client.stub import ChatStub
from shared.protocol import decode

def thread_recebimento(stub, rodando):
    """
    Roda em paralelo — é a ÚNICA thread que lê do socket.

    Classifica cada mensagem recebida:
    - 'server-push'  → imprime na tela (broadcast, privado, notificação)
    - qualquer outra → é uma resposta RPC; coloca na fila do stub
                       para a thread principal consumir via _call()

    Dessa forma nunca há duas threads competindo pelo mesmo readline(),
    eliminando o race condition que causava o freeze no /lista.
    """
    while rodando[0]:
        try:
            raw = stub.socket_file.readline()

            if not raw:
                # servidor fechou a conexão
                print("\n[Cliente] Conexão encerrada pelo servidor.")
                rodando[0] = False
                break

            msg = decode(raw)

            if msg.get("request_id") == "server-push":
                # notificação do servidor — imprime direto
                print(f"\n{msg['payload']['msg']}")
                print(">> ", end="", flush=True)  # reimprime o prompt
            else:
                # resposta a um request RPC — roteia para a thread principal
                stub._response_queue.put(msg)

        except Exception:
            if rodando[0]:
                print("\n[Cliente] Erro na conexão.")
            rodando[0] = False
            break

def fazer_login(stub):
    """Pede usuário e senha até conseguir logar."""
    while True:
        print("\n─── Login ───────────────────")
        usuario = input("Usuário: ").strip()
        senha   = input("Senha:   ").strip()

        res = stub.login(usuario, senha)

        if res and res.get("status") == "ok":
            print(f"\n{res['payload'].get('msg', 'Login OK!')}")
            return usuario
        else:
            msg = res['payload'].get('msg', 'Erro desconhecido.') if res else 'Sem resposta.'
            print(f"[Erro] {msg}")

def mostrar_ajuda():
    print("""
─── Comandos ────────────────────────────
  /p <usuario> <mensagem>  → mensagem privada
  /lista                   → ver quem está online
  /sair                    → desconectar
  qualquer texto           → broadcast pra todos
─────────────────────────────────────────""")

def main():
    stub = ChatStub()

    try:
        stub.conectar()
    except Exception as e:
        print(f"[Erro] Não foi possível conectar: {e}")
        return

    # ─── sobe a thread de recebimento ANTES do login ──────────────────────────
    # A thread precisa estar rodando antes de qualquer _call(), pois é ela
    # que lê o socket e coloca as respostas na fila. Sem ela, _call() trava
    # em queue.get() indefinidamente, mesmo no login.
    rodando = [True]
    t = threading.Thread(
        target=thread_recebimento,
        args=(stub, rodando),
        daemon=True
    )
    t.start()

    # ─── faz login ────────────────────────────────────────────────────────────
    usuario = fazer_login(stub)

    mostrar_ajuda()

    # ─── loop principal: lê input e chama o stub ──────────────────────────────
    while rodando[0]:
        try:
            entrada = input(">> ").strip()

            if not entrada:
                continue

            # ─── /sair ────────────────────────────────────────────────────────
            if entrada == "/sair":
                stub.logout()
                rodando[0] = False
                break

            # ─── /lista ───────────────────────────────────────────────────────
            elif entrada == "/lista":
                res = stub.listar_usuarios()
                if res:
                    usuarios = res["payload"].get("usuarios", [])
                    print(f"Online: {', '.join(usuarios)}")

            # ─── /p usuario mensagem ──────────────────────────────────────────
            elif entrada.startswith("/p "):
                partes = entrada.split(" ", 2)
                if len(partes) < 3:
                    print("[Erro] Use: /p <usuario> <mensagem>")
                else:
                    _, destinatario, mensagem = partes
                    res = stub.mensagem_privada(destinatario, mensagem)
                    if res and res.get("status") == "error":
                        print(f"[Erro] {res['payload'].get('msg')}")

            # ─── broadcast ────────────────────────────────────────────────────
            else:
                stub.broadcast(entrada)

        except KeyboardInterrupt:
            stub.logout()
            rodando[0] = False
            break

    stub.desconectar()
    print("[Cliente] Desconectado.")

if __name__ == "__main__":
    main()