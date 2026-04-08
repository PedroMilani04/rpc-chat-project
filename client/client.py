# client/client.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import threading
from client.stub import ChatStub
from shared.protocol import decode

def thread_recebimento(socket_file, rodando):
    """
    Roda em paralelo — fica escutando mensagens que chegam do servidor.
    Quando chega algo, imprime na tela.
    'rodando' é uma lista com um booleano — usamos lista pelo mesmo
    motivo do usuario_atual: referência mutável entre threads.
    """
    while rodando[0]:
        try:
            raw = socket_file.readline()

            if not raw:
                # servidor fechou a conexão
                print("\n[Cliente] Conexão encerrada pelo servidor.")
                rodando[0] = False
                break

            msg = decode(raw)

            # mensagens do servidor são "server-push" — não são respostas a requests
            if msg.get("request_id") == "server-push":
                print(f"\n{msg['payload']['msg']}")
                print(">> ", end="", flush=True)  # reimprime o prompt

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

    # ─── faz login antes de qualquer coisa ───────────────────────────────────
    usuario = fazer_login(stub)

    # ─── sobe a thread de recebimento ─────────────────────────────────────────
    rodando = [True]
    t = threading.Thread(
        target=thread_recebimento,
        args=(stub.socket_file, rodando),
        daemon=True
    )
    t.start()

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