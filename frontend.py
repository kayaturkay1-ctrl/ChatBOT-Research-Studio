"""Mevcut HTML/CSS/JS tasarımı tek Python dosyasında saklanır."""
import hashlib,os,tempfile
from pathlib import Path
# JavaScript açıklamaları ilgili kodun yanındadır: D26–D34, D37, D39–D41, D44–D54.
# CSS tasarımı korundu; animasyon/GPU etkisi gerçek tarayıcı profilinde ayrıca ölçülmelidir.
ASSETS = {
'base.css': """/* Widget kutu modeli artık uygulamaya aittir. */
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--material-canvas,#fafbfc);color:var(--apple-text,#1d1d1f)}button,input,textarea,select{font:inherit;color:inherit}button{cursor:pointer;border:0;background:transparent}button:disabled{cursor:default}textarea{width:100%;resize:none;border:1px solid var(--apple-border);border-radius:16px;padding:12px;background:var(--apple-surface)}.row{display:flex;gap:16px;min-width:0}.column{display:flex;flex-direction:column;gap:16px;min-width:0}.block{min-width:0;position:relative}.research-app{display:flex;flex-direction:column;gap:24px}p{margin:0 0 1em}p:last-child{margin-bottom:0}.message-row{display:flex;flex-direction:column;align-items:stretch;padding:14px 0}.message{min-width:0}.bot-row .message-content{line-height:1.7}.message-content ul,.message-content ol{padding-left:24px}.message-content table{border-collapse:collapse;width:100%;margin:12px 0}.message-content th,.message-content td{padding:10px 12px;border:1px solid var(--apple-border);text-align:left}.message-content pre{overflow:auto;padding:14px;background:rgba(125,135,150,.08);border-radius:12px}.message-content code{font-family:ui-monospace,monospace;font-size:.9em}.message-content :not(pre)>code{background:rgba(125,135,150,.08);padding:2px 4px;border-radius:4px}.message-content a{color:var(--apple-blue)}.upload-drop{height:100%;width:100%;display:flex;gap:16px;flex-direction:column;align-items:center;justify-content:center;position:relative;cursor:pointer}.upload-drop input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}.upload-icon{font-size:36px;color:#0071e3}.bubble-wrap{height:100%;overflow:auto;min-height:0;padding:14px 20px;overscroll-behavior:contain}.placeholder-content{align-items:center}.placeholder{display:flex;align-items:center;justify-content:center}.message-image{max-width:min(320px,100%);max-height:240px;object-fit:contain;border-radius:16px;margin-bottom:8px}
""",
'bridge.js': """/* Resmî Streamlit component protokolü. Tek sunucu; komutlar ACK ile yalnızca bir kez işlenir.
 * Sabit mesaj düğümleri kaynak atıflarını, taslağı ve focus'u her rerun'da korur.
 */
(()=>{'use strict';
const $=s=>document.querySelector(s),ui=()=>window.researchFrontend,uid=()=>crypto.randomUUID();
let ready=false,flight=null,queue=[],pendingRender=null,rendering=false,resyncing=false,latest=null,revision=-1,reset='',photo='',doc='',runtime='',lastError='',lastPdf='',lastHeight=0,sending=false,uploading=false;
let lastSelectedPdfId='',renderedRows=null;
let descriptorRaw=null,descriptor=null,composerPdfId='';
// DÜZELTME [D33]: sunucu ACK'si gelmeden ilk karede soru ve bekleme durumu gösterilir.
// Geçici satırlar sunucu geçmişine yazılmaz; command_id ile tek kez uzlaştırılır.
let pendingSend=null,syncId=null;
const diagnostics=window.researchDiagnostics={lastSend:null};
const nodes=new Map(),empty=$('.bubble-wrap').innerHTML;
const post=(type,body={})=>window.parent.postMessage({isStreamlitMessage:true,type,...body},'*');
const error=message=>{let n=$('.bridge-error');if(!n){n=document.createElement('div');n.className='bridge-error';n.setAttribute('role','alert');document.body.append(n);}n.textContent=message;n.hidden=false;clearTimeout(n.timer);n.timer=setTimeout(()=>n.hidden=true,6500);};
const transmit=()=>{flight.sent=Date.now();post('streamlit:setComponentValue',{value:{...flight.value,attempt:flight.attempt++},dataType:'json'});};
const pump=()=>{if(!ready||flight||!queue.length)return;flight=queue.shift();flight.started=Date.now();flight.attempt=0;transmit();};
const command=(action,data={},id=uid())=>new Promise((resolve,reject)=>{queue.push({value:{id,action,...data},resolve,reject});pump();});
const height=()=>{let h=innerHeight;try{h=parent.visualViewport?.height||parent.innerHeight;}catch(_){}h=Math.max(280,Math.round(h));if(h!==lastHeight){lastHeight=h;post('streamlit:setFrameHeight',{height:h});}};
const setDisabled=(selector,value)=>{const n=$(selector);if(n&&n.disabled!==Boolean(value))n.disabled=Boolean(value);};
// [D26] Runtime nesnesini doğrudan olayla ilet: büyük PDF haritasını JSON string ve
// gizli textarea içinde her turda yeniden üretmek ana tarayıcı iş parçacığına ek yük bindirir.
const field=(selector,value,event)=>{if(event==='apple-runtime-update'&&typeof value==='object'){dispatchEvent(new CustomEvent(event,{detail:value}));return;}const n=$(selector+' textarea'),raw=typeof value==='string'?value:JSON.stringify(value);if(n&&n.value!==raw)n.value=raw;if(event)dispatchEvent(new CustomEvent(event,{detail:raw}));};
// [D47] Akışta tüm cevabın innerHTML'ini silmek yerine aynı düğümleri koru.
// Sunucunun temizlediği HTML ayrıştırılır; değişen metin/özellikler yerinde
// güncellenir. Markdown yapısı değişirse yalnız ilgili alt ağaç değiştirilir.
const htmlTemplate=document.createElement('template');
const reconcileChildren=(target,source)=>{
 let current=target.firstChild;
 for(const next of [...source.childNodes]){
  const following=current?.nextSibling;
  if(!current)target.appendChild(next);
  else if(current.nodeType!==next.nodeType||current.nodeName!==next.nodeName)current.replaceWith(next);
  else if(!current.isEqualNode(next)){
   if(current.nodeType===Node.TEXT_NODE){const value=next.data;if(value.startsWith(current.data))current.appendData(value.slice(current.data.length));else current.data=value;}
   else if(current.nodeType===Node.ELEMENT_NODE){
    for(const attr of [...current.attributes])if(!next.hasAttribute(attr.name))current.removeAttribute(attr.name);
    for(const attr of [...next.attributes])if(current.getAttribute(attr.name)!==attr.value)current.setAttribute(attr.name,attr.value);
    reconcileChildren(current,next);
   }else current.replaceWith(next);
  }
  current=following;
 }
 while(current){const next=current.nextSibling;current.remove();current=next;}
};
const patchMessage=(target,html)=>{htmlTemplate.innerHTML=html;reconcileChildren(target,htmlTemplate.content);};
// [D27] Mesaj düğümleri sabit tutulur; sadece değişen HTML ve kaynak satırı işaretlenir.
// Böylece eski cevapların atıfları, kullanıcının taslağı ve focus gereksiz yere yeniden kurulmaz.
const paint=rows=>{
 const wrap=$('.bubble-wrap'),near=wrap.scrollHeight-wrap.clientHeight-wrap.scrollTop<100;let changed=false;
 if(rows.length&&$('.placeholder-content')){wrap.replaceChildren();changed=true;}
 const ids=new Set(rows.map(r=>r.id));for(const [key,n]of nodes)if(!ids.has(key)){n.remove();nodes.delete(key);changed=true;}
 let assistantIndex=0;
 for(const row of rows){let n=nodes.get(row.id);if(!n){n=document.createElement('div');n.className='message-row '+(row.role==='assistant'?'bot-row':'user-row');n.dataset.role=row.role;n.dataset.messageId=row.id;n.innerHTML=`<div class="message"><div class="message-content" data-testid="${row.role==='assistant'?'bot':'user'}"><div class="prose"></div></div></div>`;nodes.set(row.id,n);wrap.append(n);changed=true;}
 if(row.role==='assistant' && n.dataset.assistantIndex!==String(assistantIndex))n.dataset.assistantIndex=String(assistantIndex);
 if(row.role==='assistant')assistantIndex++;
 if(n._row!==row){n._row=row;ui()?.markSources(n);}
 if(n._html!==row.html){const started=performance.now();patchMessage(n.querySelector('.prose'),row.html||'');const elapsed=performance.now()-started;const measure=diagnostics.rendering||(diagnostics.rendering={updates:0,max_patch_ms:0,last_patch_ms:0});measure.updates++;measure.last_patch_ms=elapsed;measure.max_patch_ms=Math.max(measure.max_patch_ms,elapsed);n._html=row.html;changed=true;}
 if(row.image&&!n.querySelector('.message-image')){const img=document.createElement('img');img.className='message-image';img.alt='Gönderilen fotoğraf';img.src=row.image;n.querySelector('.message').prepend(img);changed=true;}}
 if(!rows.length&&!$('.placeholder-content')){wrap.innerHTML=empty;changed=true;}
 if(changed&&near)requestAnimationFrame(()=>wrap.scrollTop=wrap.scrollHeight);
 return changed;
};
const restoreDraft=pending=>{const box=$('.mesaj-kutusu textarea');if(!box.value){box.value=pending.message;box.dispatchEvent(new Event('input',{bubbles:true}));}};
const pendingRuntime=()=>pendingSend ? {id:'pending-'+pendingSend.id,phase:'sending',elapsed_ms:0,assistant_index:pendingSend.assistantIndex} : null;
// [D40] Belge yalnız değiştiğinde çözülür. Yeni soru ve geçmiş telemetrisi aynı
// descriptor'ı referansla kullanır; büyük harita tekrar tekrar taşınmaz.
const resolveDocuments=data=>{
 const raw=data.document??latest?.document;
 if(raw!==descriptorRaw){const parsed=typeof raw==='string'?JSON.parse(raw||'{}'):raw;descriptor=parsed?.document?.viewer||null;descriptorRaw=raw;}
 const resolve=value=>{
  if(!value?.document?.$document_ref)return value;
  if(descriptor?.id!==value.document.$document_ref)throw new Error('Belge referansı eşleşmedi.');
  return {...value,document:descriptor};
 };
 const result={...data};
 if(data.runtime)result.runtime=resolve(data.runtime);
 if(data.runtime_patch)result.runtime_patch=resolve(data.runtime_patch);
 for(const key of ['rows','rows_patch'])if(data[key])result[key]=data[key].map(row=>row.telemetry?.document?.$document_ref?{...row,telemetry:resolve(row.telemetry)}:row);
 return result;
};
const settlePending=(data,isFull)=>{
 if(!pendingSend)return;
 const accepted=(data.rows||[]).some(row=>row.command_id===pendingSend.id);
 const rejected=data.error?.id===pendingSend.id;
 // Zaman aşımında teslim sonucu belirsizdir. Aynı soruyu yeni ID ile yollamak
 // yerine tam sync sonucunu bekle; böylece API çağrısı iki kez başlatılmaz.
 if(!accepted&&!rejected&&data.ack!==pendingSend.id&&!(isFull&&pendingSend.uncertain&&data.ack===pendingSend.recoveryId))return;
 const item=pendingSend;pendingSend=null;
 if(!accepted)restoreDraft(item);
 diagnostics.lastSend={...diagnostics.lastSend,accepted,ack_ms:Math.round(performance.now()-item.started),dispatch_ms:data.command_timing?.id===item.id?data.command_timing.dispatch_ms:null};
 renderedRows=null;runtime=null;revision=-1;
};
const render=async data=>{
 if(data.revision===revision)return;
 // [D41] Açılışta aktif PDF bir ek dosya seçimi değildir. Yalnız bu oturumda
 // başarılı PDF değişikliği chip oluşturur; varsayılana dönüş chip'i kaldırır.
 const activeId=descriptor?.id||'';
 if(composerPdfId&&composerPdfId!==activeId)composerPdfId='';
 if(reset!==data.reset_id){if(reset&&data.reset_reason==='pdf'){composerPdfId=data.active_kind==='uploaded'?activeId:'';await window.applePreparePdfConversation?.(true);}reset=data.reset_id;nodes.clear();$('.bubble-wrap').innerHTML=empty;ui()?.resetAnswers();field('#apple-runtime-state',{reset_id:reset},'apple-runtime-update');runtime='';}
 const selectedPdf=composerPdfId===activeId&&activeId?{id:activeId,name:data.active_name}:null;
 ui()?.composerPdf?.(selectedPdf);
 if(renderedRows!==data.rows){paint(pendingSend?[...(data.rows||[]),...pendingSend.rows]:data.rows||[]);ui()?.restoreAnswers(data.rows||[]);renderedRows=data.rows;}
 const nextRuntime=pendingRuntime()||data.runtime;
 if(nextRuntime!==runtime){runtime=nextRuntime;field('#apple-runtime-state',nextRuntime?.phase?nextRuntime:{id:'idle-'+data.reset_id,phase:'ready'},'apple-runtime-update');}
 if(data.document!==doc){doc=data.document;field('#apple-document-state',doc,'apple-document-update');}
 if(data.photo!==photo){photo=data.photo;field('#apple-photo-state',photo,'apple-photo-update');}
 $('#apple-update-status textarea').value=data.status||'';if($('#request-log').value!==data.request_log)$('#request-log').value=data.request_log||'';
 if($('#token-card')._html!==data.token_card){$('#token-card').innerHTML=data.token_card||'';$('#token-card')._html=data.token_card;}
 setDisabled('.gonder-butonu',Boolean(pendingSend)||Boolean(data.busy)||!data.storage_ready);
 setDisabled('#apple-pdf-upload input',Boolean(pendingSend)||Boolean(data.busy)||!data.storage_ready);
 setDisabled('#apple-photo-upload input',Boolean(pendingSend)||Boolean(data.busy)||!data.storage_ready);
 ui()?.uploadBusy(data.busy==='upload');
 setDisabled('#apple-reset-pdf',Boolean(pendingSend)||Boolean(data.busy)||!data.storage_ready||!data.default_available);
 const hint=data.default_available?'Aktif PDF ve FAISS indeksi tüm kullanıcılar için ortaktır.':'Varsayılan PDF eklenmedi: sunucuya default.pdf koyun.';if($('#apple-reset-hint').textContent!==hint)$('#apple-reset-hint').textContent=hint;
 if(data.storage_warning && data.storage_warning!==lastError){lastError=data.storage_warning;error(data.storage_warning);}
 // [D44] Veritabanı kartı da yalnız bu oturumdaki başarılı seçimi gösterir.
 // Varsayılan/kayıttan açılan PDF seçilmiş sayılmaz; kimlik değişmeden X ile kapatılan kartı yeniden açma.
 if((selectedPdf?.id||'')!==lastSelectedPdfId){lastSelectedPdfId=selectedPdf?.id||'';const preview=$('#apple-pdf-upload .file-preview');preview.hidden=!selectedPdf;preview.querySelector('.stem').textContent=selectedPdf?.name||'';preview.querySelector('.ext').textContent='';}
 const card=$('#ai-ingestion-card');
 if(card){
  let cancel=$('#apple-ingestion-cancel');if(!cancel){cancel=document.createElement('button');cancel.id='apple-ingestion-cancel';cancel.type='button';cancel.textContent='İptal';cancel.addEventListener('click',()=>{cancel.disabled=true;command('stop').catch(e=>error(e.message));});card.append(cancel);}
  cancel.hidden=data.busy!=='upload';cancel.disabled=data.ingestion?.cancellable===false;
  let meter=card.querySelector('progress');if(!meter){meter=document.createElement('progress');meter.setAttribute('aria-label','E5 vektörleme ilerlemesi');card.querySelector('.ai-ingestion-copy').append(meter);}
  meter.hidden=data.busy!=='upload';const total=data.ingestion?.total||0;if(total>0&&data.ingestion?.embedding_stage==='embedding'){meter.max=total;meter.value=data.ingestion.done||0;}else meter.removeAttribute('value');
 }
 if(data.pdf_result&&data.pdf_result.request_id!==lastPdf){lastPdf=data.pdf_result.request_id;field('#apple-pdf-view-response',data.pdf_result,'apple-pdf-page');command('page_ack',{request_id:lastPdf}).catch(e=>error(e.message));}
 ui()?.refresh();
 revision=data.revision;
};
const requestSync=()=>{if(resyncing){if(pendingSend?.uncertain)pendingSend.recoveryId=syncId;return;}resyncing=true;syncId=uid();if(pendingSend?.uncertain)pendingSend.recoveryId=syncId;command('sync',{},syncId).catch(e=>error(e.message)).finally(()=>{resyncing=false;syncId=null;});};
const drain=async()=>{if(rendering)return;rendering=true;try{while(pendingRender){const data=pendingRender;pendingRender=null;await render(data);}}catch(e){error('Arayüz güncellenemedi: '+e.message);console.error(e);requestSync();}finally{rendering=false;}};
// [D47] Aynı ekran karesinde biriken paketleri bir kez çiz. Durum farkları
// aşağıda sırayla birleştirilir; son metin ve kaynak bilgisi kaybolmaz.
let renderFrame=0;
const scheduleRender=()=>{if(!renderFrame)renderFrame=requestAnimationFrame(()=>{renderFrame=0;void drain();});};
const acceptSnapshot=data=>{
 // Önce sıra kontrolü: atlanmış bir delta yeni belge önbelleğini de bozmamalı.
 if(data.delta&&(!latest||(data.base_revision!==latest.revision&&data.revision!==latest.revision))){requestSync();return;}
 try{data=resolveDocuments(data);}catch(e){error(e.message);requestSync();return;}
 if(data.delta){
  if(!latest || (data.base_revision!==latest.revision && data.revision!==latest.revision)){requestSync();return;}
  if(data.revision===latest.revision)return;
  const merged={...latest,...data};
  // [D02/D26] Sunucunun aynı soru için gönderdiği küçük runtime farkını mevcut nesneye birleştir.
  // Belge haritası korunur; kaldırılan alanlar da silinir. Yeni soru tam runtime gönderir.
  if(data.runtime_patch){merged.runtime={...latest.runtime,...data.runtime_patch};for(const key of data.runtime_removed||[])delete merged.runtime[key];}
  delete merged.runtime_patch;delete merged.runtime_removed;
  if(data.rows_patch){const byId=new Map(latest.rows.map(row=>[row.id,row]));for(const row of data.rows_patch)byId.set(row.id,row);merged.rows=data.row_ids.map(id=>byId.get(id));if(merged.rows.some(row=>!row)){requestSync();return;}}
  delete merged.delta;delete merged.base_revision;delete merged.rows_patch;delete merged.row_ids;latest=merged;
 }else{latest=data;}
 settlePending(latest,!data.delta);pendingRender=latest;scheduleRender();
};
addEventListener('message',e=>{
 if(e.source!==parent||e.data?.type!=='streamlit:render')return;ready=true;const data=e.data.args?.snapshot;if(!data)return;
 if(flight&&data.ack===flight.value.id){const done=flight;flight=null;if(data.error?.id===done.value.id)done.reject(new Error(data.error.message));else done.resolve(data);}
 if(data.error&&data.error.id!==lastError){lastError=data.error.id;error(data.error.message);}
 acceptSnapshot(data);pump();height();
 // [D39] İlk tam snapshot zaten eşitlenmiştir. Fazladan sync, ilk soruyu
 // komut kuyruğunda bir sunucu gidiş-dönüşü bekletiyordu. Eksik delta hâlâ sync ister.
});
$('.gonder-butonu').addEventListener('click',async()=>{
 if(sending||pendingSend||uploading||latest?.busy||!latest?.storage_ready)return;const box=$('.mesaj-kutusu textarea'),message=box.value;
 if(!message.trim()&&!JSON.parse(latest?.photo||'{}').ready)return;
 if(message.trim().length>100000)return error('Mesaj çok uzun.');
 sending=true;const id=uid(),started=performance.now();
 // Kullanıcı metnini HTML olarak çalıştırma; sunucu daha sonra temizlenmiş Markdown yollar.
 const safe=document.createElement('p');safe.style.whiteSpace='pre-wrap';safe.textContent=message.trim()||'Bu fotoğrafı inceleyip açıkla.';
 pendingSend={id,message,started,assistantIndex:(latest.rows||[]).filter(row=>row.role==='assistant').length,rows:[
  {id:'pending-user-'+id,role:'user',html:safe.outerHTML},
  {id:'pending-bot-'+id,role:'assistant',html:'<div class="apple-processing-status" role="status"><span class="apple-processing-dot"></span><strong>Gönderiliyor…</strong></div>'}
 ]};
 diagnostics.lastSend={command_id:id,accepted:false,feedback_frame_ms:null,ack_ms:null,dispatch_ms:null};
 paint([...(latest.rows||[]),...pendingSend.rows]);renderedRows=null;
 for(const selector of ['.gonder-butonu','#apple-pdf-upload input','#apple-photo-upload input','#apple-reset-pdf'])setDisabled(selector,true);
 field('#apple-runtime-state',pendingRuntime(),'apple-runtime-update');runtime=null;ui()?.refresh();
 // ÖLÇÜM: İlk rAF callback zamanı; gerçek ekran boyama/FPS ölçümü değildir.
 requestAnimationFrame(()=>{if(diagnostics.lastSend?.command_id===id)diagnostics.lastSend.feedback_frame_ms=Math.round(performance.now()-started);});
 try{const task=command('send',{message,model:$('#apple-model-controls input:checked').value,detail:$('#apple-detail-controls input:checked').value,memory:$('#memory').checked,advanced_memory:$('#advanced-memory').checked},id);box.value='';box.dispatchEvent(new Event('input',{bubbles:true}));box.focus();await task;}
 catch(e){if(pendingSend?.id===id){if(e.unknownOutcome){pendingSend.uncertain=true;requestSync();}else{restoreDraft(pendingSend);pendingSend=null;revision=-1;renderedRows=null;runtime=null;pendingRender=latest;scheduleRender();}}error(e.message);}finally{sending=false;}
});
$('#apple-stop').addEventListener('click',()=>command('stop').catch(e=>error(e.message)));
$('#apple-reset-pdf').addEventListener('click',()=>{$('#apple-reset-confirmation').hidden=false;$('#apple-reset-confirm').focus();});
$('#apple-reset-cancel').addEventListener('click',()=>{$('#apple-reset-confirmation').hidden=true;$('#apple-reset-pdf').focus();});
$('#apple-reset-confirm').addEventListener('click',async()=>{
 $('#apple-reset-confirmation').hidden=true;
 try{await command('reset_pdf');$('[data-apple-action="close-settings"]').click();}catch(e){error(e.message);}
});
$('#native-clear').addEventListener('click',()=>command('clear').catch(e=>{ui()?.cancelReset();error(e.message);}));
addEventListener('apple-pdf-request',event=>command('page',{request:event.detail}).catch(e=>error(e.message)));
$('#apple-pdf-view-submit').addEventListener('click',()=>command('page',{request:$('#apple-pdf-view-request textarea').value}).catch(e=>error(e.message)));
$('#apple-photo-clear').addEventListener('click',()=>command('photo_clear').catch(e=>error(e.message)));
$('#memory').addEventListener('change',()=>{const a=$('#advanced-memory');a.disabled=!$('#memory').checked;if(a.disabled)a.checked=false;});
$('#apple-model-controls').addEventListener('change',()=>$('.apple-topbar-model').textContent=$('#apple-model-controls input:checked').value==='1'?'GPT-5.6 Luna':'GPT-4o-mini');
$('.mesaj-kutusu textarea').addEventListener('input',e=>{e.target.style.height='auto';e.target.style.height=Math.min(160,e.target.scrollHeight)+'px';});
const upload=async(file,kind)=>{
 if(uploading||pendingSend||latest?.busy)return error('Mevcut işlemin tamamlanmasını bekleyin.');uploading=true;const upload_id=uid();
 try{if(file.size>20*1024*1024)throw new Error('Dosya en fazla 20 MB olabilir.');await command('upload_begin',{upload_id,name:file.name,size:file.size,kind});
 const step=512*1024;for(let offset=0;offset<file.size;offset+=step){const bytes=new Uint8Array(await file.slice(offset,offset+step).arrayBuffer());let raw='';for(let i=0;i<bytes.length;i+=8192)raw+=String.fromCharCode(...bytes.subarray(i,i+8192));await command('upload_chunk',{upload_id,offset,chunk:btoa(raw)});}
 // [D44] Yükleme ACK'si PDF'nin başarıyla işlendiği anlamına gelmez; kartı başarılı belge reset'i açar.
 await command('upload_finish',{upload_id});}
 catch(e){await command('upload_abort',{upload_id}).catch(()=>{});if(kind==='photo')field('#apple-photo-state',{id:uid(),name:file.name,ready:false,error:e.message},'apple-photo-update');else field('#apple-document-state',{phase:'error',ingestion:{id:upload_id,name:file.name,stage:'error'}},'apple-document-update');error(e.message);}
 finally{uploading=false;$(kind==='pdf'?'#apple-pdf-upload input':'#apple-photo-upload input').value='';}
};
$('#apple-pdf-upload input').addEventListener('change',e=>{if(e.target.files[0])upload(e.target.files[0],'pdf');});
$('#apple-photo-upload input').addEventListener('change',e=>{if(e.target.files[0])upload(e.target.files[0],'photo');});
$('#pdf-selection-clear').addEventListener('click',()=>{$('#apple-pdf-upload input').value='';$('#apple-pdf-upload .file-preview').hidden=true;$('#apple-pdf-upload .stem').textContent='';ui()?.refresh();});
addEventListener('resize',height);try{parent.visualViewport?.addEventListener('resize',height);}catch(_){}
// Yeniden iletim aynı iş ID'sini kullanır. Ağ kesintisi işlemi iki kez başlatamaz.
setInterval(()=>{if(!flight)return;if(Date.now()-flight.started>45000){const f=flight;flight=null;const e=new Error('Sunucu yanıtı gecikti. Gönderim durumu kontrol ediliyor.');e.unknownOutcome=true;f.reject(e);pump();return;}if(Date.now()-flight.sent>1800)transmit();},600);
post('streamlit:componentReady',{apiVersion:1});height();
})();
""",
'index.html': """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><link rel="stylesheet" href="base.css"><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="streamlit.css"></head><body><main class="research-app"><div class="block apple-phone-header">
        <div class="apple-topbar" data-phase="ready">
            <div class="apple-topbar-left">
                <div class="apple-app-mark">A</div>
                <div class="apple-topbar-copy">
                    <div class="apple-topbar-title">Akıllı Asistan</div>
                    <div class="apple-topbar-meta">
                        <span class="apple-ready-dot"></span>
                        <span class="apple-topbar-phase">Hazır</span>
                        <span class="apple-topbar-separator">·</span>
                        <span class="apple-topbar-model">GPT-5.6 Luna</span>
                        <span class="apple-topbar-separator">·</span>
                        <span id="apple-active-document" class="apple-topbar-pdf">PDF eklenmedi</span>
                    </div>
                </div>
            </div>
            <div class="apple-topbar-right">
                <button type="button" id="apple-global-settings-button" class="apple-topbar-button" data-apple-action="commands" title="Settings (Ctrl+K)" aria-haspopup="dialog" aria-expanded="false" aria-controls="apple-settings-menu">Settings</button>
                <button type="button" class="apple-topbar-button" data-apple-action="inspector" title="Inspector'ı gizle/göster">◫</button>
                <button type="button" class="apple-topbar-button" data-apple-action="theme" title="Koyu/Açık tema">◐</button>
            </div>
        </div>
        <div id="apple-settings-menu" class="apple-command-overlay" popover="manual" aria-hidden="true">
            <div class="apple-command-palette" role="dialog" aria-label="Settings">
                <div class="apple-command-head"><span>Settings</span><button type="button" class="apple-settings-close" data-apple-action="close-settings" aria-label="Settings menüsünü kapat">×</button></div>
                <div class="apple-mode-section">
                    <div class="apple-mode-label">Arayüz modu</div>
                    <div class="apple-mode-options" role="group" aria-label="Arayüz modu">
                        <button type="button" data-ui-mode="0" aria-pressed="true">Kullanıcı</button>
                        <button type="button" data-ui-mode="1" aria-pressed="false">Geliştirici</button>
                    </div>
                    <p class="apple-mode-description">Geliştirici modu istek logunu, token kullanımını ve maliyeti gösterir.</p>
                </div>
                <div class="apple-reset-section">
                    <button type="button" id="apple-reset-pdf" class="apple-reset-button" disabled>↺ Varsayılan PDF’ye dön</button>
                    <small id="apple-reset-hint">Varsayılan PDF kontrol ediliyor…</small>
                    <div id="apple-reset-confirmation" hidden role="group" aria-label="PDF sıfırlama onayı">
                        <p>Bu sohbet temizlenecek ve ortak aktif PDF tüm kullanıcılar için varsayılan PDF’ye dönecek. Diğer kullanıcıların sohbetleri korunur.</p>
                        <button type="button" id="apple-reset-confirm">Sıfırla</button><button type="button" id="apple-reset-cancel">Vazgeç</button>
                    </div>
                </div>
                <div class="apple-command-list">
                    <button class="apple-command-item" data-command="pdf"><span class="apple-command-icon">▱</span><span class="apple-command-label">PDF değiştir</span><span class="apple-command-hint">Dosya seç</span></button>
                    <button class="apple-command-item" data-command="clear"><span class="apple-command-icon">⌫</span><span class="apple-command-label">Sohbeti temizle</span><span class="apple-command-hint">Yeni başlangıç</span></button>
                    <button class="apple-command-item" data-command="memory"><span class="apple-command-icon">◉</span><span class="apple-command-label">Hafızayı aç / kapat</span><span class="apple-command-hint">Son mesajlar</span></button>
                    <button class="apple-command-item" data-command="detail"><span class="apple-command-icon">≡</span><span class="apple-command-label">Detay seviyesini değiştir</span><span class="apple-command-hint">İdeal / Detaylı</span></button>
                    <button class="apple-command-item" data-command="inspector"><span class="apple-command-icon">◫</span><span class="apple-command-label">Inspector'ı aç / kapat</span><span class="apple-command-hint">Yan panel</span></button>
                    <button class="apple-command-item" data-command="theme"><span class="apple-command-icon">◐</span><span class="apple-command-label">Koyu / açık tema</span><span class="apple-command-hint">Görünüm</span></button>
                </div>
            </div>
        </div>
        <div class="apple-toast-stack" aria-live="polite"></div>
        </div>
<div id="apple-document-state" class="transport-field"><textarea></textarea></div><div id="apple-runtime-state" class="transport-field"><textarea></textarea></div><div id="apple-photo-state" class="transport-field"><textarea></textarea></div><div id="apple-pdf-view-request" class="transport-field"><textarea></textarea></div><div id="apple-pdf-view-response" class="transport-field"><textarea></textarea></div>
<button id="apple-pdf-view-submit" class="transport-field">PDF sayfasını getir</button><div id="apple-photo-upload" class="transport-field"><input type="file" accept="image/jpeg,image/png,image/webp,image/gif"></div><button id="apple-photo-clear" class="transport-field">Fotoğrafı kaldır</button>
<div id="apple-mode-controls"><label><input type="radio" name="apple-mode-controls" value="0" checked>Kullanıcı</label><label><input type="radio" name="apple-mode-controls" value="1" >Geliştirici</label></div>
<div id="apple-user-home" class="row apple-main-row apple-home-collapsed"><section class="column apple-chat-column">
<div id="apple-chat" class="chatbot block" data-testid="chatbot"><button class="transport-field" id="native-clear" aria-label="Sohbeti temizle">Temizle</button><div class="bubble-wrap" role="log" aria-label="Sohbet"><div class="placeholder-content"><div class="placeholder"><div class="apple-empty-state"><div class="apple-intelligence-orb"><span></span></div><strong>Bir PDF ekleyerek başlayın</strong><div class="apple-example-prompts"><button class="apple-example-chip" data-empty-action="upload">PDF ekle</button></div></div></div></div></div></div>
<div id="apple-composer" class="row chatgpt-composer"><button class="composer-plus" type="button" aria-label="Dosya ekle">＋</button><div class="mesaj-kutusu block"><textarea rows="2" placeholder="Mesajınızı yazın..." aria-label="Mesajınızı yazın"></textarea></div>
<div id="apple-model-controls"><label><input type="radio" name="apple-model-controls" value="1" checked>GPT-5.6 Luna</label><label><input type="radio" name="apple-model-controls" value="0" >GPT-4o-mini</label></div><div id="apple-detail-controls"><label><input type="radio" name="apple-detail-controls" value="İdeal" checked>İdeal</label><label><input type="radio" name="apple-detail-controls" value="Detaylı" >Detaylı</label><label><input type="radio" name="apple-detail-controls" value="Çok Detaylı" >Çok Detaylı</label></div>
<div class="block" id="apple-reasoning-widget"><button type="button" id="apple-settings-trigger" aria-haspopup="dialog" aria-expanded="false" aria-controls="apple-settings-popover" aria-label="Model ve detay ayarları">
  <span id="apple-summary-model">GPT-5.6 Luna</span><span id="apple-summary-detail">İdeal</span><svg class="apple-summary-arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg>
</button>
<div id="apple-settings-popover" class="apple-reasoning-card" popover="manual" role="dialog" aria-label="Model ve detay ayarları" hidden>
  <div class="apple-reasoning-head">
<span class="apple-reasoning-bolt" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="m13 3-8 11h6l-1 7 9-12h-6l0-6Z"/></svg></span>
<button type="button" id="apple-model-trigger" aria-haspopup="menu" aria-expanded="false" aria-controls="apple-model-popover" aria-label="Model seç">
  <span class="apple-reasoning-title"><span id="apple-reasoning-label">İdeal</span><span class="apple-reasoning-chevron" aria-hidden="true">›</span></span>
  <span id="apple-reasoning-model">GPT-5.6 Luna</span>
</button>
<button type="button" id="apple-reasoning-reset" title="Detay seviyesini sıfırla" aria-label="Detay seviyesini İdeal olarak sıfırla"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 10a8 8 0 1 1 1 8M4 4v6h6"/></svg></button>
  </div>
  <div class="apple-reasoning-rail">
<input id="apple-reasoning-range" type="range" min="0" max="2" step="1" value="0" aria-label="Cevap detay seviyesi" aria-valuetext="İdeal" />
<div class="apple-reasoning-stops" aria-hidden="true"><i></i><i></i><i></i></div>
  </div>
</div>
</div><button class="gonder-butonu" type="button" aria-label="Gönder">↑</button><button id="apple-stop" type="button">Durdur</button><div id="apple-send-visual"><svg id="apple-send-shape" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 11 L12 5 L18 11 M12 5 L12 12 L12 19"/></svg></div><div id="apple-attachment-slot"><div id="apple-composer-attachment" hidden><span class="ai-file-icon">PDF</span><div><strong></strong><small>Belge seçildi</small></div></div></div></div></section>
<aside id="apple-inspector-panel" class="column apple-inspector"><div id="apple-developer-title" class="apple-developer-heading">Geliştirici Modu</div><div class="row"><div class="apple-switch block"><label><input id="memory" type="checkbox" checked><span>🧠 Sohbet Hafızası</span></label><p>Son 10 mesajı hatırlar.</p></div><div class="apple-switch block"><label><input id="advanced-memory" type="checkbox" checked><span>⚡ Gelişmiş Hafıza</span></label><p>Özetlemeden tam iletir.</p></div></div>
<div id="apple-data-controls" class="column"><div id="apple-pdf-heading" class="apple-section-header"><strong>PDF Veritabanı</strong><span>Yeni bir PDF yüklediğinizde ortak arama bağlamı tüm kullanıcılar için güncellenir.</span></div><div id="apple-pdf-upload" class="apple-upload block"><label class="upload-drop"><input type="file" accept="application/pdf,.pdf"><span class="upload-icon">↥</span><span>Dosyayı buraya sürükle</span></label><button id="pdf-selection-clear" class="transport-field" aria-label="PDF seçimini kaldır">Kaldır</button><div class="file-preview" hidden><span class="stem"></span><span class="ext"></span></div></div><div id="apple-update-heading" class="apple-section-header"><strong>Güncelleme Durumu</strong><span>Okuma, vektörleştirme ve kayıt adımları.</span></div><div id="apple-update-status" class="apple-status block"><textarea readonly rows="5">Hazır.</textarea></div></div>
<div id="apple-developer-panel" class="column"><section id="apple-telemetry" aria-label="İstek ölçümleri"><div class="ai-telemetry-head"><span>REQUEST TIMELINE</span><span class="ai-live-badge">Bekliyor</span></div><p class="ai-empty-metrics">Yeni bir istek gönderdiğinizde ölçümler burada görünür.</p><div class="ai-timeline"></div><div class="ai-retrieval"></div><div class="ai-token-breakdown"></div></section><div class="apple-section-header"><strong>İstek Analitiği</strong><span>Token ve maliyet bilgileri.</span></div><div id="token-card" class="apple-developer-box"></div><div class="apple-section-header"><strong>İstek Logu</strong><span>Modele giden JSON payload.</span></div><div class="apple-developer-box"><textarea id="request-log" readonly rows="10">Henüz bir istek gönderilmedi.</textarea></div></div></aside></div></main><script src="ui.js"></script><script src="bridge.js"></script></body></html>
""",
'streamlit.css': """/* Streamlit bağlantı yerleşimi; asıl tasarım ve animasyonlar style.css'te korunur. */
.transport-field{display:none!important}html,body{overflow:hidden}.research-app{height:100dvh!important;min-height:0!important;overflow:hidden!important}.apple-main-row{flex:1 1 auto;min-height:0!important;display:flex}.apple-chat-column{flex:1 1 0;width:0;min-height:0}.apple-chat-column #apple-chat{flex:1 1 0;min-height:0;overflow:hidden}.apple-chat-column #apple-composer{flex-shrink:0}#apple-inspector-panel{flex-shrink:0;width:31%;overflow:auto}#apple-mode-controls,#apple-model-controls,#apple-detail-controls{display:none!important}#apple-pdf-upload{min-height:180px}.file-preview[hidden]{display:none}.apple-switch>label{display:flex;align-items:center;gap:8px}.apple-switch>p{font-size:12px;color:var(--apple-tertiary);margin:0}#apple-chat .message-row[data-role="user"]{align-items:flex-end}#apple-chat .message-content{overflow-wrap:anywhere}#apple-chat .message-content img{max-width:100%}#apple-chat .bot-row{position:relative}#apple-chat .message-content table{display:block;max-width:100%;overflow:auto}.ai-sources-footer{flex:none}#apple-composer .mesaj-kutusu textarea{outline:none}.bridge-error{position:fixed;bottom:130px;left:50%;transform:translateX(-50%);background:var(--material-panel);padding:12px 18px;max-width:90%;border-radius:16px;z-index:20000;box-shadow:var(--material-panel-shadow);font-size:13px}.bridge-error[hidden]{display:none}#apple-chat:has(.placeholder-content) .bubble-wrap{display:flex;align-items:stretch}.placeholder-content .apple-empty-state{margin:auto}#apple-composer .gonder-butonu,#apple-stop{font-size:0!important}
@media(max-width:900px){.apple-main-row{gap:0!important}.apple-chat-column{width:100%}.bubble-wrap{padding:10px 12px}#apple-inspector-panel{display:none!important}.research-app .apple-phone-header{flex-shrink:0}#apple-chat .message-row{padding:10px 0}}
/* Gradio'nun satır yönü ve dosya önizleme kabuğu yerine native DOM karşılıkları. */
#apple-chat .user-row{flex-direction:row!important}
#apple-pdf-upload.apple-has-file .upload-drop{display:none}
#apple-pdf-upload.apple-has-file{min-height:0!important}
.apple-intelligence-orb span{inset:34%}
#apple-ingestion-cancel{pointer-events:auto}
.apple-topbar[data-phase="indexing"] .apple-ready-dot{background:#007aff}
.apple-reset-section{margin:12px 0;padding:12px;border-radius:16px;background:rgba(128,128,140,.07)}.apple-reset-button{padding:10px 0;font-weight:600;font-size:14px}.apple-reset-button:disabled{opacity:.45;cursor:not-allowed}.apple-reset-section small{display:block;font-size:11px;line-height:1.5;color:var(--apple-tertiary,#777)}#apple-reset-confirmation{padding-top:10px;font-size:13px}#apple-reset-confirmation[hidden]{display:none}#apple-reset-confirmation button{padding:9px 14px;margin-right:8px;border-radius:12px;background:rgba(0,122,255,.1)}#apple-ingestion-cancel{align-self:center;flex:none;padding:8px 12px;border-radius:12px;background:rgba(128,128,140,.09);font-size:12px}#apple-ingestion-cancel[hidden]{display:none}.ai-ingestion-copy progress{display:block;width:100%;height:5px;margin-top:8px;accent-color:#007aff}.ai-ingestion-copy progress[hidden]{display:none}.ai-ingestion-copy span{overflow-wrap:anywhere}
""",
'style.css': """
/* Tek tasarım sistemi. Bileşenlerin temel kuralları burada; ekran ve erişilebilirlik koşulları sonda toplanır. */

/* Tasarım değişkenleri */

:root {
    --apple-bg: #f5f5f7;
    --apple-surface: rgba(255, 255, 255, 0.78);
    --apple-surface-strong: rgba(255, 255, 255, 0.92);
    --apple-border: rgba(15, 23, 42, 0.08);
    --apple-border-strong: rgba(15, 23, 42, 0.12);
    --apple-text: #1d1d1f;
    --apple-secondary: #6e6e73;
    --apple-tertiary: #8e8e93;
    --apple-blue: #0071e3;
    --apple-blue-2: #0a84ff;
    --apple-blue-soft: rgba(0, 113, 227, 0.10);
    --apple-green: #34c759;
    --apple-shadow-lg: 0 24px 80px rgba(15, 23, 42, 0.10);
    --apple-shadow-md: 0 14px 38px rgba(15, 23, 42, 0.08);
    --apple-shadow-sm: 0 8px 20px rgba(15, 23, 42, 0.06);
    --apple-spring: cubic-bezier(.22, 1, .36, 1);
    --apple-ease: cubic-bezier(.25, .1, .25, 1);
    --material-canvas: #fafbfc;
    --material-canvas-filter: none;
    --material-canvas-shadow: none;
    --material-float: rgba(255,255,255,.78);
    --material-float-filter: blur(18px) saturate(135%);
    --material-float-shadow: 0 10px 36px rgba(30,42,65,.065), inset 0 1px 0 rgba(255,255,255,.85);
    --material-panel: rgba(247,249,253,.94);
    --material-panel-filter: blur(32px) saturate(160%);
    --material-panel-shadow: 0 24px 80px rgba(24,38,62,.16), inset 0 1px 0 rgba(255,255,255,.9);
    --material-line: rgba(95,110,135,.14);
    --intelligence-ink: #222b39;
    --intelligence-muted: #77808e;
    --intelligence-accent: #1685f7;
    --intelligence-spring: cubic-bezier(.2,.8,.2,1);
    --ai-pressure-shadow: inset 0 1px 3px rgba(15,23,42,.10),0 1px 2px rgba(15,23,42,.025);
}

html.apple-dark {
    --apple-bg: #111113;
    --apple-surface: rgba(37,37,40,.78);
    --apple-surface-strong: rgba(45,45,48,.92);
    --apple-border: rgba(255,255,255,.08);
    --apple-border-strong: rgba(255,255,255,.12);
    --apple-text: #f5f5f7;
    --apple-secondary: #b4b4b8;
    --apple-tertiary: #8e8e93;
    --material-canvas: #141619;
    --material-float: rgba(32,35,41,.8);
    --material-float-shadow: 0 10px 36px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.055);
    --material-panel: rgba(35,39,46,.94);
    --material-panel-shadow: 0 24px 80px rgba(0,0,0,.36), inset 0 1px 0 rgba(255,255,255,.07);
    --material-line: rgba(170,187,213,.17);
    --intelligence-ink: #eef2f8;
    --intelligence-muted: #a2adbd;
    --ai-pressure-shadow: inset 0 1px 3px rgba(0,0,0,.24),0 1px 2px rgba(0,0,0,.1);
}

/* Uygulama ve yerleşim */

body::before {
    content: "";
    position: fixed;
    z-index: -1;
    width: 380px;
    height: 380px;
    border-radius: 999px;
    filter: blur(78px);
    opacity: .34;
    pointer-events: none;
    left: -140px;
    top: 8vh;
    background: rgba(10, 132, 255, .18);
    animation: appleAmbientFloat 16s var(--apple-ease) infinite alternate;
}

body::after {
    content: "";
    position: fixed;
    z-index: -1;
    width: 380px;
    height: 380px;
    border-radius: 999px;
    filter: blur(78px);
    opacity: .34;
    pointer-events: none;
    right: -150px;
    top: 42vh;
    background: rgba(175, 82, 222, .16);
    animation: appleAmbientFloat 18s var(--apple-ease) infinite alternate-reverse;
}

footer {
    display: none !important;
}

h1,
h2,
h3,
p,
span,
label,
textarea,
input,
select,
button {
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}

.research-app .block,
.research-app .panel,
.research-app .form,
.research-app .wrap {
    transition: border-color .24s var(--apple-ease),
        box-shadow .34s var(--apple-spring),
        background .24s var(--apple-ease),
        transform .34s var(--apple-spring);
}

.research-app input[type="checkbox"] {
    accent-color: var(--apple-blue) !important;
}

.research-app input:focus,
.research-app textarea:focus,
.research-app select:focus {
    outline: none !important;
}

.apple-section-header {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin: 4px 0 10px 0;
    padding: 0 4px;
    animation: appleFadeIn .55s var(--apple-spring) both;
}

.apple-section-header strong {
    font-size: 15px;
    line-height: 1.2;
    color: var(--apple-text);
    font-weight: 700;
    letter-spacing: -0.01em;
}

.apple-section-header span {
    font-size: 12px;
    color: var(--apple-tertiary);
    line-height: 1.35;
}

ul.options[role="listbox"],
ul[role="listbox"].options {
    margin-top: 6px !important;
    padding: 8px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,255,255,.80) !important;
    background: rgba(255,255,255,.92) !important;
    box-shadow: 0 22px 60px rgba(15,23,42,.16),
        inset 0 1px 0 rgba(255,255,255,.86) !important;
    backdrop-filter: blur(24px) saturate(170%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(170%) !important;
    overflow: hidden !important;
    animation: applePopoverIn .24s var(--apple-spring) both;
}

li[data-testid="dropdown-option"] {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    min-height: 42px !important;
    padding: 10px 12px !important;
    border-radius: 14px !important;
    color: var(--apple-text) !important;
    font-size: 14px !important;
    font-weight: 520 !important;
    letter-spacing: -0.01em !important;
    transition: transform .22s var(--apple-spring),
        background .18s var(--apple-ease),
        color .18s var(--apple-ease) !important;
}

li[data-testid="dropdown-option"]:hover,
li[data-testid="dropdown-option"].active {
    transform: translateX(1px) !important;
    background: rgba(0,113,227,.08) !important;
}

li[data-testid="dropdown-option"][aria-selected="true"],
li[data-testid="dropdown-option"].selected {
    background: rgba(0,113,227,.12) !important;
    color: #0a4da8 !important;
    font-weight: 700 !important;
}

li[data-testid="dropdown-option"] .inner-item {
    width: 18px !important;
    min-width: 18px !important;
    color: var(--apple-blue) !important;
    font-weight: 800 !important;
}

.placeholder-content {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: stretch !important;
    justify-content: stretch !important;
    padding: 4px !important;
    margin: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    box-sizing: border-box !important;
}

.placeholder-content .placeholder {
    width: 100% !important;
    max-width: none !important;
    min-width: 100% !important;
    min-height: 100% !important;
    height: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    border-radius: 0 !important;
    box-sizing: border-box !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}

.apple-intelligence-orb {
    position: relative;
    display: block !important;
    flex: 0 0 auto;
    width: 102px;
    height: 102px;
    border-radius: 36px;
    background: radial-gradient(circle at 30% 18%, rgba(255,255,255,.98), rgba(255,255,255,.10) 29%, transparent 45%),
        conic-gradient(from 18deg, #67ddff, #6081ff, #bd69ff, #ff72af, #ff9c62, #6fe3ba, #67ddff);
    box-shadow: 0 20px 42px rgba(79,95,255,.17),
        0 9px 24px rgba(255,91,164,.11),
        inset 0 1px 0 rgba(255,255,255,.78);
    animation: appleOrbFloat 4.6s ease-in-out infinite;
    isolation: isolate;
}

.apple-intelligence-orb::before {
    content: "";
    position: absolute;
    inset: 8px;
    border-radius: 28px;
    background: rgba(255,255,255,.63);
    backdrop-filter: blur(13px) saturate(165%);
    -webkit-backdrop-filter: blur(13px) saturate(165%);
    z-index: 1;
}

.apple-intelligence-orb::after {
    content: "";
    position: absolute;
    inset: -14px;
    border-radius: 40px;
    background: conic-gradient(from 180deg, rgba(75,200,255,.22), rgba(153,90,255,.17), rgba(255,92,153,.17), rgba(75,200,255,.22));
    filter: blur(16px);
    z-index: -1;
    animation: appleOrbAura 5.8s linear infinite;
}

.apple-intelligence-orb span {
    position: absolute;
    inset: 35px;
    z-index: 2;
    border-radius: 999px;
    background: rgba(255,255,255,.96);
    box-shadow: 0 0 20px rgba(255,255,255,.95);
    animation: appleOrbCore 2.8s ease-in-out infinite;
}

html {
    scroll-behavior: smooth;
    background: var(--apple-bg) !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 100% !important;
    overflow: hidden !important;
}

body {
    background: radial-gradient(circle at 10% 0%, rgba(10, 132, 255, 0.11), transparent 28%),
        radial-gradient(circle at 100% 12%, rgba(175, 82, 222, 0.08), transparent 24%),
        radial-gradient(circle at 50% 100%, rgba(52, 199, 89, 0.05), transparent 30%),
        linear-gradient(180deg, #fbfbfd 0%, #f6f6f8 40%, #f3f4f6 100%) !important;
    color: var(--apple-text) !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 100% !important;
    overflow: hidden !important;
}

.research-app {
    max-width: 1440px !important;
    width: min(96%, 1440px) !important;
    margin: auto !important;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', Roboto, sans-serif !important;
    color: var(--apple-text) !important;
    animation: applePageIn .55s var(--apple-ease) both;
    height: 100vh !important;
    min-height: 0 !important;
    padding: 8px 12px 10px !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
}

.apple-main-row {
    height: calc(100vh - 76px) !important;
    min-height: 0 !important;
    max-height: calc(100vh - 76px) !important;
    overflow: hidden !important;
    align-items: stretch !important;
}

.apple-example-chip {
    border: 1px solid rgba(15,23,42,.07);
    border-radius: 999px;
    padding: 8px 12px;
    background: rgba(255,255,255,.63);
    color: #6e6e73;
    font-family: inherit;
    font-size: 11px;
    font-weight: 620;
    cursor: pointer;
    box-shadow: 0 5px 14px rgba(15,23,42,.035), inset 0 1px 0 rgba(255,255,255,.80);
    transition: transform .24s var(--apple-spring), color .18s ease, background .18s ease, box-shadow .24s var(--apple-spring);
}

.apple-example-chip:hover {
    transform: translateY(-1px);
    color: #1d1d1f;
    background: rgba(255,255,255,.92);
    box-shadow: 0 8px 18px rgba(15,23,42,.06);
}

.apple-example-chip:active {
    transform: scale(.97);
}

.apple-pdf-compact-card {
    position: relative;
    display: grid;
    grid-template-columns: 38px minmax(0,1fr) auto;
    align-items: center;
    gap: 10px;
    min-height: 66px;
    padding: 9px 10px;
    border: 1px solid rgba(15,23,42,.065);
    border-radius: 20px;
    background: rgba(255,255,255,.72);
    box-shadow: 0 9px 22px rgba(15,23,42,.05), inset 0 1px 0 rgba(255,255,255,.86);
    animation: appleCompactPdfIn .34s var(--apple-spring) both;
}

.apple-pdf-icon {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border-radius: 12px;
    color: #fff;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: -.02em;
    background: linear-gradient(145deg,#ff5f57,#ff375f);
    box-shadow: 0 6px 14px rgba(255,55,95,.16), inset 0 1px 0 rgba(255,255,255,.30);
}

.apple-pdf-info {
    min-width: 0;
}

.apple-pdf-name {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    color: #1d1d1f;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: -.012em;
}

.apple-pdf-sub {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-top: 2px;
    color: #8e8e93;
    font-size: 10px;
}

.apple-pdf-ok {
    color: #248a3d;
    font-weight: 700;
}

.apple-pdf-clear {
    width: 30px;
    height: 30px;
    border: 0;
    border-radius: 10px;
    background: rgba(118,118,128,.075);
    color: #6e6e73;
    font-size: 15px;
    cursor: pointer;
    transition: transform .2s var(--apple-spring), background .18s ease;
}

.apple-pdf-clear:hover {
    transform: scale(1.04);
    background: rgba(255,59,48,.10);
    color: #ff3b30;
}

.apple-pdf-clear:active {
    transform: scale(.92);
}

body[data-apple-phase="thinking"]::before {
    opacity: .48;
    animation-duration: 8s !important;
}

body[data-apple-phase="web"]::before {
    background: rgba(10,132,255,.25) !important;
    opacity: .52;
}

body[data-apple-phase="web"]::after {
    background: rgba(48,209,88,.13) !important;
    opacity: .40;
}

body[data-apple-phase="streaming"]::after {
    background: rgba(191,90,242,.18) !important;
    opacity: .44;
    animation-duration: 9s !important;
}

html.apple-dark .apple-pdf-compact-card {
    background: rgba(35,35,38,.78) !important;
    border-color: rgba(255,255,255,.085) !important;
    box-shadow: 0 18px 52px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.055) !important;
}

html.apple-dark .apple-pdf-name {
    color: #f5f5f7 !important;
}

html.apple-dark ul.options[role="listbox"],
html.apple-dark ul[role="listbox"].options {
    background: rgba(38,38,41,.96) !important;
    border-color: rgba(255,255,255,.09) !important;
    color: #f5f5f7 !important;
}

html.apple-dark li[data-testid="dropdown-option"] {
    color: #e5e5ea !important;
}

.research-app.apple-mobile {
    position: fixed !important;
    top: var(--apple-phone-top, 0px) !important;
    left: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
    max-width: none !important;
    height: var(--apple-mobile-height, 100dvh) !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: max(6px, env(safe-area-inset-top)) max(8px, env(safe-area-inset-right)) max(8px, env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left)) !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
    animation: none !important;
    transform: none !important;
}

.research-app.apple-mobile .apple-phone-shell {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 0 !important;
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    padding: 0 !important;
    margin: 0 !important;
    gap: 6px !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

.research-app.apple-mobile .apple-phone-header {
    flex: 0 0 auto !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 0 !important;
    overflow: visible !important;
}

.research-app.apple-mobile .apple-main-row.apple-main-row {
    flex: 1 1 0 !important;
    display: flex !important;
    flex-direction: column !important;
    flex-wrap: nowrap !important;
    width: 100% !important;
    min-width: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: none !important;
    margin: 0 !important;
    gap: 0 !important;
    position: relative !important;
    overflow: hidden !important;
}

#apple-mode-controls#apple-mode-controls {
    display: none !important;
}

#apple-data-controls#apple-data-controls {
    display: contents !important;
}

html body {
    background: var(--material-canvas) !important;
}

html.apple-dark body {
    color: #f5f5f7 !important;
    background: var(--material-canvas) !important;
}

html .research-app {
    background: var(--material-canvas) !important;
}

#apple-runtime-state#apple-runtime-state,
.form:has(> #apple-runtime-state) {
    display: none !important;
}

.ai-file-icon {
    display: grid;
    place-items: center;
    flex: 0 0 32px;
    width: 32px;
    height: 36px;
    border-radius: 8px;
    background: rgba(31,136,245,.09);
    color: #1685f7;
    font-size: 9px;
    font-weight: 700;
}

.ai-sheet-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 25px 24px 18px;
    border-bottom: 1px solid var(--material-line);
}

.ai-sheet-head small {
    font-size: 9px;
    font-weight: 650;
    letter-spacing: .16em;
    color: var(--intelligence-muted);
}

.ai-sheet-head h2 {
    margin: 7px 0 0;
    font-size: 22px;
    letter-spacing: -.6px;
    color: var(--intelligence-ink);
}

.ai-sheet-close {
    width: 36px;
    height: 36px;
    border: 1px solid var(--material-line);
    border-radius: 50%;
    background: var(--material-float);
    color: var(--intelligence-ink);
    font-size: 22px;
    cursor: pointer;
}

.ai-sheet-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 18px 20px 26px;
    overscroll-behavior: contain;
}

.ai-live-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border: 1px solid var(--material-line);
    border-radius: 99px;
    padding: 4px 7px;
    font-size: 9px;
    letter-spacing: 0;
}

.ai-live-badge::before {
    content: '';
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: currentColor;
}

.ai-timeline {
    display: grid;
    grid-template-columns: repeat(2,minmax(0,1fr));
    gap: 0 18px;
}

#apple-document-state,
.form:has(> #apple-document-state) {
    display: none !important;
}

.ai-pdf-open-passage {
    margin: 4px 14px 12px;
    padding: 7px 10px;
    border: 1px solid var(--material-line,#ddd);
    border-radius: 10px;
    background: transparent;
    color: var(--intelligence-ink,#222);
    font-size: 11px;
    cursor: pointer;
}

.ai-pdf-open-passage:active {
    transform: scale(.96);
}

.research-app.apple-mobile #apple-active-document {
    display: inline-flex !important;
    max-width: 92px;
    min-width: 0;
    padding: 4px 0;
}

/* Üst bar */

.apple-topbar {
    margin-top: 0 !important;
    margin-bottom: 8px !important;
    position: sticky;
    top: 8px;
    z-index: 90;
    display: grid;
    grid-template-columns: minmax(0,1fr) auto;
    align-items: center;
    gap: 12px;
    min-height: 48px;
    margin: 2px 0 12px 0;
    padding: 7px 8px 7px 14px;
    border: 1px solid rgba(255,255,255,.78);
    border-radius: 22px;
    background: rgba(255,255,255,.70);
    box-shadow: 0 10px 30px rgba(15,23,42,.065), inset 0 1px 0 rgba(255,255,255,.90);
    backdrop-filter: blur(24px) saturate(170%);
    -webkit-backdrop-filter: blur(24px) saturate(170%);
    animation: appleTopbarIn .5s var(--apple-spring) both;
}

.apple-topbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
}

.apple-topbar-right {
    display: flex;
    align-items: center;
    gap: 6px;
}

.apple-app-mark {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    flex: 0 0 30px;
    border-radius: 10px;
    color: #fff;
    font-size: 13px;
    font-weight: 800;
    background: linear-gradient(145deg,#52c8ff,#6a74ff 43%,#e168ff 72%,#ff789f);
    box-shadow: 0 6px 16px rgba(97,95,255,.22), inset 0 1px 0 rgba(255,255,255,.46);
}

.apple-topbar-copy {
    min-width: 0;
}

.apple-topbar-title {
    color: #1d1d1f;
    font-size: 13px;
    line-height: 1.15;
    font-weight: 720;
    letter-spacing: -.018em;
}

.apple-topbar-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    margin-top: 2px;
    color: #8e8e93;
    font-size: 10px;
    line-height: 1.15;
}

.apple-topbar-separator {
    opacity: .48;
}

.apple-ready-dot {
    width: 8px;
    height: 8px;
    flex: 0 0 8px;
    border-radius: 999px;
    background: #34c759;
    box-shadow: 0 0 0 3px rgba(52,199,89,.10);
    transition: background .2s ease, box-shadow .2s ease, transform .25s var(--apple-spring);
}

.apple-topbar[data-phase="thinking"] .apple-ready-dot,
.apple-topbar[data-phase="web"] .apple-ready-dot {
    background: #0a84ff;
    box-shadow: 0 0 0 4px rgba(10,132,255,.10);
    animation: appleStatusPulse 1.35s ease-in-out infinite;
}

.apple-topbar[data-phase="streaming"] .apple-ready-dot {
    background: #bf5af2;
    box-shadow: 0 0 0 4px rgba(191,90,242,.10);
    animation: appleStatusPulse 1.1s ease-in-out infinite;
}

.apple-topbar-button {
    display: inline-grid;
    place-items: center;
    width: 34px;
    height: 34px;
    min-width: 34px;
    padding: 0;
    border: 0;
    border-radius: 12px;
    background: rgba(118,118,128,.075);
    color: #48484a;
    font-size: 15px;
    cursor: pointer;
    transition: transform .24s var(--apple-spring), background .18s ease, box-shadow .24s var(--apple-spring);
}

.apple-topbar-button:hover {
    transform: translateY(-1px);
    background: rgba(118,118,128,.12);
    box-shadow: 0 5px 12px rgba(15,23,42,.07);
}

.apple-topbar-button:active {
    transform: scale(.92);
}

html.apple-dark .apple-topbar {
    background: rgba(35,35,38,.78) !important;
    border-color: rgba(255,255,255,.085) !important;
    box-shadow: 0 18px 52px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.055) !important;
}

html.apple-dark .apple-topbar-title {
    color: #f5f5f7 !important;
}

html.apple-dark .apple-topbar-button {
    background: rgba(118,118,128,.18) !important;
    color: #d1d1d6 !important;
}

.research-app.apple-mobile .apple-topbar {
    position: relative !important;
    top: 0 !important;
    margin: 0 !important;
    min-height: 52px !important;
    padding: 4px 6px 4px 10px !important;
    border-radius: 17px !important;
    box-sizing: border-box !important;
}

.research-app.apple-mobile .apple-topbar-pdf {
    display: none !important;
}

.research-app.apple-mobile .apple-topbar-button {
    width: 44px !important;
    height: 44px !important;
}

.research-app.apple-mobile .apple-topbar-meta {
    white-space: nowrap;
    overflow: hidden;
}

html .apple-topbar {
    background: var(--material-float) !important;
    backdrop-filter: var(--material-float-filter) !important;
    -webkit-backdrop-filter: var(--material-float-filter) !important;
    box-shadow: var(--material-float-shadow) !important;
    border: 1px solid var(--material-line) !important;
}

body[data-apple-phase="web"] .apple-topbar {
    --intelligence-accent: #199ba6;
}

.apple-topbar .apple-ready-dot {
    transition: background-color 450ms ease, box-shadow 450ms ease !important;
}

body:is([data-apple-phase="retrieval"],[data-apple-phase="thinking"],[data-apple-phase="web"],[data-apple-phase="streaming"]) .apple-topbar .apple-ready-dot {
    background: var(--intelligence-accent) !important;
    animation: intelligenceBeacon 1.8s ease-in-out infinite !important;
}

body[data-apple-phase="error"] .apple-topbar .apple-ready-dot {
    background: #e05a63 !important;
    box-shadow: 0 0 0 3px rgba(224,90,99,.09) !important;
}

.apple-topbar-pdf {
    max-width: 250px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    position: relative;
}

.apple-topbar-pdf .ai-pdf-name-current {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.apple-topbar-pdf .ai-pdf-name-outgoing {
    position: absolute;
    inset: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    pointer-events: none;
}

:is(#apple-composer,#apple-chat,#apple-source-sheet,#apple-model-popover,#apple-settings-menu,#apple-settings-popover,#apple-inspector-panel,.apple-topbar) [data-ai-pressed="true"] {
    box-shadow: var(--ai-pressure-shadow) !important;
    transform: none !important;
}

:where(.apple-topbar button, #apple-composer button, #apple-settings-popover button, #apple-model-popover button, #apple-settings-menu button, #apple-chat .apple-example-chip, #apple-chat .ai-source-capsule, #apple-chat .ai-inline-citation, #apple-chat .apple-scroll-bottom, #apple-source-sheet summary, #apple-source-sheet a.ai-source-web, #apple-source-sheet button, #apple-inspector-panel label:has(input[type="checkbox"]), #apple-inspector-panel label:has(input[type="radio"])) {
    -webkit-tap-highlight-color: transparent;
}

.apple-topbar-pdf[role="button"] {
    cursor: pointer;
}

.apple-topbar-pdf:focus-visible {
    outline: 2px solid #3989f9;
    outline-offset: 3px;
}

/* Sohbet ve boş ekran */

.research-app > .prose,
.research-app > div > .prose {
    animation: appleHeaderIn .8s .05s var(--apple-spring) both;
}

.research-app [data-testid="chatbot"],
.research-app .chatbot {
    background: rgba(255, 255, 255, .62) !important;
    border: 1px solid rgba(255, 255, 255, .74) !important;
    border-radius: 28px !important;
    box-shadow: 0 24px 70px rgba(15, 23, 42, .08),
        inset 0 1px 0 rgba(255, 255, 255, .76) !important;
    backdrop-filter: blur(24px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
    overflow: hidden !important;
    animation: appleCardIn .72s .1s var(--apple-spring) both;
}

.research-app .message-row {
    animation: appleMessageIn .40s var(--apple-spring) both;
}

.research-app [data-testid="chatbot"] .message:hover,
.research-app .chatbot .message:hover {
    transform: translateY(-1px) !important;
}

.research-app [data-testid="chatbot"] .prose,
.research-app .chatbot .prose {
    line-height: 1.6 !important;
    letter-spacing: -0.008em !important;
}

.research-app [data-testid="chatbot"] pre,
.research-app .chatbot pre {
    border-radius: 16px !important;
    border: 1px solid var(--apple-border) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.10) !important;
}

.research-app [data-testid="chatbot"] .wrapper,
.research-app .chatbot .wrapper {
    width: 100% !important;
    height: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
    box-sizing: border-box !important;
}

.research-app [data-testid="chatbot"] .message-row,
.research-app .chatbot .message-row {
    margin: 6px 0 !important;
}

.research-app [data-testid="chatbot"] .message,
.research-app .chatbot .message {
    animation: appleMessageIn .40s var(--apple-spring) both;
    border-radius: 22px !important;
    transition: transform .28s var(--apple-spring),
        box-shadow .28s var(--apple-spring),
        background .22s var(--apple-ease) !important;
    width: fit-content !important;
    min-height: auto !important;
    box-sizing: border-box !important;
}

.research-app [data-testid="chatbot"] .user-row > .flex-wrap.user,
.research-app .chatbot .user-row > .flex-wrap.user {
    width: fit-content !important;
    max-width: min(68%, 460px) !important;
    height: auto !important;
    min-height: 0 !important;
    align-self: flex-end !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    overflow: visible !important;
}

.research-app [data-testid="chatbot"] .user-row > .flex-wrap.user > .user,
.research-app .chatbot .user-row > .flex-wrap.user > .user {
    width: fit-content !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    align-self: flex-end !important;
    padding: 9px 13px !important;
    margin: 0 !important;
    border-radius: 17px 17px 5px 17px !important;
    box-sizing: border-box !important;
    box-shadow: 0 5px 14px rgba(15,23,42,.05),
        inset 0 1px 0 rgba(255,255,255,.42) !important;
}

.research-app .chatbot .user-row .message {
    width: fit-content !important;
    max-width: 100% !important;
    min-width: 0 !important;
    min-height: 0 !important;
    height: auto !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}

.research-app [data-testid="chatbot"] .user-row .message > [data-testid="user"],
.research-app .chatbot .user-row .message > [data-testid="user"] {
    width: fit-content !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 0 !important;
}

.research-app .chatbot .user-row .message-content,
.research-app .chatbot .user-row .prose {
    width: fit-content !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.research-app [data-testid="chatbot"] .user-row .message-content p,
.research-app .chatbot .user-row .message-content p {
    font-size: 15px !important;
    line-height: 1.4 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.research-app .chatbot .user-row .prose p {
    margin: 0 !important;
    padding: 0 !important;
}

.research-app [data-testid="chatbot"] .bot-row .message,
.research-app .chatbot .bot-row .message {
    max-width: min(86%, 760px) !important;
    padding: 11px 15px !important;
    border-radius: 19px !important;
    box-shadow: 0 8px 20px rgba(15,23,42,.045),
        inset 0 1px 0 rgba(255,255,255,.50) !important;
}

.research-app [data-testid="chatbot"] .bot-row .message-content p,
.research-app .chatbot .bot-row .message-content p {
    font-size: 15px !important;
    line-height: 1.5 !important;
}

.research-app [data-testid="chatbot"] .message > [data-testid],
.research-app .chatbot .message > [data-testid] {
    width: auto !important;
    min-width: 0 !important;
}

.research-app [data-testid="chatbot"] .message-content,
.research-app .chatbot .message-content {
    width: auto !important;
    min-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.research-app [data-testid="chatbot"] .message-content .prose,
.research-app .chatbot .message-content .prose {
    margin: 0 !important;
}

.research-app [data-testid="chatbot"] .message-content p,
.research-app .chatbot .message-content p {
    margin: 0 !important;
    font-size: 15px !important;
    line-height: 1.45 !important;
}

.research-app [data-testid="chatbot"] .placeholder,
.research-app .chatbot .placeholder {
    width: 100% !important;
    max-width: none !important;
    min-width: 100% !important;
    min-height: 100% !important;
    height: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    border-radius: 0 !important;
    box-sizing: border-box !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}

.apple-empty-state strong {
    display: inline-block;
    margin: 0 !important;
    padding: 0 !important;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', sans-serif;
    font-size: clamp(21px, 1.85vw, 28px);
    line-height: 1.14;
    font-weight: 650;
    letter-spacing: -.034em;
    color: #1d1d1f;
    text-wrap: balance;
    text-shadow: 0 1px 0 rgba(255,255,255,.60);
}

.apple-processing-status {
    position: relative;
    display: grid;
    grid-template-columns: 10px minmax(0,1fr);
    align-items: center;
    column-gap: 10px;
    row-gap: 8px;
    min-width: 230px;
    padding: 11px 13px;
    border-radius: 18px;
    border: 1px solid rgba(15,23,42,.06);
    background: rgba(255,255,255,.72);
    box-shadow: 0 8px 22px rgba(15,23,42,.055), inset 0 1px 0 rgba(255,255,255,.82);
    backdrop-filter: blur(18px) saturate(155%);
    -webkit-backdrop-filter: blur(18px) saturate(155%);
    overflow: hidden;
}

.apple-processing-status strong {
    font-size: 13px;
    line-height: 1.25;
    color: var(--apple-text);
    font-weight: 700;
}

.apple-processing-status small {
    font-size: 10.5px;
    line-height: 1.25;
    color: var(--apple-tertiary);
}

.apple-processing-dot {
    width: 9px;
    height: 9px;
    border-radius: 999px;
    background: #0a84ff;
    box-shadow: 0 0 0 0 rgba(10,132,255,.26);
    animation: appleStatusPulse 1.7s ease-out infinite;
}

.apple-processing-status.web .apple-processing-dot {
    background: #5856d6;
}

.research-app .bot-row .message:has(.apple-processing-status),
.research-app [data-testid="chatbot"] .bot-row .message:has(.apple-processing-status) {
    padding: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    border: 0 !important;
    max-width: 390px !important;
}

.apple-chat-column > [data-testid="chatbot"],
.apple-chat-column > .chatbot,
.apple-chat-column [data-testid="chatbot"] {
    flex: 1 1 auto !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
}

.apple-empty-state {
    width: 100%;
    max-width: none;
    height: 100%;
    min-height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 42px 34px;
    box-sizing: border-box;
    text-align: center;
    color: var(--apple-text);
    background: rgba(255, 255, 255, .60);
    border: 1px solid rgba(255,255,255,.82);
    border-radius: 42px;
    box-shadow: 0 28px 64px rgba(15, 23, 42, .08),
        inset 0 1px 0 rgba(255,255,255,.86);
    backdrop-filter: blur(20px) saturate(160%);
    -webkit-backdrop-filter: blur(20px) saturate(160%);
    animation: appleEmptyIn .72s var(--apple-spring) both;
    gap: 22px !important;
}

.apple-example-prompts {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 7px;
    max-width: 640px;
    margin-top: 1px;
}

.apple-chat-column {
    min-height: 0 !important;
    height: 100% !important;
    max-height: 100% !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
    flex-wrap: nowrap !important;
    min-width: 0 !important;
    overflow: hidden !important;
    transition: none !important;
}

html.apple-dark .apple-empty-state {
    background: rgba(35,35,38,.78) !important;
    border-color: rgba(255,255,255,.085) !important;
    box-shadow: 0 18px 52px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.055) !important;
}

html.apple-dark .research-app [data-testid="chatbot"],
html.apple-dark .research-app .chatbot {
    background: rgba(25,25,27,.58) !important;
    border-color: rgba(255,255,255,.07) !important;
}

html.apple-dark .apple-empty-state strong,
html.apple-dark .research-app .user-row .message,
html.apple-dark .research-app [data-testid="chatbot"] .user-row .message {
    color: #f5f5f7 !important;
}

html.apple-dark .research-app .bot-row .message,
html.apple-dark .research-app [data-testid="chatbot"] .bot-row .message {
    color: #e5e5ea !important;
}

.research-app [data-testid="chatbot"] .user-row {
    width: 100% !important;
    min-width: 0 !important;
    justify-content: flex-end !important;
    align-items: flex-start !important;
}

.research-app [data-testid="chatbot"] .user-row > .flex-wrap {
    flex: 0 1 auto !important;
    width: fit-content !important;
    min-width: 0 !important;
    max-width: min(85%, 560px) !important;
    height: auto !important;
    min-height: 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    margin-left: auto !important;
    align-self: flex-start !important;
}

.research-app [data-testid="chatbot"] .user-row .wrapper {
    flex: 0 1 auto !important;
    width: fit-content !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow-wrap: anywhere !important;
}

.research-app [data-testid="chatbot"] .user-row .message {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    flex: 0 1 auto !important;
    width: fit-content !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow-wrap: anywhere !important;
}

.research-app [data-testid="chatbot"] .user-row .message-content,
.research-app [data-testid="chatbot"] .user-row .prose,
.research-app [data-testid="chatbot"] .user-row [data-testid="user"] {
    flex: 0 1 auto !important;
    width: fit-content !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow-wrap: anywhere !important;
}

.research-app [data-testid="chatbot"] .user-row > .flex-wrap > .user {
    flex: 0 1 auto !important;
    width: fit-content !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    padding: 8px 12px !important;
    align-self: flex-start !important;
}

.research-app [data-testid="chatbot"] .user-row .prose p {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.4 !important;
}

.research-app [data-testid="chatbot"] .bot-row .wrapper {
    height: auto !important;
    min-height: 0 !important;
}

.research-app [data-testid="chatbot"] .user-row .user:not(.flex-wrap) {
    width: fit-content !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    padding: 8px 12px !important;
    background: var(--color-accent-soft, #fff7e9) !important;
    border: 1px solid var(--border-color-accent-subdued, #ffdbad) !important;
    border-radius: 17px 17px 5px 17px !important;
    box-sizing: border-box !important;
}

.research-app [data-testid="chatbot"] .user-row > .flex-wrap > div {
    height: auto !important;
    min-height: 0 !important;
    max-width: 100% !important;
    min-width: 0 !important;
}

#apple-chat .user-row {
    display: flex !important;
    flex: 0 0 auto !important;
    justify-content: flex-end !important;
    align-items: flex-start !important;
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

#apple-chat .user-row .flex-wrap,
#apple-chat .user-row .flex-wrap > div,
#apple-chat .user-row .user,
#apple-chat .user-row .message,
#apple-chat .user-row [data-testid="user"],
#apple-chat .user-row .wrapper {
    display: block !important;
    flex: 0 1 auto !important;
    width: fit-content !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    box-sizing: border-box !important;
    align-self: flex-start !important;
}

#apple-chat .user-row > .flex-wrap {
    max-width: min(85%, 560px) !important;
    margin-left: auto !important;
}

#apple-chat .user-row .message-content {
    display: block !important;
    width: fit-content !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 7px 11px !important;
    border: 1px solid var(--border-color-accent-subdued, #ffdbad) !important;
    border-radius: 17px 17px 5px 17px !important;
    background: var(--color-accent-soft, #fff7e9) !important;
    box-shadow: none !important;
    box-sizing: border-box !important;
    overflow-wrap: anywhere !important;
}

#apple-chat .user-row .message-content p {
    margin: 0 !important;
    padding: 0 !important;
    font-size: 15px !important;
    line-height: 1.4 !important;
}

#apple-chat .user-row .message-content pre {
    max-width: 100% !important;
    overflow-x: auto !important;
}

#apple-chat .user-row .message-content .prose,
#apple-chat .user-row .message-content .md {
    display: block !important;
    width: auto !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    font-size: 15px !important;
    line-height: 1.4 !important;
    overflow-wrap: anywhere !important;
    border-radius: 0 !important;
    overflow: visible !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    animation: none !important;
    transform: none !important;
}

.research-app.apple-mobile .apple-chat-column {
    flex: 1 1 0 !important;
    min-height: 0 !important;
}

.research-app.apple-mobile .apple-main-row .apple-chat-column.apple-chat-column {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: none !important;
    padding: 0 !important;
    gap: 6px !important;
    overflow: hidden !important;
}

.research-app.apple-mobile .apple-main-row .apple-chat-column > #apple-chat {
    flex: 1 1 0 !important;
    width: 100% !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: none !important;
    border-radius: 18px !important;
    overflow: hidden !important;
}

.research-app.apple-mobile .apple-example-prompts {
    gap: 5px !important;
}

.research-app.apple-mobile .apple-empty-state {
    padding: 12px !important;
    gap: 12px !important;
}

#apple-chat .bot-row .message {
    animation: none !important;
}

#apple-chat .bot-row [data-testid="bot"] {
    transform-origin: left top;
    animation: none !important;
}

#apple-chat .apple-processing-status {
    animation: none !important;
}

#apple-chat .bot-row.ai-morphing {
    overflow: visible !important;
}

#apple-chat :is(.bot-row,.user-row) button:is([aria-label="Copy"],[title="Copy"],[aria-label="Copy message"],[aria-label="Retry"],[title="Retry"],[aria-label="Regenerate"],[title="Regenerate"],[aria-label="Kopyala"],[aria-label="Yeniden üret"],[aria-label="Yeniden oluştur"]) {
    display: none !important;
}

#apple-chat#apple-chat {
    background: var(--material-canvas) !important;
    box-shadow: var(--material-canvas-shadow) !important;
    backdrop-filter: var(--material-canvas-filter) !important;
    border-color: var(--material-line) !important;
    overflow: hidden !important;
}

#apple-chat .scroll-down-button-container {
    display: none !important;
}

#apple-chat > .wrapper {
    flex: 1 1 0 !important;
    min-height: 0 !important;
    min-width: 0 !important;
    overflow: hidden !important;
    z-index: 0;
}

#apple-chat > .wrapper > .bubble-wrap {
    flex: 1 1 0 !important;
    min-height: 0 !important;
    min-width: 0 !important;
    overflow: auto !important;
    overscroll-behavior: contain;
}

#apple-chat .apple-empty-state {
    animation: none !important;
}

#apple-chat .apple-empty-state strong {
    max-width: 580px;
    overflow-wrap: anywhere;
    line-height: 1.24;
}

#apple-chat .apple-example-prompts {
    flex-wrap: wrap;
    justify-content: center;
}

#apple-chat[data-resetting="true"] {
    pointer-events: none;
}

#apple-chat .apple-empty-heading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 9px;
    max-width: 100%;
}

#apple-chat .apple-empty-document {
    display: block;
    max-width: min(560px,100%);
    color: var(--intelligence-ink);
    opacity: .56;
    font-size: clamp(15px,1.35vw,20px);
    font-weight: 450;
    line-height: 1.4;
    letter-spacing: -.015em;
    overflow-wrap: anywhere;
    text-wrap: balance;
}

#apple-chat .apple-empty-document[hidden] {
    display: none;
}

#apple-chat .apple-empty-heading strong {
    display: block;
    max-width: 600px;
}

#apple-chat .bot-row {
    position: relative !important;
    transition: transform 380ms cubic-bezier(.2,.8,.2,1);
}

#apple-chat [data-testid="bot"].ai-stream-surface {
    min-height: var(--ai-stream-floor,112px) !important;
    box-sizing: border-box;
}

#apple-chat [data-testid="bot"]:has(.apple-processing-status) {
    min-height: 112px !important;
}

.ai-ingestion-pages:empty {
    border: 1px solid var(--material-line,#ddd);
    border-radius: 7px;
    background: linear-gradient(#f2f3f5,#fff);
}

.apple-empty-state[data-typing="true"] {
    opacity: 0 !important;
    visibility: hidden;
    pointer-events: none;
    transition: opacity 100ms ease,visibility 0s 100ms;
}

.apple-empty-state:not([data-typing="true"]) {
    transition: opacity 150ms ease;
}

.apple-empty-document {
    font-weight: 450 !important;
    opacity: .65;
}

#apple-chat .user-row img {
    max-width: min(300px,65vw);
    max-height: 260px;
    object-fit: contain;
    border-radius: 16px;
}

/* Composer ve ekler */

.chatgpt-composer::before {
    content: "";
    position: absolute;
    inset: -1px;
    z-index: -1;
    border-radius: inherit;
    padding: 1px;
    background: linear-gradient(120deg, rgba(255,255,255,.86), rgba(0,113,227,.18), rgba(255,255,255,.70));
    opacity: 0;
    transition: opacity .28s var(--apple-ease);
    pointer-events: none;
}

.chatgpt-composer:hover {
    border-color: rgba(15,23,42,.10) !important;
    box-shadow: 0 20px 50px rgba(15,23,42,.10),
        0 4px 14px rgba(15,23,42,.05),
        inset 0 1px 0 rgba(255,255,255,.9) !important;
}

.chatgpt-composer:focus-within {
    border-color: rgba(0,113,227,.28) !important;
    background: rgba(255,255,255,.92) !important;
    box-shadow: 0 24px 58px rgba(15,23,42,.11),
        0 0 0 4px rgba(0,113,227,.08),
        inset 0 1px 0 rgba(255,255,255,.94) !important;
}

.chatgpt-composer:focus-within::before {
    opacity: 1;
}

.chatgpt-composer > div,
.chatgpt-composer .form,
.chatgpt-composer .block,
.chatgpt-composer .wrap,
.chatgpt-composer .container {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    margin: 0 !important;
    min-width: 0 !important;
}

.composer-plus {
    flex: 0 0 42px !important;
    min-width: 42px !important;
    max-width: 42px !important;
    height: 42px !important;
    min-height: 42px !important;
    padding: 0 !important;
    margin: 0 !important;
}

.composer-plus button,
button.composer-plus {
    width: 42px !important;
    height: 42px !important;
    min-height: 42px !important;
    border: 1px solid transparent !important;
    border-radius: 999px !important;
    background: rgba(15,23,42,.045) !important;
    color: #252527 !important;
    font-size: 27px !important;
    font-weight: 300 !important;
    line-height: 1 !important;
    padding: 0 0 3px 0 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.76) !important;
    cursor: pointer !important;
    transition: transform .34s var(--apple-spring),
        background .2s var(--apple-ease),
        box-shadow .3s var(--apple-spring),
        border-color .2s var(--apple-ease) !important;
}

.composer-plus button:hover,
button.composer-plus:hover {
    transform: scale(1.06) rotate(2deg) !important;
    background: rgba(15,23,42,.075) !important;
    border-color: rgba(15,23,42,.045) !important;
    box-shadow: 0 6px 16px rgba(15,23,42,.08) !important;
}

.composer-plus button:active,
button.composer-plus:active {
    transform: scale(.90) rotate(-3deg) !important;
    transition-duration: 90ms !important;
}

.mesaj-kutusu {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}

.mesaj-kutusu label,
.mesaj-kutusu .container,
.mesaj-kutusu .wrap,
.mesaj-kutusu .form {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 !important;
}

.mesaj-kutusu textarea {
    min-height: 48px !important;
    max-height: 150px !important;
    padding: 10px 8px !important;
    resize: none !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    font-size: 16px !important;
    line-height: 24px !important;
    letter-spacing: -0.01em !important;
    color: var(--apple-text) !important;
    caret-color: var(--apple-blue) !important;
    transition: color .2s var(--apple-ease) !important;
}

.mesaj-kutusu textarea::placeholder {
    color: #98989d !important;
    opacity: 1 !important;
    transition: opacity .22s var(--apple-ease) !important;
}

.mesaj-kutusu textarea:focus::placeholder {
    opacity: .56 !important;
}

.gonder-butonu {
    flex: 0 0 48px !important;
    min-width: 48px !important;
    max-width: 48px !important;
    height: 48px !important;
    min-height: 48px !important;
    padding: 0 !important;
    margin: 0 !important;
}

.gonder-butonu button::before,
button.gonder-butonu::before {
    content: "";
    position: absolute;
    inset: -35%;
    background: linear-gradient(120deg, transparent 28%, rgba(255,255,255,.24) 50%, transparent 72%);
    transform: translateX(-120%) rotate(10deg);
    animation: appleShimmer 3.8s ease-in-out infinite;
    pointer-events: none;
}

.gonder-butonu button:hover,
button.gonder-butonu:hover {
    transform: translateY(-2px) scale(1.055) !important;
    filter: brightness(1.04) !important;
    box-shadow: 0 14px 28px rgba(0,113,227,.32),
        0 6px 12px rgba(0,113,227,.18),
        inset 0 1px 0 rgba(255,255,255,.34) !important;
}

.gonder-butonu button:active,
button.gonder-butonu:active {
    transform: scale(0.86) !important;
    filter: brightness(0.91) !important;
    box-shadow: 0 4px 10px rgba(0,113,227,.20),
        inset 0 1px 0 rgba(255,255,255,.22) !important;
    transition-duration: 85ms !important;
}

.research-app button:not(.gonder-butonu):not(.composer-plus) {
    border-radius: 14px !important;
    transition: transform .30s var(--apple-spring),
        box-shadow .30s var(--apple-spring),
        filter .18s var(--apple-ease),
        background .20s var(--apple-ease) !important;
}

.research-app button:not(.gonder-butonu):not(.composer-plus):hover {
    transform: translateY(-1px) !important;
}

.research-app button:not(.gonder-butonu):not(.composer-plus):active {
    transform: scale(.96) !important;
    transition-duration: 90ms !important;
}

.gonder-butonu button:disabled,
button.gonder-butonu:disabled {
    opacity: 0.56 !important;
    cursor: default !important;
    transform: scale(.96) !important;
    box-shadow: 0 4px 12px rgba(0,113,227,.10) !important;
    animation: none !important;
    color: transparent !important;
    position: relative !important;
}

.gonder-butonu button:disabled::after,
button.gonder-butonu:disabled::after {
    content: "" !important;
    position: absolute !important;
    width: 16px !important;
    height: 16px !important;
    inset: 50% auto auto 50% !important;
    border: 2px solid rgba(255,255,255,.40) !important;
    border-top-color: #fff !important;
    border-radius: 999px !important;
    background: transparent !important;
    transform: translate(-50%,-50%) !important;
    animation: appleSpinner .72s linear infinite !important;
    opacity: 1 !important;
}

.chatgpt-composer::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 0;
    border-radius: inherit;
    pointer-events: none;
    opacity: 0;
    background: radial-gradient(190px circle at var(--apple-mx) var(--apple-my), rgba(10,132,255,.085), transparent 62%);
    transition: opacity .22s ease;
}

.chatgpt-composer:hover::after,
.chatgpt-composer:focus-within::after {
    opacity: 1;
}

.chatgpt-composer > * {
    position: relative;
    z-index: 1;
}

.gonder-butonu button,
button.gonder-butonu {
    position: relative !important;
    overflow: hidden !important;
    width: 48px !important;
    height: 48px !important;
    min-height: 48px !important;
    border-radius: 999px !important;
    border: none !important;
    background: linear-gradient(180deg, #1b8cff 0%, #0071e3 100%) !important;
    color: #ffffff !important;
    font-size: 24px !important;
    font-weight: 700 !important;
    padding: 0 0 3px 0 !important;
    margin: 0 !important;
    box-shadow: 0 10px 20px rgba(0,113,227,.28),
        0 4px 8px rgba(0,113,227,.16),
        inset 0 1px 0 rgba(255,255,255,.30) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transform: translateZ(0) !important;
    transition: transform .36s var(--apple-spring),
        filter .18s var(--apple-ease),
        opacity .18s var(--apple-ease),
        box-shadow .34s var(--apple-spring) !important;
    animation: appleOrbBreathe 3.2s ease-in-out infinite;
    --apple-btn-x: 35%;
    --apple-btn-y: 25%;
}

.gonder-butonu button::after,
button.gonder-butonu::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    opacity: .72;
    pointer-events: none;
    background: radial-gradient(circle at var(--apple-btn-x) var(--apple-btn-y), rgba(255,255,255,.48), rgba(255,255,255,.12) 28%, transparent 58%) !important;
}

.gonder-butonu button[data-apple-state="ready"],
button.gonder-butonu[data-apple-state="ready"] {
    color: #fff !important;
}

.gonder-butonu button[data-apple-state="thinking"],
button.gonder-butonu[data-apple-state="thinking"] {
    color: transparent !important;
    opacity: .88 !important;
    animation: appleThinkingGlow 1.45s ease-in-out infinite !important;
}

.gonder-butonu button[data-apple-state="thinking"]::after,
button.gonder-butonu[data-apple-state="thinking"]::after {
    content: "" !important;
    position: absolute !important;
    width: 16px !important;
    height: 16px !important;
    inset: 50% auto auto 50% !important;
    border: 2px solid rgba(255,255,255,.38) !important;
    border-top-color: #fff !important;
    border-radius: 999px !important;
    background: transparent !important;
    transform: translate(-50%,-50%) !important;
    animation: appleSpinner .72s linear infinite !important;
    opacity: 1 !important;
}

.gonder-butonu button[data-apple-state="streaming"],
button.gonder-butonu[data-apple-state="streaming"] {
    color: #fff !important;
    font-size: 15px !important;
    opacity: .96 !important;
    animation: appleStreamingPulse 1.25s ease-in-out infinite !important;
}

.gonder-butonu button[data-apple-state="streaming"]::after,
button.gonder-butonu[data-apple-state="streaming"]::after {
    content: "" !important;
    position: absolute !important;
    inset: 0 !important;
    width: auto !important;
    height: auto !important;
    border: 0 !important;
    border-radius: inherit !important;
    background: radial-gradient(circle at var(--apple-btn-x) var(--apple-btn-y), rgba(255,255,255,.34), transparent 54%) !important;
    transform: none !important;
    animation: none !important;
    opacity: .78 !important;
}

.gonder-butonu button:disabled:not([data-apple-state="thinking"]):not([data-apple-state="streaming"]),
button.gonder-butonu:disabled:not([data-apple-state="thinking"]):not([data-apple-state="streaming"]) {
    color: transparent !important;
}

.chatgpt-composer {
    position: relative !important;
    isolation: isolate !important;
    width: 90% !important;
    border-radius: 36px !important;
    box-sizing: border-box !important;
    animation: appleComposerIn .58s .12s var(--apple-ease) both;
    --apple-mx: 50%;
    --apple-my: 50%;
    flex: 0 0 auto !important;
    margin: 2px auto 0 auto !important;
}

html.apple-dark .chatgpt-composer {
    background: rgba(35,35,38,.78) !important;
    border-color: rgba(255,255,255,.085) !important;
    box-shadow: 0 18px 52px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.055) !important;
}

html.apple-dark .mesaj-kutusu textarea {
    color: #f5f5f7 !important;
}

.research-app.apple-mobile .chatgpt-composer > .form {
    display: contents !important;
}

.research-app.apple-mobile .mesaj-kutusu {
    grid-area: message;
    width: 100% !important;
}

.research-app.apple-mobile .composer-plus {
    grid-area: plus;
    width: 44px !important;
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    min-height: 44px !important;
}

.research-app.apple-mobile .gonder-butonu {
    grid-area: send;
    width: 44px !important;
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    min-height: 44px !important;
}

.research-app.apple-mobile .composer-plus button,
.research-app.apple-mobile .gonder-butonu button {
    width: 44px !important;
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    min-height: 44px !important;
}

.research-app.apple-mobile .chatgpt-composer > .form:has(.mesaj-kutusu) {
    display: block !important;
    grid-area: message !important;
    width: 100% !important;
    min-width: 0 !important;
}

.research-app.apple-mobile .chatgpt-composer .mesaj-kutusu {
    width: 100% !important;
    min-width: 0 !important;
}

.research-app.apple-mobile .mesaj-kutusu textarea {
    width: 100% !important;
    height: 60px !important;
    min-height: 44px !important;
    max-height: 60px !important;
    padding: 6px 2px !important;
    font-size: 16px !important;
    line-height: 24px !important;
    overflow-y: auto !important;
    box-sizing: border-box !important;
    position: relative !important;
    display: block !important;
    margin: 0 !important;
    text-align: left !important;
    transform: none !important;
}

.research-app.apple-mobile .apple-main-row .chatgpt-composer.chatgpt-composer {
    display: grid !important;
    align-items: center !important;
    flex: 0 0 auto !important;
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 6px !important;
    gap: 4px 6px !important;
    border-radius: 22px !important;
    box-sizing: border-box !important;
    animation: none !important;
    grid-template-columns: 44px minmax(0,1fr) minmax(0,1fr) 44px !important;
    grid-template-areas: "plus message message send" "model model detail detail" !important;
}

#apple-composer#apple-composer::before {
    content: '' !important;
    position: absolute !important;
    inset: -1px !important;
    border-radius: inherit !important;
    pointer-events: none !important;
    z-index: -1 !important;
    background: radial-gradient(ellipse at 74% 100%, rgba(31,139,255,.07), transparent 66%) !important;
    box-shadow: 0 0 0 0 transparent !important;
    opacity: 1 !important;
    transition: background 700ms ease, box-shadow 600ms ease !important;
}

body[data-apple-phase="thinking"] #apple-composer::before {
    box-shadow: 0 4px 22px rgba(63,113,181,.055) !important;
    background: radial-gradient(ellipse at 50% 100%,rgba(60,118,186,.055),transparent 70%) !important;
}

body[data-apple-phase="web"] #apple-composer::before {
    background: radial-gradient(ellipse at 72% 90%,rgba(82,169,184,.14),transparent 72%) !important;
    box-shadow: 0 7px 30px rgba(45,159,167,.1) !important;
}

body[data-apple-phase="thinking"] #apple-composer .mesaj-kutusu textarea {
    color: var(--intelligence-muted) !important;
}

#apple-composer .mesaj-kutusu textarea:focus {
    color: var(--intelligence-ink) !important;
}

#apple-composer button.gonder-butonu {
    color: transparent !important;
    font-size: 0 !important;
    animation: none !important;
    width: var(--composer-control-size) !important;
    min-width: var(--composer-control-size) !important;
    height: var(--composer-control-size) !important;
    padding: 0 !important;
    transition: background-color 300ms ease, transform 200ms var(--intelligence-spring) !important;
}

#apple-composer .gonder-butonu button::after,
#apple-composer .gonder-butonu button::before,
#apple-composer button.gonder-butonu::after,
#apple-composer button.gonder-butonu::before {
    content: none !important;
    animation: none !important;
}

#apple-stop#apple-stop {
    display: none !important;
    grid-area: send !important;
    align-self: center !important;
    justify-self: center !important;
    z-index: 3 !important;
    width: var(--composer-control-size) !important;
    min-width: 0 !important;
    height: var(--composer-control-size) !important;
    padding: 0 !important;
    border-radius: 50% !important;
    border: 0 !important;
    background: #1387f8 !important;
    color: transparent !important;
    font-size: 0 !important;
    box-shadow: 0 6px 18px rgba(10,132,255,.2) !important;
}

#apple-composer[data-busy="true"] #apple-stop#apple-stop {
    display: grid !important;
}

#apple-stop:hover {
    background: #0878e5 !important;
}

#apple-stop:focus-visible {
    outline: 3px solid #83bcff !important;
    outline-offset: 3px;
}

#apple-send-visual#apple-send-visual {
    grid-area: send !important;
    align-self: center !important;
    justify-self: center !important;
    width: 27px !important;
    min-width: 0 !important;
    height: 27px !important;
    padding: 0 !important;
    margin: 0 !important;
    background: none !important;
    border: 0 !important;
    z-index: 4 !important;
    pointer-events: none !important;
    overflow: visible !important;
}

#apple-send-visual .html-container,
#apple-send-visual .prose {
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
    height: 100% !important;
}

#apple-composer .composer-plus button,
#apple-composer button.composer-plus {
    font-size: 0 !important;
}

#apple-composer .composer-plus button::before,
#apple-composer button.composer-plus::before {
    content: '+' !important;
    position: static !important;
    font: 300 28px/1 sans-serif !important;
    color: var(--intelligence-ink) !important;
    background: none !important;
    width: auto !important;
    height: auto !important;
    transform: none !important;
}

#apple-send-shape {
    display: block;
    width: 100%;
    height: 100%;
    fill: none;
    stroke: #fff;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
}

#apple-send-shape[data-shape="thinking"] {
    animation: intelligenceSpin 1.8s linear infinite;
}

#apple-composer-attachment {
    display: flex;
    align-items: center;
    gap: 10px;
    width: fit-content;
    max-width: 100%;
    box-sizing: border-box;
    padding: 8px 13px;
    border: 1px solid var(--material-line);
    border-radius: 15px;
    background: var(--material-float);
    color: var(--intelligence-ink);
}

#apple-composer-attachment > div {
    min-width: 0;
}

#apple-composer-attachment strong {
    display: block;
    max-width: 420px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
    font-weight: 550;
}

#apple-composer-attachment small {
    display: block;
    margin-top: 2px;
    color: var(--intelligence-muted);
    font-size: 11px;
}

#apple-composer[data-document-pending="true"] .gonder-butonu {
    opacity: .55 !important;
    cursor: wait !important;
}

#apple-composer .gonder-butonu {
    grid-area: send !important;
    transform: none !important;
    transition: filter 100ms ease, box-shadow 100ms ease !important;
}

#apple-composer .gonder-butonu:hover,
#apple-composer .gonder-butonu:active {
    transform: none !important;
    transition: filter 100ms ease, box-shadow 100ms ease !important;
}

#apple-composer .gonder-butonu button {
    color: transparent !important;
    font-size: 0 !important;
    animation: none !important;
    width: var(--composer-control-size) !important;
    min-width: var(--composer-control-size) !important;
    height: var(--composer-control-size) !important;
    padding: 0 !important;
    transform: none !important;
    transition: filter 100ms ease, box-shadow 100ms ease !important;
}

#apple-composer .gonder-butonu button:hover,
#apple-composer .gonder-butonu button:active {
    transform: none !important;
    transition: filter 100ms ease, box-shadow 100ms ease !important;
}

#apple-composer#apple-composer {
    display: grid !important;
    align-items: center !important;
    gap: 5px 8px !important;
    padding: 8px !important;
    min-height: 0 !important;
    grid-template-columns: 44px minmax(0,1fr) auto 48px !important;
    background: var(--material-float) !important;
    backdrop-filter: var(--material-float-filter) !important;
    -webkit-backdrop-filter: var(--material-float-filter) !important;
    box-shadow: var(--material-float-shadow) !important;
    border: 1px solid var(--material-line) !important;
    --composer-control-size: 52px;
    height: auto !important;
    transition: background-color 180ms ease, box-shadow 180ms ease !important;
}

#apple-composer .composer-plus {
    grid-area: plus !important;
    transition: opacity 160ms ease, background-color 160ms ease !important;
}

#apple-composer[data-composing="true"] .composer-plus {
    opacity: .56;
}

#apple-composer .composer-plus:is(:hover,:focus-within) {
    opacity: 1;
}

#apple-composer .ai-composer-state {
    position: absolute;
    bottom: 4px;
    left: 50%;
    display: flex;
    align-items: center;
    gap: 5px;
    max-width: calc(100% - 120px);
    transform: translate(-50%,2px);
    opacity: 0;
    color: var(--intelligence-muted);
    font: 450 10px/1.25 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    white-space: nowrap;
    pointer-events: none;
    transition: opacity 160ms ease,transform 160ms ease;
}

#apple-composer .ai-composer-state[data-visible="true"] {
    opacity: 1;
    transform: translate(-50%,0);
}

#apple-composer .ai-composer-state[data-visible="true"]::before {
    content: '';
    flex: 0 0 4px;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: currentColor;
    animation: aiComposerBreathe 1.8s ease-in-out infinite;
}

#apple-composer[data-phase="error"] .ai-composer-state::before {
    animation: none;
}

#apple-attachment-slot#apple-attachment-slot {
    grid-area: attachment !important;
    border: 0 !important;
    background: none !important;
    padding: 0 !important;
    min-width: 0 !important;
    display: grid !important;
    min-height: 0 !important;
    margin: 0 !important;
    grid-template-rows: 0fr;
    opacity: 0;
    visibility: hidden;
    padding-bottom: 0 !important;
    transition: grid-template-rows 220ms var(--intelligence-spring), padding-bottom 220ms var(--intelligence-spring),opacity 140ms ease,visibility 0s 220ms;
}

#apple-attachment-slot > * {
    min-height: 0 !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
}

#apple-composer .mesaj-kutusu textarea {
    color: var(--intelligence-ink) !important;
    box-sizing: border-box !important;
}

#apple-composer[data-has-file="true"] #apple-attachment-slot#apple-attachment-slot {
    display: grid !important;
    min-height: 0 !important;
    margin: 0 !important;
    grid-template-rows: 1fr;
    opacity: 1;
    visibility: visible;
    padding-bottom: 8px !important;
    transition-delay: 0s;
}

#apple-composer#apple-composer#apple-composer {
    grid-template-areas: "attachment attachment attachment attachment" "plus message settings send" !important;
    row-gap: 0 !important;
    padding-bottom: 15px !important;
}

#apple-composer > .form:has(.mesaj-kutusu) {
    display: block !important;
    grid-area: message !important;
    width: 100% !important;
    min-width: 0 !important;
    padding: 0 !important;
}

#apple-composer .composer-plus:is(:hover,:active),
#apple-composer .composer-plus button:is(:hover,:active) {
    transform: none !important;
}

#apple-composer-attachment[role="button"] {
    cursor: pointer;
}

#apple-composer-attachment:focus-visible {
    outline: 2px solid #3989f9;
    outline-offset: 3px;
}

#apple-photo-upload,
#apple-photo-state,
#apple-photo-clear,
.form:has(> #apple-photo-state) {
    display: none !important;
}

#apple-attachment-menu {
    position: fixed;
    inset: auto;
    margin: 0;
    z-index: 10040;
    width: 224px;
    box-sizing: border-box;
    padding: 7px;
    border: 1px solid var(--material-line,#e5e5e8);
    border-radius: 20px;
    background: var(--material-float,rgba(255,255,255,.96));
    color: var(--intelligence-ink,#202126);
    box-shadow: 0 12px 40px rgba(0,0,0,.12);
    backdrop-filter: blur(24px);
    transform-origin: bottom left;
}

#apple-attachment-menu[hidden] {
    display: none !important;
}

#apple-attachment-menu button {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 10px;
    border: 0;
    border-radius: 13px;
    background: transparent;
    color: inherit;
    text-align: left;
    font: inherit;
    font-size: 14px;
    cursor: pointer;
    transition: background 120ms,transform 120ms;
}

#apple-attachment-menu button:is(:hover,:focus-visible) {
    background: rgba(128,128,140,.1);
    outline: none;
}

#apple-attachment-menu button:active {
    transform: scale(.97);
}

#apple-attachment-menu button span {
    font-size: 21px;
    width: 24px;
    text-align: center;
}

#apple-photo-preview {
    display: flex;
    align-items: center;
    gap: 11px;
    width: fit-content;
    max-width: 100%;
    box-sizing: border-box;
    padding: 7px 10px 7px 7px;
    margin-top: 5px;
    border: 1px solid var(--material-line,#e5e5e8);
    border-radius: 18px;
    background: var(--material-float,#fff);
    color: var(--intelligence-ink,#202126);
}

#apple-photo-preview[hidden],
#apple-composer-attachment[hidden] {
    display: none !important;
}

#apple-photo-preview img {
    width: 54px;
    height: 54px;
    flex: none;
    object-fit: cover;
    border-radius: 12px;
}

#apple-photo-preview > div {
    min-width: 0;
}

#apple-photo-preview strong {
    display: block;
    max-width: min(340px,calc(100vw - 190px));
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
    font-weight: 550;
}

#apple-photo-preview small {
    display: block;
    font-size: 11px;
    line-height: 1.4;
    margin-top: 4px;
    color: var(--intelligence-muted,#777);
}

#apple-photo-preview[data-error=true] small {
    color: #c34848;
}

#apple-photo-preview button {
    display: grid;
    place-items: center;
    flex: none;
    width: 32px;
    height: 32px;
    margin: 0;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: rgba(128,128,140,.1);
    color: inherit;
    font-size: 20px;
    cursor: pointer;
    transition: transform 120ms;
}

#apple-photo-preview button:active {
    transform: scale(.94);
}

#apple-photo-preview button:disabled {
    opacity: .35;
    cursor: wait;
}

#apple-photo-preview button:focus-visible {
    outline: 2px solid #3989f9;
    outline-offset: 2px;
}

/* Model ve ayarlar */

.apple-command-overlay {
    position: fixed;
    inset: 0;
    z-index: 10000;
    display: none;
    align-items: flex-start;
    justify-content: center;
    padding-top: min(18vh, 150px);
    background: rgba(15,23,42,.16);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}

.apple-command-overlay.open {
    display: flex;
    animation: appleOverlayIn .16s ease-out both;
}

.apple-command-palette {
    width: min(92vw, 480px);
    padding: 8px;
    border: 1px solid rgba(255,255,255,.72);
    border-radius: 22px;
    background: rgba(250,250,252,.93);
    box-shadow: 0 28px 90px rgba(15,23,42,.24), inset 0 1px 0 rgba(255,255,255,.96);
    backdrop-filter: blur(30px) saturate(170%);
    -webkit-backdrop-filter: blur(30px) saturate(170%);
    animation: applePaletteIn .24s var(--apple-spring) both;
}

.apple-command-head {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 9px 10px 11px;
    color: #8e8e93;
    font-size: 11px;
    border-bottom: 1px solid rgba(118,118,128,.10);
}

.apple-command-list {
    display: grid;
    gap: 3px;
    padding-top: 6px;
}

.apple-command-item {
    display: grid;
    grid-template-columns: 28px minmax(0,1fr) auto;
    align-items: center;
    gap: 8px;
    min-height: 42px;
    padding: 5px 8px;
    border: 0;
    border-radius: 14px;
    background: transparent;
    color: #343437;
    text-align: left;
    font-family: inherit;
    cursor: pointer;
}

.apple-command-item:hover {
    background: rgba(0,113,227,.085);
}

.apple-command-icon {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    border-radius: 9px;
    background: rgba(118,118,128,.075);
    font-size: 12px;
}

.apple-command-label {
    font-size: 12px;
    font-weight: 650;
}

.apple-command-hint {
    color: #a0a0a5;
    font-size: 9px;
}

html.apple-dark .apple-command-label {
    color: #f5f5f7 !important;
}

html.apple-dark .apple-command-palette {
    background: rgba(38,38,41,.96) !important;
    border-color: rgba(255,255,255,.09) !important;
    color: #f5f5f7 !important;
}

#apple-model-controls#apple-model-controls,
#apple-detail-controls#apple-detail-controls {
    display: none !important;
}

#apple-reasoning-widget .apple-reasoning-card {
    padding: 8px 13px 12px !important;
    border: 1px solid rgba(20,20,25,.09) !important;
    border-radius: 26px !important;
    background: rgba(255,255,255,.96) !important;
    box-shadow: 0 3px 15px rgba(0,0,0,.045) !important;
    box-sizing: border-box !important;
    font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important;
}

#apple-reasoning-widget .apple-reasoning-head {
    display: grid !important;
    grid-template-columns: 32px minmax(0,1fr) 32px !important;
    align-items: center !important;
    gap: 4px !important;
    margin-bottom: 7px !important;
}

#apple-reasoning-widget .apple-reasoning-bolt {
    display: grid !important;
    place-items: center !important;
    width: 32px !important;
    height: 40px !important;
    border: 0 !important;
    background: transparent !important;
    color: #929296 !important;
    padding: 7px !important;
    box-sizing: border-box !important;
}

#apple-reasoning-reset {
    display: grid !important;
    place-items: center !important;
    width: 32px !important;
    height: 40px !important;
    border: 0 !important;
    background: transparent !important;
    color: #929296 !important;
    padding: 7px !important;
    box-sizing: border-box !important;
    cursor: pointer !important;
    border-radius: 12px !important;
}

#apple-reasoning-widget svg {
    width: 18px !important;
    height: 18px !important;
}

#apple-model-trigger {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 2px !important;
    min-height: 47px !important;
    width: 100% !important;
    padding: 4px 8px !important;
    border: 0 !important;
    border-radius: 14px !important;
    background: #f5f5f5 !important;
    cursor: pointer !important;
    font-family: inherit !important;
}

#apple-reasoning-widget .apple-reasoning-title {
    display: flex !important;
    gap: 5px !important;
    align-items: center !important;
}

#apple-reasoning-label {
    font-size: 16px !important;
    font-weight: 650 !important;
    color: #0088ff !important;
    line-height: 20px !important;
    white-space: nowrap !important;
}

#apple-reasoning-widget .apple-reasoning-chevron {
    font-size: 20px !important;
    line-height: 20px !important;
    color: #999 !important;
}

#apple-reasoning-model {
    font-size: 12px !important;
    font-weight: 400 !important;
    line-height: 16px !important;
    color: #777 !important;
    white-space: nowrap !important;
}

#apple-reasoning-widget .apple-reasoning-rail {
    position: relative !important;
    height: 30px !important;
}

#apple-reasoning-range {
    --apple-slider-fill: 0%;
    -webkit-appearance: none !important;
    appearance: none !important;
    position: relative !important;
    z-index: 2 !important;
    display: block !important;
    width: 100% !important;
    height: 30px !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    cursor: pointer !important;
    touch-action: pan-y !important;
}

#apple-reasoning-range::-webkit-slider-runnable-track {
    height: 26px;
    border-radius: 99px;
    border: 1px solid #e4e4e7;
    background: linear-gradient(to right,#0088ff var(--apple-slider-fill),#f2f2f3 var(--apple-slider-fill));
    box-shadow: inset 0 1px 2px rgba(0,0,0,.04);
}

#apple-reasoning-range::-moz-range-track {
    height: 26px;
    border-radius: 99px;
    border: 1px solid #e4e4e7;
    background: linear-gradient(to right,#0088ff var(--apple-slider-fill),#f2f2f3 var(--apple-slider-fill));
}

#apple-reasoning-widget .apple-reasoning-stops {
    position: absolute !important;
    inset: 0 14px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    pointer-events: none !important;
    z-index: 3 !important;
}

#apple-reasoning-widget .apple-reasoning-stops i {
    display: block !important;
    width: 5px !important;
    height: 5px !important;
    border-radius: 50% !important;
    background: rgba(150,150,156,.55) !important;
}

#apple-reasoning-widget .apple-reasoning-stops i.apple-stop-active {
    visibility: hidden !important;
}

#apple-model-trigger:focus-visible,
#apple-reasoning-reset:focus-visible,
#apple-reasoning-range:focus-visible {
    outline: 2px solid #0088ff !important;
    outline-offset: 3px !important;
}

html.apple-dark #apple-reasoning-widget .apple-reasoning-card {
    background: #29292c !important;
    border-color: #414145 !important;
}

html.apple-dark #apple-model-trigger {
    background: #353539 !important;
}

html.apple-dark #apple-reasoning-model {
    color: #b8b8bf !important;
}

#apple-reasoning-widget#apple-reasoning-widget {
    grid-area: settings !important;
    min-width: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    overflow: visible !important;
    width: auto !important;
    max-width: 286px !important;
    justify-self: end !important;
}

#apple-summary-model {
    color: #222 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    line-height: 20px !important;
}

#apple-summary-detail {
    color: #929296 !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    line-height: 20px !important;
}

#apple-settings-trigger .apple-summary-arrow {
    flex: 0 0 13px !important;
    width: 13px !important;
    height: 13px !important;
    color: #929296 !important;
}

#apple-settings-trigger:hover,
#apple-settings-trigger[aria-expanded="true"] {
    background: rgba(118,118,128,.07) !important;
}

#apple-settings-trigger:focus-visible {
    outline: 2px solid #0088ff !important;
    outline-offset: 2px !important;
}

#apple-settings-popover {
    position: fixed !important;
    inset: auto;
    margin: 0 !important;
    max-width: calc(100vw - 20px) !important;
    max-height: calc(100dvh - 20px) !important;
    overflow: auto !important;
    z-index: 2147482999 !important;
}

#apple-settings-popover[hidden] {
    display: none !important;
}

#apple-settings-popover::backdrop,
#apple-model-popover::backdrop {
    background: transparent;
    pointer-events: none;
}

html.apple-dark #apple-summary-model {
    color: #efeff2 !important;
}

html.apple-dark #apple-summary-detail {
    color: #aaaab0 !important;
}

#apple-global-settings-button#apple-global-settings-button {
    display: inline-grid !important;
    width: auto !important;
    min-width: 64px !important;
    padding: 0 10px !important;
    font-size: 12px !important;
    font-weight: 600;
    flex: 0 0 auto;
}

#apple-settings-menu {
    position: fixed;
    inset: 0;
    width: 100%;
    height: 100dvh;
    max-width: none;
    max-height: none;
    margin: 0;
    border: 0;
    box-sizing: border-box;
    padding: 20px 12px;
    overflow: auto;
    z-index: 2147483001;
}

#apple-settings-menu::backdrop {
    background: transparent;
}

#apple-settings-menu .apple-command-head {
    font-size: 14px;
    font-weight: 600;
}

#apple-settings-menu .apple-settings-close {
    margin-left: auto;
    width: 36px;
    height: 36px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
}

#apple-settings-menu .apple-mode-section {
    padding: 14px 8px 10px;
    border-bottom: 1px solid rgba(118,118,128,.10);
}

#apple-settings-menu .apple-mode-label {
    margin-bottom: 8px;
    font-size: 12px;
    font-weight: 600;
    color: #6e6e73;
}

#apple-settings-menu .apple-mode-options {
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: 14px;
    background: rgba(118,118,128,.10);
}

#apple-settings-menu [data-ui-mode] {
    flex: 1;
    min-width: 0;
    min-height: 44px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: #6e6e73;
    font: inherit;
    font-size: 13px;
    cursor: pointer;
}

#apple-settings-menu [data-ui-mode][aria-pressed="true"] {
    background: #fff;
    color: #0071e3;
    box-shadow: 0 2px 6px rgba(0,0,0,.08);
    font-weight: 600;
}

#apple-settings-menu .apple-mode-description {
    margin: 8px 0 0;
    font-size: 11px;
    color: #6e6e73;
    line-height: 1.5;
}

#apple-settings-menu button:focus-visible {
    outline: 2px solid #007aff;
    outline-offset: 2px;
}

html.apple-dark #apple-settings-menu .apple-mode-label,
html.apple-dark #apple-settings-menu .apple-mode-description,
html.apple-dark #apple-settings-menu [data-ui-mode] {
    color: #c5c5ca;
}

html.apple-dark #apple-settings-menu [data-ui-mode][aria-pressed="true"] {
    background: #3a3a3c;
    color: #8dcbff;
}

#apple-settings-menu .apple-command-palette {
    max-height: calc(100dvh - 40px);
    overflow-y: auto;
    box-sizing: border-box;
    background: var(--material-panel) !important;
    backdrop-filter: var(--material-panel-filter) !important;
    -webkit-backdrop-filter: var(--material-panel-filter) !important;
    box-shadow: var(--material-panel-shadow) !important;
    border: 1px solid var(--material-line) !important;
    color: var(--intelligence-ink);
}

#apple-settings-popover#apple-settings-popover,
#apple-model-popover#apple-model-popover {
    background: var(--material-panel) !important;
    backdrop-filter: var(--material-panel-filter) !important;
    -webkit-backdrop-filter: var(--material-panel-filter) !important;
    box-shadow: var(--material-panel-shadow) !important;
    border: 1px solid var(--material-line) !important;
    color: var(--intelligence-ink);
}

#apple-reasoning-range::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 32px;
    height: 32px;
    margin-top: -4px;
    border: 1px solid #ddd;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,.12);
    transform: scale(var(--ai-thumb-scale,1));
}

#apple-reasoning-range::-moz-range-thumb {
    width: 30px;
    height: 30px;
    border: 1px solid #ddd;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,.12);
    transform: scale(var(--ai-thumb-scale,1));
}

#apple-settings-trigger {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 5px !important;
    width: 100% !important;
    min-height: 44px !important;
    padding: 6px 8px !important;
    margin: 0 !important;
    border: 0 !important;
    border-radius: 12px !important;
    background: transparent !important;
    box-shadow: none !important;
    font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    box-sizing: border-box !important;
    transition: opacity 160ms ease, background-color 160ms ease !important;
    opacity: .8;
}

#apple-composer[data-composing="true"] #apple-settings-trigger {
    opacity: .56;
}

#apple-composer[data-composing="true"] #apple-summary-detail {
    opacity: .7;
}

#apple-composer #apple-settings-trigger:is(:hover,:focus-visible,[aria-expanded="true"]) {
    opacity: 1;
}

#apple-reasoning-widget > .html-container {
    padding: 0 !important;
}

/* Inspector ve telemetri */

.apple-upload {
    position: relative !important;
}

.apple-upload > .block,
.apple-status > .block,
.apple-developer-box > .block,
.apple-status .wrap,
.apple-developer-box .wrap {
    border-radius: 24px !important;
    border: 1px solid rgba(255, 255, 255, .72) !important;
    background: rgba(255,255,255,.58) !important;
    backdrop-filter: blur(20px) saturate(155%) !important;
    -webkit-backdrop-filter: blur(20px) saturate(155%) !important;
    box-shadow: 0 16px 46px rgba(15, 23, 42, .07),
        inset 0 1px 0 rgba(255,255,255,.78) !important;
}

.apple-upload .wrap,
.apple-upload .block,
.apple-upload .container {
    background: transparent !important;
}

.apple-upload [data-testid="file-upload"],
.apple-upload .upload-container {
    width: 100% !important;
    min-height: 170px !important;
    height: 170px !important;
    border-radius: 26px !important;
    border: 1.5px dashed rgba(0,113,227,.18) !important;
    background: linear-gradient(180deg, rgba(255,255,255,.88) 0%, rgba(248,250,252,.78) 100%) !important;
    box-shadow: 0 16px 40px rgba(15,23,42,.07),
        inset 0 1px 0 rgba(255,255,255,.86) !important;
    backdrop-filter: blur(22px) saturate(155%) !important;
    -webkit-backdrop-filter: blur(22px) saturate(155%) !important;
    transition: transform .38s var(--apple-spring),
        border-color .24s var(--apple-ease),
        box-shadow .34s var(--apple-spring),
        background .24s var(--apple-ease) !important;
    overflow: hidden !important;
}

.apple-upload button[aria-dropeffect="copy"]:hover,
.apple-upload [data-testid="file-upload"]:hover,
.apple-upload .upload-container:hover {
    transform: translateY(-3px) !important;
    border-color: rgba(0,113,227,.32) !important;
    box-shadow: 0 24px 48px rgba(15,23,42,.10),
        inset 0 1px 0 rgba(255,255,255,.92) !important;
    background: linear-gradient(180deg, rgba(255,255,255,.95) 0%, rgba(247,250,255,.90) 100%) !important;
}

.apple-upload button[aria-dropeffect="copy"] .wrap,
.apple-upload .upload-container .wrap {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 10px !important;
    padding: 22px 16px !important;
    height: 100% !important;
    text-align: center !important;
    position: relative !important;
    font-size: 0 !important;
    line-height: 0 !important;
    color: transparent !important;
}

.apple-upload button[aria-dropeffect="copy"] {
    width: 100% !important;
    min-height: 170px !important;
    height: 170px !important;
    border-radius: 26px !important;
    border: 1.5px dashed rgba(0,113,227,.18) !important;
    background: linear-gradient(180deg, rgba(255,255,255,.88) 0%, rgba(248,250,252,.78) 100%) !important;
    box-shadow: 0 16px 40px rgba(15,23,42,.07),
        inset 0 1px 0 rgba(255,255,255,.86) !important;
    backdrop-filter: blur(22px) saturate(155%) !important;
    -webkit-backdrop-filter: blur(22px) saturate(155%) !important;
    transition: transform .38s var(--apple-spring),
        border-color .24s var(--apple-ease),
        box-shadow .34s var(--apple-spring),
        background .24s var(--apple-ease) !important;
    overflow: hidden !important;
    font-size: 0 !important;
    line-height: 0 !important;
}

.apple-upload button[aria-dropeffect="copy"] .wrap::after,
.apple-upload .upload-container .wrap::after {
    content: "Dosyayı buraya sürükle";
    display: block !important;
    font-size: 14px !important;
    line-height: 1.35 !important;
    color: var(--apple-secondary) !important;
    font-weight: 500 !important;
    letter-spacing: -0.01em !important;
    white-space: nowrap !important;
}

.apple-upload button[aria-dropeffect="copy"] .icon-wrap,
.apple-upload .upload-container .icon-wrap {
    width: 74px !important;
    height: 74px !important;
    min-width: 74px !important;
    border-radius: 24px !important;
    background: linear-gradient(180deg, rgba(0,113,227,.10) 0%, rgba(0,113,227,.06) 100%) !important;
    color: var(--apple-blue) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 10px 24px rgba(0,113,227,.10),
        inset 0 1px 0 rgba(255,255,255,.9) !important;
    animation: appleFloatTiny 3.2s ease-in-out infinite;
}

.apple-upload button[aria-dropeffect="copy"] .icon-wrap svg,
.apple-upload .upload-container .icon-wrap svg {
    width: 30px !important;
    height: 30px !important;
}

.apple-upload button[aria-dropeffect="copy"] h2,
.apple-upload .upload-container h2 {
    display: none !important;
    margin: 4px 0 0 0 !important;
    font-size: 24px !important;
    line-height: 1.12 !important;
    color: var(--apple-text) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

.apple-upload button[aria-dropeffect="copy"] p,
.apple-upload .upload-container p {
    display: none !important;
    margin: 0 !important;
    font-size: 14px !important;
    line-height: 1.45 !important;
    color: var(--apple-tertiary) !important;
}

.apple-upload button[aria-dropeffect="copy"] .or,
.apple-upload .upload-container .or {
    display: none !important;
    margin: 0 !important;
    font-size: 14px !important;
    line-height: 1.45 !important;
    color: var(--apple-tertiary) !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
}

.apple-status textarea,
.apple-status input,
.apple-developer-box textarea,
.apple-developer-box input {
    border-radius: 18px !important;
    border: 1px solid rgba(15,23,42,.08) !important;
    background: rgba(255,255,255,.54) !important;
    color: var(--apple-text) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.70) !important;
}

.apple-status textarea:focus,
.apple-developer-box textarea:focus,
.apple-developer-box input:focus {
    border-color: rgba(0,113,227,.28) !important;
    box-shadow: 0 0 0 4px rgba(0,113,227,.06),
        inset 0 1px 0 rgba(255,255,255,.78) !important;
}

.apple-developer-box button {
    border-radius: 14px !important;
}

.apple-inspector::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    pointer-events: none;
    background: linear-gradient(135deg, rgba(255,255,255,.42), transparent 34%, rgba(10,132,255,.025));
}

.apple-inspector > * {
    position: relative;
    z-index: 1;
}

.apple-switch {
    min-width: 0 !important;
    padding: 9px 10px !important;
    border-radius: 18px !important;
    background: rgba(255,255,255,.48) !important;
    border: 1px solid rgba(15,23,42,.055) !important;
}

.apple-switch .checkbox-container {
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    cursor: pointer !important;
}

.apple-switch input[type="checkbox"] {
    appearance: none !important;
    -webkit-appearance: none !important;
    position: relative !important;
    width: 42px !important;
    min-width: 42px !important;
    height: 24px !important;
    margin: 0 !important;
    border: none !important;
    border-radius: 999px !important;
    background: #d1d1d6 !important;
    box-shadow: inset 0 0 0 1px rgba(15,23,42,.04) !important;
    cursor: pointer !important;
    transition: background .22s var(--apple-ease), box-shadow .22s var(--apple-ease) !important;
}

.apple-switch input[type="checkbox"]:checked {
    background: #34c759 !important;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,.02), 0 0 0 3px rgba(52,199,89,.08) !important;
}

.apple-switch input[type="checkbox"]:checked::after {
    transform: translateX(18px) !important;
}

.apple-switch .checkbox-container.disabled input[type="checkbox"],
.apple-switch input[type="checkbox"]:disabled {
    opacity: .45 !important;
    cursor: default !important;
}

.apple-switch .label-text {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--apple-text) !important;
    letter-spacing: -.01em !important;
}

.apple-switch .info {
    margin-top: 4px !important;
    font-size: 11px !important;
    color: var(--apple-tertiary) !important;
}

.apple-processing-status > div:not(.apple-status-shimmer) {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 1px;
}

.apple-status-shimmer {
    grid-column: 1 / -1;
    display: grid;
    gap: 5px;
    width: 100%;
}

.apple-status-shimmer i {
    display: block;
    height: 5px;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(118,118,128,.08) 0%, rgba(118,118,128,.16) 46%, rgba(118,118,128,.08) 100%);
    background-size: 220% 100%;
    animation: appleShimmerLine 1.25s linear infinite;
}

.apple-status-shimmer i:nth-child(2) {
    width: 78%;
    animation-delay: .08s;
}

.apple-status-shimmer i:nth-child(3) {
    width: 58%;
    animation-delay: .16s;
}

.apple-token-card {
    position: relative !important;
    overflow: hidden !important;
    display: grid !important;
    grid-template-columns: minmax(150px, .9fr) minmax(190px, 1.35fr) !important;
    gap: 16px !important;
    padding: 16px 17px !important;
    margin: 0 0 8px 0 !important;
    border: 1px solid rgba(15,23,42,.075) !important;
    border-radius: 22px !important;
    background: linear-gradient(145deg, rgba(255,255,255,.90), rgba(248,249,251,.74)) !important;
    box-shadow: 0 8px 24px rgba(15,23,42,.055), inset 0 1px 0 rgba(255,255,255,.90) !important;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif !important;
    transition: transform .28s var(--apple-spring), box-shadow .28s var(--apple-spring), border-color .22s ease, background .22s ease !important;
}

.apple-token-card::after {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: .55;
    background: radial-gradient(circle at 12% 5%, rgba(10,132,255,.09), transparent 34%);
}

.apple-token-card:hover {
    transform: translateY(-2px) !important;
    border-color: rgba(0,113,227,.13) !important;
    box-shadow: 0 13px 32px rgba(15,23,42,.085), inset 0 1px 0 rgba(255,255,255,.94) !important;
}

.apple-token-main {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
}

.apple-token-eyebrow {
    color: #86868b;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .08em;
}

.apple-token-value {
    margin-top: 2px;
    color: #1d1d1f;
    font-size: clamp(26px, 2.6vw, 38px);
    line-height: 1;
    font-weight: 760;
    letter-spacing: -.045em;
}

.apple-token-subtitle {
    margin-top: 6px;
    color: #8e8e93;
    font-size: 11px;
    line-height: 1.3;
}

.apple-token-secondary {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;
    align-content: center;
}

.apple-token-secondary-detailed {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.apple-token-stat {
    min-width: 0;
    padding: 9px 10px;
    border-radius: 14px;
    background: rgba(118,118,128,.055);
    border: 1px solid rgba(118,118,128,.055);
}

.apple-token-stat span {
    display: block;
    color: #8e8e93;
    font-size: 9px;
    font-weight: 650;
    letter-spacing: .015em;
}

.apple-token-stat strong {
    display: block;
    margin-top: 2px;
    color: #343437;
    font-size: 13px;
    line-height: 1.2;
    font-weight: 700;
    overflow: visible;
    white-space: normal;
    overflow-wrap: anywhere;
}

.apple-token-cost strong {
    color: #248a3d !important;
}

.apple-token-card-detailed {
    grid-template-columns: minmax(145px, .8fr) minmax(210px, 1.45fr) !important;
}

.apple-token-footer {
    position: relative;
    z-index: 1;
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: -5px;
    padding-top: 9px;
    border-top: 1px solid rgba(118,118,128,.10);
    color: #8e8e93;
    font-size: 10px;
}

.apple-token-footer strong {
    color: #3a3a3c;
}

.apple-token-cost-inline {
    color: #248a3d !important;
    font-size: 12px;
    font-weight: 750;
}

.apple-status,
.apple-developer-box {
    position: relative !important;
    transition: transform .28s var(--apple-spring), box-shadow .28s var(--apple-spring), border-color .22s ease !important;
}

.apple-status:hover,
.apple-developer-box:hover {
    transform: translateY(-1px) !important;
}

.apple-upload.apple-has-file,
.apple-upload.apple-has-file > .block,
.apple-upload.apple-has-file .wrap,
.apple-upload.apple-has-file .container {
    min-height: 0 !important;
    height: auto !important;
}

.apple-upload.apple-has-file .file-preview-holder,
.apple-upload.apple-has-file .file-preview,
.apple-upload.apple-has-file button[aria-dropeffect="copy"] {
    display: none !important;
}

.apple-inspector {
    position: relative !important;
    padding: 14px !important;
    border: 1px solid rgba(255,255,255,.78) !important;
    border-radius: 30px !important;
    background: rgba(248,249,252,.66) !important;
    box-shadow: 0 24px 70px rgba(15,23,42,.08),
        inset 0 1px 0 rgba(255,255,255,.92) !important;
    backdrop-filter: blur(28px) saturate(165%) !important;
    -webkit-backdrop-filter: blur(28px) saturate(165%) !important;
    overflow: visible !important;
    min-height: 0 !important;
    height: 100% !important;
    max-height: 100% !important;
    box-sizing: border-box !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding-right: 4px !important;
    overscroll-behavior: contain;
    transition: none !important;
}

.research-app.apple-inspector-collapsed .apple-inspector {
    flex: 0 0 0 !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    opacity: 0 !important;
    transform: translateX(18px) scale(.98) !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    overflow: hidden !important;
    pointer-events: none !important;
    border-width: 0 !important;
}

.research-app.apple-inspector-collapsed .apple-chat-column {
    flex: 1 1 100% !important;
    max-width: 100% !important;
}

html.apple-dark .apple-inspector,
html.apple-dark .apple-token-card {
    background: rgba(35,35,38,.78) !important;
    border-color: rgba(255,255,255,.085) !important;
    box-shadow: 0 18px 52px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.055) !important;
}

html.apple-dark .apple-token-value {
    color: #f5f5f7 !important;
}

html.apple-dark .apple-switch,
html.apple-dark .apple-token-stat {
    background: rgba(118,118,128,.18) !important;
    color: #d1d1d6 !important;
}

html.apple-dark .apple-status textarea,
html.apple-dark .apple-developer-box textarea,
html.apple-dark .apple-developer-box input {
    background: rgba(28,28,30,.68) !important;
    color: #f5f5f7 !important;
    border-color: rgba(255,255,255,.07) !important;
}

.research-app.apple-mobile .apple-inspector {
    display: none !important;
}

.research-app.apple-mobile.apple-mobile-inspector-open .apple-inspector {
    display: flex !important;
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: 100% !important;
    padding: 14px !important;
    opacity: 1 !important;
    transform: none !important;
    pointer-events: auto !important;
    background: var(--apple-bg) !important;
    z-index: 80 !important;
    overflow-y: auto !important;
}

#apple-user-home:not(.apple-developer-mode) #apple-developer-panel {
    display: none !important;
}

#apple-user-home.apple-developer-mode #apple-inspector-panel {
    display: flex !important;
    flex-direction: column !important;
    flex-wrap: nowrap !important;
    align-items: stretch !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    min-height: 0 !important;
}

#apple-user-home.apple-developer-mode #apple-inspector-panel > * {
    flex: 0 0 auto !important;
    min-width: 0 !important;
    max-width: 100% !important;
}

#apple-developer-panel#apple-developer-panel {
    flex: 0 0 auto !important;
    flex-direction: column !important;
    flex-wrap: nowrap !important;
    align-items: stretch !important;
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    box-sizing: border-box !important;
}

#apple-developer-panel > * {
    flex: 0 0 auto !important;
    min-width: 0 !important;
    max-width: 100% !important;
}

#apple-inspector-panel .apple-developer-heading {
    margin: 0;
    padding: 10px 12px;
    border-radius: 14px;
    background: rgba(0,113,227,.08);
    color: #0071e3;
    font-size: 14px;
    font-weight: 650;
}

html.apple-dark #apple-inspector-panel .apple-developer-heading {
    color: #8dcbff;
    background: rgba(10,132,255,.14);
}

#apple-user-home:not(.apple-developer-mode) #apple-developer-title {
    display: none !important;
}

#apple-user-home.apple-developer-mode #apple-data-controls#apple-data-controls {
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
    grid-template-areas: "pdf-heading update-heading" "pdf-upload update-status";
    grid-template-rows: auto 170px;
    align-items: stretch !important;
    gap: 10px 12px !important;
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    padding: 0 !important;
    box-sizing: border-box !important;
}

#apple-user-home.apple-developer-mode #apple-data-controls > .form {
    display: contents !important;
}

#apple-user-home.apple-developer-mode #apple-pdf-heading {
    grid-area: pdf-heading;
}

#apple-user-home.apple-developer-mode #apple-update-heading {
    grid-area: update-heading;
}

#apple-user-home.apple-developer-mode #apple-data-controls > .block {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
}

#apple-user-home.apple-developer-mode #apple-pdf-upload {
    grid-area: pdf-upload;
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: 170px !important;
    min-height: 170px !important;
    max-height: 170px !important;
    margin: 0 !important;
    box-sizing: border-box !important;
}

#apple-user-home.apple-developer-mode #apple-update-status {
    grid-area: update-status;
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    height: 170px !important;
    min-height: 170px !important;
    max-height: 170px !important;
    margin: 0 !important;
    box-sizing: border-box !important;
}

#apple-user-home.apple-developer-mode #apple-update-status .wrap {
    height: 100% !important;
}

#apple-user-home.apple-developer-mode #apple-update-status textarea {
    width: 100% !important;
    height: 150px !important;
    min-height: 150px !important;
    max-height: 150px !important;
    box-sizing: border-box !important;
}

#apple-inspector-panel#apple-inspector-panel {
    background: var(--material-panel) !important;
    backdrop-filter: var(--material-panel-filter) !important;
    -webkit-backdrop-filter: var(--material-panel-filter) !important;
    box-shadow: var(--material-panel-shadow) !important;
    border: 1px solid var(--material-line) !important;
    color: var(--intelligence-ink);
}

body[data-apple-phase="retrieval"] #apple-composer::before {
    box-shadow: 0 4px 22px rgba(63,113,181,.055) !important;
    background: radial-gradient(ellipse at 50% 100%,rgba(60,118,186,.055),transparent 70%) !important;
}

body[data-apple-phase="retrieval"] #apple-composer .mesaj-kutusu textarea {
    color: var(--intelligence-muted) !important;
}

#apple-telemetry {
    color: var(--intelligence-ink);
    border: 1px solid var(--material-line);
    border-radius: 18px;
    padding: 16px;
    background: var(--material-float);
    font-variant-numeric: tabular-nums;
}

.ai-telemetry-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
    font-size: 9px;
    letter-spacing: .12em;
    font-weight: 650;
    color: var(--intelligence-muted);
}

#apple-telemetry[data-live="true"] .ai-live-badge {
    color: #1685f7;
}

.ai-empty-metrics {
    color: var(--intelligence-muted);
    font-size: 12px;
    line-height: 1.6;
}

.ai-metric {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    padding: 10px 0;
    border-bottom: 1px solid var(--material-line);
    font-size: 11px;
}

.ai-metric span {
    color: var(--intelligence-muted);
}

.ai-metric strong {
    font-weight: 550;
    white-space: nowrap;
}

.ai-metric:last-child strong {
    color: #1685f7;
}

.ai-metric[data-pending="true"] strong {
    color: var(--intelligence-muted);
}

.ai-retrieval h4,
.ai-token-breakdown h4 {
    margin: 17px 0 10px;
    font-size: 10px;
    color: var(--intelligence-muted);
    font-weight: 550;
}

.ai-score-row {
    display: grid;
    grid-template-columns: 75px minmax(25px,1fr) 42px;
    align-items: center;
    gap: 9px;
    margin: 7px 0;
    font-size: 10px;
    color: var(--intelligence-muted);
}

.ai-score-track {
    height: 4px;
    background: rgba(103,137,180,.12);
    border-radius: 99px;
    overflow: hidden;
}

.ai-score-track i {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg,#93caff,#238bf7);
    transition: width 400ms var(--intelligence-spring);
}

.ai-score-row b {
    text-align: right;
    font-weight: 550;
    color: var(--intelligence-ink);
}

.ai-token-strip {
    display: flex;
    height: 5px;
    gap: 2px;
    border-radius: 99px;
    overflow: hidden;
    margin-bottom: 9px;
    background: rgba(103,137,180,.12);
}

.ai-token-strip i {
    min-width: 0;
    background: #248bf9;
}

.ai-token-strip i:nth-child(2) {
    background: #b69aeb;
}

.ai-token-strip i:nth-child(3) {
    background: #7cc7ce;
}

.ai-token-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 5px 12px;
    font-size: 10px;
    color: var(--intelligence-muted);
}

.ai-token-legend b {
    font-weight: 550;
    color: var(--intelligence-ink);
}

.apple-switch input[type="checkbox"]::after {
    content: "";
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 2px 6px rgba(0,0,0,.18), 0 1px 2px rgba(0,0,0,.10);
    transition: transform 140ms var(--intelligence-spring) !important;
}

/* Kaynaklar ve belge görünümü */

#apple-chat .ai-sources-footer {
    display: flex;
    align-items: center;
    align-self: flex-start;
    max-width: 100%;
    min-height: 30px;
    min-width: 0;
    margin: 6px 0 0;
    padding-left: 12px;
    box-sizing: border-box;
    opacity: 0;
    transform: translateY(-3px);
    pointer-events: none;
    transition: opacity 180ms ease, transform 180ms ease;
}

#apple-chat .bot-row:focus-within > .ai-sources-footer,
#apple-chat .bot-row[data-sources-revealed="true"] > .ai-sources-footer {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
}

#apple-chat .ai-source-capsule {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    min-height: 28px;
    min-width: 0;
    max-width: 100%;
    padding: 4px 9px;
    border: 1px solid var(--material-line);
    border-radius: 9px;
    background: var(--material-float);
    color: var(--intelligence-muted);
    font: inherit;
    font-size: 11px;
    cursor: pointer;
    pointer-events: inherit;
    box-shadow: 0 3px 10px rgba(15,23,42,.04);
    transition: color 150ms ease, border-color 150ms ease;
}

#apple-chat .ai-source-capsule:hover {
    color: var(--intelligence-ink);
    border-color: rgba(22,133,247,.35);
}

#apple-chat .ai-source-label {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

#apple-chat .ai-source-capsule:focus-visible {
    outline: 2px solid var(--intelligence-accent);
    outline-offset: 2px;
}

#apple-chat .bot-row:has(.ai-sources-footer) {
    flex-direction: column !important;
    align-items: flex-start !important;
}

#apple-source-sheet::backdrop {
    background: rgba(20,32,51,.11);
    backdrop-filter: blur(3px);
}

#apple-source-sheet .ai-sheet-inner {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.ai-source-note {
    margin: 0 0 16px;
    font-size: 12px;
    line-height: 1.6;
    color: var(--intelligence-muted);
}

.ai-source-card {
    margin-bottom: 10px;
    border: 1px solid var(--material-line);
    border-radius: 17px;
    background: var(--material-float);
    overflow: hidden;
}

.ai-source-card summary {
    padding: 14px;
    cursor: pointer;
    font-size: 13px;
    line-height: 1.5;
    color: var(--intelligence-ink);
    overflow-wrap: anywhere;
}

.ai-source-card summary small {
    display: block;
    margin: 4px 0 0 16px;
    color: var(--intelligence-muted);
    font-size: 11px;
}

.ai-source-passage {
    padding: 0 15px 16px;
    color: var(--intelligence-ink);
    font-size: 13px;
    line-height: 1.75;
}

.ai-source-passage section+section {
    margin-top: 12px;
    border-top: 1px solid var(--material-line);
    padding-top: 12px;
}

.ai-source-passage p {
    margin: 5px 0 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.ai-source-passage small {
    color: var(--intelligence-muted);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .07em;
}

.ai-source-passage mark {
    border-radius: 3px;
    padding: 1px 2px;
    background: rgba(55,163,255,.18);
    color: inherit;
}

a.ai-source-web {
    display: block;
    padding: 15px;
    color: var(--intelligence-ink);
    text-decoration: none;
}

a.ai-source-web small {
    display: block;
    margin-top: 5px;
    color: var(--intelligence-muted);
    font-size: 11px;
    overflow-wrap: anywhere;
}

#apple-source-sheet button:focus-visible,
#apple-source-sheet a:focus-visible,
#apple-source-sheet summary:focus-visible {
    outline: 2px solid #1685f7;
    outline-offset: -3px;
}

#apple-chat button.ai-inline-citation {
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    vertical-align: baseline;
    position: relative;
    top: -.12em;
    min-width: 26px;
    min-height: 24px;
    width: auto;
    margin: 0 3px;
    padding: 0 5px;
    border: 1px solid var(--material-line);
    border-radius: 7px;
    background: var(--material-float);
    color: var(--intelligence-muted);
    font: 500 11px/1 sans-serif;
    box-shadow: none;
    cursor: pointer;
    transition: background-color 160ms ease,color 160ms ease;
}

#apple-chat button.ai-inline-citation:is(:hover,:focus-visible),
#apple-chat a.ai-linked-citation:is(:hover,:focus-visible) {
    color: var(--intelligence-accent);
    background: rgba(22,133,247,.09);
}

#apple-chat button.ai-inline-citation:focus-visible {
    outline: 2px solid var(--intelligence-accent);
    outline-offset: 2px;
}

#apple-chat a.ai-linked-citation {
    border-radius: 4px;
    text-decoration-style: dotted;
    text-underline-offset: 3px;
}

::highlight(ai-citation-sentence) {
    background-color: rgba(22,133,247,.16);
    color: inherit;
}

::highlight(ai-citation-passage) {
    background-color: rgba(22,133,247,.27);
    color: inherit;
}

#apple-source-sheet .ai-source-card[data-source-active="true"] {
    border-color: rgba(22,133,247,.4);
    background: rgba(22,133,247,.055);
}

#apple-source-sheet .ai-source-card {
    scroll-margin-top: 16px;
    transition: border-color 160ms ease, background-color 160ms ease;
}

#apple-source-sheet {
    background: var(--material-panel) !important;
    backdrop-filter: var(--material-panel-filter) !important;
    -webkit-backdrop-filter: var(--material-panel-filter) !important;
    box-shadow: var(--material-panel-shadow) !important;
    border: 1px solid var(--material-line) !important;
    color: var(--intelligence-ink);
    position: fixed;
    inset: 12px 12px 12px auto;
    margin: 0;
    padding: 0;
    max-width: none;
    height: calc(100dvh - 24px);
    max-height: none;
    border-radius: 25px;
    overflow: hidden;
    font-family: inherit;
    z-index: 10003;
    width: min(560px,42vw);
}

#apple-source-sheet:not([open]) {
    display: none !important;
}

#apple-source-sheet .ai-sheet-head {
    padding: 20px;
    flex: none;
}

#apple-source-sheet .ai-sheet-body {
    scroll-padding-top: 100px;
}

#apple-chat .bot-row.ai-answer-spatial {
    width: min(100%,var(--ai-source-width,100%)) !important;
    max-width: min(100%,var(--ai-source-width,100%)) !important;
    min-width: 0 !important;
    transform: translateX(-4px) scale(.985) !important;
    transform-origin: left top;
}

#apple-pdf-view-request,
#apple-pdf-view-response,
#apple-pdf-view-submit {
    display: none !important;
}

.ai-pdf-viewer {
    margin: 0 0 22px;
    min-width: 0;
}

.ai-pdf-viewer-head {
    position: sticky;
    top: -18px;
    z-index: 2;
    display: flex;
    gap: 12px;
    justify-content: space-between;
    align-items: center;
    background: var(--material-float,#fafafc);
    border-bottom: 1px solid var(--material-line,#ddd);
    padding: 13px 0;
}

.ai-pdf-viewer-head>div {
    min-width: 0;
}

.ai-pdf-viewer-head small {
    display: block;
    font-size: 10px;
    color: var(--intelligence-muted,#727780);
    letter-spacing: .08em;
}

.ai-pdf-viewer-head strong {
    display: block;
    font-size: 12px;
    max-width: 260px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    color: var(--intelligence-ink,#222);
}

.ai-pdf-viewer-head nav {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: none;
}

.ai-pdf-viewer button {
    border: 1px solid var(--material-line,#ddd);
    background: var(--material-float,#fff);
    border-radius: 11px;
    width: 34px;
    height: 34px;
    font-size: 22px;
    cursor: pointer;
    color: var(--intelligence-ink,#222);
}

.ai-pdf-viewer button:disabled {
    opacity: .35;
    cursor: default;
}

.ai-pdf-page-label {
    font-size: 11px;
    min-width: 44px;
    text-align: center;
    color: var(--intelligence-muted,#777);
}

.ai-pdf-status {
    color: var(--intelligence-muted,#777);
    font-size: 11px;
    line-height: 1.6;
    min-height: 18px;
    margin: 10px 0;
}

.ai-pdf-stage {
    position: relative;
    background: white;
    line-height: 0;
    box-shadow: 0 3px 18px rgba(0,0,0,.08);
}

.ai-pdf-stage[hidden] {
    display: none;
}

.ai-pdf-stage canvas {
    display: block;
    width: 100%;
    height: auto;
}

.ai-pdf-highlights {
    position: absolute;
    inset: 0;
    pointer-events: none;
}

.ai-pdf-highlights span {
    position: absolute;
    background: rgba(255,205,65,.36);
    border-radius: 2px;
    mix-blend-mode: multiply;
}

.ai-pdf-viewer button:active {
    transform: scale(.96);
}

#apple-source-sheet[data-phone="true"] {
    width: calc(100vw - 16px);
    inset: 8px;
    height: calc(100dvh - 16px);
    border-radius: 22px;
}

#apple-source-sheet[data-phone="true"] .ai-pdf-viewer-head strong {
    max-width: calc(100vw - 220px);
}

#apple-source-sheet[data-phone="true"] .ai-pdf-viewer button {
    width: 44px;
    height: 44px;
}

#apple-source-sheet[data-reduced-motion="true"] * {
    animation: none !important;
    transition: none !important;
}

/* Ortak etkileşimler */

.research-app *::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

.research-app *::-webkit-scrollbar-track {
    background: transparent;
}

.research-app *::-webkit-scrollbar-thumb {
    background: rgba(60,60,67,.20);
    border: 3px solid transparent;
    border-radius: 999px;
    background-clip: padding-box;
}

.research-app *::-webkit-scrollbar-thumb:hover {
    background: rgba(60,60,67,.34);
    border: 3px solid transparent;
    background-clip: padding-box;
}

.apple-scroll-bottom {
    position: absolute;
    right: 18px;
    bottom: 18px;
    z-index: 50;
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border: 1px solid rgba(255,255,255,.78);
    border-radius: 999px;
    background: rgba(255,255,255,.84);
    color: #3a3a3c;
    box-shadow: 0 8px 20px rgba(15,23,42,.10), inset 0 1px 0 rgba(255,255,255,.90);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    opacity: 0;
    transform: translateY(6px) scale(.92);
    pointer-events: none;
    cursor: pointer;
    transition: opacity .18s ease, transform .24s var(--apple-spring);
}

.apple-scroll-bottom.visible {
    opacity: 1;
    transform: translateY(0) scale(1);
    pointer-events: auto;
}

.apple-toast-stack {
    position: fixed;
    top: 72px;
    right: 18px;
    z-index: 12000;
    display: grid;
    gap: 7px;
    width: min(340px, calc(100vw - 36px));
    pointer-events: none;
}

.apple-toast {
    display: grid;
    grid-template-columns: 24px minmax(0,1fr);
    align-items: center;
    gap: 8px;
    padding: 10px 11px;
    border: 1px solid rgba(255,255,255,.76);
    border-radius: 16px;
    background: rgba(255,255,255,.88);
    color: #343437;
    box-shadow: 0 14px 40px rgba(15,23,42,.12), inset 0 1px 0 rgba(255,255,255,.96);
    backdrop-filter: blur(22px) saturate(160%);
    -webkit-backdrop-filter: blur(22px) saturate(160%);
    animation: appleToastIn .28s var(--apple-spring) both;
}

.apple-toast.out {
    animation: appleToastOut .22s ease-in both;
}

.apple-toast-icon {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: rgba(52,199,89,.11);
    color: #248a3d;
    font-size: 11px;
    font-weight: 800;
}

.apple-toast.error .apple-toast-icon {
    background: rgba(255,59,48,.11);
    color: #ff3b30;
}

.apple-toast-text {
    font-size: 11px;
    line-height: 1.35;
    font-weight: 620;
}

html.apple-dark .apple-toast {
    background: rgba(35,35,38,.78) !important;
    border-color: rgba(255,255,255,.085) !important;
    box-shadow: 0 18px 52px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.055) !important;
}

.ai-liquid-surface {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 10004;
    pointer-events: none;
    background: var(--material-float,rgba(250,250,252,.96));
    border-radius: 0;
    filter: drop-shadow(0 12px 22px rgba(25,30,40,.10));
    will-change: transform,clip-path;
    contain: layout style;
}

.ai-liquid-identity {
    position: fixed;
    inset: 0 auto auto 0;
    z-index: 10005;
    pointer-events: none;
    font: 500 12px/14px sans-serif;
    color: var(--intelligence-ink,#222);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    will-change: transform;
}

[data-liquid-active="true"] {
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}

#ai-ingestion-card {
    position: fixed;
    z-index: 10002;
    left: 50%;
    bottom: calc(160px + env(safe-area-inset-bottom,0px));
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 17px;
    width: min(380px,calc(100vw - 32px));
    padding: 18px 20px;
    border: 1px solid var(--material-line,rgba(120,130,150,.18));
    background: var(--material-float,rgba(250,250,252,.97));
    backdrop-filter: blur(18px);
    border-radius: 23px;
    box-shadow: 0 18px 48px rgba(20,28,40,.13);
    box-sizing: border-box;
    pointer-events: none;
}

#ai-ingestion-card[hidden] {
    display: none;
}

.ai-ingestion-pages {
    position: relative;
    width: 65px;
    height: 76px;
    flex: none;
}

.ai-ingestion-pages img {
    position: absolute;
    width: 47px;
    height: 66px;
    object-fit: cover;
    object-position: top;
    border: 1px solid #ddd;
    background: #fff;
    border-radius: 5px;
    box-shadow: 0 3px 9px #0001;
    animation: ai-page-breathe 1800ms ease-in-out infinite;
}

.ai-ingestion-pages img:nth-child(1) {
    transform: translate(12px,0) rotate(8deg);
    animation-delay: 160ms;
}

.ai-ingestion-pages img:nth-child(2) {
    transform: translate(5px,4px) rotate(-5deg);
    animation-delay: 80ms;
}

.ai-ingestion-pages img:nth-child(3) {
    transform: translate(0,8px);
}

#ai-ingestion-card[data-stage="ready"] img,
#ai-ingestion-card[data-stage="error"] img {
    animation: none;
}

.ai-ingestion-copy {
    min-width: 0;
}

.ai-ingestion-copy strong {
    display: block;
    font-size: 12px;
    color: var(--intelligence-ink,#222);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.ai-ingestion-copy small {
    display: block;
    font-size: 11px;
    color: var(--intelligence-muted,#777);
    margin: 5px 0 10px;
}

.ai-ingestion-copy span {
    display: block;
    font-size: 12px;
    color: var(--intelligence-ink,#222);
}

#ai-ingestion-card[data-reduced-motion="true"] img {
    animation: none !important;
    transition: none !important;
}

#apple-source-coverage { margin-top:18px; padding-top:16px; border-top:1px solid var(--material-line); }
#apple-source-coverage h4 { margin:0 0 8px; font-size:11px; font-weight:600; color:var(--intelligence-muted); }
#apple-source-coverage strong { display:block; font-size:15px; line-height:1.5; font-weight:600; color:var(--intelligence-ink); }
#apple-source-coverage small { display:block; margin-top:8px; font-size:11px; line-height:1.6; color:var(--intelligence-muted); }
#apple-source-coverage progress { display:block; width:100%; height:5px; margin-top:10px; appearance:none; border:0; border-radius:10px; overflow:hidden; background:rgba(128,128,140,.12); accent-color:#3989f9; }
#apple-source-coverage progress::-webkit-progress-bar { background:rgba(128,128,140,.12); border-radius:10px; }
#apple-source-coverage progress::-webkit-progress-value { background:#3989f9; border-radius:10px; }
#apple-source-coverage progress::-moz-progress-bar { background:#3989f9; border-radius:10px; }
#apple-source-coverage progress[hidden] { display:none; }
.ai-document-map { scroll-margin-block-start:88px; margin:12px 0; border:1px solid var(--material-line,#e4e6eb); border-radius:16px; background:var(--material-float,#fff); color:var(--intelligence-ink,#222); overflow:hidden; }
.ai-document-map summary { display:flex; align-items:center; justify-content:space-between; gap:8px; padding:12px; cursor:pointer; list-style:none; font-size:12px; font-weight:600; }
.ai-document-map summary::-webkit-details-marker { display:none; }
.ai-document-map summary::after { content:'⌄'; font-size:16px; transition:transform 150ms ease; }
.ai-document-map[open] summary::after { transform:rotate(180deg); }
.ai-document-map summary:focus-visible { outline:2px solid #3989f9; outline-offset:-3px; border-radius:14px; }
.ai-document-map nav { max-height:190px; overflow:auto; overscroll-behavior:contain; padding:0 6px 6px; scrollbar-width:thin; }
.ai-document-map input { width:calc(100% - 20px); box-sizing:border-box; margin:0 10px 8px; padding:8px 10px; border:1px solid var(--material-line,#e4e6eb); border-radius:10px; background:transparent; font:inherit; font-size:12px; color:inherit; }
.ai-document-map input[hidden] { display:none; }
#apple-source-sheet .ai-document-map button.ai-section-button { display:flex; align-items:center; justify-content:space-between; gap:8px; width:100%; height:auto; min-height:38px; margin:2px 0; padding:9px 10px 9px calc(10px + var(--section-depth,0)*10px); border:0; border-radius:10px; background:transparent; color:inherit; text-align:left; font-family:inherit; font-size:12px; line-height:1.4; transition:background 140ms,transform 120ms; }
#apple-source-sheet .ai-document-map button.ai-section-button[hidden] { display:none; }
#apple-source-sheet .ai-document-map button.ai-section-button:is(:hover,:focus-visible) { background:rgba(128,128,140,.09); outline:none; }
#apple-source-sheet .ai-document-map button.ai-section-button[aria-current=true] { background:rgba(0,122,255,.09); color:#0875da; }
.ai-section-title { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ai-section-meta { display:flex; align-items:center; gap:7px; flex:none; font-size:10px; color:var(--intelligence-muted,#777); }
.ai-section-used { width:6px; height:6px; border-radius:50%; background:#3989f9; visibility:hidden; }
.ai-section-button[data-used=true] .ai-section-used { visibility:visible; }
.ai-document-map-note { padding:0 12px 10px; margin:0; color:var(--intelligence-muted,#777); font-size:10px; line-height:1.5; }
#apple-source-sheet[data-phone=true] .ai-document-map nav { max-height:160px; }
#apple-source-sheet[data-phone=true] .ai-document-map button.ai-section-button { min-height:44px; }
#apple-source-sheet[data-reduced-motion=true] .ai-document-map summary::after { transition:none; }

@media (max-width:980px) {

    /* Uygulama ve yerleşim */

    .research-app {
        width: 98% !important;
    }

    /* Composer ve ekler */

    .chatgpt-composer {
        width: 94% !important;
    }
}

@media (max-width:720px) {

    /* Inspector ve telemetri */

    .apple-upload button[aria-dropeffect="copy"],
.apple-upload [data-testid="file-upload"],
.apple-upload .upload-container {
        min-height: 160px !important;
        height: 160px !important;
    }

    .apple-upload button[aria-dropeffect="copy"] h2,
.apple-upload .upload-container h2 {
        font-size: 20px !important;
    }
}

@media (max-width:620px) {

    /* Composer ve ekler */

    .gonder-butonu button,
button.gonder-butonu {
        font-size: 21px !important;
    }
}

@media (max-width:760px) {

    /* Üst bar */

    .apple-topbar {
        grid-template-columns: minmax(0,1fr) auto;
    }

    .apple-topbar-pdf {
        max-width: 110px;
    }

    /* Inspector ve telemetri */

    .apple-inspector {
        border-radius: 24px !important;
        padding: 10px 4px 10px 10px !important;
    }
}

@media (prefers-reduced-motion:reduce) {

    /* Uygulama ve yerleşim */

    *,
*::before,
*::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
    }

    /* Üst bar */

    html body[data-apple-phase] .apple-topbar .apple-ready-dot {
        animation: none !important;
    }

    /* Sohbet ve boş ekran */

    #apple-chat .bot-row,
.apple-empty-state {
        transition: none !important;
    }

    /* Composer ve ekler */

    #apple-send-shape {
        animation: none !important;
    }

    #apple-composer#apple-composer,
#apple-attachment-slot#apple-attachment-slot,
#apple-composer .composer-plus,
#apple-composer .ai-composer-state {
        transition: none !important;
    }

    #apple-composer .ai-composer-state::before {
        animation: none !important;
    }

    /* Model ve ayarlar */

    #apple-reasoning-range::-webkit-slider-thumb,
#apple-reasoning-range::-moz-range-thumb {
        transform: none;
    }

    /* Inspector ve telemetri */

    #apple-settings-trigger,
.ai-score-track i,
.apple-switch input[type="checkbox"]::after {
        transition: none !important;
    }

    /* Kaynaklar ve belge görünümü */

    #apple-chat .ai-sources-footer,
#apple-chat .ai-source-capsule {
        transition: none !important;
        transform: none !important;
    }

    #apple-source-sheet .ai-source-card,
#apple-chat button.ai-inline-citation {
        transition: none !important;
    }

    /* Ortak etkileşimler */

    .ai-liquid-surface {
        display: none;
    }

    .ai-ingestion-pages img {
        animation: none;
    }
}

@media (max-width:740px) {

    /* Inspector ve telemetri */

    .apple-token-card,
.apple-token-card-detailed {
        grid-template-columns: 1fr !important;
    }

    .apple-token-secondary,
.apple-token-secondary-detailed {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (max-height:760px) {

    /* Uygulama ve yerleşim */

    .apple-main-row {
        height: calc(100vh - 70px) !important;
        max-height: calc(100vh - 70px) !important;
    }

    .apple-section-header {
        margin-bottom: 6px !important;
    }

    /* Inspector ve telemetri */

    .apple-upload button[aria-dropeffect="copy"],
.apple-upload [data-testid="file-upload"],
.apple-upload .upload-container {
        min-height: 145px !important;
        height: 145px !important;
    }
}

@media (max-width:900px) {

    /* Uygulama ve yerleşim */

    html,
body {
        overflow: hidden !important;
    }

    .research-app {
        width: 100% !important;
        max-width: 100% !important;
        height: var(--apple-mobile-height, 100dvh) !important;
        padding: max(6px, env(safe-area-inset-top)) max(8px, env(safe-area-inset-right)) max(8px, env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left)) !important;
        animation: none !important;
    }

    .apple-main-row {
        position: relative !important;
        display: flex !important;
        flex-direction: column !important;
        flex-wrap: nowrap !important;
        gap: 0 !important;
        height: var(--apple-mobile-main-height, calc(100dvh - 86px)) !important;
        max-height: none !important;
        min-width: 0 !important;
        overflow: hidden !important;
    }

    .apple-intelligence-orb {
        width: 64px !important;
        height: 64px !important;
        border-radius: 24px !important;
    }

    .apple-example-chip {
        min-height: 40px;
    }

    .ai-sheet-head {
        padding: 19px 18px 15px;
    }

    .ai-sheet-body {
        padding: 15px;
    }

    /* Üst bar */

    .apple-topbar {
        position: relative !important;
        top: 0 !important;
        padding: 6px 8px !important;
        gap: 6px !important;
        margin: 0 0 6px !important;
        border-radius: 16px !important;
    }

    .apple-topbar-left {
        gap: 8px !important;
    }

    .apple-topbar-meta {
        overflow: hidden;
        white-space: nowrap;
    }

    .apple-topbar-pdf {
        display: none !important;
    }

    .apple-topbar-meta .apple-topbar-separator:last-of-type {
        display: none;
    }

    .apple-topbar-button {
        min-width: 44px;
        min-height: 44px;
    }

    .apple-topbar [data-apple-action="inspector"] {
        display: none !important;
    }

    /* Sohbet ve boş ekran */

    .apple-chat-column {
        flex: 1 1 auto !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        height: 100% !important;
        min-height: 0 !important;
        gap: 6px !important;
        transition: none !important;
    }

    .research-app [data-testid="chatbot"] {
        border-radius: 20px !important;
    }

    .apple-empty-state {
        padding: 16px 12px !important;
        gap: 16px !important;
        border-radius: 20px !important;
    }

    .apple-empty-state strong {
        font-size: 21px !important;
    }

    .apple-example-prompts,
.research-app [data-testid="chatbot"] .bot-row .message {
        max-width: 100% !important;
    }

    .research-app [data-testid="chatbot"] pre {
        max-width: 100%;
        overflow-x: auto;
    }

    .apple-chat-column > #apple-chat {
        flex: 1 1 0 !important;
        height: auto !important;
        min-height: 0 !important;
        max-height: none !important;
    }

    #apple-chat .apple-empty-state strong {
        font-size: 21px !important;
        max-width: 100%;
    }

    #apple-chat .apple-example-chip {
        max-width: 100%;
        white-space: normal;
    }

    #apple-chat .apple-empty-document {
        font-size: 15px;
        line-height: 1.45;
    }

    #apple-chat .apple-empty-heading {
        gap: 7px;
    }

    /* Composer ve ekler */

    .chatgpt-composer {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
        flex-wrap: wrap !important;
        margin: 0 !important;
    }

    .chatgpt-composer > .form {
        display: contents !important;
    }

    .composer-plus,
.gonder-butonu {
        flex: 0 0 44px !important;
        width: 44px !important;
        min-width: 44px !important;
        max-width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
    }

    .composer-plus button,
button.composer-plus,
.gonder-butonu button,
button.gonder-butonu {
        width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
    }

    .mesaj-kutusu {
        flex: 1 1 0 !important;
        width: auto !important;
        min-width: 0 !important;
    }

    .mesaj-kutusu textarea {
        font-size: 16px !important;
        min-height: 44px !important;
        max-height: min(120px, 24dvh) !important;
        padding: 8px 4px !important;
    }

    #apple-composer#apple-composer {
        padding: 6px !important;
        gap: 4px 6px !important;
        grid-template-columns: 44px minmax(0,1fr) 44px !important;
        --composer-control-size: 46px;
        border-radius: 26px !important;
    }

    #apple-composer[data-has-file="true"]#apple-composer {
        grid-template-areas: "attachment attachment attachment" "plus message message" "settings settings send" !important;
        row-gap: 6px !important;
    }

    #apple-stop#apple-stop {
        width: 46px !important;
        height: 46px !important;
    }

    #apple-send-visual#apple-send-visual {
        width: 23px !important;
        height: 23px !important;
    }

    #apple-composer-attachment {
        padding: 6px 10px;
    }

    #apple-composer-attachment strong {
        max-width: calc(100vw - 110px);
    }

    #apple-composer .mesaj-kutusu textarea {
        max-height: 22dvh !important;
    }

    #apple-composer#apple-composer#apple-composer {
        grid-template-areas: "attachment attachment attachment" "plus message message" "settings settings send" !important;
        min-height: 108px !important;
        padding-top: 7px !important;
    }

    #apple-composer[data-writing="true"]#apple-composer#apple-composer {
        min-height: 108px !important;
    }

    #apple-composer .ai-composer-state {
        font-size: 9px;
    }

    /* Model ve ayarlar */

    .apple-command-palette {
        width: calc(100vw - 24px) !important;
        max-height: 80dvh;
        overflow-y: auto;
    }

    #apple-reasoning-widget#apple-reasoning-widget {
        width: 100% !important;
        max-width: none !important;
        justify-self: start !important;
    }

    #apple-summary-model,
#apple-summary-detail {
        font-size: 13px !important;
    }

    #apple-global-settings-button#apple-global-settings-button,
#apple-settings-menu#apple-settings-menu {
        display: none !important;
    }

    /* Inspector ve telemetri */

    .research-app.apple-inspector-collapsed .apple-chat-column {
        flex: 1 1 auto !important;
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        height: 100% !important;
        min-height: 0 !important;
        gap: 6px !important;
        transition: none !important;
    }

    .research-app .apple-inspector {
        display: none !important;
    }

    .research-app.apple-mobile-inspector-open .apple-inspector {
        max-height: 100% !important;
        margin: 0 !important;
        border-radius: 20px !important;
        transition: none !important;
    }

    html.apple-dark .research-app.apple-mobile-inspector-open .apple-inspector {
        background: #1c1c1e !important;
    }

    #apple-user-home#apple-user-home #apple-inspector-panel#apple-inspector-panel {
        display: none !important;
    }

    #apple-user-home.apple-developer-mode #apple-data-controls#apple-data-controls {
        gap: 8px !important;
    }

    #apple-user-home.apple-developer-mode #apple-pdf-upload .upload-text,
#apple-user-home.apple-developer-mode #apple-pdf-upload p {
        min-width: 0 !important;
        overflow-wrap: anywhere;
        white-space: normal !important;
        font-size: 12px !important;
    }

    /* Kaynaklar ve belge görünümü */

    #apple-source-sheet {
        inset: auto 8px 8px;
        height: 82dvh;
        border-radius: 24px;
    }

    /* Ortak etkileşimler */

    .apple-toast-stack {
        max-width: calc(100vw - 24px);
        right: 12px !important;
    }
}

@media (min-width:901px) {

    /* Uygulama ve yerleşim */

    #apple-user-home#apple-user-home {
        height: calc(100dvh - 148px) !important;
        max-height: calc(100dvh - 148px) !important;
    }

    #apple-user-home {
        position: relative !important;
    }

    /* Sohbet ve boş ekran */

    #apple-user-home.apple-home-collapsed .apple-chat-column {
        flex: 1 1 100% !important;
        width: 100% !important;
        max-width: 100% !important;
        min-width: 0 !important;
    }

    #apple-user-home .apple-chat-column {
        height: 100% !important;
        min-height: 0 !important;
    }

    #apple-chat#apple-chat {
        flex: 1 1 0 !important;
        min-height: 0 !important;
        height: 0 !important;
    }

    #apple-user-home > .apple-chat-column {
        transition: none !important;
    }

    /* Composer ve ekler */

    #apple-composer#apple-composer {
        flex: 0 0 auto !important;
        margin-top: 18px !important;
        margin-bottom: 10px !important;
    }

    #apple-composer[data-writing="true"]#apple-composer {
        padding-top: 15px !important;
        padding-bottom: 15px !important;
    }

    #apple-composer[data-has-file="true"]#apple-composer {
        grid-template-areas: "attachment attachment attachment attachment" "plus message settings send" !important;
        row-gap: 9px !important;
        border-radius: 30px !important;
    }

    #apple-composer[data-compact="true"][data-has-file="true"]#apple-composer#apple-composer {
        grid-template-areas: "attachment attachment attachment" "plus message message" "settings settings send" !important;
    }

    #apple-composer#apple-composer#apple-composer {
        min-height: 76px !important;
        padding-top: 9px !important;
    }

    #apple-composer[data-writing="true"]#apple-composer#apple-composer {
        min-height: 76px !important;
    }

    #apple-composer[data-compact="true"]#apple-composer#apple-composer {
        grid-template-columns: 44px minmax(0,1fr) var(--composer-control-size) !important;
        grid-template-areas: "attachment attachment attachment" "plus message message" "settings settings send" !important;
    }

    /* Model ve ayarlar */

    #apple-composer[data-compact="true"] #apple-reasoning-widget#apple-reasoning-widget {
        justify-self: start !important;
        max-width: 100% !important;
    }

    /* Inspector ve telemetri */

    #apple-user-home.apple-home-collapsed:not([data-inspector-motion]) > #apple-inspector-panel {
        display: none !important;
    }

    #apple-user-home.apple-developer-mode:not(.apple-home-collapsed) .apple-chat-column {
        flex: 5 1 0 !important;
    }

    #apple-user-home.apple-developer-mode:not(.apple-home-collapsed) .apple-inspector {
        flex: 5 1 0 !important;
        min-width: 320px !important;
    }

    #apple-inspector-panel#apple-inspector-panel {
        max-height: 100% !important;
        overflow-y: auto !important;
    }

    #apple-user-home > #apple-inspector-panel {
        transition: none !important;
    }

    #apple-user-home[data-inspector-motion] > #apple-inspector-panel {
        position: absolute !important;
        top: 0 !important;
        right: 0 !important;
        left: auto !important;
        display: flex !important;
        flex: none !important;
        width: var(--inspector-motion-width) !important;
        min-width: var(--inspector-motion-width) !important;
        max-width: var(--inspector-motion-width) !important;
        height: var(--inspector-motion-height) !important;
        padding: var(--inspector-motion-padding) !important;
        margin: 0 !important;
        opacity: 1 !important;
        transform: none !important;
        transform-origin: right center !important;
        filter: none !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        background: var(--material-panel) !important;
        overflow: hidden !important;
        pointer-events: none !important;
        z-index: 3 !important;
        will-change: transform,clip-path;
        contain: layout paint;
    }

    #apple-user-home[data-inspector-motion] > .apple-chat-column {
        flex: 0 0 var(--inspector-chat-width) !important;
        width: var(--inspector-chat-width) !important;
        min-width: 0 !important;
        max-width: var(--inspector-chat-width) !important;
        transform-origin: left top !important;
        will-change: transform;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }

    #apple-user-home[data-inspector-motion] > .apple-chat-column * {
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }

    #apple-user-home[data-inspector-motion] #apple-inspector-panel *,
#apple-user-home[data-inspector-motion] #apple-inspector-panel *::before,
#apple-user-home[data-inspector-motion] #apple-inspector-panel *::after {
        animation-play-state: paused !important;
        transition: none !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
    }
}

@media (hover:hover) and (pointer:fine) {

    /* Kaynaklar ve belge görünümü */

    #apple-chat .bot-row:hover > .ai-sources-footer {
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
    }
}

@media (hover:none), (pointer:coarse) {

    /* Kaynaklar ve belge görünümü */

    #apple-chat .ai-source-capsule {
        min-height: 44px;
        padding: 7px 10px;
    }

    #apple-chat .ai-sources-footer {
        min-height: 44px;
    }

    #apple-chat button.ai-inline-citation {
        min-width: 32px;
        min-height: 32px;
        margin-inline: 4px;
    }
}

/* Animasyon tanımları */

@keyframes applePageIn {

    0% {
        opacity: 0;
    }

    100% {
        opacity: 1;
    }
}

@keyframes appleHeaderIn {

    0% {
        opacity: 0;
        transform: translateY(-8px);
    }

    100% {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes appleCardIn {

    0% {
        opacity: 0;
        transform: translateY(18px) scale(.985);
    }

    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

@keyframes appleComposerIn {

    0% {
        opacity: 0;
    }

    100% {
        opacity: 1;
    }
}

@keyframes appleMessageIn {

    0% {
        opacity: 0;
        transform: translateY(10px) scale(.985);
        filter: blur(2px);
    }

    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }
}

@keyframes appleAmbientFloat {

    0% {
        transform: translate3d(0,0,0) scale(1);
    }

    100% {
        transform: translate3d(24px,-18px,0) scale(1.08);
    }
}

@keyframes appleFadeIn {

    0% {
        opacity: 0;
        transform: translateY(6px);
    }

    100% {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes applePopoverIn {

    0% {
        opacity: 0;
        transform: translateY(8px) scale(.97);
        filter: blur(2px);
    }

    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }
}

@keyframes appleFloatTiny {

    0%, 100% {
        transform: translateY(0px);
    }

    50% {
        transform: translateY(-5px);
    }
}

@keyframes appleOrbBreathe {

    0%, 100% {
        box-shadow: 0 10px 20px rgba(0,113,227,.28), 0 4px 8px rgba(0,113,227,.16), inset 0 1px 0 rgba(255,255,255,.30);
    }

    50% {
        box-shadow: 0 14px 26px rgba(0,113,227,.34), 0 6px 14px rgba(0,113,227,.20), inset 0 1px 0 rgba(255,255,255,.34);
    }
}

@keyframes appleShimmer {

    0%, 70%, 100% {
        transform: translateX(-120%) rotate(10deg);
        opacity: 0;
    }

    14%, 24% {
        transform: translateX(120%) rotate(10deg);
        opacity: 1;
    }
}

@keyframes appleEmptyIn {

    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes appleOrbFloat {

    0%,100% {
        transform: translateY(0) scale(1);
    }

    50% {
        transform: translateY(-6px) scale(1.025);
    }
}

@keyframes appleOrbAura {

    from {
        transform: rotate(0deg) scale(.98);
    }

    50% {
        transform: rotate(180deg) scale(1.06);
    }

    to {
        transform: rotate(360deg) scale(.98);
    }
}

@keyframes appleOrbCore {

    0%,100% {
        transform: scale(.92);
        opacity: .82;
    }

    50% {
        transform: scale(1.16);
        opacity: 1;
    }
}

@keyframes appleStatusPulse {

    0%,100% {
        transform: scale(.92);
        opacity: .78;
    }

    50% {
        transform: scale(1.12);
        opacity: 1;
    }
}

@keyframes appleShimmerLine {

    from {
        background-position: 110% 0;
    }

    to {
        background-position: -110% 0;
    }
}

@keyframes appleSpinner {

    to {
        transform: translate(-50%,-50%) rotate(360deg);
    }
}

@keyframes appleThinkingGlow {

    0%,100% {
        box-shadow: 0 8px 18px rgba(0,113,227,.20), inset 0 1px 0 rgba(255,255,255,.26);
    }

    50% {
        box-shadow: 0 12px 26px rgba(0,113,227,.32), 0 0 0 5px rgba(10,132,255,.055), inset 0 1px 0 rgba(255,255,255,.30);
    }
}

@keyframes appleStreamingPulse {

    0%,100% {
        transform: scale(.96);
        box-shadow: 0 8px 18px rgba(0,113,227,.22), inset 0 1px 0 rgba(255,255,255,.28);
    }

    50% {
        transform: scale(1);
        box-shadow: 0 13px 27px rgba(0,113,227,.32), 0 0 0 5px rgba(10,132,255,.06), inset 0 1px 0 rgba(255,255,255,.32);
    }
}

@keyframes appleTopbarIn {

    from {
        opacity: 0;
        transform: translateY(-8px);
    }

    to {
        opacity: 1;
        transform: none;
    }
}

@keyframes appleCompactPdfIn {

    from {
        opacity: 0;
        transform: translateY(6px) scale(.98);
    }

    to {
        opacity: 1;
        transform: none;
    }
}

@keyframes appleOverlayIn {

    from {
        opacity: 0;
    }

    to {
        opacity: 1;
    }
}

@keyframes applePaletteIn {

    from {
        opacity: 0;
        transform: translateY(-8px) scale(.97);
    }

    to {
        opacity: 1;
        transform: none;
    }
}

@keyframes appleToastIn {

    from {
        opacity: 0;
        transform: translateX(12px) scale(.97);
    }

    to {
        opacity: 1;
        transform: none;
    }
}

@keyframes appleToastOut {

    to {
        opacity: 0;
        transform: translateX(10px) scale(.97);
    }
}

@keyframes intelligenceBeacon {

    0%,100% {
        box-shadow: 0 0 0 3px rgba(22,133,247,.06);
        transform: scale(.92);
    }

    50% {
        box-shadow: 0 0 0 6px rgba(22,133,247,.1);
        transform: scale(1.05);
    }
}

@keyframes intelligenceSpin {

    to {
        transform: rotate(360deg);
    }
}

@keyframes aiComposerBreathe {

    0%,100% {
        opacity: .45;
    }

    50% {
        opacity: 1;
    }
}

@keyframes ai-page-breathe {

    50% {
        translate: 0 -3px;
    }
}

/* Önceki açıklama notları içerikleri değiştirilmeden korunmuştur; aşağıda stil kuralı bulunmaz. */

/* =========================================================
   APPLE-INSPIRED UI LAYER v2
   Backend / RAG / event akışı değişmez. Sadece frontend iyileştirmesi.
   ========================================================= */

/* Genel blok görünümü */

/* Üst başlık */

/* Chat alanı */

/* Sohbet balonlarını yazıyla daha orantılı yap */

/* Kullanıcı mesajı: gerçek balon yazıya göre küçülür. */

/* Gradio 6 role="user" sınıfını hem flex-wrap'a hem iç balona verdiği için
   dış kapsayıcının sarı arka planını ve %100 yüksekliğini sıfırlıyoruz. */

/* Sarı arka plan yalnızca gerçek iç balonda kalsın. */

/* Asistan mesajı: biraz daha geniş, daha ferah ama kontrollü */

/* Side başlıklar */

/* Apple tarzı cam kartlar */

/* Composer */

/* Plus butonu */

/* Mesaj kutusu */

/* Detay dropdown - görünür alan */

/* Dropdown açılır menü - fixed koordinatı parent transform/filter ile bozulmamalı */

/* Gönder butonu */

/* Dosya yükleme kartı - hazır kutusuyla dengeli boyut */

/* Gradio'nun ham upload yazısını tamamen gizle */

/* Varsayılan Gradio metinlerini gizle, temiz tek bir satır göster */

/* Status / log kutuları */

/* Geliştirici kutuları */

/* Normal butonlar */

/* Scrollbar */

/* Animasyonlar */

/* Responsive */

/* =========================================================
   APPLE UI v9 — SEGMENTED / SWITCH / INSPECTOR / STATUS / ORB
   ========================================================= */

/* Sağ paneli tek bir macOS Inspector cam paneline dönüştür */

/* Checkbox'ları gerçek Apple switch görünümüne getir */

/* Dropdown yerine Apple segmented control */

/* Apple Intelligence benzeri empty state - dış kutuya neredeyse tam yayılır */

/* Gradio'nun placeholder kart görünümünü tamamen sök */

/* Retrieval / web / reasoning durumunu Apple status pill'e çevir */

/* Status mesajı normal chatbot balonunun padding'ini iki kere almasın */

/* Gönder tuşu çalışırken spinner hissi */

/* Erişilebilirlik */

/* =========================================================
   APPLE UI v11 - Analitik kartı, hover depth, mouse-follow
   ve gönder butonu durumları
   ========================================================= */

/* Token kartı: tek ana metrik + secondary bilgiler */

/* Kartlarda çok hafif Apple depth */

/* Composer mouse-follow highlight */

/* Send butonunda mouse konumunu takip eden çok hafif ışık */

/* Buton durumları: ready / thinking / streaming */

/* Eski genel disabled spinner kuralını state-aware hale getir */

/* ---------- Tek ekran / viewport düzeni ---------- */

/* =========================================================
   APPLE UI v19 — Native micro-interactions suite
   Top bar · compact PDF · hover tools · collapse inspector
   command palette · context chip · dark mode · toast · scroll
   ========================================================= */

/* ---------- Top status bar ---------- */

/* ---------- Context chip ---------- */

/* ---------- Empty state example prompts ---------- */

/* ---------- Compact PDF card ---------- */

/* ---------- Assistant hover toolbar ---------- */

/* ---------- Streaming fade ---------- */

/* ---------- Inspector collapse ---------- */

/* ---------- Command palette ---------- */

/* ---------- Scroll to bottom ---------- */

/* ---------- Toasts ---------- */

/* ---------- Dynamic ambient background ---------- */

/* ---------- Dark mode ---------- */

/* Existing Gradio message surfaces in dark mode */

/* Mobil düzen ve içeriği saran mesaj balonları. */

/* Kullanıcı balonu: dış kapsayıcılar saydam, tek yüzey gerçek metin alanında. */

/* Gradio'nun medya sorgularındaki otomatik kapsamından bağımsız mobil kök. */

/* Telefon: görünen ekran içinde esneyen sohbet ve her zaman erişilebilir yazma alanı. */

/* Detay seviyesi: yazı alanı olmayan, dokunulabilir üç seçenek. */

/* Mesaj kutusunda salt okunur model ve detay seçim menüleri. */

/* Tek kontrol: yatay detay kaydırıcısı ve başlıktan model seçimi. */

/* Kapalı görünüm yalnızca model, detay ve ok; kaydırıcı tıklanınca açılır. */
""",
'ui.js': """(
        () => {
            if (window.__appleUiV20Installed) return [];
            window.__appleUiV20Installed = true;

            const $ = (sel, root=document) => root.querySelector(sel);
            const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));
            const container = $('.research-app') || document.body;
            
            let lastStatusValue = null;
            let refreshQueued = false;

            const toast = (message, type='ok') => {
                const stack = $('.apple-toast-stack');
                if (!stack) return;
                const el = document.createElement('div');
                el.className = `apple-toast ${type === 'error' ? 'error' : ''}`;
                el.innerHTML = `<span class="apple-toast-icon">${type === 'error' ? '!' : '✓'}</span><span class="apple-toast-text"></span>`;
                $('.apple-toast-text', el).textContent = message;
                stack.appendChild(el);
                setTimeout(() => {
                    el.classList.add('out');
                    setTimeout(() => el.remove(), 240);
                }, 2300);
            };

            const setTextareaValue = (textarea, value) => {
                if (!textarea) return;
                const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
                if (setter) setter.call(textarea, value); else textarea.value = value;
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                textarea.dispatchEvent(new Event('change', { bubbles: true }));
                textarea.focus();
            };

            const getComposerTextarea = () => $('.mesaj-kutusu textarea');
            const getSendButton = () => $('.gonder-butonu button, button.gonder-butonu');

            

            const setAppPhase = (phase) => {
                const normalized = phase === 'complete' ? 'ready' : phase === 'finalizing' ? 'thinking' : phase;
                const previousPhase = document.body.dataset.applePhase || 'ready';

                if (previousPhase !== normalized) {
                    document.body.dataset.applePhase = normalized;
                }

                const bar = $('.apple-topbar');
                if (bar) {
                    if (bar.dataset.phase !== normalized) bar.dataset.phase = normalized;
                    const phaseLabel = $('.apple-topbar-phase', bar);
                    if (phaseLabel) {
                        const nextLabel = normalized === 'thinking' ? 'Düşünüyor' : normalized === 'web' ? 'Web araştırıyor' : normalized === 'streaming' ? 'Yanıtlıyor' : 'Hazır';
                        if (phaseLabel.textContent !== nextLabel) phaseLabel.textContent = nextLabel;
                    }
                }

            };

            const ui = { phase:'ready', request:null, answers:new Map(), cancelled:new Set(), lastBridge:'', lastBusy:false, completeUntil:0, fileName:'', fileSeen:false, telemetryKey:'', processingBox:null, morphed:null };
            const answerSourceKeys=new Map();
            const answerStates=new Map();
            // [D49] Eski cevapların aynı telemetri nesnesini her akış parçasında
            // yeniden JSON'a çevirme. Yeni/geç kaynak kaydı yeni nesneyle denetlenir.
            const answerSignatures=new WeakMap();
            // [D50] Modelin bildirdiği kaynak listesi hazır olduğunda panel açılabilir.
            // Cümle doğrulaması tamamlanmadan satır içi atıf işareti eklenmez.
            const hasAnswerSources=data=>data?.phase==='complete' || (data?.phase==='finalizing' && data.sources_ready===true);
            // [D45] Eski kaynak davranışını koru: aynı cevap ID'sine sonradan
            // gelen atıfları da kabul et. Metin değişmese bile kaynak satırını yenile.
            // Anahtar büyük PDF haritasını içermez; değişmeyen atıflar tekrar çizilmez.
            const rememberAnswer=(index,data)=>{
                if(!Number.isInteger(index) || index<0)return;
                if(!hasAnswerSources(data) && !['cancelled','error'].includes(data?.phase))return;
                // DÜZELTME [D53]: satır önbelleği ve runtime ayrı paketlerle gelebilir.
                // Eski finalizing satırı, yeni complete runtime'ını ezip cümle
                // atıflarını silemez. İptal/hata kaydı da eski satırla diriltilmez.
                const previous=answerStates.get(index);
                if(previous && previous.id===data.id){
                    if(['cancelled','error'].includes(previous.phase) && data.phase!==previous.phase)return;
                    if(previous.phase==='complete' && data.phase==='finalizing')return;
                    if(Number.isFinite(previous.elapsed_ms) && Number.isFinite(data.elapsed_ms) && data.elapsed_ms<previous.elapsed_ms)return;
                }
                answerStates.set(index,data);
                if(data?.phase==='cancelled' || data?.phase==='error'){
                    if(ui.answers.get(index)?.id===data.id){
                        ui.answers.delete(index);answerSourceKeys.delete(index);
                        const row=$(`#apple-chat .bot-row[data-assistant-index="${index}"]`);
                        if(row){pendingCitationRows.delete(row);sourceDirtyRows.add(row);}
                        if(sourceSheet?.dataset.requestId===data.id)closeSources();
                    }
                    return;
                }
                if(!hasAnswerSources(data))return;
                let key=answerSignatures.get(data);
                if(key===undefined){key=JSON.stringify([data.id,data.phase,data.sources_ready,data.sources,data.sentence_citations,data.source_kind,
                    data.pdf_name,data.web_used,data.web_calls,data.document?.id,data.citation_diagnostics]);answerSignatures.set(data,key);}
                if(ui.answers.has(index) && answerSourceKeys.get(index)===key)return;
                answerSourceKeys.set(index,key);ui.answers.set(index,data);
                const row=$(`#apple-chat .bot-row[data-assistant-index="${index}"]`);
                if(row)sourceDirtyRows.add(row);
            };
            const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
            const isBusyPhase = phase => ['sending','indexing','retrieval','thinking','web','streaming','finalizing'].includes(phase);
            const phaseNames = {ready:'Hazır',sending:'Gönderiliyor',indexing:'PDF işleniyor',retrieval:'PDF inceleniyor',thinking:'Düşünüyor',web:'Web araştırıyor',streaming:'Yanıtlıyor',finalizing:'Kaynak işaretleri hazırlanıyor',complete:'Tamamlandı',error:'Hata',cancelled:'Durduruldu'};
            const putText = (el, value) => { if (el && el.textContent !== String(value)) el.textContent = String(value); };
            const putData = (el, key, value) => { if (el && el.dataset[key] !== String(value)) el.dataset[key] = String(value); };
            const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
            const safeUrl = value => { try { const url=new URL(value); return ['http:','https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; } catch (_) { return null; } };
            const setUiPhase = phase => {
                if (ui.phase !== phase && phase === 'complete') ui.completeUntil = performance.now() + 700;
                ui.phase = phase;
                setAppPhase(phase === 'cancelled' ? 'ready' : phase);
                const label = $('.apple-topbar-phase');
                putText(label, phase === 'complete' ? 'Hazır' : phaseNames[phase] || 'Hazır');
            };
            const acceptRuntime = raw => {
                let data;
                try { data = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (_) { return; }
                if (data?.reset_id) {
                    if (documentUi.lastResetId !== data.reset_id) {
                        documentUi.lastResetId=data.reset_id;
                        if(documentUi.reset) documentUi.reset.acknowledged=true;
                        scheduleRefresh();
                    }
                    return;
                }
                if (!data || !data.phase) return;
                if (ui.cancelled.has(data.id) && data.phase !== 'cancelled') return;
                if (data.id === ui.request?.id && data.phase !== 'cancelled' && data.elapsed_ms < ui.request.elapsed_ms) return;
                if (data.id && data.id !== ui.request?.id) { ui.processingBox=null; ui.morphed=null; }
                ui.request = data;
                setUiPhase(data.phase);
                if (data.phase === 'retrieval' && data.retrieval_stage) {
                    const retrievalLabels = {
                        loading: 'Model hazırlanıyor',
                        queue: 'Arama hazırlanıyor',
                        embedding: 'PDF aranıyor'
                    };
                    putText($('.apple-topbar-phase'), retrievalLabels[data.retrieval_stage] || 'PDF inceleniyor');
                }
                if (data.id) rememberAnswer(data.assistant_index,data);
                scheduleRefresh();
            };
            const readRuntimeBridge = () => {
                readPhotoBridge();
                const raw = $('#apple-runtime-state textarea')?.value || '';
                if (raw && raw !== ui.lastBridge) { ui.lastBridge=raw; acceptRuntime(raw); }
                syncSendStates();
                updateComposerMaterial();
            };
            const shapePoints = {
                ready:[6,11,12,5,18,11,12,5,12,12,12,19],
                thinking:[5,12,5,5,12,5,19,12,19,19,12,19],
                streaming:[7,7,17,7,17,17,17,17,7,17,7,7],
                complete:[5,12,10,17,19,7,19,7,19,7,19,7]
            };
            let currentPoints=shapePoints.ready.slice(), currentShape='', shapeFrame=0;
            const morphShape = shape => {
                const svg=$('#apple-send-shape'), path=$('path',svg || document);
                if (!svg || !path || currentShape === shape) return;
                currentShape=shape;
                putData(svg,'shape',shape);
                const from=currentPoints.slice(), to=shapePoints[shape] || shapePoints.ready;
                cancelAnimationFrame(shapeFrame);
                const started=performance.now(), duration=reducedMotion.matches ? 0 : 270;
                const frame = now => {
                    const t=duration ? Math.min(1,(now-started)/duration) : 1, k=1-Math.pow(1-t,3);
                    currentPoints=from.map((v,i)=>v+(to[i]-v)*k);
                    const p=currentPoints.map(v=>v.toFixed(2));
                    path.setAttribute('d',`M${p[0]} ${p[1]} L${p[2]} ${p[3]} L${p[4]} ${p[5]} M${p[6]} ${p[7]} L${p[8]} ${p[9]} L${p[10]} ${p[11]}`);
                    if (t<1) shapeFrame=requestAnimationFrame(frame);
                };
                shapeFrame=requestAnimationFrame(frame);
            };
            const syncSendStates = () => {
                const button=getSendButton();
                if (!button) return;
                const busy=button.disabled;
                const blocked=busy || documentUi.pending || Boolean(documentUi.reset) || photoUi.pending || Boolean(photoUi.file && !photoUi.ready);
                if(button.getAttribute('aria-disabled') !== String(blocked)) button.setAttribute('aria-disabled',String(blocked));
                if (busy && !ui.lastBusy && !isBusyPhase(ui.phase)) {
                    ui.request=null;
                    setUiPhase(documentUi.pending ? 'indexing' : 'retrieval');
                }
                ui.lastBusy=busy;
                // Disabled gönder butonu tek başına "thinking" anlamına gelmez. Restore/indexleme
                // sırasında bu eski çıkarım uygulamayı açılır açılmaz sahte "Düşünüyor" durumuna sokuyordu.
                if (!ui.request && busy && !documentUi.pending && ui.phase === 'ready') setUiPhase('retrieval');
                if (!busy && isBusyPhase(ui.phase) && !ui.request) setUiPhase('ready');
                if (ui.phase === 'complete' && performance.now() > ui.completeUntil) setUiPhase('ready');
                putData($('#apple-composer'),'busy',busy && isBusyPhase(ui.phase));
                putData(button,'appleState',isBusyPhase(ui.phase) ? (ui.phase === 'streaming' ? 'streaming' : 'thinking') : 'ready');
                if (button.getAttribute('aria-label') !== 'Mesajı gönder') button.setAttribute('aria-label','Mesajı gönder');
                const stop=$('#apple-stop');
                if (stop && stop.getAttribute('aria-label') !== 'Yanıtı durdur') stop.setAttribute('aria-label','Yanıtı durdur');
                morphShape(ui.phase === 'streaming' ? 'streaming' : isBusyPhase(ui.phase) ? 'thinking' : ui.phase === 'complete' ? 'complete' : 'ready');
            };
            const updateComposerMaterial = () => {
                const composer=$('#apple-composer'), input=getComposerTextarea();
                if (!composer) return;
                const writing=Boolean(input?.value.trim());
                putData(composer,'writing',writing);
                putData(composer,'composing',writing && document.activeElement===input);
                putData(composer,'phase',ui.phase);
                let state=$('.ai-composer-state',composer);
                if(!state) {
                    state=document.createElement('span');state.className='ai-composer-state';
                    state.setAttribute('role','status');state.setAttribute('aria-live','polite');state.setAttribute('aria-atomic','true');
                    composer.append(state);
                }
                const stateText=isBusyPhase(ui.phase) ? phaseNames[ui.phase] : ui.phase==='error' ? 'Tekrar deneyebilirsiniz' : '';
                putText(state,stateText);
                putData(state,'visible',Boolean(stateText));
                // [D41] Ayarlar panelindeki aktif PDF'yi yeni seçilmiş ek sanma.
                // ui.fileName yalnız bridge'in doğruladığı PDF değişiminden gelir.
                const card=$('#apple-composer-attachment');
                const hasAttachment=Boolean(ui.fileName || photoUi.file);
                putData(composer,'hasFile',hasAttachment);
                const slot=$('#apple-attachment-slot');
                if(slot && slot.getAttribute('aria-hidden')!==String(!hasAttachment)) slot.setAttribute('aria-hidden',String(!hasAttachment));
                if(card && card.hidden!==!ui.fileName)card.hidden=!ui.fileName;
                renderPhotoPreview();
                if (card && ui.fileName) {
                    card.hidden=false;
                    putText($('strong',card),ui.fileName);
                    const status=$('.apple-status textarea')?.value || '';
                    const label=/❌|güncellenemedi/i.test(status) ? 'Güncellenemedi' : /✅ Veritabanı başarıyla/.test(status) ? 'Arama bağlamı güncellendi' : /update ediliyor/i.test(status) ? 'Belge işleniyor…' : 'Belge seçildi';
                    putText($('small',card),label);
                }
            };

            const morphFromComposer = panel => liquidMorph($('#apple-settings-trigger'),panel,{duration:360});
            const liquidMotions=new Map();
            const liquidRect=element=>element?.isConnected ? element.getBoundingClientRect() : null;
            const liquidMorph=(origin,target,{closing=false,duration=460,identity=null,done=()=>{}}={})=>{
                const previous=liquidMotions.get(target);
                const from=previous?.rect() || liquidRect(closing ? target : origin);
                const to=liquidRect(closing ? origin : target);
                previous?.cancel();
                if(!from?.width || !to?.width || !target || reducedMotion.matches) {done();return;}
                const surface=document.createElement('div');surface.className='ai-liquid-surface';surface.setAttribute('aria-hidden','true');
                target.dataset.liquidActive='true';
                const width=Math.max(from.width,to.width),height=Math.max(from.height,to.height);
                Object.assign(surface.style,{width:width+'px',height:height+'px'});document.body.append(surface);
                const bounds=liquidRect(target),ease=t=>1-Math.pow(1-t,4),mix=(a,b,t)=>a+(b-a)*t;
                const geometry=t=>({left:mix(from.left,to.left,t),top:mix(from.top,to.top,t),width:mix(from.width,to.width,t),height:mix(from.height,to.height,t)});
                const surfaceFrames=[],contentFrames=[];
                for(let frame=0;frame<=60;frame++) {
                    const time=frame/60,p=ease(time),box=geometry(p);
                    surfaceFrames.push({offset:time,transform:`translate3d(${box.left}px,${box.top}px,0)`,clipPath:inspectorOutline(box.width,box.height,p),opacity:closing ? Math.min(1,time*7)*(1-Math.max(0,(time-.86)/.14)) : 1-Math.max(0,(time-.28)/.72)});
                    const top=Math.min(bounds.height,Math.max(0,box.top-bounds.top));
                    const left=Math.min(bounds.width,Math.max(0,box.left-bounds.left));
                    const right=Math.max(0,Math.min(bounds.width-left,bounds.right-box.left-box.width));
                    const bottom=Math.max(0,Math.min(bounds.height-top,bounds.bottom-box.top-box.height));
                    contentFrames.push({offset:time,clipPath:`inset(${top}px ${right}px ${bottom}px ${left}px round ${mix(closing?24:14,closing?14:24,p)}px)`});
                }
                const animation=surface.animate(surfaceFrames,{duration,easing:'linear',fill:'both'});
                const content=target.animate(contentFrames,{duration,easing:'linear',fill:'both'});
                let identityLabel=null,identityMotion=null;
                const identityBox=liquidRect(identity?.element);
                if(identityBox?.width && identity.text) {
                    identityLabel=document.createElement('span');identityLabel.className='ai-liquid-identity';identityLabel.textContent=identity.text;identityLabel.setAttribute('aria-hidden','true');
                    identityLabel.style.maxWidth=Math.min(280,identityBox.width)+'px';document.body.append(identityLabel);
                    const start=closing ? identityBox : from,end=closing ? to : identityBox;
                    identityMotion=identityLabel.animate([{transform:`translate3d(${start.left}px,${start.top+start.height/2-7}px,0)`,opacity:0},{offset:.14,opacity:.85},{offset:.8,opacity:.85},{transform:`translate3d(${end.left}px,${end.top+end.height/2-7}px,0)`,opacity:0}],{duration,easing:'cubic-bezier(.16,1,.3,1)',fill:'both'});
                }
                let stopped=false;
                const motion={rect:()=>geometry(ease(Math.min(1,Number(animation.currentTime || 0)/duration))),cancel:()=>{stopped=true;animation.cancel();content.cancel();identityMotion?.cancel();identityLabel?.remove();surface.remove();delete target.dataset.liquidActive;liquidMotions.delete(target);}};
                liquidMotions.set(target,motion);
                animation.finished.then(()=>{if(stopped)return;motion.cancel();done();},()=>{});
            };
            const settleLiquid=()=>{for(const motion of [...liquidMotions.values()])motion.cancel();};
            window.addEventListener('resize',()=>{
                settleLiquid();
                if(sourceSheet?.dataset.closing==='true')finishSourcesClose();
                else if(sourceSheet?.open) {
                    const mobile=window.matchMedia('(max-width:900px)').matches;
                    sourceSheet.dataset.phone=String(mobile);
                    if(sourceSheet.getAttribute('aria-modal')!==String(mobile)) {
                        sourceSheet.close();if(mobile)sourceSheet.showModal();else sourceSheet.show();sourceSheet.setAttribute('aria-modal',String(mobile));
                    }
                    setSpatialAnswer(sourceOrigin);
                }
            },{passive:true});
            reducedMotion.addEventListener('change',()=>{settleLiquid();if(sourceSheet)sourceSheet.dataset.reducedMotion=String(reducedMotion.matches);if(ingestionCard)ingestionCard.dataset.reducedMotion=String(reducedMotion.matches);if(sourceSheet?.dataset.closing==='true')finishSourcesClose();});

            const streamingSurfaces=new WeakMap();
            const morphAnswer = () => {
                const row=$$('#apple-chat .bot-row').at(-1),message=row && $('[data-testid="bot"]',row);
                if(!message) {ui.processingBox=null;return;}
                const key=ui.request?.id || String($$('#apple-chat .bot-row').length);
                if($('.apple-processing-status',message)) {
                    if(!streamingSurfaces.has(message)) {
                        const box=message.getBoundingClientRect();
                        streamingSurfaces.set(message,{key,height:Math.max(112,box.height)});
                        message.style.setProperty('--ai-stream-floor',Math.max(112,box.height)+'px');
                        message.classList.add('ai-stream-surface');
                    }
                    ui.processingBox=message.getBoundingClientRect();return;
                }
                if(!ui.processingBox || ui.morphed===key || !message.textContent.trim())return;
                ui.morphed=key;
                const from=ui.processingBox;ui.processingBox=null;
                message.classList.add('ai-stream-surface');message.style.setProperty('--ai-stream-floor',Math.max(112,from.height)+'px');
                if(reducedMotion.matches)return;
                const text=$('p',message);
                liquidMorph({isConnected:true,getBoundingClientRect:()=>from},message,{duration:360});
                if(text) text.animate([{clipPath:'inset(0 0 100% 0 round 10px)',transform:'translateY(3px)'},{clipPath:'inset(0 round 0)',transform:'none'}],{duration:320,easing:'cubic-bezier(.2,.8,.2,1)'});
            };

            let emptyIntro=null;
            const quietEmpty=()=>{
                const empty=$('#apple-chat .apple-empty-state');
                emptyIntro?.forEach(animation=>animation.cancel());emptyIntro=null;
                if(empty) empty.dataset.typing=String(Boolean(getComposerTextarea()?.value.trim()));
            };
            const enterEmpty=empty=>{
                quietEmpty();
                if(reducedMotion.matches || !empty || getComposerTextarea()?.value.trim())return;
                const orb=$('.apple-intelligence-orb',empty),heading=$('.apple-empty-heading',empty),prompts=$('.apple-example-prompts',empty);
                emptyIntro=[orb?.animate([{transform:'translateY(15px) scale(1.09)'},{transform:'translateY(0) scale(1)'}],{duration:850,easing:'cubic-bezier(.16,1,.3,1)'}),heading?.animate([{clipPath:'inset(0 0 100% 0)',transform:'translateY(10px)'},{clipPath:'inset(0)',transform:'none'}],{duration:650,easing:'cubic-bezier(.16,1,.3,1)'}),prompts?.animate([{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:500,delay:130,easing:'ease-out'})].filter(Boolean);
            };
            document.addEventListener('input',event=>{if(event.target===getComposerTextarea())quietEmpty();},true);

            let ingestionCard=null,ingestionId=null,ingestionTimer=null;
            const showIngestion = ingestion=>{
                if(!ingestion)return;
                // [D41] Aktif ek kimliğini genel yükleme ilerlemesinden türetme:
                // başarısız yeni yükleme, korunmuş eski PDF'nin chip'ini bozmamalı.
                clearTimeout(ingestionTimer);
                if(!ingestionCard) {
                    ingestionCard=document.createElement('div');ingestionCard.id='ai-ingestion-card';ingestionCard.setAttribute('role','status');ingestionCard.setAttribute('aria-live','polite');
                    ingestionCard.innerHTML='<div class="ai-ingestion-pages" aria-hidden="true"></div><div class="ai-ingestion-copy"><strong></strong><small></small><span></span></div>';
                    document.body.append(ingestionCard);
                }
                const fresh=ingestionId!==ingestion.id;ingestionId=ingestion.id;
                ingestionCard.hidden=false;ingestionCard.dataset.stage=ingestion.stage;
                ingestionCard.dataset.reducedMotion=String(reducedMotion.matches);
                const doc=ingestion.document;
                putText($('strong',ingestionCard),doc?.name || ingestion.name || $('strong',ingestionCard).textContent || 'PDF');
                putText($('small',ingestionCard),doc?.pages ? `${doc.pages} sayfa` : 'Sayfa bilgisi bekleniyor');
                putText($('.ai-ingestion-copy span',ingestionCard),ingestion.message || ({received:'PDF alındı',extracting:'Metin çıkarılıyor',mapping:'Kaynak haritası oluşturuluyor',ready:'Hazır',error:'Belge işlenemedi'})[ingestion.stage] || 'Belge hazırlanıyor');
                const pages=$('.ai-ingestion-pages',ingestionCard);
                if(doc && pages.dataset.documentId!==doc.id) {
                    pages.dataset.documentId=doc.id;
                    pages.replaceChildren(...(doc.thumbnails || []).map(item=>{const img=document.createElement('img');img.src=item.image;img.alt='';return img;}));
                } else if(fresh && !doc) {pages.replaceChildren();delete pages.dataset.documentId;}
                if(fresh)liquidMorph($('#apple-composer-attachment:not([hidden])') || $('.composer-plus') || $('#apple-composer'),ingestionCard,{duration:420});
                if(ingestion.stage==='ready') {
                    const id=ingestionId;
                    ingestionTimer=setTimeout(()=>{if(id!==ingestionId)return;const badge=$('.apple-topbar-pdf');liquidMorph(ingestionCard,badge,{duration:520,identity:{element:badge,text:$('strong',ingestionCard).textContent}});ingestionCard.hidden=true;},650);
                } else if(ingestion.stage==='error') ingestionTimer=setTimeout(()=>{ingestionCard.hidden=true;},4500);
            };
            document.addEventListener('change',event=>{
                if(event.target.matches?.('.apple-upload input[type="file"]') && event.target.files?.[0])showIngestion({id:'local-'+Date.now(),name:event.target.files[0].name,stage:'received'});
            },true);
            document.addEventListener('dragover',event=>{
                if(event.target.closest?.('#apple-composer') && event.dataTransfer?.types.includes('Files'))event.preventDefault();
            });
            document.addEventListener('drop',event=>{
                if(!event.target.closest?.('#apple-composer') || !event.dataTransfer?.files.length)return;
                event.preventDefault();
                if(documentUi.pending || isBusyPhase(ui.phase))return toast('Mevcut işlemin tamamlanmasını bekleyin.','error');
                const file=event.dataTransfer.files[0],input=$('.apple-upload input[type="file"]');
                if(/\\.(jpe?g|png|webp|gif)$/i.test(file.name)){void putPhotoFile(file);return;}
                if(!input || !/\\.pdf$/i.test(file.name))return toast('Lütfen bir PDF dosyası seçin.','error');
                const transfer=new DataTransfer();transfer.items.add(file);input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
            });

            const durationText = value => Number.isFinite(value) ? value < 1000 ? `${Math.round(value)} ms` : `${(value/1000).toFixed(2)} s` : '—';
            const renderRequestError = () => {
                const panel=$('#apple-telemetry');if(!panel)return;
                let note=$('.ai-request-error',panel);
                if(!note){note=document.createElement('p');note.className='ai-request-error ai-source-note';note.setAttribute('role','status');panel.append(note);}
                const data=ui.request,failed=data?.phase==='error';
                if(note.hidden===failed)note.hidden=!failed;
                const parts=failed ? [data.error_message,data.error_type,data.http_status ? 'HTTP '+data.http_status : '',data.incomplete_reason,data.api_error_code,data.total_ms != null ? 'Süre: '+durationText(data.total_ms) : '',data.error_request_id || data.response_id].filter(Boolean) : [];
                putText(note,parts.join(' · '));
            };
            const renderTelemetry = () => {
                const panel=$('#apple-telemetry'), data=ui.request;
                if (!panel || !data?.id) return;
                const key=JSON.stringify([data.id,data.phase,data.embedding_ms,data.faiss_ms,data.first_token_ms,data.total_ms,data.parent_count,data.web_calls,data.tokens,data.retrieval]);
                if (ui.telemetryKey === key) return;
                ui.telemetryKey=key;
                $('.ai-empty-metrics',panel)?.setAttribute('hidden','');
                putData(panel,'live',isBusyPhase(data.phase));
                putText($('.ai-live-badge',panel),phaseNames[data.phase] || 'Hazır');
                const metrics=[['Query embedding',data.embedding_ms,'time'],['FAISS',data.faiss_ms,'time'],['Parent bağlamı',data.parent_count,'count'],['Web çağrısı',data.web_calls,'count'],['İlk token',data.first_token_ms,'time'],['Toplam',data.total_ms,'time']];
                $('.ai-timeline',panel).innerHTML=metrics.map(([label,value,type])=>`<div class="ai-metric" data-pending="${value == null}"><span>${label}</span><strong>${type==='time' ? durationText(value) : value == null ? '—' : escapeHtml(value)}</strong></div>`).join('');
                const retrieval=data.retrieval || [];
                $('.ai-retrieval',panel).innerHTML=retrieval.length ? '<h4>Retrieval · Kosinüs benzerliği (−1 → 1)</h4>'+retrieval.map(item=>{
                    const score=Number(item.score), width=Number.isFinite(score) ? Math.max(0,Math.min(100,(score+1)*50)) : 0;
                    return `<div class="ai-score-row"><span>Parent ${escapeHtml(item.parent)}</span><span class="ai-score-track"><i style="width:${width}%"></i></span><b>${Number.isFinite(score) ? score.toFixed(3) : '—'}</b></div>`;
                }).join('') : '';
                const tokens=data.tokens;
                if (!tokens) { $('.ai-token-breakdown',panel).innerHTML='<h4>Token dağılımı</h4><span class="ai-source-note">'+(isBusyPhase(data.phase) ? 'API kullanım verisi bekleniyor.' : 'API kullanım verisi iletilmedi.')+'</span>'; return; }
                const reasoning=tokens.reasoning, visible=reasoning == null ? tokens.output : Math.max(0,tokens.output-reasoning);
                const segments=[tokens.input,reasoning || 0,visible], total=Math.max(1,segments.reduce((a,b)=>a+b,0));
                $('.ai-token-breakdown',panel).innerHTML='<h4>Token dağılımı</h4><div class="ai-token-strip">'+segments.map(n=>`<i style="flex-basis:${n/total*100}%"></i>`).join('')+'</div><div class="ai-token-legend">'+[['Girdi',tokens.input],['Reasoning',reasoning],[reasoning == null ? 'Çıktı' : 'Görünür çıktı',visible],['Cache · girdiye dahil',tokens.cached]].map(([label,value])=>`<span>${label} <b>${value == null ? '—' : escapeHtml(value)}</b></span>`).join('')+'</div>';
            };
            const citationRecords=new WeakMap();
            const citationText = element => {
                const nodes=[];let text='';
                // Satır içi code alanları belge değeridir; yalnızca pre içindeki gerçek kod blokları dışarıda kalır.
                const walker=document.createTreeWalker(element,NodeFilter.SHOW_TEXT,{acceptNode:node=>node.parentElement?.closest('button,pre,script,style,.ai-inline-citation') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT});
                while(walker.nextNode()) {const node=walker.currentNode;nodes.push({node,start:text.length,end:text.length+node.length});text+=node.data;}
                return {text,nodes};
            };
            const citationRange = (block,start,end) => {
                const {nodes}=citationText(block);
                const first=nodes.find(item=>item.end>start),last=[...nodes].reverse().find(item=>item.start<end);
                if(!first || !last) return null;
                const range=document.createRange();
                range.setStart(first.node,Math.max(0,start-first.start));range.setEnd(last.node,Math.min(last.node.length,end-last.start));
                return range;
            };
            let activeSentenceCitationControl=null;
            let suppressCitationFocusOnce=false;
            let sourceOriginKeyboard=false;
            const clearSentenceHighlight = () => {
                if(window.CSS?.highlights) CSS.highlights.delete('ai-citation-sentence');
                activeSentenceCitationControl=null;
            };
            const clearPassageHighlight = () => {
                if(window.CSS?.highlights) CSS.highlights.delete('ai-citation-passage');
            };
            const clearCitationHighlight = () => {
                clearSentenceHighlight();
                clearPassageHighlight();
            };
            const highlightCitation = (control,block,start,end) => {
                if(window.CSS?.highlights) CSS.highlights.delete('ai-citation-sentence');
                activeSentenceCitationControl=control || null;
                if(!window.CSS?.highlights || typeof Highlight==='undefined') return;
                const range=citationRange(block,start,end);
                if(range) CSS.highlights.set('ai-citation-sentence',new Highlight(range));
            };
            const citationSourceKey = source => source.kind==='pdf' ? `pdf:${source.parent_id}` : `web:${safeUrl(source.url) || ''}`;
            // [D28] Aynı cümle ayırıcıyı yeniden kullan; her atıf için tekrar oluşturma.
            const sentenceSegmenter = typeof Intl.Segmenter==='function' ? new Intl.Segmenter(undefined,{granularity:'sentence'}) : null;
            const citationSentences = text => {
                if(sentenceSegmenter) return [...sentenceSegmenter.segment(text)].map(item=>({start:item.index,end:item.index+item.segment.length,text:item.segment}));
                return [...text.matchAll(/[^.!?\\n]+[.!?]*[”"’']*\\s*/gu)].map(item=>({start:item.index,end:item.index+item[0].length,text:item[0]}));
            };
            // [D28] Aynı paragraf/cevap birçok atıfta tekrar aranır. Sadece atıf kurma işlemi sırasında
            // en fazla 100.000 giriş karakterinin normalizasyonu tutulur ve finally ile bırakılır.
            // UTF-16 konum haritası korunur; Türkçe/emoji metninde düğme yanlış karaktere bağlanmaz.
            let normalizationCache=null,normalizationChars=0;
            const normalizedCitationMap = text => {
                const input=String(text || '');
                if(normalizationCache?.has(input))return normalizationCache.get(input);
                let value='';
                const map=[];
                let lastWasSpace=false;
                for(let i=0;i<input.length;) {
                    const hyphenBreak=input[i]==='-' ? input.slice(i).match(/^-\\s*\\r?\\n\\s*(?=[\\p{L}])/u) : null;
                    if(hyphenBreak && value && /[\\p{L}]/u.test(value.slice(-1))) {
                        i+=hyphenBreak[0].length;
                        continue;
                    }
                    const cp=input.codePointAt(i);
                    const ch=String.fromCodePoint(cp);
                    const width=ch.length;
                    if(ch==='\\u00ad') {i+=width;continue;}
                    const normalized=ch.normalize('NFKD').toLowerCase().replace(/i\\u0307/g,'i').replace(/ı/g,'i');
                    for(const out of normalized) {
                        if(/\\s/u.test(out)) {
                            if(!lastWasSpace && value.length) {
                                value+=' ';
                                map.push({start:i,end:i+width});
                                lastWasSpace=true;
                            }
                        } else {
                            value+=out;
                            for(let unit=0;unit<out.length;unit++) map.push({start:i,end:i+width});
                            lastWasSpace=false;
                        }
                    }
                    i+=width;
                }
                while(value.endsWith(' ')) {value=value.slice(0,-1);map.pop();}
                const result={value,map};
                if(normalizationCache && normalizationChars+input.length<=100000){normalizationCache.set(input,result);normalizationChars+=input.length;}
                return result;
            };
            const normalizedCitation = text => normalizedCitationMap(text).value.trim();
            const locateCitationQuote = (text,quote) => {
                const original=String(text || ''),rawQuote=String(quote || '');
                const exact=original.indexOf(rawQuote);
                if(exact>=0) return {start:exact,end:exact+rawQuote.length};
                const haystack=normalizedCitationMap(original),needle=normalizedCitation(rawQuote);
                if(!needle) return null;
                const normalizedStart=haystack.value.indexOf(needle);
                if(normalizedStart<0) return null;
                const first=haystack.map[normalizedStart],last=haystack.map[normalizedStart+needle.length-1];
                if(!first || !last) return null;
                return {start:first.start,end:last.end};
            };
            const clearSentenceCitations = message => {
                const record=message && citationRecords.get(message);
                if(!record) return;
                const activeBelongsToRecord=Boolean(activeSentenceCitationControl && record.controls.includes(activeSentenceCitationControl));
                record.abort.abort();record.cleanup.forEach(dispose=>dispose());citationRecords.delete(message);
                if(activeBelongsToRecord) clearSentenceHighlight();
            };
            const focusSourceCard = (key,quote='',location=null) => {
                const body=$('.ai-sheet-body',sourceSheet);
                const card=$$('[data-source-key]',body || document).find(element=>element.dataset.sourceKey===key);
                if(!body || !card) return;
                card.dataset.sourceActive='true';
                if(card.tagName==='DETAILS') card.open=true;
                let target=card;
                clearPassageHighlight();
                if(quote) {
                    for(const paragraph of $$('.ai-source-passage p',card)) {
                        if(location?.page && paragraph.closest('section')?.dataset.page!==String(location.page))continue;
                        const snapshot=citationText(paragraph);
                        const scope=location?.context ? locateCitationQuote(snapshot.text,location.context) : {start:0,end:snapshot.text.length};
                        if(!scope)continue;
                        const match=locateCitationQuote(snapshot.text.slice(scope.start,scope.end),quote);
                        if(!match)continue;
                        const rangeLocation={start:scope.start+match.start,end:scope.start+match.end};
                        target=paragraph.closest('section') || card;
                        if(window.CSS?.highlights && typeof Highlight!=='undefined') {
                            const range=citationRange(paragraph,rangeLocation.start,rangeLocation.end);
                            if(range) CSS.highlights.set('ai-citation-passage',new Highlight(range));
                        }
                        break;
                    }
                }
                const top=target.getBoundingClientRect().top-body.getBoundingClientRect().top+body.scrollTop-16;
                body.scrollTo({top:Math.max(0,top),behavior:reducedMotion.matches ? 'instant' : 'smooth'});
                const focus=$('summary',card) || card;
                focus.focus({preventScroll:true});
            };
            const sourceCoverage=new Map();
            const renderSourceCoverage=()=>{
                const panel=$('#apple-telemetry');if(!panel)return;
                let card=$('#apple-source-coverage');
                if(!card){
                    card=document.createElement('section');card.id='apple-source-coverage';card.setAttribute('aria-label','Kaynak kapsaması');
                    card.innerHTML='<h4>Kaynak kapsaması</h4><strong role="status" aria-live="polite"></strong><progress hidden aria-label="Kaynakla eşleşen cümleler"></progress><small>Paragraf, liste ve tablo cümlelerindeki atıf eşleşmeleri sayılır; kod ve başlıklar hariçtir. Bu bir doğruluk veya güven skoru değildir.</small>';
                    panel.append(card);
                }
                const data=ui.request,coverage=data?.phase==='complete' ? sourceCoverage.get(data.id) : null;
                let diagnostic=$('.ai-citation-diagnostic',card);
                if(!diagnostic){diagnostic=document.createElement('p');diagnostic.className='ai-citation-diagnostic ai-source-note';card.append(diagnostic);}
                const report=data?.citation_diagnostics;
                diagnostic.hidden=!(data?.phase==='complete' && report && (data.sources || []).some(source=>source.kind==='pdf' && source.role==='cited'));
                const reasons={parent_not_cited:'kullanılmayan parent',answer_anchor_missing:'cevap metni eşleşmedi',answer_anchor_ambiguous:'cevapta tekrar eden ifade',table_row_not_unique:'tablo satırı belirsiz',table_identity_mismatch:'tablo kimliği uyuşmadı',field_value_mismatch:'alan/değer uyuşmadı',quote_location_unresolved:'alıntı konumu belirsiz',value_or_condition_conflict:'değer/koşul uyuşmadı',subclaim_value_conflict:'alt iddia uyuşmadı',document_unavailable:'belge kullanılamıyor',document_changed:'belge değişti'};
                putText(diagnostic,report ? `Atıf kaydı: ${report.received} · Bağlanan: ${report.linked}${report.exact ? ' · Doğrudan eşleşme: '+report.exact : ''}${!report.metadata_present ? ' · Model cümle kaynak kaydı döndürmedi' : ''}${Object.keys(report.rejected || {}).length ? ' · '+Object.entries(report.rejected).map(([reason,count])=>`${reasons[reason] || 'geçersiz kayıt'}: ${count}`).join(' · ') : ''}` : '');
                const label=coverage ? coverage.total ? `${coverage.total} cümlenin ${coverage.covered}'si kaynağa bağlı` : 'Ölçülebilecek cümle bulunamadı.' : ['complete','finalizing'].includes(data?.phase) ? 'Cümle eşleşmeleri hazırlanıyor…' : isBusyPhase(data?.phase) ? 'Yanıt tamamlanınca hesaplanır.' : data?.phase==='cancelled' || data?.phase==='error' ? 'Tamamlanmayan yanıtta kapsama hesaplanmadı.' : 'Henüz tamamlanmış yanıt yok.';
                putText($('strong',card),label);
                putData(card,'requestId',data?.id || '');putData(card,'total',coverage?.total ?? '');putData(card,'covered',coverage?.covered ?? '');
                const meter=$('progress',card),hidden=!coverage?.total;
                if(meter.hidden!==hidden)meter.hidden=hidden;
                if(coverage?.total){if(meter.max!==coverage.total)meter.max=coverage.total;if(meter.value!==coverage.covered)meter.value=coverage.covered;}
            };

            const installSentenceCitations = (message,data) => {
                if(!message || data.phase!=='complete') return;
                const current=citationRecords.get(message);
                if(current?.data===data && current.text===citationText(message).text && current.controls.every(control=>message.contains(control))) return;
                clearSentenceCitations(message);
                normalizationCache=new Map();normalizationChars=0;
                try {
                const record={data,abort:new AbortController(),cleanup:[],controls:[],units:[]};
                const signal=record.abort.signal;
                const sources=(data.sources || []).filter(source=>source.kind==='web' ? Boolean(safeUrl(source.url)) : source.kind==='pdf' && source.role==='cited' && data.source_kind!=='retrieved' && Number.isInteger(source.parent_id));
                const bind=(control,block,start,end,source,quote='',location=null)=>{
                    for(const unit of record.units){
                        const sameRow=location?.table_row && unit.block.closest('tr')===block.closest('tr');
                        if(sameRow || (unit.block===block && unit.start<end && unit.end>start))unit.sources.add(citationSourceKey(source));
                    }
                    const showHighlight=()=>{
                        const row=location?.table_row ? block.closest('tr') : null;
                        if(row)highlightCitation(control,row,0,citationText(row).text.length);
                        else {
                            const part=location?.supports ? locateCitationQuote(citationText(block).text.slice(start,end),location.supports) : null;
                            highlightCitation(control,block,part ? start+part.start : start,part ? start+part.end : end);
                        }
                    };
                    control.addEventListener('pointerenter',showHighlight,{signal});
                    control.addEventListener('pointerleave',()=>{if(document.activeElement!==control && activeSentenceCitationControl===control) clearSentenceHighlight();},{signal});
                    control.addEventListener('focus',()=>{if(suppressCitationFocusOnce){suppressCitationFocusOnce=false;return;}showHighlight();},{signal});
                    control.addEventListener('blur',()=>{if(!sourceSheet?.open && activeSentenceCitationControl===control) clearSentenceHighlight();},{signal});
                    control.addEventListener('click',event=>{
                        if(event.button!==0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
                        event.preventDefault();
                        sourceOriginKeyboard=event.detail===0;
                        showHighlight();
                        openSources(data,control,{key:citationSourceKey(source),quote,location});
                    },{signal});
                    record.controls.push(control);
                };
                const paragraphs=$$('p,li,td,blockquote',message).filter(block=>!block.closest('pre,code') && !block.querySelector('p,li,td,blockquote'));
                const pdfs=sources.filter(source=>source.kind==='pdf');
                const semanticCitations=Array.isArray(data.sentence_citations) ? data.sentence_citations : [];
                const snapshots=new Map(paragraphs.map(block=>[block,citationText(block)])),whole=citationText(message),anchored=new Map();
                const locateAll=(text,needle)=>{
                    const hay=normalizedCitationMap(text),key=normalizedCitation(needle),result=[];
                    if(!key)return result;
                    let offset=0;
                    while((offset=hay.value.indexOf(key,offset))>=0){
                        const first=hay.map[offset],last=hay.map[offset+key.length-1];
                        if(first && last)result.push({start:first.start,end:last.end});
                        offset+=Math.max(1,key.length);
                    }
                    return result;
                };
                for(const item of semanticCitations){
                    if(item?.verified!==true || !['citation-v1','citation-v2'].includes(item.engine))continue;
                    const source=pdfs.find(source=>source.parent_id===item.parent_id);if(!source)continue;
                    const candidates=[],globalRanges=locateAll(whole.text,item.answer || '');
                    for(const block of paragraphs){
                        const snapshot=snapshots.get(block);
                        if(item.table_row){
                            const cells=block.closest('tr')?.querySelectorAll('td');
                            if(block.tagName!=='TD' || !cells || cells[cells.length-1]!==block || cells.length!==item.table_row.length)continue;
                            if(![...cells].every((cell,index)=>normalizedCitation(citationText(cell).text)===normalizedCitation(item.table_row[index])))continue;
                            if(normalizedCitation(snapshot.text)!==normalizedCitation(item.answer))continue;
                            candidates.push({block,start:0,end:snapshot.text.trimEnd().length,ordinal:1});continue;
                        }
                        const sentences=citationSentences(snapshot.text);
                        for(const range of locateAll(snapshot.text,item.answer || '')){
                            const begins=sentences.some(sentence=>sentence.start<=range.start && !snapshot.text.slice(sentence.start,range.start).trim());
                            const ends=sentences.some(sentence=>range.end<=sentence.end && /^[\\s.!?…'"”’]*$/u.test(snapshot.text.slice(range.end,sentence.end)));
                            if(!begins || !ends)continue;
                            const node=snapshot.nodes.find(node=>node.end>range.start),globalNode=node && whole.nodes.find(item=>item.node===node.node);
                            const start=globalNode ? globalNode.start+range.start-node.start : -1;
                            const ordinal=globalRanges.findIndex(item=>item.start===start)+1;
                            candidates.push({block,...range,ordinal});
                        }
                    }
                    const chosen=Number.isInteger(item.occurrence) ? candidates.filter(candidate=>candidate.ordinal===item.occurrence) : candidates;
                    if(chosen.length!==1 || (!item.table_row && !item.occurrence && globalRanges.length!==1))continue;
                    const target=chosen[0],list=anchored.get(target.block) || [];
                    if(!list.some(match=>match.sentence.start===target.start && match.source.parent_id===item.parent_id && match.quote===item.quote && match.location.page===item.page && match.location.supports===item.supports)){
                        list.push({sentence:{start:target.start,end:target.end,text:snapshots.get(target.block).text.slice(target.start,target.end)},source,quote:String(item.quote || ''),location:item});anchored.set(target.block,list);
                    }
                }
                for(const block of paragraphs) {
                    const snapshot=citationText(block),sentences=citationSentences(snapshot.text);
                    record.units.push(...sentences.filter(sentence=>/[\\p{L}\\p{N}]/u.test(sentence.text)).map(sentence=>({block,start:sentence.start,end:sentence.end,sources:new Set()})));
                    for(const link of $$('a[href]',block)) {
                        const source=sources.find(source=>source.kind==='web' && safeUrl(source.url)===safeUrl(link.href));
                        if(!source) continue;
                        const item=snapshot.nodes.find(item=>link.contains(item.node));
                        const sentence=sentences.find(sentence=>item && sentence.start<=item.start && sentence.end>item.start);
                        if(!sentence) continue;
                        const oldTitle=link.getAttribute('title'),oldPopup=link.getAttribute('aria-haspopup');
                        link.classList.add('ai-linked-citation');link.setAttribute('aria-haspopup','dialog');link.title='Kaynak panelinde aç: '+(source.title || source.domain || 'Web');
                        record.cleanup.push(()=>{link.classList.remove('ai-linked-citation');if(oldTitle===null) link.removeAttribute('title');else link.title=oldTitle;if(oldPopup===null) link.removeAttribute('aria-haspopup');else link.setAttribute('aria-haspopup',oldPopup);});
                        bind(link,block,sentence.start,sentence.end,source);
                    }
                    const matches=(anchored.get(block) || []).sort((a,b)=>a.sentence.start-b.sentence.start || a.sentence.end-b.sentence.end);
                    for(const {sentence,source,quote,location} of matches.reverse()) {
                        const end=sentence.end-(sentence.text.match(/\\s*$/u)?.[0].length || 0);
                        const range=citationRange(block,sentence.start,end);
                        if(!range) continue;
                        const button=document.createElement('button');button.type='button';button.className='ai-inline-citation';button.textContent='▤';
                        const label=`Kaynaklar · Parent ${source.parent_id}${location.page ? ' · Sayfa '+location.page : ''}`;
                        button.setAttribute('aria-label',label);button.setAttribute('aria-haspopup','dialog');button.title=label;
                        button.dataset.sourceKey=citationSourceKey(source);
                        range.collapse(false);
                        // Alan değeri code ile biçimlendirilse de kaynak düğmesi code kutusunun dışında durur.
                        const code=range.startContainer.parentElement?.closest('code');
                        if(code && !code.closest('pre')) {
                            const tail=document.createRange();tail.selectNodeContents(code);tail.setStart(range.startContainer,range.startOffset);
                            if(!tail.toString()){range.setStartAfter(code);range.collapse(true);}
                        }
                        range.insertNode(button);
                        record.cleanup.push(()=>button.remove());bind(button,block,sentence.start,end,source,quote,location);
                    }
                }
                record.text=citationText(message).text;
                citationRecords.set(message,record);
                sourceCoverage.set(data.id,{total:record.units.length,covered:record.units.filter(unit=>unit.sources.size>0).length});
                } finally {normalizationCache=null;normalizationChars=0;}
            };

            let sourceSheet=null, sourceOrigin=null;
            const pdfRequests=new Map();
            // [D30] Yeni sayfa seçimi önceki istemci bekleyişinin yerini alır; eski Promise 25 saniye beklemez.
            // Sunucuda başlamış native PDF işi zorla kesilmez; eski yanıt kimliği ekrana uygulanmaz.
            const cancelPdfRequests=()=>{for(const pending of pdfRequests.values()){clearTimeout(pending.timer);pending.reject(new Error('Sayfa isteği yenilendi.'));}pdfRequests.clear();};
            const requestPdfPage=request=>new Promise((resolve,reject)=>{
                cancelPdfRequests();
                const requestId=crypto.randomUUID?.() || String(Date.now())+'-'+Math.random();
                const timer=setTimeout(()=>{pdfRequests.delete(requestId);reject(new Error('Sayfa yüklenemedi. Yeniden deneyebilirsiniz.'));},25000);
                pdfRequests.set(requestId,{resolve,reject,timer});
                const input=$('#apple-pdf-view-request textarea');
                if(!input){clearTimeout(timer);pdfRequests.delete(requestId);reject(new Error('PDF görüntüleme bağlantısı hazır değil.'));return;}
                const setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value')?.set;
                const value=JSON.stringify({...request,request_id:requestId});
                if(setter)setter.call(input,value);else input.value=value;
                input.dispatchEvent(new Event('input',{bubbles:true}));
                input.dispatchEvent(new Event('change',{bubbles:true}));
                // [D30] İstek JSON’unu şimdi yakala. Gecikmiş callback’in ortak textarea’dan daha yeni
                // sayfanın değerini okuması hızlı geçişlerde yanlış/kaybolan isteğe neden oluyordu.
                window.dispatchEvent(new CustomEvent('apple-pdf-request',{detail:value}));
            });
            window.addEventListener('apple-pdf-page',event=>{
                let result;try{result=JSON.parse(event.detail);}catch(_){return;}
                const pending=pdfRequests.get(result.request_id);if(!pending)return;
                clearTimeout(pending.timer);pdfRequests.delete(result.request_id);
                if(result.error)pending.reject(new Error(result.error));else pending.resolve(result);
            });
            let pdfView=null,pdfRevision=0,sourceClosing=false,spatialRow=null;
            const setSpatialAnswer=origin=>{
                if(spatialRow)spatialRow.classList.remove('ai-answer-spatial');
                spatialRow=origin?.closest('.bot-row') || null;
                if(spatialRow && window.innerWidth>900) {
                    const bounds=spatialRow.getBoundingClientRect(),sheet=sourceSheet.getBoundingClientRect();
                    const width=window.innerWidth>900 ? Math.max(280,sheet.left-bounds.left-22) : bounds.width;
                    spatialRow.style.setProperty('--ai-source-width',width+'px');
                    spatialRow.classList.add('ai-answer-spatial');
                }
                container.classList.toggle('ai-source-open',Boolean(spatialRow));
            };
            const renderPdfPage=async({page=1,parent=null,quote='',context='',autoPage=false,section=null,spans=null}={})=>{
                if(!pdfView || !sourceSheet?.open)return;
                const view=pdfView,revision=++pdfRevision,viewer=$('.ai-pdf-viewer',sourceSheet);
                const status=$('.ai-pdf-status',viewer),canvas=$('canvas',viewer),marks=$('.ai-pdf-highlights',viewer);
                view.spans=Array.isArray(spans) ? spans : [];
                if(view.spans.length){
                    const span=view.spans.find(span=>span.page===page);
                    parent=span ? (view.data.sources || []).find(source=>source.kind==='pdf' && source.parent_id===span.parent_id) || null : null;
                    quote=span?.quote || '';context=span?.context || '';autoPage=false;
                }
                view.page=page;view.parent=parent;view.quote=quote;view.context=context;view.section=section?.id || null;
                viewer.dataset.loading='true';viewer.setAttribute('aria-busy','true');putText(status,'Sayfa yükleniyor…');
                $('.ai-pdf-stage',viewer).hidden=true;marks.replaceChildren();
                try {
                    const result=await requestPdfPage({document_id:view.document.id,page,parent_id:parent?.parent_id,quote,context,auto_page:autoPage});
                    if(revision!==pdfRevision || pdfView!==view || !sourceSheet.open)return;
                    const image=new Image();image.src=result.image;await image.decode();
                    if(revision!==pdfRevision || pdfView!==view || !sourceSheet.open)return;
                    canvas.width=result.width;canvas.height=result.height;canvas.getContext('2d').drawImage(image,0,0);
                    canvas.setAttribute('aria-label',`${view.document.name} · Sayfa ${result.page}`);
                    marks.replaceChildren(...result.rects.map(rect=>{const mark=document.createElement('span');Object.assign(mark.style,{left:rect[0]*100+'%',top:rect[1]*100+'%',width:(rect[2]-rect[0])*100+'%',height:(rect[3]-rect[1])*100+'%'});return mark;}));
                    view.page=result.page;view.y=section?.y ?? (result.rects.length ? Math.min(...result.rects.map(rect=>rect[1])) : 0);putText($('.ai-pdf-page-label',viewer),`${result.page} / ${result.pages}`);
                    $('.ai-pdf-prev',viewer).disabled=result.page<=1;$('.ai-pdf-next',viewer).disabled=result.page>=result.pages;
                    putText(status,result.highlight_kind==='quote' ? 'İlgili alıntı vurgulandı' : result.highlight_kind==='passage' ? 'İlgili PDF pasajı vurgulandı; tam cümle eşleşmesi yok' : quote ? 'Bu atfın kesin konumu doğrulanamadı; yanıltıcı vurgu yapılmadı' : section ? section.title : 'Gerçek PDF sayfası');
                    viewer.dataset.loading='false';viewer.setAttribute('aria-busy','false');$('.ai-pdf-stage',viewer).hidden=false;
                    const scroller=$('.ai-sheet-body',sourceSheet),stage=$('.ai-pdf-stage',viewer),first=marks.firstElementChild;
                    updateDocumentNavigator();
                    const target=first || stage;
                    const sectionOffset=section ? stage.getBoundingClientRect().height * section.y : 0;
                    scroller.scrollTo({top:Math.max(0,target.getBoundingClientRect().top-scroller.getBoundingClientRect().top+scroller.scrollTop+sectionOffset-110),behavior:reducedMotion.matches?'instant':'smooth'});
                } catch(error) {
                    if(revision!==pdfRevision || pdfView!==view)return;
                    putText(status,error.message);viewer.dataset.loading='false';viewer.setAttribute('aria-busy','false');
                }
            };
            const updateDocumentNavigator=()=>{
                const view=pdfView,map=$('.ai-document-map',sourceSheet || document);
                if(!view || !map)return;
                const entries=view.document.outline || [],used=new Set();
                for(const data of [view.data,...ui.answers.values()]){
                    if(data?.document?.id!==view.document.id || !hasAnswerSources(data) || data.source_kind==='retrieved')continue;
                    for(const source of data.sources || []){
                        if(source.kind!=='pdf' || source.role!=='cited' || !Number.isInteger(source.parent_id))continue;
                        for(const id of (view.document.parent_sections || {})[String(source.parent_id)] || [])used.add(id);
                    }
                }
                const position=view.page*2+(view.y || 0);
                const current=view.section || [...entries].reverse().find(entry=>entry.page*2+entry.y<=position && position<entry.end_page*2+entry.end_y)?.id || entries.find(entry=>entry.page===view.page)?.id;
                const key=JSON.stringify([current,[...used].sort()]);if(map.dataset.stateKey===key)return;map.dataset.stateKey=key;
                for(const button of $$('.ai-section-button',map)){
                    const active=button.dataset.sectionId===current;
                    if(button.getAttribute('aria-current')!==String(active))button.setAttribute('aria-current',String(active));
                    putData(button,'used',used.has(button.dataset.sectionId));
                    const section=entries.find(item=>item.id===button.dataset.sectionId);
                    const label=`${section.title} · Sayfa ${section.page}${used.has(section.id) ? ' · Yanıtta kullanılan bölüm' : ''}`;
                    if(button.getAttribute('aria-label')!==label)button.setAttribute('aria-label',label);
                }
            };
            const mountDocumentNavigator=(viewer,data)=>{
                const entries=data.document.outline || [];
                const map=document.createElement('details');map.className='ai-document-map';map.open=!mobileLayout.matches;
                const summary=document.createElement('summary');summary.textContent=`Belge haritası · ${entries.length} bölüm`;map.append(summary);
                const search=document.createElement('input');search.type='search';search.placeholder='Bölüm bul';search.setAttribute('aria-label','Belge bölümlerinde ara');search.hidden=entries.length<9;map.append(search);
                const nav=document.createElement('nav');nav.setAttribute('aria-label','PDF bölümleri');map.append(nav);
                for(const section of entries){
                    const button=document.createElement('button');button.type='button';button.className='ai-section-button';button.dataset.sectionId=section.id;button.style.setProperty('--section-depth',String(Math.max(0,Math.min(2,section.level-1))));
                    const title=document.createElement('span');title.className='ai-section-title';title.textContent=section.title;
                    const meta=document.createElement('span');meta.className='ai-section-meta';
                    const dot=document.createElement('i');dot.className='ai-section-used';dot.setAttribute('aria-hidden','true');meta.append(dot,document.createTextNode('s. '+section.page));button.append(title,meta);nav.append(button);
                    button.addEventListener('click',()=>{microFeedback(button);renderPdfPage({page:section.page,section});});
                }
                const note=document.createElement('p');note.className='ai-document-map-note';
                note.textContent=entries.length ? (entries[0].origin==='bookmark' ? 'PDF yer imleri' : 'PDF metninden çıkarılan başlıklar')+' · Mavi nokta: yanıtta kullanılan bölüm.' : 'Bu PDF’de bölüm başlığı bulunamadı. Sayfa oklarıyla gezinebilirsiniz.';map.append(note);
                search.addEventListener('input',()=>{
                    const query=search.value.trim().toLocaleLowerCase('tr');let count=0;
                    for(const button of $$('.ai-section-button',nav)){button.hidden=!$('.ai-section-title',button).textContent.toLocaleLowerCase('tr').includes(query);if(!button.hidden)count++;}
                    if(!count)note.textContent='Bu aramayla eşleşen bölüm bulunamadı.';
                    else note.textContent=(entries[0]?.origin==='bookmark' ? 'PDF yer imleri' : 'PDF metninden çıkarılan başlıklar')+' · Mavi nokta: yanıtta kullanılan bölüm.';
                });
                $('.ai-pdf-viewer-head',viewer).after(map);updateDocumentNavigator();
            };

            const mountPdfViewer=(data,target)=>{
                const pdfDocument=data.document;
                pdfView=null;pdfRevision++;
                if(!pdfDocument?.id)return false;
                if(target?.key?.startsWith('web:'))return false;
                if(!(data.sources || []).some(source=>source.kind==='pdf' && source.role==='cited') && !String(data.id).startsWith('document-'))return false;
                const body=$('.ai-sheet-body',sourceSheet),viewer=document.createElement('section');
                viewer.className='ai-pdf-viewer';viewer.setAttribute('aria-label','PDF sayfa görünümü');
                viewer.innerHTML='<header class="ai-pdf-viewer-head"><div><small>PDF</small><strong></strong></div><nav aria-label="PDF sayfaları"><button type="button" class="ai-pdf-prev" aria-label="Önceki sayfa">‹</button><span class="ai-pdf-page-label"></span><button type="button" class="ai-pdf-next" aria-label="Sonraki sayfa">›</button></nav></header><p class="ai-pdf-status" role="status"></p><div class="ai-pdf-stage" hidden><canvas role="img"></canvas><div class="ai-pdf-highlights" aria-hidden="true"></div></div>';
                $('strong',viewer).textContent=pdfDocument.name;body.prepend(viewer);
                pdfView={document:pdfDocument,data,page:1,parent:null,quote:'',section:null};
                mountDocumentNavigator(viewer,data);
                $('.ai-pdf-prev',viewer).addEventListener('click',()=>renderPdfPage({page:Math.max(1,pdfView.page-1),parent:pdfView.parent,quote:pdfView.quote,context:pdfView.context,spans:pdfView.spans}));
                $('.ai-pdf-next',viewer).addEventListener('click',()=>renderPdfPage({page:Math.min(pdfDocument.pages,pdfView.page+1),parent:pdfView.parent,quote:pdfView.quote,context:pdfView.context,spans:pdfView.spans}));
                for(const card of $$('details[data-source-key]',body)) {
                    const source=(data.sources || []).find(item=>citationSourceKey(item)===card.dataset.sourceKey);
                    const button=document.createElement('button');button.type='button';button.className='ai-pdf-open-passage';button.textContent='PDF sayfasında göster';
                    button.addEventListener('click',()=>renderPdfPage({page:source.pages?.[0] || 1,parent:source,quote:source.passage || '',autoPage:true}));card.append(button);
                    for(const section of $$('.ai-source-passage section',card)) {
                        const page=source.segments?.[$$('.ai-source-passage section',card).indexOf(section)]?.page;
                        if(!page)continue;
                        const open=document.createElement('button');open.type='button';open.className='ai-pdf-open-passage';open.textContent=`Sayfa ${page} →`;
                        open.addEventListener('click',()=>renderPdfPage({page,parent:source,quote:$('p',section)?.textContent || ''}));section.append(open);
                    }
                }
                const source=(data.sources || []).find(item=>item.kind==='pdf' && item.role==='cited' && (target ? citationSourceKey(item)===target.key : true));
                renderPdfPage({page:target?.location?.page || source?.pages?.[0] || 1,parent:source,quote:target?.quote || '',context:target?.location?.context || '',autoPage:Boolean(target?.quote) && !target?.location?.page,spans:target?.location?.spans});
                return true;
            };
            const finishSourcesClose=()=>{
                liquidMotions.get(sourceSheet)?.cancel();
                if(sourceSheet?.open)sourceSheet.close();
                if(sourceSheet)delete sourceSheet.dataset.closing;
                sourceClosing=false;pdfRevision++;pdfView=null;cancelPdfRequests();setSpatialAnswer(null);clearCitationHighlight();
                if(sourceOrigin?.isConnected) {
                    const citation=sourceOrigin.matches?.('.ai-inline-citation,.ai-linked-citation');
                    if(citation && !sourceOriginKeyboard)suppressCitationFocusOnce=true;
                    sourceOrigin.focus({preventScroll:true});if(!citation)suppressCitationFocusOnce=false;
                }
                sourceOriginKeyboard=false;
            };
            const closeSources = () => {
                if(!sourceSheet?.open || sourceClosing)return;
                sourceClosing=true;sourceSheet.dataset.closing='true';pdfRevision++;setSpatialAnswer(null);
                const identity=sourceSheet.dataset.requestId?.startsWith('document-') ? {element:$('.ai-pdf-viewer-head strong',sourceSheet),text:pdfView?.document.name || ''} : null;
                liquidMorph(sourceOrigin,sourceSheet,{closing:true,duration:380,identity,done:finishSourcesClose});
            };
            document.addEventListener('keydown',event=>{if(event.key==='Escape' && sourceSheet?.open){event.preventDefault();closeSources();}});
            document.addEventListener('click',event=>{
                const chip=event.target.closest?.('#apple-composer-attachment,.apple-topbar-pdf');
                if(!chip || !documentUi.document?.viewer)return;
                const viewer=documentUi.document.viewer;
                if(chip.id==='apple-composer-attachment' && (documentUi.pending || documentUi.attachmentDocumentId!==viewer.id))return;
                openSources({id:'document-'+viewer.id,document:viewer,sources:[],source_kind:'cited'},chip);
            });
            document.addEventListener('keydown',event=>{
                if((event.key==='Enter' || event.key===' ') && event.target.matches?.('#apple-composer-attachment,.apple-topbar-pdf')){event.preventDefault();event.target.click();}
            });

            const openSources = (data, origin, target=null) => {
                if(sourceSheet?.open && sourceOrigin===origin && sourceSheet.dataset.requestId===String(data.id) && !sourceClosing) {closeSources();return;}
                sourceClosing=false;
                if(sourceSheet) delete sourceSheet.dataset.closing;
                const originBox=liquidRect(origin);
                const motionOrigin=originBox ? {isConnected:true,getBoundingClientRect:()=>originBox} : origin;
                if (!sourceSheet) {
                    sourceSheet=document.createElement('dialog');sourceSheet.id='apple-source-sheet';sourceSheet.setAttribute('aria-labelledby','ai-source-title');
                    sourceSheet.innerHTML='<div class="ai-sheet-inner"><header class="ai-sheet-head"><div><small>ANSWER INTELLIGENCE</small><h2 id="ai-source-title">Kaynaklar</h2></div><button type="button" class="ai-sheet-close" aria-label="Kaynakları kapat">×</button></header><div class="ai-sheet-body"></div></div>';
                    document.body.append(sourceSheet);
                    $('.ai-sheet-close',sourceSheet).addEventListener('click',closeSources);
                    sourceSheet.addEventListener('cancel',event=>{event.preventDefault();closeSources();});
                    sourceSheet.addEventListener('click',event=>{const rect=sourceSheet.getBoundingClientRect();if(event.target===sourceSheet && (event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)) closeSources();});
                }
                sourceOrigin=origin;
                sourceSheet.dataset.phone=String(window.matchMedia('(max-width:900px)').matches);
                sourceSheet.dataset.reducedMotion=String(reducedMotion.matches);
                const body=$('.ai-sheet-body',sourceSheet);body.replaceChildren();body.scrollTop=0;clearPassageHighlight();
                if(!origin?.matches?.('.ai-inline-citation,.ai-linked-citation')) clearSentenceHighlight();
                $('#ai-source-title',sourceSheet).textContent=String(data.id).startsWith('document-') ? 'Belge' : 'Kaynaklar';
                sourceSheet.dataset.requestId=data.id;
                const note=document.createElement('p');note.className='ai-source-note';
                note.textContent=data.source_kind==='retrieved' ? 'Bu yanıtta kullanılan PDF pasajları bildirilmedi. Varsa doğrulanmış web kaynakları aşağıda gösterilir.' : 'Yanıtta bildirilen PDF pasajları ve API tarafından iletilen web kaynakları.';
                body.append(note);
                for (const source of data.sources || []) {
                    if (source.kind==='web') {
                        const url=safeUrl(source.url);if(!url) continue;
                        const link=document.createElement('a');link.className='ai-source-card ai-source-web';link.dataset.sourceKey=citationSourceKey(source);link.href=url;link.target='_blank';link.rel='noopener noreferrer';
                        link.append(document.createTextNode(source.title || source.domain));
                        const small=document.createElement('small');small.textContent=`Web · ${source.domain || new URL(url).hostname} ↗`;link.append(small);body.append(link);
                    } else if (source.kind==='pdf' && source.role==='cited' && data.source_kind!=='retrieved') {
                        const card=document.createElement('details');card.className='ai-source-card';card.dataset.sourceKey=citationSourceKey(source);
                        const summary=document.createElement('summary');summary.textContent=source.title;
                        const small=document.createElement('small');small.textContent=source.pages?.length ? `Sayfa ${source.pages.join(', ')} · Pasaj ${source.parent_id}` : `Pasaj ${source.parent_id} · Sayfa bilgisi yok`;summary.append(small);card.append(summary);
                        const passage=document.createElement('div');passage.className='ai-source-passage';
                        const segments=source.segments?.length ? source.segments : [{text:source.passage || '',page:null}];
                        for(const segment of segments) {
                            const section=document.createElement('section');section.dataset.page=segment.page || '';
                            const caption=document.createElement('small');caption.textContent=segment.page ? `Sayfa ${segment.page}` : 'İlgili pasaj';
                            const paragraph=document.createElement('p');paragraph.textContent=segment.text || '';section.append(caption,paragraph);passage.append(section);
                        }
                        card.append(passage);body.append(card);
                    }
                }
                if (usedWebSearch(data) && !(data.sources || []).some(s=>s.kind==='web')) {
                    const note=document.createElement('p');note.className='ai-source-note';note.textContent='Web araması yapıldı; API bu yanıt için kaynak bağlantısı iletmedi.';body.append(note);
                }
                if (!sourceSheet.open) {
                    if(window.matchMedia('(max-width:900px)').matches) sourceSheet.showModal();else sourceSheet.show();
                }
                sourceSheet.setAttribute('aria-modal',String(window.matchMedia('(max-width:900px)').matches));
                setSpatialAnswer(origin);
                if(target) focusSourceCard(target.key,target.quote,target.location);
                mountPdfViewer(data,target);
                const identity=String(data.id).startsWith('document-') ? {element:$('.ai-pdf-viewer-head strong',sourceSheet),text:data.document?.name || ''} : null;
                liquidMorph(motionOrigin,sourceSheet,{duration:480,identity,done:()=>{
                    if(sourceSheet.open && !sourceClosing && !target) $('.ai-sheet-close',sourceSheet)?.focus({preventScroll:true});
                }});
            };
            const usedWebSearch = data => data?.web_used===true || (Number.isFinite(data?.web_calls) && data.web_calls>0);
            const sourceSummary = data => {
                const parents=new Map();
                const webSources=(data.sources || []).filter(source=>source.kind==='web' && safeUrl(source.url));
                for(const source of data.sources || []) {
                    if(source.kind!=='pdf' || source.role!=='cited' || data.source_kind==='retrieved' || !Number.isInteger(source.parent_id)) continue;
                    if(!parents.has(source.parent_id)) parents.set(source.parent_id,new Set());
                    for(const page of source.pages || []) if(Number.isInteger(page) && page>0) parents.get(source.parent_id).add(page);
                }
                const web=usedWebSearch(data);
                if(!parents.size && !web && !webSources.length) return null;
                const pageRanges = pages => {
                    const sorted=[...pages].sort((a,b)=>a-b), ranges=[];
                    for(let i=0;i<sorted.length;i++) {
                        const start=sorted[i];let end=start;
                        while(i+1<sorted.length && sorted[i+1]===end+1) end=sorted[++i];
                        ranges.push(start===end ? String(start) : `${start}–${end}`);
                    }
                    return ranges.join(', ');
                };
                const prefix=['▤ Kaynaklar'];
                if(web) prefix.push('Web araması kullanıldı');
                else if(webSources.length) prefix.push(`${webSources.length} web kaynağı`);
                const separator=parents.size>1 || web || webSources.length ? ' — ' : ' · ';
                const details=[...parents].map(([id,pages])=>`Parent ${id}${pages.size ? `${separator}Sayfa ${pageRanges(pages)}` : ''}`);
                const full=[...prefix,...details].join(' · ');
                const limit=window.matchMedia('(max-width:900px)').matches ? 70 : 115;
                const compact=parents.size>2 || (parents.size>0 && full.length>limit);
                return {text:compact ? [...prefix,`${parents.size} PDF pasajı`].join(' · ') : full, full};
            };
            // [D27] Her yenilemede tüm eski bot satırlarını sorgulamak yerine yalnız değişenleri işle.
            // Pencere boyutu değişirse kaynak etiketleri için gereken satırlar ayrıca işaretlenir.
            const sourceDirtyRows=new Set();
            // OPTİMİZASYON [D51]: önce kaynak düğmesini çiz. Pahalı metin içi
            // eşlemeyi sonraki kareden sonra çalıştır; aynı satırdaki işler birleştirilir.
            // Eski istek, değişen metin, iptal ve reset bekleyen işi geçersiz kılar.
            const pendingCitationRows=new Map();
            let citationWorkScheduled=false;
            const scheduleCitationWork=()=>{
                if(citationWorkScheduled || !pendingCitationRows.size)return;
                citationWorkScheduled=true;
                requestAnimationFrame(()=>setTimeout(()=>{
                    citationWorkScheduled=false;
                    const started=performance.now();
                    for(const [row,job] of pendingCitationRows){
                        pendingCitationRows.delete(row);
                        if(row.isConnected && row._html===job.html && ui.answers.get(Number(row.dataset.assistantIndex))===job.data && job.data.phase==='complete'){
                            installSentenceCitations(job.message,job.data);
                        }
                        // Birden fazla eski cevap yüklenince tek görev bütün geçmişi tutmasın.
                        if(performance.now()-started>=8)break;
                    }
                    renderSourceCoverage();scheduleCitationWork();
                },0));
            };
            const installSources = () => {
                const rows=[...sourceDirtyRows];sourceDirtyRows.clear();
                rows.forEach(row=>{
                    if(!row.isConnected)return;
                    const index=Number(row.dataset.assistantIndex);
                    const data=ui.answers.get(index);
                    const message=$('[data-testid="bot"]',row);
                    if(row._sourcesData===data && row._sourcesHtml===row._html)return;
                    row._sourcesData=data;row._sourcesHtml=row._html;
                    const summary=data ? sourceSummary(data) : null;
                    const footers=$$('.ai-sources-footer',row);
                    const existing=footers.shift();
                    footers.forEach(footer=>footer.remove());
                    if (!hasAnswerSources(data) || !message?.textContent.trim() || $('.apple-processing-status',row)) {
                        pendingCitationRows.delete(row);
                        existing?.remove();
                        clearSentenceCitations(message);
                        row.removeAttribute('data-sources-revealed');
                        return;
                    }
                    if(data.phase==='complete'){
                        pendingCitationRows.set(row,{message,data,html:row._html});scheduleCitationWork();
                    }else{
                        pendingCitationRows.delete(row);clearSentenceCitations(message);
                    }
                    if(!summary){existing?.remove();row.removeAttribute('data-sources-revealed');return;}
                    if (existing?.dataset.requestId === data.id) {
                        const button=$('.ai-source-capsule',existing);
                        putText($('.ai-source-label',button),summary.text);
                        if(button.getAttribute('aria-label')!==summary.full) button.setAttribute('aria-label',summary.full);
                        // [D52] aria-label fare ipucu değildir. Kısaltılmış etikette
                        // gizlenen bütün Parent/sayfa bilgilerini hover'da da koru.
                        if(button.title!==summary.full)button.title=summary.full;
                        return;
                    }
                    existing?.remove();
                    row.removeAttribute('data-sources-revealed');
                    const footer=document.createElement('div');footer.className='ai-sources-footer';footer.dataset.requestId=data.id;
                    const button=document.createElement('button');button.type='button';button.className='ai-source-capsule';
                    button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-label',summary.full);
                    button.title=summary.full; // [D52] Hazır kaynak verisinden; ek istek yok.
                    const label=document.createElement('span');label.className='ai-source-label';label.textContent=summary.text;button.append(label);
                    button.addEventListener('click',()=>{
                        const current=ui.answers.get(index);
                        if(current?.id===footer.dataset.requestId) openSources(current,button);
                    });
                    footer.append(button);row.append(footer);
                });
            };
            document.addEventListener('click',event=>{
                if(event.pointerType!=='touch' && event.pointerType!=='pen' && !window.matchMedia('(hover:none), (max-width:900px)').matches) return;
                if(sourceSheet?.contains(event.target)) return;
                const row=event.target.closest?.('#apple-chat .bot-row');
                const button=row?.querySelector('.ai-source-capsule');
                $$('#apple-chat .bot-row[data-sources-revealed="true"]').forEach(previous=>{
                    if(previous===row) return;
                    previous.removeAttribute('data-sources-revealed');
                    if(document.activeElement?.matches('.ai-source-capsule') && previous.contains(document.activeElement)) document.activeElement.blur();
                });
                if(!button || event.target.closest?.('button,a,input,textarea,select,summary,pre,code') || window.getSelection()?.toString()) return;
                putData(row,'sourcesRevealed',true);
                button.focus({preventScroll:true});
            });
            window.addEventListener('resize',()=>{
                for(const row of $$('#apple-chat .bot-row')){row._sourcesHtml=null;sourceDirtyRows.add(row);}
                scheduleRefresh();
            });
            const refreshIntelligence = () => { updateComposerMaterial(); renderTelemetry(); renderRequestError(); morphAnswer(); installSources(); renderSourceCoverage(); updateDocumentNavigator(); };
            const installIntelligence = () => {
                window.addEventListener('apple-runtime-update',event=>acceptRuntime(event.detail));
                document.addEventListener('input',event=>{if(event.target.matches('.mesaj-kutusu textarea')) updateComposerMaterial();});
                document.addEventListener('focusin',event=>{if(event.target.closest('#apple-composer')) updateComposerMaterial();});
                document.addEventListener('focusout',event=>{if(event.target.closest('#apple-composer')) requestAnimationFrame(updateComposerMaterial);});
                document.addEventListener('change',event=>{if(event.target.matches('.apple-upload input[type="file"]')) updateComposerMaterial();});
                $('#apple-stop')?.addEventListener('click',()=>{
                    if(ui.request?.id) {ui.cancelled.add(ui.request.id);if(ui.cancelled.size>64)ui.cancelled.delete(ui.cancelled.values().next().value);}
                    setUiPhase('cancelled');
                    syncSendStates();
                });
                readRuntimeBridge();
            };


            const microAnimations = new WeakMap();
            const pressure = {duration:140, press:80, scale:.975, sendScale:.94, overshoot:1.006, easing:'cubic-bezier(.2,.8,.2,1)'};
            const pressureTargets = element => element?.matches('.gonder-butonu, .gonder-butonu button, #apple-stop') ? [element,$('#apple-send-visual')].filter(Boolean) : [element];
            const runPressure = (element, values, duration) => {
                if(!element?.animate) return;
                microAnimations.get(element)?.cancel();
                if(reducedMotion.matches) return;
                const animation=element.animate(values.map(scale=>({scale:String(scale)})),{duration,easing:pressure.easing,fill:'none'});
                microAnimations.set(element,animation);
                animation.finished.then(()=>{if(microAnimations.get(element)===animation) microAnimations.delete(element);},()=>{});
            };
            const microFeedback = element => {
                if(!element || element.dataset.aiPressed==='true' || performance.now()-(Number(element.dataset.aiReleased)||0)<pressure.duration) return;
                const scale=element.matches('.gonder-butonu, .gonder-butonu button, #apple-stop') ? pressure.sendScale : pressure.scale;
                pressureTargets(element).forEach(target=>runPressure(target,[1,scale,pressure.overshoot,1],pressure.duration));
            };
            let thumbFrame = 0;
            const snapSlider = () => {
                const slider=$('#apple-reasoning-range');
                cancelAnimationFrame(thumbFrame);
                if (!slider) return;
                if (reducedMotion.matches) {slider.style.removeProperty('--ai-thumb-scale');return;}
                const start=performance.now();
                const frame=now=>{
                    const t=Math.min(1,(now-start)/pressure.duration);
                    const value=t<.55 ? pressure.scale+(pressure.overshoot-pressure.scale)*(1-Math.pow(1-t/.55,2)) : 1+(pressure.overshoot-1)*Math.pow((1-t)/.45,2);
                    slider.style.setProperty('--ai-thumb-scale',String(value));
                    if(t<1 && !reducedMotion.matches) thumbFrame=requestAnimationFrame(frame);
                    else slider.style.removeProperty('--ai-thumb-scale');
                };
                thumbFrame=requestAnimationFrame(frame);
            };
            const pressureSelector='.apple-topbar button, #apple-composer button, #apple-settings-popover button, #apple-model-popover button, #apple-settings-menu button, #apple-chat .apple-example-chip, #apple-chat .ai-source-capsule, #apple-chat .ai-inline-citation, #apple-chat .apple-scroll-bottom, #apple-source-sheet summary, #apple-source-sheet a.ai-source-web, #apple-source-sheet button, #apple-inspector-panel label:has(input[type="checkbox"]), #apple-inspector-panel label:has(input[type="radio"])';
            let pressedControl=null, pressedPointer=null;
            const releasePressure = (cancelled=false) => {
                const element=pressedControl;
                if(!element) return;
                const scale=element.matches('.gonder-butonu, .gonder-butonu button, #apple-stop') ? pressure.sendScale : pressure.scale;
                const targets=pressureTargets(element);
                const starts=targets.map(target=>Number.parseFloat(getComputedStyle(target).scale)||scale);
                element.removeAttribute('data-ai-pressed');element.dataset.aiReleased=String(performance.now());
                targets.forEach((target,index)=>runPressure(target,[starts[index],...(cancelled ? [] : [pressure.overshoot]),1],pressure.duration));
                pressedControl=null;pressedPointer=null;
            };
            const pressControl = element => {
                if(!element || element.matches(':disabled,[aria-disabled="true"]') || $('input:disabled',element)) return;
                if(pressedControl===element) return;
                releasePressure(true);
                pressedControl=element;
                const scale=element.matches('.gonder-butonu, .gonder-butonu button, #apple-stop') ? pressure.sendScale : pressure.scale;
                if(reducedMotion.matches || !element.animate) return;
                element.dataset.aiPressed='true';
                pressureTargets(element).forEach(target=>{
                    microAnimations.get(target)?.cancel();
                    const animation=target.animate([{scale:'1'},{scale:String(scale)}],{duration:pressure.press,easing:pressure.easing,fill:'forwards'});
                    microAnimations.set(target,animation);
                });
            };
            document.addEventListener('pointerdown',event=>{
                if(event.button!==0 || event.isPrimary===false) return;
                const element=event.target.closest?.(pressureSelector);
                if(element) {pressControl(element);pressedPointer=event.pointerId;}
            },{passive:true});
            document.addEventListener('pointerup',event=>{if(event.pointerId===pressedPointer) releasePressure();},{passive:true});
            document.addEventListener('pointercancel',event=>{if(event.pointerId===pressedPointer) releasePressure(true);},{passive:true});
            document.addEventListener('keydown',event=>{
                if(event.repeat || !['Enter',' '].includes(event.key)) return;
                const element=event.target.closest?.(pressureSelector);
                if(element && !event.target.matches('textarea,input:not([type=checkbox]):not([type=radio])')) pressControl(element);
            });
            document.addEventListener('keyup',event=>{if(['Enter',' '].includes(event.key)) releasePressure();});
            document.addEventListener('click',event=>{if(event.detail===0) microFeedback(event.target.closest?.(pressureSelector));});
            document.addEventListener('focusout',event=>{if(pressedControl?.contains(event.target)) releasePressure(true);});
            window.addEventListener('blur',()=>releasePressure(true));
            reducedMotion.addEventListener('change',()=>{releasePressure(true);cancelAnimationFrame(thumbFrame);$('#apple-reasoning-range')?.style.removeProperty('--ai-thumb-scale');});

            const documentUi = {document:null,lastRaw:'',pending:false,reset:null,lastResetId:'',sequence:0,headerRevision:0,bypassClear:false};
            const setDocumentPending = value => {
                documentUi.pending=value;
                putData($('#apple-composer'),'documentPending',value);
                getSendButton()?.setAttribute('aria-disabled',String(value || Boolean(documentUi.reset) || Boolean(getSendButton()?.disabled)));
            };
            const crossfadePdfName = name => {
                const node=$('.apple-topbar-pdf');
                if(!node) return;
                const next=name || 'PDF eklenmedi';
                if(node.dataset.activeName === next) return;
                const previous=$('.ai-pdf-name-current',node)?.textContent || node.textContent;
                const revision=++documentUi.headerRevision;
                node.dataset.activeName=next;
                node.title=next;
                const current=document.createElement('span');current.className='ai-pdf-name-current';current.textContent=next;
                node.replaceChildren(current);
                if(reducedMotion.matches || !previous || previous===next) return;
                const old=document.createElement('span');old.className='ai-pdf-name-outgoing';old.textContent=previous;old.setAttribute('aria-hidden','true');node.append(old);
                current.animate([{opacity:0,transform:'translateY(3px)'},{opacity:1,transform:'translateY(0)'}],{duration:160,easing:'ease-out'});
                const animation=old.animate([{opacity:1,transform:'translateY(0)'},{opacity:0,transform:'translateY(-3px)'}],{duration:160,easing:'ease-out',fill:'forwards'});
                animation.finished.catch(()=>{}).then(()=>{if(revision===documentUi.headerRevision) old.remove();});
            };
            const renderEmptyState = () => {
                const doc=documentUi.document;
                const empty=$('#apple-chat .apple-empty-state');
                if(!doc || !empty || empty.dataset.documentRevision === doc.revision) return;
                let heading=$('.apple-empty-heading',empty);
                if(!heading) {
                    const title=$('strong',empty);
                    heading=document.createElement('div');heading.className='apple-empty-heading';
                    const name=document.createElement('span');name.className='apple-empty-document';
                    title.before(heading);heading.append(name,title);
                }
                const name=$('.apple-empty-document',heading);
                name.hidden=!doc.available || !doc.name;
                putText(name,doc.available ? doc.name : '');
                putText($('strong',heading),doc.available && doc.name ? 'hakkında ne öğrenmek istersiniz?' : doc.title);
                const prompts=$('.apple-example-prompts',empty);
                if(prompts) {
                    prompts.replaceChildren(...doc.prompts.map(item=>{
                        const button=document.createElement('button');button.type='button';button.className='apple-example-chip';button.textContent=item.label;
                        button.dataset.prompt=item.prompt || '';button.dataset.emptyAction=item.action || '';
                        return button;
                    }));
                }
                empty.dataset.documentRevision=doc.revision;
                enterEmpty(empty);
            };
            const acceptDocument = raw => {
                let data;try{data=typeof raw==='string' ? JSON.parse(raw) : raw;}catch(_){return;}
                if(!data) return;
                showIngestion(data.ingestion);
                if(data.phase==='updating') setDocumentPending(true);
                if(data.phase==='error') setDocumentPending(false);
                const doc=data.document;
                if(!doc || typeof doc.revision!=='string' || !Array.isArray(doc.prompts)) return;
                documentUi.document=doc;
                crossfadePdfName(doc.name);
                if(data.phase!=='updating') setDocumentPending(false);
                if(!documentUi.reset) renderEmptyState();
                scheduleRefresh();
            };
            const readDocumentBridge = () => {
                const raw=$('#apple-document-state textarea')?.value;
                if(raw && raw!==documentUi.lastRaw) {documentUi.lastRaw=raw;acceptDocument(raw);}
                renderEmptyState();
                finishConversationReset();
            };
            const resetConversationIndicators = () => {
                ui.cancelled.clear();
                if(ui.request?.id) ui.cancelled.add(ui.request.id);
                ui.request=null;ui.answers.clear();answerSourceKeys.clear();answerStates.clear();pendingCitationRows.clear();sourceCoverage.clear();ui.processingBox=null;ui.morphed=null;ui.completeUntil=0;ui.lastBridge=$('#apple-runtime-state textarea')?.value || '';
                ui.telemetryKey='';
                const panel=$('#apple-telemetry');
                if(panel) {
                    const empty=$('.ai-empty-metrics',panel);if(empty) empty.hidden=false;
                    putData(panel,'live',false);putText($('.ai-live-badge',panel),'Bekliyor');
                    $$('.ai-timeline, .ai-retrieval, .ai-token-breakdown',panel).forEach(node=>node.replaceChildren());
                }
                setUiPhase('ready');
                if(sourceSheet?.open) finishSourcesClose();
                clearCitationHighlight();
                refreshIntelligence();
            };
            const releaseConversationReset = token => {
                if(documentUi.reset!==token) return;
                clearTimeout(token.timeout);
                token.animation?.cancel();
                const chat=$('#apple-chat');
                if(chat){chat.inert=false;putData(chat,'resetting',false);}
                documentUi.reset=null;
                setDocumentPending(false);
            };
            const finishConversationReset = () => {
                const token=documentUi.reset;
                if(!token?.armed || !token.acknowledged || !$('#apple-chat .apple-empty-state') || $$('#apple-chat .user-row, #apple-chat .bot-row').length) return;
                renderEmptyState();
                releaseConversationReset(token);
                const chat=$('#apple-chat');
                if(chat && !reducedMotion.matches) chat.animate([{opacity:0,transform:'scale(.992)'},{opacity:1,transform:'scale(1)'}],{duration:150,easing:'ease-out'});
                if(token.reason==='clear') toast('Sohbet temizlendi');
            };
            const beginConversationReset = async (reason='clear') => {
                if(documentUi.reset) return false;
                const chat=$('#apple-chat');
                const token={sequence:++documentUi.sequence,reason,armed:false,animation:null,timeout:null};
                documentUi.reset=token;
                if(chat) {
                    putData(chat,'resetting',true);chat.inert=true;
                    if(!reducedMotion.matches) {
                        token.animation=chat.animate([{opacity:1,transform:'scale(1)'},{opacity:0,transform:'scale(.992)'}],{duration:150,easing:'ease-in',fill:'forwards'});
                        await token.animation.finished.catch(()=>{});
                    }
                }
                if(documentUi.reset!==token) return false;
                resetConversationIndicators();
                token.armed=true;
                token.timeout=setTimeout(()=>{
                    if(documentUi.reset===token) {releaseConversationReset(token);toast('Sohbet geçişi tamamlanamadı; tekrar deneyin.','error');}
                },8000);
                return true;
            };
            window.applePreparePdfConversation = async completed => {
                if(completed) {
                    if(documentUi.reset) releaseConversationReset(documentUi.reset);
                    await beginConversationReset('pdf');
                } else setDocumentPending(false);
                return [completed];
            };
            const isNativeClear = button => Boolean(button?.closest('#apple-chat') && /clear|temiz/i.test((button.getAttribute('aria-label') || '')+' '+(button.title || '')));
            const pickReplacementPdf = () => {
                let picker=$('#apple-pdf-replacement');
                if(!picker) {
                    picker=document.createElement('input');picker.type='file';picker.accept='.pdf,application/pdf';picker.id='apple-pdf-replacement';picker.hidden=true;
                    picker.addEventListener('change',async()=>{
                        const file=picker.files?.[0];if(!file) return;
                        const upload=$('.apple-upload');
                        const clear=$$('button',upload || document).find(button=>!button.classList.contains('apple-pdf-clear') && /clear|temiz|kaldır|remove/i.test((button.getAttribute('aria-label') || '')+' '+(button.title || '')));
                        if(!clear) {toast('PDF seçicisi hazırlanamadı.','error');return;}
                        clear.click();
                        const start=performance.now();
                        let target;
                        while(!(target=$('.apple-upload input[type="file"]')) && performance.now()-start<2500) await new Promise(resolve=>requestAnimationFrame(resolve));
                        if(!target) {toast('PDF seçicisi hazırlanamadı; tekrar deneyin.','error');return;}
                        const transfer=new DataTransfer();transfer.items.add(file);target.files=transfer.files;
                        target.dispatchEvent(new Event('change',{bubbles:true}));
                        picker.value='';
                    });
                    document.body.append(picker);
                }
                picker.click();
            };
            const installRefinements = () => {
                for(const chip of $$('#apple-composer-attachment,.apple-topbar-pdf')) {
                    chip.setAttribute('role','button');chip.tabIndex=0;chip.setAttribute('aria-haspopup','dialog');chip.setAttribute('aria-label','PDF belgesini aç');
                }
                window.addEventListener('apple-document-update',event=>{
                    documentUi.lastRaw=typeof event.detail==='string' ? event.detail : JSON.stringify(event.detail);
                    acceptDocument(event.detail);
                });
                document.addEventListener('click',async event=>{
                    const button=event.target.closest?.('button');
                    if(!button) return;
                    if(button===getSendButton()) {
                        if(photoUi.pending || (photoUi.file && !photoUi.ready)) {
                            event.preventDefault();event.stopImmediatePropagation();
                            toast(photoUi.error || 'Fotoğrafın yüklenmesini bekleyin.','error');return;
                        }
                        if(documentUi.pending || documentUi.reset) {
                            event.preventDefault();event.stopImmediatePropagation();
                            toast(documentUi.pending ? 'PDF güncellemesinin tamamlanmasını bekleyin.' : 'Yeni sohbet hazırlanıyor.');return;
                        }
                        if(!button.disabled && getComposerTextarea()?.value.trim()) {
                            microFeedback(button);
                        }
                    }
                    if(isNativeClear(button) && !documentUi.bypassClear) {
                        event.preventDefault();event.stopImmediatePropagation();
                        if(getSendButton()?.disabled || documentUi.pending) return toast('Mevcut işlemin tamamlanmasını bekleyin.','error');
                        if(await beginConversationReset('clear')) {
                            documentUi.bypassClear=true;
                            try{button.click();}finally{documentUi.bypassClear=false;}
                            requestAnimationFrame(finishConversationReset);
                        }
                    }
                },true);
                readDocumentBridge();
            };

            const updatePdfUi = () => {
                $$('.apple-upload').forEach((upload) => {
                    const stem = $('.file-preview .stem', upload)?.textContent?.trim();
                    const ext = $('.file-preview .ext', upload)?.textContent?.trim();
                    const filename = stem ? `${stem}${ext || ''}` : null;
                    const existingCard = $('.apple-pdf-compact-card', upload);

                    if (filename) {
                        if (!upload.classList.contains('apple-has-file')) upload.classList.add('apple-has-file');
                        let card = existingCard;
                        if (!card) {
                            card = document.createElement('div');
                            card.className = 'apple-pdf-compact-card';
                            card.innerHTML = `<span class="apple-pdf-icon">PDF</span><span class="apple-pdf-info"><span class="apple-pdf-name"></span><span class="apple-pdf-sub"><span class="apple-pdf-ok">PDF seçildi</span><span>· Veritabanı</span></span></span><button type="button" class="apple-pdf-clear" title="PDF'yi kaldır">×</button>`;
                            upload.appendChild(card);
                            $('.apple-pdf-clear', card)?.addEventListener('click', (e) => {
                                e.preventDefault(); e.stopPropagation();
                                const clear = $$('button', upload).find(b => /clear|temiz|kaldır|remove/i.test((b.getAttribute('aria-label') || '') + ' ' + (b.title || '')) && !b.classList.contains('apple-pdf-clear'));
                                if (clear) clear.click();
                                else {
                                    const input = $('input[type="file"]', upload);
                                    if (input) { input.value = ''; input.dispatchEvent(new Event('change', { bubbles:true })); }
                                }
                                setTimeout(scheduleRefresh, 40);
                            });
                        }
                        const nameEl = $('.apple-pdf-name', card);
                        if (nameEl && nameEl.textContent !== filename) nameEl.textContent = filename;
                    } else {
                        if (upload.classList.contains('apple-has-file')) upload.classList.remove('apple-has-file');
                        existingCard?.remove();
                    }
                });

            };

            let inspectorMotion = null;
            let inspectorTargetOpen = false;
            let inspectorTargetDeveloper = false;
            let inspectorScrollTop = 0;

            const inspectorOutline = (width, height, progress) => {
                const r = Math.min(30, width / 4, height / 4), k = .55228475;
                const anchors = [[r,0],[width-r,0],[width,r],[width,height/3],
                    [width,height*2/3],[width,height-r],[width-r,height],[r,height],
                    [0,height-r],[0,height*2/3],[0,height/3],[0,r]];
                const map = ([x,y]) => {
                    const bend = Math.min(80,width*.12) * Math.sin(Math.PI * progress) *
                        Math.sin(Math.PI * y / height) * (1 - x / width);
                    return [x+bend,y];
                };
                const point = value => map(value).map(n => n.toFixed(3)).join(' ');
                const corners = {
                    1:[[width-r+k*r,0],[width,r-k*r]],
                    5:[[width,height-r+k*r],[width-r+k*r,height]],
                    7:[[r-k*r,height],[0,height-r+k*r]],
                    11:[[0,r-k*r],[r-k*r,0]]
                };
                let path = `M${point(anchors[0])}`;
                anchors.forEach((a,i) => {
                    const b = anchors[(i+1)%anchors.length];
                    const controls = corners[i] || [
                        [a[0]+(b[0]-a[0])/3,a[1]+(b[1]-a[1])/3],
                        [a[0]+(b[0]-a[0])*2/3,a[1]+(b[1]-a[1])*2/3]
                    ];
                    path += ` C${point(controls[0])} ${point(controls[1])} ${point(b)}`;
                });
                return `path("${path} Z")`;
            };

            const inspectorProgress = motion => {
                const t = Math.max(0,Math.min(1,Number(motion.panel.currentTime || 0)/motion.duration));
                return motion.from + (motion.to-motion.from)*(1-Math.pow(1-t,3));
            };

            const settleInspector = () => {
                const row = $('#apple-user-home'), panel = $('#apple-inspector-panel');
                if (!row || !panel) return;
                const old = inspectorMotion;
                inspectorMotion = null;
                container.classList.toggle('apple-inspector-collapsed',!inspectorTargetOpen);
                row.classList.toggle('apple-home-collapsed',!inspectorTargetOpen);
                row.classList.toggle('apple-developer-mode',inspectorTargetDeveloper);
                row.removeAttribute('data-inspector-motion');
                ['width','height','padding'].forEach(key => row.style.removeProperty(`--inspector-motion-${key}`));
                row.style.removeProperty('--inspector-chat-width');
                if (old) { old.panel.cancel(); old.chat?.cancel(); old.content.forEach(a=>a.cancel()); inspectorScrollTop=old.scrollTop; }
                if (inspectorTargetOpen) panel.scrollTop=inspectorScrollTop;
                panel.inert = !inspectorTargetOpen || mobileLayout.matches;
                panel.setAttribute('aria-hidden',String(panel.inert));
                $$('[data-apple-action="inspector"]').forEach(button => {
                    button.setAttribute('aria-expanded',String(!panel.inert));
                    button.setAttribute('aria-label',inspectorTargetOpen ? 'Inspector’ı kapat' : 'Inspector’ı aç');
                    button.setAttribute('aria-controls','apple-inspector-panel');
                });
            };

            const animateInspector = (open, developer=inspectorTargetDeveloper, immediate=false) => {
                const row = $('#apple-user-home'), panel = $('#apple-inspector-panel');
                const chat = $('.apple-chat-column',row || document);
                if (!row || !panel || !chat) return;
                if (!immediate && open===inspectorTargetOpen && developer===inspectorTargetDeveloper) return;
                const old = inspectorMotion;
                const from = old ? inspectorProgress(old) : (inspectorTargetOpen ? 1 : 0);
                const firstChat = chat.getBoundingClientRect();
                const previousWidth = old?.width;
                const previousHeight = old?.height;
                const scrollTop = old?.scrollTop ?? (inspectorTargetOpen ? panel.scrollTop : inspectorScrollTop);
                inspectorScrollTop=scrollTop;
                inspectorTargetOpen = open;
                inspectorTargetDeveloper = developer;
                if (immediate || mobileLayout.matches || reducedMotion.matches || !panel.animate ||
                    !CSS.supports('scale','1') || !CSS.supports('clip-path','path("M0 0 L1 0 L1 1 Z")')) {
                    settleInspector();
                    return;
                }
                if (old) { old.panel.cancel(); old.chat?.cancel(); old.content.forEach(a=>a.cancel()); }
                if (open && developer) row.classList.add('apple-developer-mode');
                row.removeAttribute('data-inspector-motion');
                row.classList.remove('apple-home-collapsed');
                container.classList.remove('apple-inspector-collapsed');
                const expanded = panel.getBoundingClientRect();
                const style = getComputedStyle(panel);
                const width = expanded.width || previousWidth, height = expanded.height || previousHeight;
                if (!width || !height) { settleInspector(); return; }
                row.style.setProperty('--inspector-motion-width',`${width}px`);
                row.style.setProperty('--inspector-motion-height',`${height}px`);
                row.style.setProperty('--inspector-motion-padding',style.padding);
                const expandedChat = chat.getBoundingClientRect();
                row.style.setProperty('--inspector-chat-width',open ? `${expandedChat.width}px` : '100%');
                row.dataset.inspectorMotion = open ? 'opening' : 'closing';
                row.classList.add('apple-home-collapsed');
                container.classList.add('apple-inspector-collapsed');
                panel.scrollTop=scrollTop;
                const fullChat = chat.getBoundingClientRect();
                const to = open ? 1 : 0;
                const duration = Math.max(160,(open ? 500 : 440)*Math.abs(to-from));
                const frames = Array.from({length:61},(_,i) => {
                    const t=i/60, p=from+(to-from)*(1-Math.pow(1-t,3));
                    return {offset:t,clipPath:inspectorOutline(width,height,p),scale:`${p} ${Math.pow(p,.72)}`};
                });
                const firstScale = firstChat.width/fullChat.width;
                const lastScale = 1;
                const chatFrames = Array.from({length:61},(_,i) => {
                    const t=i/60,k=1-Math.pow(1-t,3);
                    return {offset:t,transform:`scaleX(${firstScale+(lastScale-firstScale)*k})`};
                });
                panel.inert = true;
                panel.setAttribute('aria-hidden','true');
                if (panel.contains(document.activeElement)) $('[data-apple-action="inspector"]')?.focus({preventScroll:true});
                const options={duration,easing:'linear',fill:'both'};
                const panelAnimation = panel.animate(frames,options);
                const chatAnimation = chat.animate(chatFrames,options);
                const contentFrames = Array.from({length:61},(_,i) => {
                    const t=i/60,k=1-Math.pow(1-t,3);
                    return {offset:t,scale:`${1/(firstScale+(lastScale-firstScale)*k)} 1`};
                });
                const content = $$('#apple-chat .apple-empty-state, #apple-chat .message-wrap, #apple-composer textarea, #apple-composer .composer-plus, #apple-composer #apple-reasoning-widget, #apple-composer .gonder-butonu, #apple-stop, #apple-send-visual',chat)
                    .filter(el=>el.getBoundingClientRect().width>0)
                    .map(el=>el.animate(contentFrames.map(frame=>({...frame,
                        transformOrigin:el.matches('textarea,.message-wrap') ? 'left center' :
                            el.id==='apple-reasoning-widget' ? 'right center' : 'center center'
                    })),options));
                const motion={panel:panelAnimation,chat:chatAnimation,content,from,to,duration,width,height,scrollTop};
                inspectorMotion=motion;
                panelAnimation.finished.then(() => {
                    if(inspectorMotion===motion) settleInspector();
                }).catch(() => {});
            };

            const toggleInspector = (force) => {
                if (mobileLayout.matches) return;
                animateInspector(typeof force==='boolean' ? !force : !inspectorTargetOpen);
            };
            window.addEventListener('resize',() => { if(inspectorMotion) settleInspector(); },{passive:true});
            reducedMotion.addEventListener('change',() => { if(inspectorMotion) settleInspector(); });

            const toggleTheme = () => {
                const dark = !document.documentElement.classList.contains('apple-dark');
                document.documentElement.classList.toggle('apple-dark', dark);
                // [D31] Tarayıcı depolamayı engelleyebilir; tema tercihi kaydedilemese de arayüz çalışmalıdır.
                try{localStorage.setItem('appleTheme', dark ? 'dark' : 'light');}catch(_){}
                toast(dark ? 'Koyu tema açıldı' : 'Açık tema açıldı');
            };

            const overlay = $('.apple-command-overlay');
            const openPalette = () => {
                if (mobileLayout.matches) return;
                closeSettingsPopover();
                overlay?.classList.add('open');
                overlay?.setAttribute('aria-hidden','false');
                if (typeof overlay?.showPopover === 'function' && !overlay.matches(':popover-open')) overlay.showPopover();
                $('#apple-global-settings-button')?.setAttribute('aria-expanded','true');
                $('.apple-mode-options [aria-pressed="true"]')?.focus({preventScroll:true});
            };
            const closePalette = () => {
                const wasOpen = overlay?.classList.contains('open');
                if (overlay?.matches(':popover-open')) overlay.hidePopover();
                overlay?.classList.remove('open');
                overlay?.setAttribute('aria-hidden','true');
                $('#apple-global-settings-button')?.setAttribute('aria-expanded','false');
                if (wasOpen && !mobileLayout.matches) $('#apple-global-settings-button')?.focus({preventScroll:true});
            };

            const photoUi={file:null,url:'',pending:false,ready:false,error:'',started:0,lastRaw:''};
            let attachmentMenu=null,photoPicker=null;
            const photoClearButton=()=>$('#apple-photo-clear button,button#apple-photo-clear');
            const renderPhotoPreview=()=>{
                const slot=$('#apple-composer-attachment')?.parentElement;
                if(!slot)return;
                let card=$('#apple-photo-preview');
                if(!card) {
                    card=document.createElement('div');card.id='apple-photo-preview';card.hidden=true;
                    card.innerHTML='<img alt="Seçilen fotoğraf" /><div><strong></strong><small role="status" aria-live="polite"></small></div><button type="button" aria-label="Fotoğrafı kaldır" title="Fotoğrafı kaldır">×</button>';
                    $('button',card).addEventListener('click',()=>{
                        if(photoUi.pending)return;
                        photoClearButton()?.click();
                    });
                    slot.append(card);
                }
                if(card.hidden!==!photoUi.file)card.hidden=!photoUi.file;
                if(!photoUi.file)return;
                const picture=$('img',card);
                if(picture.getAttribute('src')!==photoUi.url)picture.src=photoUi.url;
                putText($('strong',card),photoUi.file.name);
                putText($('small',card),photoUi.error || (photoUi.pending ? 'Fotoğraf yükleniyor…' : 'Mesajla birlikte gönderilecek'));
                if($('button',card).disabled!==photoUi.pending)$('button',card).disabled=photoUi.pending;
                putData(card,'ready',photoUi.ready);
                putData(card,'error',Boolean(photoUi.error));
            };
            const acceptPhoto=raw=>{
                let data;try{data=typeof raw==='string'?JSON.parse(raw):raw;}catch(_){return;}
                if(!data || !('ready' in data))return;
                if(photoUi.pending && !data.name)return;
                photoUi.pending=false;photoUi.ready=Boolean(data.ready);photoUi.error=data.error || '';
                if(!data.name) {
                    if(photoUi.url)URL.revokeObjectURL(photoUi.url);
                    photoUi.file=null;photoUi.url='';
                }
                if(data.error)toast(data.error,'error');
                renderPhotoPreview();updateComposerMaterial();syncSendStates();
            };
            const readPhotoBridge=()=>{
                const raw=$('#apple-photo-state textarea')?.value || '';
                if(raw && raw!==photoUi.lastRaw){photoUi.lastRaw=raw;acceptPhoto(raw);}
                if(photoUi.pending) {
                    const error=$('#apple-photo-upload .error');
                    if(error || performance.now()-photoUi.started>90000) {
                        photoUi.pending=false;photoUi.ready=false;
                        photoUi.error='Yükleme tamamlanamadı. Fotoğrafı kaldırıp yeniden seçin.';
                        toast(photoUi.error,'error');renderPhotoPreview();syncSendStates();
                    }
                }
            };
            window.addEventListener('apple-photo-update',event=>{
                if(event.detail===photoUi.lastRaw)return;
                photoUi.lastRaw=event.detail;acceptPhoto(event.detail);
            });
            document.addEventListener('change',event=>{
                if(!event.target.matches?.('#apple-photo-upload input[type="file"]'))return;
                const file=event.target.files?.[0];if(!file)return;
                if(photoUi.url)URL.revokeObjectURL(photoUi.url);
                Object.assign(photoUi,{file,url:URL.createObjectURL(file),pending:true,ready:false,error:'',started:performance.now(),lastRaw:$('#apple-photo-state textarea')?.value || ''});
                renderPhotoPreview();updateComposerMaterial();syncSendStates();
            },true);
            const putPhotoFile=async file=>{
                if(documentUi.pending || documentUi.reset || getSendButton()?.disabled || photoUi.pending)return toast('Mevcut işlemin tamamlanmasını bekleyin.','error');
                if(!/\\.(jpe?g|png|webp|gif)$/i.test(file.name) || file.size>20*1024*1024)return toast('En fazla 20 MB boyutunda JPG, PNG, WebP veya hareketsiz GIF seçin.','error');
                let input=$('#apple-photo-upload input[type="file"]');
                if(!input || photoUi.file) {
                    photoClearButton()?.click();
                    const start=performance.now();
                    do {
                        await new Promise(resolve=>requestAnimationFrame(resolve));
                        input=$('#apple-photo-upload input[type="file"]');
                    } while((!input || photoUi.file) && performance.now()-start<3000);
                }
                if(!input || photoUi.file)return toast('Fotoğraf seçicisi hazırlanamadı. Tekrar deneyin.','error');
                const transfer=new DataTransfer();transfer.items.add(file);input.files=transfer.files;
                input.dispatchEvent(new Event('change',{bubbles:true}));
            };
            const openPhotoPicker=()=>{
                if(photoUi.pending || documentUi.pending || getSendButton()?.disabled)return toast('Mevcut işlemin tamamlanmasını bekleyin.','error');
                if(!photoPicker) {
                    photoPicker=document.createElement('input');photoPicker.type='file';photoPicker.hidden=true;
                    photoPicker.id='apple-photo-picker';photoPicker.accept='.jpg,.jpeg,.png,.webp,.gif,image/jpeg,image/png,image/webp,image/gif';
                    photoPicker.addEventListener('change',()=>{
                        const file=photoPicker.files?.[0];photoPicker.value='';
                        if(file)void putPhotoFile(file);
                    });
                    document.body.append(photoPicker);
                }
                photoPicker.click();
            };
            const closeAttachmentMenu=(restoreFocus=false)=>{
                if(!attachmentMenu)return;
                if(attachmentMenu.matches(':popover-open'))attachmentMenu.hidePopover();
                attachmentMenu.hidden=true;
                const plus=$('.composer-plus button,button.composer-plus');
                plus?.setAttribute('aria-expanded','false');
                if(restoreFocus)plus?.focus({preventScroll:true});
            };
            const positionAttachmentMenu=()=>{
                if(!attachmentMenu || attachmentMenu.hidden)return;
                const trigger=$('.composer-plus button,button.composer-plus');
                if(!trigger)return;
                const rect=trigger.getBoundingClientRect(),viewport=window.visualViewport;
                const left=viewport?.offsetLeft || 0,top=viewport?.offsetTop || 0;
                const width=viewport?.width || innerWidth;
                attachmentMenu.style.left=Math.min(Math.max(rect.left,left+12),left+width-236)+'px';
                attachmentMenu.style.top=Math.max(top+12,rect.top-attachmentMenu.offsetHeight-12)+'px';
            };
            const openAttachmentMenu=()=>{
                if(documentUi.pending || documentUi.reset || photoUi.pending || getSendButton()?.disabled)return toast('Mevcut işlemin tamamlanmasını bekleyin.','error');
                if(attachmentMenu && !attachmentMenu.hidden){closeAttachmentMenu();return;}
                closeSettingsPopover();
                if(!attachmentMenu) {
                    attachmentMenu=document.createElement('div');attachmentMenu.id='apple-attachment-menu';attachmentMenu.hidden=true;
                    attachmentMenu.setAttribute('popover','manual');attachmentMenu.setAttribute('role','menu');attachmentMenu.setAttribute('aria-label','Dosya ekle');
                    attachmentMenu.innerHTML='<button type="button" role="menuitem" data-attachment="photo"><span aria-hidden="true">▧</span>Fotoğraf ekle</button><button type="button" role="menuitem" data-attachment="pdf"><span aria-hidden="true">▤</span>PDF ekle / değiştir</button>';
                    attachmentMenu.addEventListener('click',event=>{
                        const item=event.target.closest('button[data-attachment]');if(!item)return;
                        closeAttachmentMenu();
                        if(item.dataset.attachment==='photo')openPhotoPicker();else openFilePicker();
                    });
                    attachmentMenu.addEventListener('keydown',event=>{
                        const items=$$('button',attachmentMenu),index=items.indexOf(document.activeElement);
                        if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeAttachmentMenu(true);}
                        else if(event.key==='ArrowDown' || event.key==='ArrowUp'){event.preventDefault();items[(index+(event.key==='ArrowDown'?1:items.length-1))%items.length].focus();}
                        else if(event.key==='Tab')closeAttachmentMenu();
                    });
                    document.body.append(attachmentMenu);
                }
                const plus=$('.composer-plus button,button.composer-plus');
                plus?.setAttribute('aria-haspopup','menu');plus?.setAttribute('aria-controls',attachmentMenu.id);plus?.setAttribute('aria-expanded','true');
                attachmentMenu.hidden=false;
                if(typeof attachmentMenu.showPopover==='function')attachmentMenu.showPopover();
                positionAttachmentMenu();microFeedback(plus);
                if(!reducedMotion.matches)attachmentMenu.animate([{opacity:0,transform:'translateY(7px) scale(.97)'},{opacity:1,transform:'translateY(0) scale(1)'}],{duration:150,easing:'cubic-bezier(.2,.8,.2,1)'});
                $('button',attachmentMenu)?.focus({preventScroll:true});
            };
            document.addEventListener('pointerdown',event=>{
                if(attachmentMenu && !attachmentMenu.hidden && !attachmentMenu.contains(event.target) && !event.target.closest?.('.composer-plus'))closeAttachmentMenu();
            },true);
            window.addEventListener('resize',positionAttachmentMenu);
            window.visualViewport?.addEventListener('resize',positionAttachmentMenu);
            window.visualViewport?.addEventListener('scroll',positionAttachmentMenu);
            const openFilePicker = () => {
                if (documentUi.pending || documentUi.reset) return toast('PDF güncellemesinin tamamlanmasını bekleyin.');
                const input = $('.apple-upload input[type="file"]');
                if (input) input.click();
                else pickReplacementPdf();
            };

            const clearConversation = () => {
                if (getSendButton()?.disabled) return toast('Mevcut yanıtın tamamlanmasını bekleyin', 'error');
                const chat = $('#apple-chat') || $('[data-testid="chatbot"]') || $('.chatbot');
                const clear = $$('button', chat || document).find(b => /clear|temiz/i.test((b.getAttribute('aria-label') || '') + ' ' + (b.title || '')));
                if (clear) clear.click();
                else toast('Temizleme düğmesi bulunamadı', 'error');
            };

            const runCommand = (command) => {
                closePalette();
                if (command === 'pdf') openFilePicker();
                else if (command === 'clear') clearConversation();
                else if (command === 'memory') $('.apple-switch input[type="checkbox"]')?.click();
                else if (command === 'detail') {
                    openSettingsPopover();
                    $('#apple-reasoning-range')?.focus({preventScroll:true});
                }
                else if (command === 'inspector') toggleInspector();
                else if (command === 'theme') toggleTheme();
            };

            let currentUiMode = null;
            const syncUiMode = () => {
                const value = $('#apple-mode-controls input:checked')?.value || '0';
                $$('[data-ui-mode]').forEach(button => {
                    const selected = button.dataset.uiMode === value;
                    if(button.getAttribute('aria-pressed')!==String(selected)) button.setAttribute('aria-pressed',String(selected));
                });
                if(currentUiMode===value) return;
                const initial = currentUiMode===null;
                currentUiMode=value;
                animateInspector(value==='1',value==='1',initial);
            };
            const selectUiMode = value => {
                const input = $$('#apple-mode-controls input[type="radio"]').find(node => node.value===value);
                if(input && !input.checked) input.click();
                syncUiMode();
                animateInspector(value==='1',value==='1');
                closePalette();
            };

            const installStaticEvents = () => {
                $$('[data-ui-mode]').forEach(button => {
                    if (button.dataset.bound) return;
                    button.dataset.bound = '1';
                    button.addEventListener('click', () => selectUiMode(button.dataset.uiMode));
                });
                const closeSettings = $('[data-apple-action="close-settings"]');
                if (closeSettings && !closeSettings.dataset.bound) {
                    closeSettings.dataset.bound = '1';
                    closeSettings.addEventListener('click', closePalette);
                }
                $$('[data-apple-action="commands"]').forEach(b => { if (!b.dataset.bound) { b.dataset.bound='1'; b.addEventListener('click', openPalette); } });
                $$('[data-apple-action="inspector"]').forEach(b => { if (!b.dataset.bound) { b.dataset.bound='1'; b.addEventListener('click', () => toggleInspector()); } });
                $$('[data-apple-action="theme"]').forEach(b => { if (!b.dataset.bound) { b.dataset.bound='1'; b.addEventListener('click', toggleTheme); } });
                $$('.apple-command-item').forEach(b => { if (!b.dataset.bound) { b.dataset.bound='1'; b.addEventListener('click', () => runCommand(b.dataset.command)); } });
                if (overlay && !overlay.dataset.bound) {
                    overlay.dataset.bound='1';
                    overlay.addEventListener('click', e => { if (e.target === overlay) closePalette(); });
                }
                $$('.apple-example-chip').forEach(chip => {
                    if (chip.dataset.bound) return;
                    chip.dataset.bound='1';
                    chip.addEventListener('click', () => {
                        microFeedback(chip);
                        if(chip.dataset.emptyAction === 'upload') openFilePicker();
                        else setTextareaValue(getComposerTextarea(), chip.dataset.prompt || chip.textContent.trim());
                    });
                });
                $$('.composer-plus button, button.composer-plus').forEach(btn => {
                    if (btn.dataset.bound) return;
                    btn.dataset.bound='1';
                    btn.setAttribute('aria-label','Fotoğraf veya PDF ekle');
                    btn.setAttribute('aria-haspopup','menu');
                    btn.setAttribute('aria-expanded','false');
                    btn.addEventListener('click', openAttachmentMenu);
                });
            };

            const findChatScroller = (fromElement = null) => {
                const chat = $('#apple-chat') || $('[data-testid="chatbot"]') || $('.chatbot');
                if (!chat) return null;

                const messageScroller = chat.querySelector('.bubble-wrap');
                if (messageScroller) return messageScroller;

                const isRealScroller = (el) => {
                    if (!el) return false;
                    const style = getComputedStyle(el);
                    const overflowY = style.overflowY || '';
                    return /(auto|scroll|overlay)/i.test(overflowY) && el.scrollHeight > el.clientHeight + 4;
                };

                // Önce status kartının gerçek scroll edilebilir üst kapsayıcısını bul.
                let node = fromElement?.parentElement || null;
                while (node && node !== document.body) {
                    if (isRealScroller(node)) return node;
                    if (node === chat) break;
                    node = node.parentElement;
                }

                if (isRealScroller(chat)) return chat;

                // Fallback: sadece gerçekten overflow-y auto/scroll olan descendant'ları kabul et.
                const candidates = [...chat.querySelectorAll('*')].filter(isRealScroller);
                if (candidates.length) {
                    return candidates.sort((a,b) => (b.scrollHeight-b.clientHeight)-(a.scrollHeight-a.clientHeight))[0];
                }

                return chat;
            };

            // [D32] Tek sefer kaydır: gecikmiş çoklu zamanlayıcılar kullanıcı yukarı çıktıktan sonra
            // sohbeti tekrar aşağı çekiyordu. Otomatik kaydırma ayrıca alta yakınlık kontrolü yapar.
            const forceChatBottom = (anchor = null) => {
                const scroller = findChatScroller(anchor);
                if (!scroller) return;

                const jump = () => {
                    scroller.scrollTop = scroller.scrollHeight;
                };

                jump();
            };

            const autoScrollThinkingStatus = () => {
                if (!getSendButton()?.disabled) return;
                const statuses = $$('#apple-chat .apple-processing-status');
                const status = statuses.at(-1);
                if (!status || status.dataset.appleThinkScrollDone === '1') return;

                const title = $('strong', status)?.textContent?.trim() || '';
                if (!/GPT\\s*düşünüyor/i.test(title)) return;

                status.dataset.appleThinkScrollDone = '1';
                const scroller=findChatScroller(status);
                if(scroller && scroller.scrollHeight-scroller.scrollTop-scroller.clientHeight<100)forceChatBottom(status);
            };

            const installScrollButton = () => {
                const chat = $('#apple-chat') || $('[data-testid="chatbot"]') || $('.chatbot');
                if (!chat || $('.apple-scroll-bottom', chat)) return;
                chat.style.position = 'relative';
                const button = document.createElement('button');
                button.className = 'apple-scroll-bottom';
                button.type = 'button';
                button.textContent = '↓';
                button.title = 'En alta git';
                button.setAttribute('aria-label','En alta git');
                button.tabIndex=-1;
                chat.appendChild(button);
                const update = () => {
                    const scroller = findChatScroller();
                    if (!scroller) return;
                    const away = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight > 90;
                    button.classList.toggle('visible', away);
                    button.tabIndex=away ? 0 : -1;
                    button.setAttribute('aria-hidden',String(!away));
                };
                button.addEventListener('click', () => forceChatBottom(button));
                chat.addEventListener('scroll', update, true);
                setTimeout(update, 100);
            };

            const pollStatus = () => {
                const status = $('.apple-status textarea');
                if (!status) return;
                const value = status.value || '';
                if (value === lastStatusValue) return;
                if (lastStatusValue !== null) {
                    if (/❌|hata|error|güncellenemedi/i.test(value)) toast('PDF güncellenirken hata oluştu', 'error');
                    else if (/✅ Veritabanı başarıyla güncellendi!/.test(value)) toast('Veritabanı başarıyla güncellendi');
                }
                lastStatusValue = value;
            };

            // Görsel kaydırıcı mevcut Gradio değerlerini değiştirir; istek akışı aynen kalır.
            const detailLevels = ['İdeal', 'Detaylı', 'Çok Detaylı'];
            let modelPopover = null;
            let modelTrigger = null;
            const renderReasoningLevel = (index) => {
                const slider = $('#apple-reasoning-range');
                const title = $('#apple-reasoning-label');
                const level = detailLevels[index] || detailLevels[0];
                if (slider) {
                    slider.value = String(index);
                    slider.setAttribute('aria-valuetext', level);
                    slider.style.setProperty('--apple-slider-fill', `${index * 50}%`);
                }
                if (title && title.textContent !== level) title.textContent = level;
                $$('.apple-reasoning-stops i').forEach((dot, i) => {
                    const active = i === index;
                    if (dot.classList.contains('apple-stop-active') !== active) dot.classList.toggle('apple-stop-active', active);
                });
            };
            const syncReasoningControl = () => {
                const detail = $('#apple-detail-controls input:checked')?.value;
                renderReasoningLevel(Math.max(0, detailLevels.indexOf(detail)));
                const model = $('#apple-model-controls input:checked');
                const name = model?.value === '0' ? 'GPT-4o-mini' : 'GPT-5.6 Luna';
                const label = $('#apple-reasoning-model');
                if (label && label.textContent !== name) label.textContent = name;
                const summaryModel = $('#apple-summary-model');
                const summaryDetail = $('#apple-summary-detail');
                const level = detailLevels[Math.max(0, detailLevels.indexOf(detail))];
                if (summaryModel && summaryModel.textContent !== name) summaryModel.textContent = name;
                if (summaryDetail && summaryDetail.textContent !== level) summaryDetail.textContent = level;
                $('#apple-settings-trigger')?.setAttribute('aria-label', `${name}, ${level}: model ve detay ayarları`);
                if (modelTrigger) modelTrigger.setAttribute('aria-label', `Model seç: ${name}`);
                if (modelPopover) $$('[role="menuitemradio"]', modelPopover).forEach(button => {
                    button.setAttribute('aria-checked', String(button.dataset.value === model?.value));
                });
            };
            const setReasoningLevel = (index) => {
                const safeIndex = Math.max(0, Math.min(2, index));
                const input = $$('#apple-detail-controls input[type="radio"]').find(node => node.value === detailLevels[safeIndex]);
                const changed = input && !input.checked;
                if (changed) input.click();
                renderReasoningLevel(safeIndex);
                if (changed) snapSlider();
                requestAnimationFrame(syncReasoningControl);
            };
            const closeModelPopover = (restoreFocus = false) => {
                if (modelPopover?.matches(':popover-open')) modelPopover.hidePopover();
                if (modelPopover) modelPopover.hidden = true;
                modelTrigger?.setAttribute('aria-expanded', 'false');
                if (restoreFocus) modelTrigger?.focus({preventScroll: true});
            };
            const positionModelPopover = () => {
                if (!modelPopover || modelPopover.hidden || !modelTrigger) return;
                const viewport = window.visualViewport;
                const leftEdge = viewport?.offsetLeft || 0;
                const topEdge = viewport?.offsetTop || 0;
                const viewWidth = viewport?.width || window.innerWidth;
                const viewHeight = viewport?.height || window.innerHeight;
                const triggerRect = modelTrigger.getBoundingClientRect();
                const width = Math.min(240, viewWidth - 20);
                modelPopover.style.width = `${width}px`;
                modelPopover.style.maxHeight = `${Math.max(80, viewHeight - 20)}px`;
                const height = modelPopover.offsetHeight;
                const left = Math.max(leftEdge + 10, Math.min(triggerRect.left + triggerRect.width / 2 - width / 2, leftEdge + viewWidth - width - 10));
                let top = triggerRect.top - height - 8;
                if (top < topEdge + 10) top = Math.min(triggerRect.bottom + 8, topEdge + viewHeight - height - 10);
                modelPopover.style.left = `${left}px`;
                modelPopover.style.top = `${Math.max(topEdge + 10, top)}px`;
            };
            const openModelPopover = () => {
                if (!modelPopover) {
                    const style = document.createElement('style');
                    style.textContent = `
                        #apple-model-popover { inset:auto; margin:0; position:fixed; z-index:2147483000; box-sizing:border-box; padding:8px; border:1px solid rgba(0,0,0,.09); border-radius:20px; background:#fff; color:#222; box-shadow:0 10px 35px rgba(0,0,0,.13); overflow:auto; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
                        #apple-model-popover[hidden] { display:none; }
                        #apple-model-popover .apple-model-menu-title { padding:6px 10px 8px; font-size:12px; color:#888; }
                        #apple-model-popover button { display:flex; align-items:center; gap:9px; width:100%; min-height:44px; padding:10px; border:0; border-radius:12px; background:transparent; color:inherit; font-family:inherit; font-size:14px; font-weight:500; text-align:left; cursor:pointer; }
                        #apple-model-popover button::before { content:'✓'; width:14px; visibility:hidden; color:#0088ff; }
                        #apple-model-popover button[aria-checked="true"] { background:#e4f1ff; color:#0071df; }
                        #apple-model-popover button[aria-checked="true"]::before { visibility:visible; }
                        #apple-model-popover button:hover, #apple-model-popover button:focus-visible { background:#f0f0f2; outline:2px solid #0088ff; outline-offset:-2px; }
                        html.apple-dark #apple-model-popover { background:#29292c; color:#eee; border-color:#444; }
                        html.apple-dark #apple-model-popover button[aria-checked="true"] { background:#143d64; color:#83c6ff; }
                        html.apple-dark #apple-model-popover button:hover, html.apple-dark #apple-model-popover button:focus-visible { background:#3b3b40; }
                    `;
                    document.head.appendChild(style);
                    modelPopover = document.createElement('div');
                    modelPopover.id = 'apple-model-popover';
                    modelPopover.setAttribute('popover','manual');
                    modelPopover.setAttribute('role','menu');
                    modelPopover.setAttribute('aria-label','Model seçimi');
                    const heading = document.createElement('div');
                    heading.className = 'apple-model-menu-title';
                    heading.textContent = 'Model';
                    modelPopover.appendChild(heading);
                    [['1','GPT-5.6 Luna'],['0','GPT-4o-mini']].forEach(([value,name]) => {
                        const option = document.createElement('button');
                        option.type = 'button';
                        option.setAttribute('role','menuitemradio');
                        option.setAttribute('aria-label',name);
                        option.setAttribute('aria-checked','false');
                        option.dataset.value = value;
                        option.textContent = name;
                        option.addEventListener('click', () => {
                            const input = $$('#apple-model-controls input[type="radio"]').find(node => node.value === value);
                            if (input && !input.checked) input.click();
                            closeModelPopover(true);
                            syncReasoningControl();
                            microFeedback(modelTrigger);
                            microFeedback($('#apple-settings-trigger'));
                            requestAnimationFrame(syncReasoningControl);
                        });
                        modelPopover.appendChild(option);
                    });
                    modelPopover.addEventListener('keydown', event => {
                        const buttons = $$('button', modelPopover);
                        const current = buttons.indexOf(document.activeElement);
                        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); closeModelPopover(true); }
                        else if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
                            event.preventDefault();
                            const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (current + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
                            buttons[next]?.focus({preventScroll:true});
                        } else if (event.key === 'Tab') closeModelPopover();
                    });
                    document.body.appendChild(modelPopover);
                }
                modelPopover.hidden = false;
                if (typeof modelPopover.showPopover === 'function' && !modelPopover.matches(':popover-open')) modelPopover.showPopover();
                modelTrigger?.setAttribute('aria-expanded','true');
                syncReasoningControl();
                positionModelPopover();
                $('[aria-checked="true"]',modelPopover)?.focus({preventScroll:true});
            };
            const closeSettingsPopover = (restoreFocus = false) => {
                closeModelPopover();
                const panel = $('#apple-settings-popover');
                if (panel?.matches(':popover-open')) panel.hidePopover();
                if (panel) panel.hidden = true;
                const trigger = $('#apple-settings-trigger');
                trigger?.setAttribute('aria-expanded','false');
                if (restoreFocus) trigger?.focus({preventScroll:true});
            };
            const positionSettingsPopover = () => {
                const panel = $('#apple-settings-popover');
                const trigger = $('#apple-settings-trigger');
                if (!panel || panel.hidden || !trigger) return;
                const viewport = window.visualViewport;
                const x = viewport?.offsetLeft || 0;
                const y = viewport?.offsetTop || 0;
                const width = viewport?.width || window.innerWidth;
                const height = viewport?.height || window.innerHeight;
                const rect = trigger.getBoundingClientRect();
                const panelWidth = Math.min(314, width - 20);
                panel.style.width = `${panelWidth}px`;
                panel.style.maxHeight = `${Math.max(80, height - 20)}px`;
                const panelHeight = panel.offsetHeight;
                const left = Math.max(x + 10, Math.min(rect.left, x + width - panelWidth - 10));
                let top = rect.top - panelHeight - 8;
                if (top < y + 10) top = Math.min(rect.bottom + 8, y + height - panelHeight - 10);
                panel.style.left = `${left}px`;
                panel.style.top = `${Math.max(y + 10, top)}px`;
                positionModelPopover();
            };
            const openSettingsPopover = () => {
                const panel = $('#apple-settings-popover');
                const trigger = $('#apple-settings-trigger');
                if (!panel || !trigger) return;
                panel.hidden = false;
                if (typeof panel.showPopover === 'function' && !panel.matches(':popover-open')) panel.showPopover();
                trigger.setAttribute('aria-expanded','true');
                syncReasoningControl();
                positionSettingsPopover();
                morphFromComposer(panel);
                $('#apple-model-trigger')?.focus({preventScroll:true});
            };
            const installSettingsPopover = () => {
                const trigger = $('#apple-settings-trigger');
                const panel = $('#apple-settings-popover');
                if (trigger && !trigger.dataset.bound) {
                    trigger.dataset.bound = '1';
                    trigger.addEventListener('click', () => {
                        if (panel && !panel.hidden) closeSettingsPopover();
                        else openSettingsPopover();
                    });
                }
                if (panel && !panel.dataset.bound) {
                    panel.dataset.bound = '1';
                    panel.addEventListener('keydown', event => {
                        if (event.key === 'Escape') {
                            event.preventDefault();
                            event.stopPropagation();
                            closeSettingsPopover(true);
                        }
                    });
                }
            };
            document.addEventListener('pointerdown', event => {
                const panel = $('#apple-settings-popover');
                const trigger = $('#apple-settings-trigger');
                if (panel && !panel.hidden && !panel.contains(event.target) && !trigger?.contains(event.target) && !modelPopover?.contains(event.target)) closeSettingsPopover();
                if (modelPopover && !modelPopover.hidden && !modelPopover.contains(event.target) && !modelTrigger?.contains(event.target)) closeModelPopover();
            });
            window.addEventListener('resize', () => closeSettingsPopover());
            window.visualViewport?.addEventListener('resize', positionSettingsPopover);
            window.visualViewport?.addEventListener('scroll', positionSettingsPopover);

            const installReasoningControl = () => {
                const slider = $('#apple-reasoning-range');
                modelTrigger = $('#apple-model-trigger');
                if (slider && !slider.dataset.bound) {
                    slider.dataset.bound = '1';
                    slider.addEventListener('input', () => setReasoningLevel(Number(slider.value)));
                }
                if (modelTrigger && !modelTrigger.dataset.bound) {
                    modelTrigger.dataset.bound = '1';
                    modelTrigger.addEventListener('click', () => {
                        if (modelPopover && !modelPopover.hidden) closeModelPopover();
                        else openModelPopover();
                    });
                }
                const reset = $('#apple-reasoning-reset');
                if (reset && !reset.dataset.bound) {
                    reset.dataset.bound = '1';
                    reset.addEventListener('click', () => setReasoningLevel(0));
                }
                syncReasoningControl();
            };

            const scheduleRefresh = () => {
                if (refreshQueued) return;
                refreshQueued = true;
                requestAnimationFrame(() => {
                    refreshQueued = false;
                    readRuntimeBridge();
                    pollStatus();
                    syncSendStates();
                    refreshIntelligence();
                    updatePdfUi();
                    readDocumentBridge();
                    installStaticEvents();
                    syncUiMode();
                    installReasoningControl();
                    installSettingsPopover();
                    installScrollButton();
                    autoScrollThinkingStatus();
                });
            };

            // [D29] Mouse hareketi frame hızından fazla gelebilir. Son konumu tutup frame başına
            // bir kez ölç/çiz; her pointermove olayında layout ölçümü ve stil yazımı yapma.
            let pointerFrame=0,pointerEvent=null;
            const paintPointer = () => {
                pointerFrame=0;
                const event=pointerEvent;pointerEvent=null;
                if(!event || document.hidden)return;
                const composer = event.target.closest?.('.chatgpt-composer');
                if (composer) {
                    const rect = composer.getBoundingClientRect();
                    composer.style.setProperty('--apple-mx', `${event.clientX - rect.left}px`);
                    composer.style.setProperty('--apple-my', `${event.clientY - rect.top}px`);
                }
                const send = event.target.closest?.('.gonder-butonu button, button.gonder-butonu');
                if (send) {
                    const rect = send.getBoundingClientRect();
                    send.style.setProperty('--apple-btn-x', `${event.clientX - rect.left}px`);
                    send.style.setProperty('--apple-btn-y', `${event.clientY - rect.top}px`);
                }
            };
            document.addEventListener('pointermove',event=>{pointerEvent=event;if(!pointerFrame)pointerFrame=requestAnimationFrame(paintPointer);},{passive:true});

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Tab' && overlay?.classList.contains('open')) {
                    const buttons = $$('button', overlay).filter(button => !button.disabled);
                    const first = buttons[0], last = buttons[buttons.length - 1];
                    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
                    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
                }
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); overlay?.classList.contains('open') ? closePalette() : openPalette(); }
                else if (e.key === 'Escape') closePalette();
            });

            // Native Streamlit köprüsü her snapshot sonrasında refresh çağırır.
            // Tüm body'yi izlemek, kendi DOM yazılarımızdan tekrar refresh üretir.
            document.addEventListener('change', scheduleRefresh);

            // [D31] Depolama izni olmaması bütün UI kurulumunu exception ile durdurmasın.
            try{if (localStorage.getItem('appleTheme') === 'dark') document.documentElement.classList.add('apple-dark');}catch(_){}
            container.classList.add('apple-inspector-collapsed');

            // Mobil görünüm ekran genişliğine göre otomatik seçilir.
            const mobileLayout = window.matchMedia('(max-width: 900px)');
            const updateMobileViewport = () => {
                if (!mobileLayout.matches) return;
                const viewport = window.visualViewport;
                // Yakınlaştırmada metni küçültme; yalnızca normal ölçekte klavyeyi takip et.
                if (viewport && Math.abs(viewport.scale - 1) > 0.05) return;
                const height = viewport?.height || window.innerHeight;
                const top = viewport?.offsetTop || 0;
                container.style.setProperty('--apple-mobile-height', `${height}px`);
                container.style.setProperty('--apple-phone-top', `${top}px`);
            };
            // Gradio sürümünden bağımsız olarak yalnızca arayüz kabuğunu işaretle.
            const phoneRow = $('.apple-main-row');
            for (let shell = phoneRow?.parentElement; shell && shell !== container; shell = shell.parentElement) {
                shell.classList.add('apple-phone-shell');
            }
            $('.apple-topbar')?.closest('.block')?.classList.add('apple-phone-header');
            window.visualViewport?.addEventListener('scroll', updateMobileViewport, { passive: true });
            const setMobileInspector = (open) => {
                open = open && !mobileLayout.matches;
                container.classList.toggle('apple-mobile-inspector-open', open);
                const chatColumn = $('.apple-chat-column');
                if (chatColumn) chatColumn.inert = open;
                $$('[data-apple-action="inspector"]').forEach(button => {
                    button.setAttribute('aria-expanded', String(open));
                    button.setAttribute('aria-label', open ? 'Ayarları kapat' : 'Ayarları aç');
                });
            };
            const syncMobileLayout = () => {
                container.classList.toggle('apple-mobile', mobileLayout.matches);
                if (mobileLayout.matches) closePalette();
                setMobileInspector(false);
                requestAnimationFrame(updateMobileViewport);
            };
            mobileLayout.addEventListener('change', syncMobileLayout);
            window.addEventListener('resize', updateMobileViewport, { passive: true });
            window.visualViewport?.addEventListener('resize', updateMobileViewport, { passive: true });
            const mobileResizeObserver = new ResizeObserver(updateMobileViewport);
            const topbar = $('.apple-topbar');
            if (topbar) mobileResizeObserver.observe(topbar);
            document.addEventListener('keydown', event => {
                if (event.key === 'Escape' && mobileLayout.matches) setMobileInspector(false);
            });
            syncMobileLayout();

            // OPTİMİZASYON: Sık DOM polling yerine olayları izle; yalnız zamana bağlı durumları görünür sekmede yokla.
            // [D29] Durum değişiklikleri snapshot/olaylarla gelir; eski dört DOM yoklama döngüsü kaldırıldı.
            // Yalnız fotoğraf timeout’u ve kısa tamamlandı durumu için görünür sekmede hafif kontrol kalır.
            const uiHeartbeat=()=>{if(document.hidden)return;if(photoUi.pending)readPhotoBridge();if(ui.phase==='complete')syncSendStates();};
            setInterval(uiHeartbeat,1000);
            document.addEventListener('visibilitychange',()=>{if(!document.hidden)scheduleRefresh();});
            installIntelligence();
            installRefinements();
            const composerPane=$('.apple-chat-column');
            const sizeComposer=()=>putData($('#apple-composer'),'compact',Boolean(composerPane && composerPane.clientWidth<=680));
            const composerResizeObserver=new ResizeObserver(sizeComposer);
            if(composerPane) {composerResizeObserver.observe(composerPane);sizeComposer();}

            scheduleRefresh();
            // Kalıcı DOM'da eski mesajların source kayıtlarını kimliklerini koruyarak geri bağla.
            window.researchFrontend={refresh:scheduleRefresh,
              composerPdf:value=>{const name=value?.name||'',id=value?.id||'';if(ui.fileName===name&&documentUi.attachmentDocumentId===id)return;ui.fileName=name;ui.fileSeen=Boolean(name);documentUi.attachmentDocumentId=id;updateComposerMaterial();},
              markSources:row=>{if(row.classList.contains('bot-row'))sourceDirtyRows.add(row);},
              cancelReset:()=>{if(documentUi.reset)releaseConversationReset(documentUi.reset);},
              uploadBusy:busy=>{setDocumentPending(busy);if(busy)setUiPhase('indexing');else if(ui.phase==='indexing')setUiPhase('ready');},
              restoreAnswers:rows=>{let i=0;for(const r of rows){if(r.role==='assistant'){rememberAnswer(i,r.telemetry);i++;}}},
              resetAnswers:()=>{ui.answers.clear();answerSourceKeys.clear();answerStates.clear();pendingCitationRows.clear();ui.cancelled.clear();sourceDirtyRows.clear();ui.request=null;ui.lastBridge='';sourceCoverage.clear();setUiPhase('ready');}
            };
            return [];
        }
        )();
"""
}

def component_directory():
    # Streamlit component dosya yolu ister; kullanıcı ayrıca frontend klasörü taşımaz.
    digest=hashlib.sha256(''.join(ASSETS.values()).encode()).hexdigest()[:20]
    folder=Path(tempfile.gettempdir())/'research-ui'/digest
    folder.mkdir(parents=True,exist_ok=True)
    for name,text in ASSETS.items():
        target=folder/name
        if target.exists() and target.read_text(encoding='utf-8')==text:continue
        fd,temp=tempfile.mkstemp(dir=folder,prefix='asset-')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as handle:handle.write(text)
            os.replace(temp,target)
        finally:
            if Path(temp).exists():Path(temp).unlink()
    return str(folder)
