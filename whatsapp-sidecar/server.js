// Optional unofficial WhatsApp Web bridge. Use only with an account you control.
require('dotenv').config();
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const pino = require('pino');
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const PORT=Number(process.env.WA_SIDECAR_PORT||8787), TOKEN=process.env.WA_SIDECAR_TOKEN||'', AUTH_DIR=process.env.WA_AUTH_DIR||path.join(__dirname,'auth');
let sock=null, state='not_connected', lastError='', pairingCode='';
if(!TOKEN) { console.error('WA_SIDECAR_TOKEN is required'); process.exit(1); }
async function connect(){
 const {state:auth,saveCreds}=await useMultiFileAuthState(AUTH_DIR);
 const {version}=await fetchLatestBaileysVersion();
 sock=makeWASocket({version,auth,logger:pino({level:'silent'}),printQRInTerminal:false,browser:['Zero Hawk','Chrome','1.0.0']});
 sock.ev.on('creds.update',saveCreds);
 sock.ev.on('connection.update',u=>{
  if(u.connection==='open'){state='connected';lastError='';}
  if(u.connection==='close'){state='disconnected';lastError=String(u.lastDisconnect?.error||'');if(u.lastDisconnect?.error?.output?.statusCode!==DisconnectReason.loggedOut)setTimeout(connect,5000);}
 });
 sock.ev.on('messages.upsert',async ({messages})=>{
  for(const m of messages||[]){
   if(m.key?.fromMe||!m.message)continue;
   const text= m.message.conversation || m.message.extendedTextMessage?.text || '';
   const payload={channel:'whatsapp',external_id:m.key.id||String(Date.now()),address:m.key.remoteJid||'',subject:'WhatsApp message',body:text};
   const target=process.env.OPENPROSPECT_INBOUND_URL;
   if(target)fetch(target,{method:'POST',headers:{'content-type':'application/json','authorization':'Bearer '+TOKEN},body:JSON.stringify(payload)}).catch(e=>console.error('Inbound callback failed',e.message));
  }
 });
}
function respond(res,code,obj){res.writeHead(code,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify(obj));}
const server=http.createServer(async(req,res)=>{
 if(req.headers.authorization!=='Bearer '+TOKEN)return respond(res,401,{error:'unauthorized'});
 const chunks=[];for await(const c of req)chunks.push(c);let body={};try{body=JSON.parse(Buffer.concat(chunks).toString()||'{}')}catch{return respond(res,400,{error:'invalid json'});}
 try{
  if(req.method==='GET'&&req.url==='/status')return respond(res,200,{state,lastError,pairingCode:pairingCode?'issued':'not_requested'});
  if(req.method==='POST'&&req.url==='/pair'){
   if(!sock)await connect();
   if(!body.phone)return respond(res,400,{error:'phone required in international format without + or spaces'});
   pairingCode=await sock.requestPairingCode(String(body.phone).replace(/\D/g,''));
   return respond(res,200,{state,pairingCode});
  }
  if(req.method==='POST'&&req.url==='/send'){
   if(state!=='connected'||!sock)return respond(res,409,{error:'WhatsApp is not connected'});
   if(body.approved!==true)return respond(res,403,{error:'explicit approval required'});
   if(!body.to||!body.text)return respond(res,400,{error:'to and text required'});
   if(!/^[0-9]{8,15}$/.test(String(body.to).replace(/\D/g,'')))return respond(res,400,{error:'invalid destination number'});
   const jid=String(body.to).replace(/\D/g,'')+'@s.whatsapp.net';
   const sent=await sock.sendMessage(jid,{text:String(body.text).slice(0,4000)});
   return respond(res,200,{sent:true,id:sent.key.id});
  }
  return respond(res,404,{error:'not found'});
 }catch(e){lastError=e.message;return respond(res,500,{error:e.message});}
});
server.listen(PORT,'127.0.0.1',()=>console.log('Zero Hawk WhatsApp sidecar on 127.0.0.1:'+PORT));
