import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>STACY</title>
<style>
body{margin:0;background:#07111f;color:#e8eef7;font:16px system-ui,sans-serif}
main{max-width:760px;margin:auto;padding:24px}
h1{margin:0 0 4px}.status{color:#7dd3fc;font-size:13px}
#chat{height:65vh;overflow:auto;border:1px solid #20334d;border-radius:14px;padding:14px;margin:18px 0;background:#0b1728}
.msg{margin:10px 0;white-space:pre-wrap}.you{color:#cbd5e1}.stacy{color:#f8fafc}
form{display:flex;gap:8px}input{flex:1;padding:14px;border-radius:10px;border:1px solid #29415f;background:#0b1728;color:white}button{padding:0 18px;border:0;border-radius:10px;cursor:pointer}
</style>
</head>
<body><main>
<h1>STACY</h1><div class="status">ONLINE · interface local</div>
<div id="chat"></div>
<form id="form"><input id="input" autocomplete="off" placeholder="Digite para STACY..."><button>Enviar</button></form>
<script>
const chat=document.getElementById('chat'), input=document.getElementById('input');
function add(who,text){const d=document.createElement('div');d.className='msg '+who;d.textContent=(who==='you'?'Você: ':'STACY: ')+text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight}
document.getElementById('form').addEventListener('submit',async e=>{
 e.preventDefault();const message=input.value.trim();if(!message)return;
 add('you',message);input.value='';input.disabled=true;
 try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message})});
 const data=await r.json();if(!r.ok)throw new Error(data.error||'Falha');
 add('stacy',data.resposta||''); if(data.fontes?.length) add('stacy','Fontes: '+data.fontes.map(x=>x.titulo||x.url).join(' | '));
 }catch(err){add('stacy','Não consegui processar a mensagem: '+err.message)}
 finally{input.disabled=false;input.focus()}
});
input.focus();
</script></main></body></html>"""


def criar_handler(orquestrador):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, content_type, body):
            raw = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if urlparse(self.path).path == "/":
                self._send(200, "text/html; charset=utf-8", HTML)
                return
            if urlparse(self.path).path == "/health":
                self._send(200, "application/json; charset=utf-8", json.dumps({"status":"online"}, ensure_ascii=False))
                return
            self._send(404, "application/json; charset=utf-8", json.dumps({"error":"not found"}))

        def do_POST(self):
            if urlparse(self.path).path != "/api/chat":
                self._send(404, "application/json; charset=utf-8", json.dumps({"error":"not found"}))
                return
            try:
                tamanho = int(self.headers.get("Content-Length", "0"))
                if tamanho <= 0 or tamanho > 64 * 1024:
                    raise ValueError("corpo inválido")
                dados = json.loads(self.rfile.read(tamanho).decode("utf-8"))
                mensagem = dados.get("message", "").strip()
                if not mensagem:
                    raise ValueError("mensagem vazia")
                resultado = orquestrador.processar(mensagem)
                if not isinstance(resultado, dict):
                    raise RuntimeError("resposta inválida")
                self._send(200, "application/json; charset=utf-8", json.dumps(resultado, ensure_ascii=False))
            except Exception as erro:
                self._send(400, "application/json; charset=utf-8", json.dumps({"error": str(erro)}, ensure_ascii=False))

        def log_message(self, fmt, *args):
            return

    return Handler


def iniciar(orquestrador, host="127.0.0.1", porta=8765):
    servidor = ThreadingHTTPServer((host, porta), criar_handler(orquestrador))
    servidor.serve_forever()
