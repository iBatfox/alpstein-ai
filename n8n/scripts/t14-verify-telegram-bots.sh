#!/usr/bin/env bash
# T14.2 — getMe for owner vs customer n8n credentials; masked output only (no tokens).
set -euo pipefail

CONTAINER="${N8N_CONTAINER:-alpstein_n8n}"
OWNER_NAME="${TELEGRAM_OWNER_CRED_NAME:-AlpsteinAIbot}"
CUSTOMER_NAME="${TELEGRAM_CUSTOMER_CRED_NAME:-alpsteinai_0001bot}"
CUSTOMER_PREFIX="${TELEGRAM_CUSTOMER_CRED_PREFIX:-telegram_customer}"

docker exec "${CONTAINER}" n8n export:credentials --all --decrypted --output=/tmp/t14-creds-dec.json >/dev/null 2>&1

docker exec "${CONTAINER}" node -e "
const fs=require('fs');
const https=require('https');
const ownerName=process.env.OWNER_NAME||'AlpsteinAIbot';
const customerName=process.env.CUSTOMER_NAME||'alpsteinai_0001bot';
const customerPrefix=process.env.CUSTOMER_PREFIX||'telegram_customer';
const data=JSON.parse(fs.readFileSync('/tmp/t14-creds-dec.json','utf8'));
function maskId(id){const s=String(id);return s.length<=4?'***':('***'+s.slice(-4));}
function getMe(token){
  return new Promise((res)=>{
    https.get('https://api.telegram.org/bot'+token+'/getMe',r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>{
      try{res(JSON.parse(b));}catch(e){res({ok:false,description:'parse_error'});}
    });}).on('error',()=>res({ok:false,description:'http_error'}));
  });
}
(async()=>{
  const tg=data.filter(c=>c.type==='telegramApi');
  const results={};
  for(const c of tg){
    const token=(c.data&&c.data.accessToken)||(c.data&&c.data.token);
    if(!token){results[c.name]={status:'no_token'};continue;}
    const j=await getMe(token);
    if(!j.ok){results[c.name]={status:'getMe_fail',desc:j.description||'unknown'};continue;}
    const u=j.result;
    results[c.name]={status:'ok',bot_id:maskId(u.id),username:'@'+(u.username||'none'),is_bot:u.is_bot};
  }
  const owner=results[ownerName];
  let customerEntry=results[customerName]?[customerName,results[customerName]]:null;
  if(!customerEntry) customerEntry=Object.entries(results).find(([n])=>n.startsWith(customerPrefix));
  console.log('OWNER_CRED='+ownerName);
  console.log(owner?JSON.stringify(owner):'{\"status\":\"missing\"}');
  if(customerEntry){
    console.log('CUSTOMER_CRED='+customerEntry[0]);
    console.log(customerEntry[1]?JSON.stringify(customerEntry[1]):'{\"status\":\"missing\"}');
  } else {
    console.log('CUSTOMER_CRED=none');
    console.log('{\"status\":\"missing\"}');
  }
  if(owner&&owner.status==='ok'&&customerEntry&&customerEntry[1].status==='ok'){
    const same=owner.bot_id===customerEntry[1].bot_id&&owner.username===customerEntry[1].username;
    console.log('SEPARATION_VERIFIED='+(same?'no_SAME_BOT':'yes'));
  } else {
    console.log('SEPARATION_VERIFIED=pending');
  }
})();
" OWNER_NAME="${OWNER_NAME}" CUSTOMER_NAME="${CUSTOMER_NAME}" CUSTOMER_PREFIX="${CUSTOMER_PREFIX}"

docker exec "${CONTAINER}" rm -f /tmp/t14-creds-dec.json 2>/dev/null || true
