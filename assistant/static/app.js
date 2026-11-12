'use strict';
const $=id=>document.getElementById(id);
if($('app')){
const csrf=document.querySelector('[name=csrfmiddlewaretoken]').value;
let folder='',job=null,page=1,total=0,epoch=0,rootRows=[],previewRow=null,pdfDoc=null,pdfPage=1,renderTask=null,previewEpoch=0;
async function api(route,body={}){const r=await fetch('/api/'+route,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(body)});let d;try{d=await r.json()}catch{throw Error('服務暫時無法使用。')}if(!r.ok)throw Error(d.error||'操作失敗，請重新登入。');return d}
const status=s=>$('status').textContent=s;
const size=n=>n<1024?n+' B':n<1048576?(n/1024).toFixed(1)+' KiB':(n/1048576).toFixed(1)+' MiB';
function button(text,fn){const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=()=>Promise.resolve(fn()).catch(e=>status(e.message));return b}
async function closeDocument(){previewEpoch++;const doc=pdfDoc;pdfDoc=null;if(renderTask){renderTask.cancel();renderTask=null}document.querySelector('iframe').src='about:blank';$('previewPanel').hidden=true;if(doc)await doc.destroy()}
async function renderPDF(){
if(!pdfDoc)return;if(renderTask)renderTask.cancel();
const my=previewEpoch,doc=pdfDoc;const p=await doc.getPage(pdfPage);if(my!==previewEpoch)return;
const initial=p.getViewport({scale:1});let scale=Math.min(1.5,1000/initial.width,Math.sqrt(4000000/(initial.width*initial.height)));
const viewport=p.getViewport({scale});const canvas=$('pdfCanvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
$('pdfStatus').textContent=`PDF 第 ${pdfPage} / ${doc.numPages} 頁${doc.numPages>200?'（預覽上限 200 頁）':''}`;
$('pdfPrev').disabled=pdfPage===1;$('pdfNext').disabled=pdfPage>=Math.min(200,doc.numPages);
renderTask=p.render({canvasContext:canvas.getContext('2d'),viewport});try{await renderTask.promise}catch(e){if(e.name!=='RenderingCancelledException')throw e}
}
async function fileAction(row,preview){
const f=$('fileForm');f.elements.root.value=$('roots').value;f.elements.path.value=row.path;
if(!preview){f.action='/api/download';f.target='_self';f.submit();return}
await closeDocument();previewRow=row;const my=previewEpoch;$('previewPanel').hidden=false;$('pdfStatus').textContent='';
const isPDF=row.name.toLowerCase().endsWith('.pdf');$('pdfCanvas').hidden=!isPDF;$('pdfPrev').hidden=!isPDF;$('pdfNext').hidden=!isPDF;document.querySelector('iframe').hidden=isPDF;
if(isPDF){
$('pdfStatus').textContent='載入 PDF…';
const response=await fetch('/api/preview',{method:'POST',body:new FormData(f),credentials:'same-origin'});
if(!response.ok)throw Error('無法預覽 PDF，請下載或重新登入。');
const bytes=new Uint8Array(await response.arrayBuffer());if(my!==previewEpoch)return;
const pdfjs=await import('/assets/pdfjs/pdf.mjs');pdfjs.GlobalWorkerOptions.workerSrc='/assets/pdfjs/pdf.worker.mjs';
const task=pdfjs.getDocument({data:bytes,isEvalSupported:false,enableXfa:false,disableFontFace:true,cMapUrl:'/assets/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'/assets/pdfjs/standard_fonts/',wasmUrl:'/assets/pdfjs/wasm/',iccUrl:'/assets/pdfjs/iccs/',maxImageSize:4000000});
const doc=await task.promise;if(my!==previewEpoch){await doc.destroy();return}pdfDoc=doc;pdfPage=1;await renderPDF();
}else{f.action='/api/preview';f.target='documentPreview';f.submit()}
$('previewPanel').scrollIntoView();
}
$('pdfPrev').onclick=()=>{pdfPage--;renderPDF().catch(e=>status(e.message))};$('pdfNext').onclick=()=>{pdfPage++;renderPDF().catch(e=>status(e.message))};
$('downloadPreview').onclick=async()=>{try{await closeDocument();await fileAction(previewRow,false)}catch(e){status(e.message)}};

function draw(rows){$('results').replaceChildren();for(const row of rows){const card=document.createElement('article');card.className='file';const h=document.createElement('h3');h.textContent=(row.directory?'📁 ':'📄 ')+row.name;card.append(h);const p=document.createElement('p');p.className='meta';p.textContent=`${row.folder||'根目錄'} · ${new Date(row.modified*1000).toLocaleString('zh-Hant')} · ${row.directory?'資料夾':size(row.size)}`;card.append(p);const actions=document.createElement('div');actions.className='actions';if(row.directory){actions.append(button('開啟資料夾',()=>{folder=row.path;$('query').value='';$('recursive').checked=false;return start()}))}else{const ext=row.name.split('.').pop().toLowerCase();if(['pdf','png','jpg','jpeg','gif','webp','bmp','txt','log','csv','md'].includes(ext)&&row.size<=20971520)actions.append(button('預覽',()=>fileAction(row,true)));actions.append(button('下載',()=>fileAction(row,false)))}card.append(actions);$('results').append(card)}$('page').textContent=`${page} / ${Math.max(1,Math.ceil(total/50))}`;$('prev').disabled=page<=1;$('next').disabled=page*50>=total}
async function poll(myEpoch){if(myEpoch!==epoch||!job)return;const d=await api('results',{job,page});if(myEpoch!==epoch)return;if(d.error)throw Error(d.error);if(!d.done){status('搜尋中… 可隨時取消');setTimeout(()=>poll(myEpoch).catch(e=>status(e.message)),250);return}total=d.total||0;draw(d.rows||[]);status(d.cancelled?'已取消搜尋':`找到 ${total} 項${d.limited?'（已達 2,000 筆結果、20,000 項掃描或 15 秒上限；請縮小範圍）':''}${d.errors?'；部分資料夾無法讀取':''}`)}
async function stop(){epoch++;if(job)await api('cancel',{job});job=null;status('已取消搜尋')}
async function start(){await stop();page=1;total=0;draw([]);await closeDocument();$('location').textContent=folder||'根目錄';if(!$('roots').value){status('請先於公司電腦設定允許的資料夾。');return}const d=await api('search',{root:$('roots').value,path:folder,q:$('query').value,extension:$('extension').value,sort:$('sort').value,descending:$('descending').checked,after:$('after').value,before:$('before').value,recursive:$('recursive').checked});job=d.job;await poll(epoch)}
$('searchForm').onsubmit=e=>{e.preventDefault();start().catch(e=>status(e.message))};$('cancel').onclick=()=>stop().catch(e=>status(e.message));$('roots').onchange=()=>{folder='';$('rootStatus').textContent=rootRows.find(r=>String(r.id)===$('roots').value)?.status||'';start().catch(e=>status(e.message))};$('up').onclick=()=>{folder=folder.split('/').slice(0,-1).join('/');start().catch(e=>status(e.message))};$('prev').onclick=()=>{page--;poll(epoch).catch(e=>status(e.message))};$('next').onclick=()=>{page++;poll(epoch).catch(e=>status(e.message))};$('closePreview').onclick=()=>closeDocument().catch(e=>status(e.message));
$('loadDevices').onclick=async()=>{try{const d=await api('devices');$('devices').replaceChildren();for(const device of d.devices){const p=document.createElement('p');p.textContent=`登入 #${device.id} · ${new Date(device.created).toLocaleString('zh-Hant')}`;p.append(button('撤銷',async()=>{await api('revoke',{id:device.id});p.remove();status('已撤銷該登入')}));$('devices').append(p)}}catch(e){status(e.message)}};
(async()=>{try{const d=await api('roots');rootRows=d.roots;for(const r of d.roots){const o=document.createElement('option');o.value=r.id;o.textContent=r.label;$('roots').append(o)}$('rootStatus').textContent=d.roots[0]?.status||'尚未設定資料夾';await start()}catch(e){status(e.message)}})();
}
