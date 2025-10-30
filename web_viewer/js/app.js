let map, markers = [];
async function init() {
  map = L.map('map').setView([28.4682, -16.2546], 10);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19}).addTo(map);
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  document.getElementById('docTitle').textContent = q.get('title') || '(sin título)';
  loadAnnotations(docId);
  document.getElementById('btnSync').addEventListener('click', async () => {
    await axios.post('/sync_annotations', { document_id: docId });
    await loadAnnotations(docId);
    alert('Sincronizado');
  });
}
async function loadAnnotations(document_id) {
  const res = await axios.get('/annotations', { params: { document_id } });
  const list = document.getElementById('annoList');
  list.innerHTML = '';
  markers.forEach(m => m.remove()); markers = [];
  (res.data.annotations || []).forEach(a => {
    const div = document.createElement('div');
    div.className = 'anno';
    div.innerHTML = `<b>#${a.id || '-'} · ${a.type||''}</b><br>${a.body||''}<br><small>${a.latitude||''}, ${a.longitude||''}</small>`;
    list.appendChild(div);
    if (a.latitude && a.longitude) {
      const m = L.marker([a.latitude, a.longitude]).addTo(map);
      m.bindPopup(`<b>${a.type||''}</b><br>${a.body||''}`);
      markers.push(m);
    }
  });
}
window.addEventListener('DOMContentLoaded', init);

document.getElementById('btnPull').addEventListener('click', async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  await axios.get('/pull_annotations', { params: { document_id: docId } });
  await loadAnnotations(docId);
  alert('Anotaciones descargadas');
});


document.getElementById('btnRunSearch').addEventListener('click', async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const params = {
    document_id: docId,
    q: document.getElementById('qText').value || '',
    tags: document.getElementById('qTags').value || '',
    type: document.getElementById('qType').value || '',
    from: document.getElementById('qFrom').value || '',
    to: document.getElementById('qTo').value || ''
  };
  const res = await axios.get('/annotations', { params });
  // re-render
  const list = document.getElementById('annoList');
  list.innerHTML = '';
  markers.forEach(m => m.remove()); markers = [];
  (res.data.annotations || []).forEach(a => {
    const div = document.createElement('div');
    div.className = 'anno';
    div.innerHTML = `<b>#${a.id || '-'} · ${a.type||''}</b><br>${a.body||''}<br><small>${a.latitude||''}, ${a.longitude||''}</small>`;
    list.appendChild(div);
    if (a.latitude && a.longitude) {
      const m = L.marker([a.latitude, a.longitude]).addTo(map);
      m.bindPopup(`<b>${a.type||''}</b><br>${a.body||''}`);
      markers.push(m);
    }
  });
});


async function loadProsopo(document_id){
  const r = await axios.get('/prosopo', { params: { document_id } });
  const p = r.data.persons || []; const g = r.data.places || [];
  const lp = document.getElementById('listPersons'); const lg = document.getElementById('listPlaces');
  lp.innerHTML = ''; lg.innerHTML = '';
  p.forEach(it => { const li=document.createElement('li'); li.textContent = `${it.id} · ${it.count}`; lp.appendChild(li); });
  g.forEach(it => { const li=document.createElement('li'); li.textContent = `${it.id} · ${it.count}`; lg.appendChild(li); });
}

(async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  await loadProsopo(docId);
})();


async function renderSigma(document_id){
  const r = await axios.get('/graph', { params: { document_id } });
  const G = new graphology.Graph();
  (r.data.nodes || []).forEach(n => { G.addNode(n.key, n); });
  (r.data.edges || []).forEach(e => { if(!G.hasEdge(e.key)) G.addEdge(e.source, e.target, e); });
  // Random layout
  graphologyLibrary.layout.random.assign(G);
  const container = document.getElementById("sigma-container");
  const renderer = new sigma.Sigma(G, container);
}

(async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  await renderSigma(docId);
})();


document.getElementById('btnLoadOCR').addEventListener('click', async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const seq = document.getElementById('ocrSeq').value;
  const res = await axios.get('/ocr_text', { params: { document_id: docId, seq: seq } });
  document.getElementById('ocrBox').value = res.data.ocr_text || '';
});


function syncScroll(divA, divB){
  let syncing=false;
  divA.addEventListener('scroll', () => {
    if(syncing) return; syncing=true;
    const ratio = divA.scrollTop / (divA.scrollHeight - divA.clientHeight || 1);
    divB.scrollTop = ratio * (divB.scrollHeight - divB.clientHeight);
    syncing=false;
  });
  divB.addEventListener('scroll', () => {
    if(syncing) return; syncing=true;
    const ratio = divB.scrollTop / (divB.scrollHeight - divB.clientHeight || 1);
    divA.scrollTop = ratio * (divA.scrollHeight - divA.clientHeight);
    syncing=false;
  });
}

async function loadComparator(){
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const seq = document.getElementById('cmpSeq').value;
  const leftMode = document.querySelector('input[name="leftMode"]:checked').value;
  // Load current corrected HTML (or text)
  const r = await axios.get('/ocr_text', { params:{ document_id: docId, seq: seq } });
  const corrected = r.data.ocr_text || '';
  const right = document.getElementById('rightPane');
  right.innerText = corrected; // start plain; user can format

  const left = document.getElementById('leftPane');
  left.innerHTML='';
  if(leftMode === 'ocr'){
    // Fetch earliest revision as "original" if exists; else fall back to current text
    const revs = await axios.get('/ocr_revisions', { params:{ document_id: docId, seq: seq } });
    if((revs.data.revisions||[]).length>0){
      const firstId = revs.data.revisions[0].id;
      // need text of first revision -> fetch from a dedicated endpoint? simplify: use current baseline
      // Since we didn't add endpoint to fetch a revision body, fallback to current baseline for now
      left.textContent = corrected;
    }else{
      left.textContent = corrected;
    }
  }else{
    const imgURL = `/page_image?document_id=${encodeURIComponent(docId)}&seq=${encodeURIComponent(seq)}`;
    const img = document.createElement('img');
    img.src = imgURL;
    left.appendChild(img);
  }
  // revisions list
  const revs = await axios.get('/ocr_revisions', { params:{ document_id: docId, seq: seq } });
  const ul = document.getElementById('revList'); ul.innerHTML='';
  (revs.data.revisions||[]).forEach(rv => {
    const li=document.createElement('li'); li.textContent = `v${rv.version} · ${rv.user||''} · ${rv.created_at||''}`;
    ul.appendChild(li);
  });
  // sync scrolling
  syncScroll(left, right);
}

function diffText(a, b){
  // Very simple word-level diff (for demo); mark additions/deletions
  const wa = a.split(/\s+/), wb=b.split(/\s+/);
  const n = wa.length, m = wb.length;
  const dp = Array(n+1).fill(0).map(()=>Array(m+1).fill(0));
  for(let i=1;i<=n;i++) for(let j=1;j<=m;j++) dp[i][j] = wa[i-1]===wb[j-1] ? dp[i-1][j-1]+1 : Math.max(dp[i-1][j], dp[i][j-1]);
  // backtrack
  let i=n, j=m, out=[];
  while(i>0 && j>0){
    if(wa[i-1]===wb[j-1]){ out.unshift(wa[i-1]); i--; j--; }
    else if(dp[i-1][j] >= dp[i][j-1]){ out.unshift(`<span class="mark-del">${wa[i-1]}</span>`); i--; }
    else { out.unshift(`<span class="mark-add">${wb[j-1]}</span>`); j--; }
  }
  while(i>0){ out.unshift(`<span class="mark-del">${wa[i-1]}</span>`); i--; }
  while(j>0){ out.unshift(`<span class="mark-add">${wb[j-1]}</span>`); j--; }
  return out.join(' ');
}

document.getElementById('btnLoadCmp').addEventListener('click', loadComparator);
document.getElementById('btnShowDiff').addEventListener('click', async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const seq = document.getElementById('cmpSeq').value;
  const leftMode = document.querySelector('input[name="leftMode"]:checked').value;
  let original='';
  if(leftMode==='ocr'){
    const r = await axios.get('/ocr_text', { params:{ document_id: docId, seq: seq } });
    original = r.data.ocr_text || '';
  }else{
    // If image selected, we cannot diff image vs text; use OCR text as proxy
    const r = await axios.get('/ocr_text', { params:{ document_id: docId, seq: seq } });
    original = r.data.ocr_text || '';
  }
  const corrected = document.getElementById('rightPane').innerText;
  const html = diffText(original, corrected);
  const left = document.getElementById('leftPane');
  left.innerHTML = html;
});

document.getElementById('btnSaveRevision').addEventListener('click', async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const seq = document.getElementById('cmpSeq').value;
  const text = document.getElementById('rightPane').innerText;
  const html = document.getElementById('rightPane').innerHTML;
  const r = await axios.post('/save_ocr_revision', { document_id: parseInt(docId), seq: parseInt(seq), ocr_text: text, ocr_html: html, user: 'web-editor' });
  if(r.data && r.data.ok){
    alert('Revisión guardada (v'+r.data.version+')');
    await loadComparator();
  }else{
    alert('Error al guardar revisión');
  }
});

// initial
(() => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  if(docId){ /* noop; user will press Cargar */ }
})();


async function populateRevisions(docId, seq){
  const revs = await axios.get('/ocr_revisions', { params:{ document_id: docId, seq: seq } });
  const sel = document.getElementById('revSelect');
  sel.innerHTML = '';
  (revs.data.revisions||[]).forEach(rv => {
    const opt = document.createElement('option');
    opt.value = rv.id; opt.textContent = `v${rv.version} · ${rv.user||''} · ${rv.created_at||''}`;
    sel.appendChild(opt);
  });
}

document.getElementById('btnLoadRevision').addEventListener('click', async () => {
  const rid = document.getElementById('revSelect').value;
  if(!rid) return;
  const r = await axios.get('/ocr_revision_body', { params:{ revision_id: rid } });
  const right = document.getElementById('rightPane');
  if(r.data && r.data.ocr_html){
    right.innerHTML = r.data.ocr_html;
  }else{
    right.innerText = r.data.ocr_text || '';
  }
});

document.getElementById('btnRestoreRevision').addEventListener('click', async () => {
  const rid = document.getElementById('revSelect').value;
  if(!rid) return;
  if(!confirm('¿Restaurar esta revisión como la versión actual?')) return;
  const r = await axios.post('/restore_ocr_revision', { revision_id: parseInt(rid) });
  if(r.data && r.data.ok){ alert('Revisión restaurada.'); } else { alert('Error al restaurar.'); }
});

document.getElementById('btnSignRevision').addEventListener('click', async () => {
  const rid = document.getElementById('revSelect').value;
  if(!rid) return;
  const who = prompt('Autor/Responsable de la firma:', 'web-editor');
  const note = prompt('Anotación de firma (opcional):', '');
  const r = await axios.post('/sign_ocr_revision', { revision_id: parseInt(rid), user: who||'web-editor', signature: note||'' });
  if(r.data && r.data.ok){ alert('Revisión firmada.'); } else { alert('Error al firmar.'); }
});

// Track changes: on save, compute diff <ins>/<del> between last baseline and current edited
function diffHTML(original, edited){
  // Basic token diff by words; wrap with <ins>/<del>
  const a = original.split(/\s+/), b = edited.split(/\s+/);
  const n=a.length, m=b.length;
  const dp=Array(n+1).fill(0).map(()=>Array(m+1).fill(0));
  for(let i=1;i<=n;i++) for(let j=1;j<=m;j++) dp[i][j] = a[i-1]===b[j-1] ? dp[i-1][j-1]+1 : Math.max(dp[i-1][j], dp[i][j-1]);
  let i=n, j=m, out=[];
  while(i>0 && j>0){
    if(a[i-1]===b[j-1]){ out.unshift(a[i-1]); i--; j--; }
    else if(dp[i-1][j] >= dp[i][j-1]){ out.unshift(`<del>${a[i-1]}</del>`); i--; }
    else { out.unshift(`<ins>${b[j-1]}</ins>`); j--; }
  }
  while(i>0){ out.unshift(`<del>${a[i-1]}</del>`); i--; }
  while(j>0){ out.unshift(`<ins>${b[j-1]}</ins>`); j--; }
  return out.join(' ');
}

async function currentBaseline(docId, seq){
  // Use current stored page text as baseline
  const r = await axios.get('/ocr_text', { params:{ document_id: docId, seq: seq } });
  return r.data.ocr_text || '';
}

// Override save handler to include changes_html when Track changes
const oldSaveHandler = document.getElementById('btnSaveRevision').onclick;
document.getElementById('btnSaveRevision').onclick = async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const seq = document.getElementById('cmpSeq').value;
  const text = document.getElementById('rightPane').innerText;
  const html = document.getElementById('rightPane').innerHTML;
  let payload = { document_id: parseInt(docId), seq: parseInt(seq), ocr_text: text, ocr_html: html, user: 'web-editor' };
  if(document.getElementById('chkTrack').checked){
    const base = await currentBaseline(docId, seq);
    payload.changes_html = diffHTML(base, text);
  }
  const r = await axios.post('/save_ocr_revision', payload);
  if(r.data && r.data.ok){ alert('Revisión guardada (v'+r.data.version+')'); await populateRevisions(docId, seq); } else { alert('Error al guardar revisión'); }
};

// Refresh revisions when loading comparator
const oldLoadCmp = loadComparator;
loadComparator = async function(){
  await oldLoadCmp();
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const seq = document.getElementById('cmpSeq').value;
  await populateRevisions(docId, seq);
};


async function loadUserRole(){
  try{
    const r = await axios.get('/user_role');
    const user = r.data.user || 'local-user';
    const role = r.data.role || 'investigador';
    document.getElementById('roleBadge').textContent = `— Usuario: ${user} · Rol: ${role}`;
    // Permissions: investigador(edit), experto(sign/restore), admin(all)
    const canEdit = (role==='investigador' || role==='experto' || role==='administrador');
    const canSign = (role==='experto' || role==='administrador');
    const canRestore = canSign;
    document.getElementById('btnSaveRevision').disabled = !canEdit;
    document.getElementById('btnSignRevision').disabled = !canSign;
    document.getElementById('btnRestoreRevision').disabled = !canRestore;
    return role;
  }catch(e){ return 'investigador'; }
}

document.getElementById('btnShowDiff').addEventListener('click', async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const seq = document.getElementById('cmpSeq').value;
  const rid = document.getElementById('revSelect').value;
  const diffsPanel = document.getElementById('panel-diffs');
  const box = document.getElementById('diffsBox');
  diffsPanel.style.display = 'block';
  if(rid){
    const r = await axios.get('/ocr_changes', { params:{ revision_id: rid }});
    box.innerHTML = r.data.changes_html || '<i>Sin cambios registrados en esta revisión.</i>';
    // Build naive paragraph list for partial restore
    const html = await axios.get('/ocr_revision_body', { params:{ revision_id: rid } });
    const raw = html.data.ocr_html || (html.data.ocr_text || '');
    const parts = raw.includes('</p>') ? raw.split(/<\/p>/).filter(x=>x.trim()!=='').map(x=>x+'</p>') : raw.split(/\n\n+/);
    const list = document.getElementById('parList'); list.innerHTML='';
    parts.forEach((p,i)=>{
      const div=document.createElement('div'); const id=`par_${i}`;
      div.innerHTML = `<label><input type="checkbox" id="${id}"> Párrafo ${i+1}</label>`;
      list.appendChild(div);
    });
  }else{
    box.innerHTML = '<i>Selecciona una revisión para ver cambios.</i>';
  }
});

document.getElementById('btnApplyPartial').addEventListener('click', async ()=>{
  const rid = document.getElementById('revSelect').value;
  if(!rid){ alert('Selecciona una revisión.'); return; }
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  const seq = parseInt(document.getElementById('cmpSeq').value);
  const checks = Array.from(document.querySelectorAll('#parList input[type=checkbox]'));
  const indices = checks.map((c,i)=> c.checked ? i : -1).filter(i=>i>=0);
  if(indices.length===0){ alert('Selecciona al menos un párrafo.'); return; }
  const r = await axios.post('/apply_partial_restore', { revision_id: parseInt(rid), document_id: parseInt(docId), seq: seq, indices });
  if(r.data && r.data.ok){
    alert('Cambios aplicados. Se creó una nueva revisión.');
  }else{
    alert('Error al aplicar cambios.');
  }
});

// On load
(async () => { await loadUserRole(); })();


document.getElementById('btnApplyRange').addEventListener('click', async ()=>{
  const rid = document.getElementById('revSelect').value;
  if(!rid){ alert('Selecciona una revisión.'); return; }
  const a = parseInt(document.getElementById('charRangeStart').value||'0');
  const b = parseInt(document.getElementById('charRangeEnd').value||'0');
  if(!(b>a)){ alert('Rango inválido'); return; }
  const r = await axios.get('/ocr_revision_body', { params:{ revision_id: rid } });
  const src = (r.data && (r.data.ocr_text || r.data.ocr_html)) ? (r.data.ocr_text || r.data.ocr_html).toString() : '';
  const snippet = src.substring(a, b);
  // Replace current selection in rightPane
  const rp = document.getElementById('rightPane');
  rp.focus();
  const sel = window.getSelection();
  if(!sel.rangeCount){ alert('Selecciona el texto a reemplazar en el panel derecho.'); return; }
  const range = sel.getRangeAt(0);
  range.deleteContents();
  range.insertNode(document.createTextNode(snippet));
  // keep selection end
  sel.removeAllRanges();
});

document.getElementById('btnExportAudit').addEventListener('click', ()=>{
  window.open('/export_audit?format=csv','_blank');
});

// Utility: save merged as a new revision via /apply_partial_restore_chars
async function saveMergedFinal(){
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(q.get('document_id')); const seq = parseInt(document.getElementById('cmpSeq').value);
  const right = document.getElementById('rightPane');
  const text = right.innerText; const html = right.innerHTML;
  const roleResp = await axios.get('/user_role');
  await axios.post('/apply_partial_restore_chars', { document_id: docId, seq: seq, final_text: text, final_html: html, user: roleResp.data.user, role: roleResp.data.role });
  alert('Guardado como nueva revisión (caracteres).');
}


async function setState(level){
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(q.get('document_id')); 
  const seq = parseInt(document.getElementById('cmpSeq') ? document.getElementById('cmpSeq').value : 0);
  const state = document.getElementById('stateSelect').value;
  const payload = { level, state, document_id: docId };
  if(level==='page') payload.seq = seq;
  const r = await axios.post('/change_state', payload);
  if(r.data && r.data.ok){ alert('Estado actualizado: '+r.data.state); } else { alert('No permitido o error.'); }
}

document.getElementById('btnSetStatePage').addEventListener('click', ()=> setState('page'));
document.getElementById('btnSetStateDoc').addEventListener('click', ()=> setState('document'));

document.getElementById('btnLoadQuality').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(q.get('document_id')); 
  const r = await axios.get('/ocr_quality_dashboard', { params: { document_id: docId } });
  const tb = document.querySelector('#tblQuality tbody'); tb.innerHTML='';
  (r.data.pages||[]).forEach(row => {
    const tr=document.createElement('tr');
    tr.innerHTML = `<td>${row.seq}</td><td>${row.state}</td><td>${(row.similarity*100).toFixed(1)}%</td>`;
    tb.appendChild(tr);
  });
});

document.getElementById('btnPublishDoc').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(q.get('document_id')); 
  const avg = await axios.get('/ocr_quality_dashboard', { params: { document_id: docId } });
  const scores = (avg.data.pages||[]).map(p=>p.similarity||0);
  const quality = scores.length ? (scores.reduce((a,b)=>a+b,0)/scores.length) : 0.0;
  const roleResp = await axios.get('/user_role');
  const signed_by = roleResp.data.user || 'web-editor';
  const signature = prompt('Nota de publicación (opcional):','');
  const r = await axios.post('/publish_to_geodocs', { document_id: docId, ocr_quality: quality, signed_by, signature });
  if(r.data && r.data.ok){ alert('Publicado en GeoDocs.'); } else { alert('Error al publicar.'); }
});


document.getElementById('btnBatchQuality').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(q.get('document_id'));
  const r = await axios.post('/run_quality_batch', { document_id: docId });
  if(r.data && r.data.ok){ alert('Análisis por lotes lanzado. Páginas: '+r.data.result.processed); } else { alert('Error: '+(r.data.error||'')); }
});

document.getElementById('btnShowSched').addEventListener('click', async ()=>{
  const r = await axios.get('/scheduler_status');
  alert('Última ejecución: ' + (r.data.last_run || '—') + '\nResultado: ' + JSON.stringify(r.data.result || {}));
});


document.getElementById('btnLoadCalib').addEventListener('click', async ()=>{
  const r = await axios.get('/calibration');
  alert('Calibración:\n' + JSON.stringify(r.data, null, 2));
});

document.getElementById('chkGrid').addEventListener('change', (ev)=>{
  const show = ev.target.checked;
  const right = document.getElementById('rightPane') || document.body;
  if(show){
    right.style.backgroundImage = 'linear-gradient(to right, rgba(0,0,0,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,0,0,0.06) 1px, transparent 1px)';
    right.style.backgroundSize = '40px 40px'; // ~10mm at 254 dpi fallback
  }else{
    right.style.backgroundImage = 'none';
  }
});


document.getElementById('btnEnhanceProj').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(q.get('document_id'));
  const r = await axios.post('/enhance_project', { document_id: docId });
  if(r.data && r.data.ok){ alert('Mejora por lotes lanzada. Páginas: '+r.data.result.processed); } else { alert('Error: '+(r.data.error||'')); }
});


async function applyMmGrid(enabled){
  try{
    const r = await axios.get('/calibration');
    const dpiX = r.data.dpi_x, dpiY = r.data.dpi_y;
    const pane = document.getElementById('rightPane') || document.body;
    if(enabled && dpiX && dpiY){
      const px10x = (dpiX/25.4)*10.0;
      const px10y = (dpiY/25.4)*10.0;
      pane.style.backgroundImage = 'linear-gradient(to right, rgba(0,0,0,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,0,0,0.06) 1px, transparent 1px)';
      pane.style.backgroundSize = px10x + 'px ' + px10y + 'px';
    }else if(enabled){
      // fallback fixed size as before
      pane.style.backgroundImage = 'linear-gradient(to right, rgba(0,0,0,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,0,0,0.06) 1px, transparent 1px)';
      pane.style.backgroundSize = '40px 40px';
    }else{
      pane.style.backgroundImage = 'none';
    }
  }catch(e){}
}

const gridChk = document.getElementById('chkGrid');
if(gridChk){
  gridChk.addEventListener('change', (ev)=> applyMmGrid(ev.target.checked));
}


const rootHtml = document.documentElement;
document.getElementById('btnFontPlus').addEventListener('click', ()=>{
  const cur = parseFloat(getComputedStyle(rootHtml).fontSize);
  rootHtml.style.fontSize = (cur*1.1) + 'px';
});
document.getElementById('btnFontMinus').addEventListener('click', ()=>{
  const cur = parseFloat(getComputedStyle(rootHtml).fontSize);
  rootHtml.style.fontSize = (cur/1.1) + 'px';
});
document.getElementById('chkContrast').addEventListener('change', (ev)=>{
  document.body.classList.toggle('high-contrast', ev.target.checked);
});


async function runTTS(corrected){
  const q = new URLSearchParams(window.location.search);
  const pageId = parseInt(q.get('page_id')) || parseInt(prompt("ID de página para TTS:"));
  if(!pageId) return;
  const r = await axios.post('/tts', { page_id: pageId, corrected: corrected, voice: 'es'});
  if(r.data && r.data.ok){
    alert('Archivo TTS listo: ' + r.data.file);
  }else{
    alert('Error TTS: ' + (r.data.error || ''));
  }
}
document.getElementById('btnTTSRaw').addEventListener('click', ()=> runTTS(false));
document.getElementById('btnTTSCorr').addEventListener('click', ()=> runTTS(true));

document.getElementById('btnSpellCheck').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const pageId = parseInt(q.get('page_id')) || parseInt(prompt("ID de página para revisión:"));
  if(!pageId) return;
  const r = await axios.post('/spellcheck', { page_id: pageId });
  if(r.data && r.data.ok){
    alert('Herramienta: ' + r.data.tool + '\nHallazgos: ' + r.data.issues.length);
    console.log(r.data.issues);
  }else{
    alert('Error revisión: ' + (r.data.error || ''));
  }
});

document.getElementById('btnXMP').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const pageId = parseInt(q.get('page_id')) || parseInt(prompt("ID de página XMP:"));
  if(!pageId) return;
  const r = await axios.post('/xmp_sidecar', { page_id: pageId });
  if(r.data && r.data.ok){ alert('XMP creado: ' + r.data.file); } else { alert('Error XMP: ' + (r.data.error || '')); }
});


function getPageIdFromQuery(){
  const q = new URLSearchParams(window.location.search);
  return parseInt(q.get('page_id')) || null;
}

document.getElementById('btnWysOpen').addEventListener('click', async ()=>{
  const pid = getPageIdFromQuery() || parseInt(prompt("ID de página:"));
  if(!pid) return;
  // fetch corrected text (ocr_html)
  const r = await axios.get('/page_text', { params: { page_id: pid, corrected: true }}).catch(()=>null);
  const html = (r && r.data && r.data.html) ? r.data.html : '';
  document.getElementById('wysArea').innerHTML = html || '';
  document.getElementById('panel-wysiwyg').style.display = 'block';
  document.getElementById('panel-wysiwyg').dataset.pageId = pid;
});
document.getElementById('btnWysClose').addEventListener('click', ()=>{
  document.getElementById('panel-wysiwyg').style.display = 'none';
});
document.getElementById('btnWysSpell').addEventListener('click', async ()=>{
  const pid = parseInt(document.getElementById('panel-wysiwyg').dataset.pageId);
  if(!pid) return;
  // call /spellcheck to get issues and underline
  const r = await axios.post('/spellcheck', { page_id: pid });
  if(!(r.data && r.data.ok)) { alert('Error en revisión'); return; }
  const issues = r.data.issues || [];
  // naive: underline words present in issues list (pyspellchecker mode)
  const area = document.getElementById('wysArea');
  let html = area.innerHTML;
  issues.forEach(it=>{
    if(it.word){
      const re = new RegExp('(?<!<[^>]*)\\b'+it.word+'\\b','gi');
      html = html.replace(re, `<span class="spell-err" title="Sugerencia: ${it.suggestion||''}" style="text-decoration:underline wavy red;">$&</span>`);
    }
  });
  area.innerHTML = html;
});
document.getElementById('btnWysSave').addEventListener('click', async ()=>{
  const pid = parseInt(document.getElementById('panel-wysiwyg').dataset.pageId);
  const html = document.getElementById('wysArea').innerHTML;
  const r = await axios.post('/save_corrected', { page_id: pid, html: html });
  alert(r.data && r.data.ok ? 'Guardado' : ('Error: '+(r.data.error||'')));
});


async function playTTSStream(corrected){
  // Try to get page_id from query or prompt
  const q = new URLSearchParams(window.location.search);
  const pageId = parseInt(q.get('page_id')) || parseInt(prompt("ID de página para TTS:"));
  if(!pageId) return;
  const url = `/tts_stream?page_id=${pageId}&corrected=${corrected?1:0}&voice=es`;
  const audio = document.getElementById('audioTTS');
  audio.src = url;
  audio.play().catch(()=>{});
}
const btnRaw = document.getElementById('btnTTSRaw');
if(btnRaw){ btnRaw.addEventListener('click', ()=> playTTSStream(false)); }
const btnCorr = document.getElementById('btnTTSCorr');
if(btnCorr){ btnCorr.addEventListener('click', ()=> playTTSStream(true)); }

// Context menu for spell suggestions inside WYSIWYG
const spellMenu = document.getElementById('spellMenu');
document.addEventListener('click', ()=> { spellMenu.style.display='none'; });
document.addEventListener('contextmenu', async (ev)=>{
  if(ev.target && ev.target.classList && ev.target.classList.contains('spell-err')){
    ev.preventDefault();
    const word = ev.target.textContent.trim();
    let items = (ev.target.getAttribute('title')||'').replace('Sugerencia: ','').split(',').filter(Boolean);
    // fetch extra suggestions
    try{
      const r = await axios.post('/spell_suggest', { word: word });
      if(r.data && r.data.ok && r.data.suggestions) items = [...new Set(items.concat(r.data.suggestions))];
    }catch(e){}
    spellMenu.innerHTML = items.slice(0,8).map(s=>`<div class="spell-item" style="padding:6px 10px;cursor:pointer">${s}</div>`).join('') || '<div style="padding:6px 10px">Sin sugerencias</div>';
    Array.from(spellMenu.querySelectorAll('.spell-item')).forEach(el=>{
      el.addEventListener('click', ()=>{
        ev.target.outerHTML = el.textContent; // replace in contenteditable
        spellMenu.style.display='none';
      });
    });
    spellMenu.style.left = ev.pageX+'px';
    spellMenu.style.top = ev.pageY+'px';
    spellMenu.style.display = 'block';
  }
});

// WYSIWYG keyboard shortcuts
(function(){
  const panel = document.getElementById('panel-wysiwyg');
  const area = document.getElementById('wysArea');
  if(!area) return;
  area.addEventListener('keydown', async (e)=>{
    // Ctrl+S => save
    if((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==='s'){
      e.preventDefault();
      document.getElementById('btnWysSave').click();
    }
    // F7 => spellcheck
    if(e.key==='F7'){
      e.preventDefault();
      document.getElementById('btnWysSpell').click();
    }
    // Ctrl+Y => redo
    if((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==='y'){
      document.execCommand('redo'); e.preventDefault();
    }
    // Ctrl+Z => undo
    if((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==='z'){
      document.execCommand('undo'); e.preventDefault();
    }
  });
})();


async function loadVoices(){
  try{
    const r = await axios.get('/tts_voices');
    const sel = document.getElementById('selVoice');
    (r.data||[]).forEach(v=>{
      const opt = document.createElement('option');
      opt.value = v.id; opt.textContent = (v.name||v.id) + (v.lang?` [${v.lang}]`:'');
      sel.appendChild(opt);
    });
  }catch(e){}
}
if(document.getElementById('selVoice')) loadVoices();

document.getElementById('btnAudiobook').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(q.get('document_id')) || parseInt(prompt("ID de documento:"));
  if(!docId) return;
  const corrected = confirm("¿Usar OCR CORREGIDO? (Aceptar) / Original (Cancelar)");
  const voice = document.getElementById('selVoice').value || null;
  const rate = parseInt(document.getElementById('rateTTS').value || 0) || null;
  const volume = parseFloat(document.getElementById('volTTS').value || 1.0);
  const seqFrom = parseInt(prompt("Desde página (seq):", "1")) || 1;
  const seqTo = parseInt(prompt("Hasta página (seq):", "9999")) || 9999;
  const r = await axios.post('/audiobook', { document_id: docId, corrected, voice_id: voice, rate, volume, seq_from: seqFrom, seq_to: seqTo, lang: 'es' });
  if(r.data && r.data.ok){
    alert('Audiolibro generado. Carpeta: ' + r.data.result.tracks[0].split('/').slice(0,-1).join('/'));
    console.log(r.data.result);
  }else{
    alert('Error: ' + (r.data.error||''));
  }
});


const gPanel = document.getElementById('panel-glossary');
document.getElementById('btnGlossary').addEventListener('click', ()=> gPanel.style.display='block');
document.getElementById('btnGlossClose').addEventListener('click', ()=> gPanel.style.display='none');
document.getElementById('btnLoadGloss').addEventListener('click', loadGlossaries);
document.getElementById('btnNewGloss').addEventListener('click', async ()=>{
  const name = prompt("Nombre del glosario:","Glosario de proyecto");
  if(!name) return;
  await axios.post('/glossaries', { scope:'project', name, language:'es', terms:{} });
  loadGlossaries();
});

async function loadGlossaries(){
  const r = await axios.get('/glossaries');
  const list = r.data.glossaries || [];
  const host = document.getElementById('glossList');
  host.innerHTML = '';
  list.forEach(g=>{
    const div = document.createElement('div');
    div.style.border='1px solid #eee'; div.style.padding='6px'; div.style.margin='6px 0';
    div.innerHTML = `<strong>${g.name}</strong> [${g.scope}] <small>${g.language}</small>
    <button data-id="${g.id}" class="btnEdit">Editar</button> <button data-id="${g.id}" class="btnDel">Eliminar</button>
    <pre style="white-space:pre-wrap;background:#fafafa;padding:6px;border:1px solid #f0f0f0;max-height:120px;overflow:auto">${g.terms_json||''}</pre>`;
    host.appendChild(div);
  });
  host.querySelectorAll('.btnDel').forEach(b=> b.addEventListener('click', async ()=>{
    await axios.post('/glossaries/delete', { id: parseInt(b.dataset.id)}); loadGlossaries();
  }));
  host.querySelectorAll('.btnEdit').forEach(b=> b.addEventListener('click', async ()=>{
    const id = parseInt(b.dataset.id);
    const el = b.parentElement.querySelector('pre');
    const txt = prompt("Pegue JSON de términos (abreviatura -> expansión):", el.textContent);
    if(!txt) return;
    let terms = {}; try{ terms = JSON.parse(txt); }catch(e){ alert("JSON inválido"); return; }
    await axios.post('/glossaries/update', { id, terms });
    loadGlossaries();
  }));
}


// Load/set abbreviation style
(async function(){
  try{
    const r = await axios.get('/abbrev_style');
    const sel = document.getElementById('selAbbrevStyle');
    if(sel && r.data && r.data.style){ sel.value = r.data.style; }
    sel.addEventListener('change', async ()=>{
      await axios.post('/abbrev_style', { style: sel.value });
      alert('Estilo actualizado: '+sel.value);
    });
  }catch(e){}
})();

// Import glossary (prompt-based mapping)
document.getElementById('btnImportGloss').addEventListener('click', async ()=>{
  const path = prompt("Ruta del fichero a importar (CSV/JSON/XML):");
  if(!path) return;
  const fmt = (path.toLowerCase().endsWith('.csv')?'csv':(path.toLowerCase().endsWith('.json')?'json':'xml'));
  let field_map = {};
  if(fmt==='csv' || fmt==='xml'){
    const ab = prompt("Nombre de columna/etiqueta para ABREVIATURA (p.ej. 'Abreviatura' o 'abbr'):", "Abreviatura");
    const ex = prompt("Nombre de columna/etiqueta para EXPANSIÓN (p.ej. 'Expansión' o 'expansion'):", "Expansión");
    field_map = { abbr: ab, expansion: ex, item: 'item' };
  }else{
    // JSON puede necesitar mapeo si es lista de objetos
    const useMap = confirm("¿El JSON es lista de objetos? (Aceptar) / Diccionario (Cancelar)");
    if(useMap){
      const ab = prompt("Campo JSON para ABREVIATURA:", "abbr");
      const ex = prompt("Campo JSON para EXPANSIÓN:", "expansion");
      field_map = { abbr: ab, expansion: ex };
    }
  }
  const name = prompt("Nombre del glosario:", "Glosario importado");
  const scope = prompt("Ámbito (global|project|theme):","project");
  const r = await axios.post('/glossary_import', { format: fmt, path, field_map, name, scope });
  alert(r.data && r.data.ok ? ('Importadas: '+r.data.terms) : ('Error: '+(r.data.error||'')));
});

// Export glossary (asks ID and format)
document.getElementById('btnExportGloss').addEventListener('click', async ()=>{
  const id = parseInt(prompt("ID de glosario a exportar:"));
  if(!id) return;
  const fmt = prompt("Formato (csv|json|tei):","csv") || "csv";
  const out = prompt("Ruta de salida (incluye extensión):","/tmp/glosario."+fmt);
  if(!out) return;
  const r = await axios.post('/glossary_export', { id, format: fmt, out });
  alert(r.data && r.data.ok ? ('Exportado: '+r.data.file) : ('Error: '+(r.data.error||'')));
});

// WYSIWYG: highlight abbreviations and click-to-expand (style-aware)
async function highlightAbbreviations(){
  const q = new URLSearchParams(window.location.search);
  const pageId = parseInt(q.get('page_id'));
  if(!pageId) return;
  // fetch corrected text and terms
  const t = await axios.get('/page_text', { params: { page_id: pageId, corrected: true }}).catch(()=>null);
  const html = (t && t.data && t.data.html) ? t.data.html : '';
  const area = document.getElementById('wysArea'); if(!area) return;
  area.innerHTML = html;
  // get hints via spellcheck (returns abbrev_hints too)
  const r = await axios.post('/spellcheck', { page_id: pageId });
  const hints = (r.data && r.data.abbrev_hints) ? r.data.abbrev_hints : [];
  // naive wrap: replace occurrences by span
  let text = area.innerHTML;
  hints.forEach(h=>{
    const ab = h.abbr.replace(/[.*+?^${}()|[\]\]/g, '\\$&');
    const re = new RegExp('(>[^<]*)\\b'+ab+'\\b','g');
    text = text.replace(re, (m)=> m.replace(h.abbr, `<span class="abbr-hint" data-exp="${h.expansion||''}" style="border-bottom:1px dotted #555; cursor:help" title="${h.expansion||''}">${h.abbr}</span>`));
  });
  area.innerHTML = text;
  // click to expand
  area.querySelectorAll('.abbr-hint').forEach(el=>{
    el.addEventListener('click', ()=>{
      const exp = el.getAttribute('data-exp') || '';
      if(!exp) return;
      const doExpand = confirm("Expandir abreviatura a: "+exp+" ?");
      if(doExpand){ el.outerHTML = exp; }
    });
  });
}

const btnWysOpen = document.getElementById('btnWysOpen');
if(btnWysOpen){
  btnWysOpen.addEventListener('click', ()=> setTimeout(highlightAbbreviations, 200));
}


async function autoExpandFirstOccurrence(){
  const area = document.getElementById('wysArea');
  if(!area) return;
  // Determine style (expand first occurrence: yes/no)
  const st = await axios.get('/abbrev_style').catch(()=>({data:{style:'Chicago'}}));
  const style = (st.data && st.data.style)||'Chicago';
  const expandFirst = true; // from current simple policy
  if(!expandFirst) return;
  // expand first occurrence by replacing first .abbr-hint with a span carrying data-original for undo
  const first = area.querySelector('.abbr-hint');
  if(first && !first.classList.contains('expanded')){
    const exp = first.getAttribute('data-exp')||'';
    if(exp){
      const orig = first.textContent;
      first.outerHTML = `<span class="abbr-expanded" data-orig="${orig}" style="background:rgba(255,235,150,.5)">${exp}</span>`;
    }
  }
}

// Undo expansion on click (toggle)
document.addEventListener('click', (ev)=>{
  const el = ev.target;
  if(el && el.classList && el.classList.contains('abbr-expanded')){
    const orig = el.getAttribute('data-orig')||'';
    el.outerHTML = `<span class="abbr-hint" data-exp="${el.textContent}" style="border-bottom:1px dotted #555; cursor:help" title="${el.textContent}">${orig}</span>`;
  }
});

// Hook auto expand after highlight
async function highlightAbbreviationsWithAuto(){
  await highlightAbbreviations();
  await autoExpandFirstOccurrence();
}

const btnWysOpen2 = document.getElementById('btnWysOpen');
if(btnWysOpen2){
  btnWysOpen2.addEventListener('click', ()=> setTimeout(highlightAbbreviationsWithAuto, 250));
}


// Panel Plantillas
const pStyle = document.getElementById('panel-style');
document.getElementById('btnStyleTpl').addEventListener('click', ()=> pStyle.style.display='block');
document.getElementById('btnStyleClose').addEventListener('click', ()=> pStyle.style.display='none');
document.getElementById('btnStyleReload').addEventListener('click', loadStyleTemplates);
document.getElementById('btnStyleNew').addEventListener('click', async ()=>{
  const name = prompt("Nombre de la plantilla:","Chicago 17 base");
  if(!name) return;
  const style_name = prompt("Etiqueta de estilo:","Chicago 17");
  const rules = prompt("Pegue JSON de reglas (opcional):","{"expand_first_occurrence":true}");
  let obj={}; try{ obj = JSON.parse(rules); }catch(e){ obj = {"expand_first_occurrence":true}; }
  await axios.post('/style_templates', { name, style_name, scope:'project', language:'es', rules: obj, meta:{} });
  loadStyleTemplates();
});
async function loadStyleTemplates(){
  const r = await axios.get('/style_templates');
  const list = r.data.templates || [];
  const host = document.getElementById('styleList'); host.innerHTML = '';
  list.forEach(t=>{
    const div = document.createElement('div');
    div.style.border='1px solid #eee'; div.style.padding='6px'; div.style.margin='6px 0';
    div.innerHTML = `<strong>${t.name}</strong> <small>${t.style_name||''}</small> [${t.scope}]<br/>
    <code style="display:block;white-space:pre-wrap;background:#fafafa">${t.rules_json||''}</code>
    <button class="btnApply" data-id="${t.id}">Aplicar al doc actual</button>
    <button class="btnEdit" data-id="${t.id}">Editar</button>
    <button class="btnDel" data-id="${t.id}">Eliminar</button>`;
    host.appendChild(div);
  });
  host.querySelectorAll('.btnDel').forEach(b=> b.addEventListener('click', async ()=>{
    await axios.post('/style_templates/delete', { id: parseInt(b.dataset.id) }); loadStyleTemplates();
  }));
  host.querySelectorAll('.btnEdit').forEach(b=> b.addEventListener('click', async ()=>{
    const id = parseInt(b.dataset.id);
    const rules = prompt("Pegue JSON actualizado de reglas:");
    if(!rules) return;
    let obj={}; try{ obj = JSON.parse(rules); }catch(e){ alert("JSON inválido"); return; }
    await axios.post('/style_templates/update', { id, name: "Plantilla", rules: obj, meta: {} });
    loadStyleTemplates();
  }));
  host.querySelectorAll('.btnApply').forEach(b=> b.addEventListener('click', async ()=>{
    const q = new URLSearchParams(window.location.search);
    const docId = parseInt(q.get('document_id')) || parseInt(prompt("ID de documento:"));
    if(!docId) return;
    const r = await axios.post('/apply_style_doc', { document_id: docId, template_id: parseInt(b.dataset.id) });
    alert(r.data && r.data.ok ? ('Cambios: '+r.data.result.count) : 'Error');
  }));
}
document.getElementById('btnApplyStyleDoc').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(q.get('document_id')) || parseInt(prompt("ID de documento:"));
  if(!docId) return;
  const rules = prompt("JSON de reglas (vacío para estilo actual):","");
  let obj = null; if(rules && rules.trim()){ try{ obj = JSON.parse(rules);}catch(e){ alert("JSON inválido"); return; } }
  const r = await axios.post('/apply_style_doc', { document_id: docId, rules: obj });
  alert(r.data && r.data.ok ? ('Cambios: '+r.data.result.count) : 'Error');
});

// Panel Diff/Merge
const pDiff = document.getElementById('panel-diff');
document.getElementById('btnGlossDiff').addEventListener('click', ()=> pDiff.style.display='block');
document.getElementById('btnDiffClose').addEventListener('click', ()=> pDiff.style.display='none');
document.getElementById('btnDoDiff').addEventListener('click', async ()=>{
  const a = parseInt(document.getElementById('glA').value);
  const b = parseInt(document.getElementById('glB').value);
  if(!a || !b) return;
  const r = await axios.post('/glossary_diff', { a, b });
  const host = document.getElementById('diffResult');
  if(!(r.data && r.data.ok)){ host.textContent = 'Error'; return; }
  const pre = document.createElement('pre');
  pre.textContent = JSON.stringify({only_a:r.data.only_a, only_b:r.data.only_b, conflicts:r.data.conflicts}, null, 2);
  host.innerHTML = ''; host.appendChild(pre);
});
document.getElementById('btnMergeBase').addEventListener('click', async ()=>{
  const a = parseInt(document.getElementById('glA').value);
  const b = parseInt(document.getElementById('glB').value);
  if(!a || !b) return;
  const r = await axios.post('/glossary_merge', { base: a, other: b, strategy: 'prefer_base' });
  alert(r.data && r.data.ok ? 'Fusionado en A' : 'Error');
});
document.getElementById('btnMergeOther').addEventListener('click', async ()=>{
  const a = parseInt(document.getElementById('glA').value);
  const b = parseInt(document.getElementById('glB').value);
  if(!a || !b) return;
  const r = await axios.post('/glossary_merge', { base: a, other: b, strategy: 'prefer_other' });
  alert(r.data && r.data.ok ? 'Fusionado en A (preferir B)' : 'Error');
});


document.getElementById('btnOpenDiff').addEventListener('click', ()=>{
  window.open('/static/wireframe_diff_review.html', '_blank');
});
document.getElementById('btnOpenRules').addEventListener('click', ()=>{
  window.open('/static/wireframe_context_rules.html', '_blank');
});
document.getElementById('btnOpenExport').addEventListener('click', ()=>{
  window.open('/static/wireframe_export_panel.html', '_blank');
});


// ---- Diff Review Live ----
function renderTokens(container, tokens){
  const host = document.getElementById(container); if(!host) return;
  let html = '<h4>'+ (container=='diffColA'?'OCR Original':(container=='diffColB'?'OCR Corregido':'Estilizado')) +'</h4><p>';
  for(const t of tokens){
    if(Array.isArray(t)) continue;
    const [kind, val] = t;
    if(kind==='keep'){ html += val; }
    else if(kind==='ins'){ html += '<span class="ins" style="background:#e6ffed;border:1px solid #b7f5c7">'+val+'</span>'; }
    else if(kind==='del'){ html += '<span class="del" style="text-decoration:line-through;background:#ffecec;border:1px solid #ffb3b3">'+val+'</span>'; }
    else if(kind==='sub'){ const a=val[0], b=val[1]; html += '<span class="sub" style="background:#fff4cc;border:1px solid #ffd24d" title="'+a+'">'+b+'</span>'; }
    else { html += val; }
  }
  html += '</p>';
  host.innerHTML = html;
}

async function loadDiff(pageId){
  const r = await axios.get('/diff_page', { params: { page_id: pageId }});
  if(!(r.data && r.data.ok)){ alert('No se pudo cargar diff'); return; }
  renderTokens('diffColA', r.data.diffs.orig_vs_corr);
  renderTokens('diffColB', r.data.diffs.orig_vs_corr); // showing corrected as target
  renderTokens('diffColC', r.data.diffs.corr_vs_style);
  const side = document.getElementById('diffSide');
  side.innerHTML = '<h4>Cambios</h4><p>orig_vs_corr: '+r.data.diffs.orig_vs_corr.length+' tokens<br/>corr_vs_style: '+r.data.diffs.corr_vs_style.length+' tokens</p>';
}

function openDiffLive(){
  const q = new URLSearchParams(window.location.search);
  const pageId = parseInt(q.get('page_id')) || parseInt(prompt("ID de página:"));
  if(!pageId) return;
  document.getElementById('panel-diff-live').style.display='block';
  loadDiff(pageId);
  // wire buttons
  document.getElementById('btnDiffAccept').onclick = async ()=>{
    await axios.post('/review_apply', { page_id: pageId, decision: 'accept' });
    alert('Aplicado estilo como corregido');
  };
  document.getElementById('btnDiffReject').onclick = async ()=>{
    await axios.post('/review_apply', { page_id: pageId, decision: 'reject' });
    alert('Sin cambios');
  };
  document.getElementById('btnDiffRevert').onclick = async ()=>{
    await axios.post('/review_apply', { page_id: pageId, decision: 'revert' });
    alert('Revertido a OCR original');
  };
  document.getElementById('btnDiffClose').onclick = ()=> document.getElementById('panel-diff-live').style.display='none';
}

const btnOpenDiff = document.getElementById('btnOpenDiff');
if(btnOpenDiff){
  btnOpenDiff.addEventListener('click', openDiffLive);
}


// Export modal live
function openExportLive(){
  document.getElementById('panel-export-live').style.display = 'block';
}
const btnOpenExport = document.getElementById('btnOpenExport');
if(btnOpenExport){ btnOpenExport.addEventListener('click', openExportLive); }

document.getElementById('btnExpClose').addEventListener('click', ()=>{
  document.getElementById('panel-export-live').style.display = 'none';
});

document.getElementById('btnExpRun').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(document.getElementById('expDocId').value || q.get('document_id') || '0');
  const out = document.getElementById('expOut').value || '/tmp';
  const base = document.getElementById('expBaseImg').value || '';
  const zones = document.getElementById('expTEIZones').checked;
  const dcxml = document.getElementById('expDCXML').checked;
  const log = document.getElementById('expLog'); log.textContent = 'Ejecutando...\n';
  try{
    const iiif = await axios.post('/export/iiif', { document_id: docId, out, base_img_url: base });
    log.textContent += 'IIIF: '+iiif.data.file+'\n';
    const tei = await axios.post('/export/tei', { document_id: docId, out, include_zones: zones });
    log.textContent += 'TEI: '+tei.data.file+'\n';
    const dc = await axios.post('/export/dc', { document_id: docId, out });
    log.textContent += 'DC JSON-LD: '+dc.data.file+'\n';
    if(dcxml){
      const dcx = await axios.post('/export/dc', { document_id: docId, out, to_xml: true });
      log.textContent += 'DC XML: '+dcx.data.file+'\n';
    }
    const gj = await axios.post('/export/geojson', { document_id: docId, out });
    log.textContent += 'GeoJSON: '+gj.data.file+'\n';
    const val = await axios.post('/export/validate', { paths: [iiif.data.file, tei.data.file, dc.data.file, gj.data.file] });
    log.textContent += 'Validación: '+JSON.stringify(val.data.exists, null, 2)+'\nHecho.';
  }catch(e){
    log.textContent += 'Error: '+(e.message||e);
  }
});

document.getElementById('btnExpValidate').addEventListener('click', async ()=>{
  const out = document.getElementById('expOut').value || '/tmp';
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(document.getElementById('expDocId').value || q.get('document_id') || '0');
  const paths = [`${out}/iiif_manifest_doc_${docId}.json`, `${out}/tei_doc_${docId}.xml`, `${out}/dc_doc_${docId}.jsonld`, `${out}/geo_doc_${docId}.geojson`];
  const val = await axios.post('/export/validate', { paths });
  document.getElementById('expLog').textContent = 'Validación: '+JSON.stringify(val.data.exists, null, 2);
});


// Load REST config on open
async function loadRestCfg(){
  try{
    const r = await axios.get('/rest_config');
    if(r.data && r.data.config){
      if(r.data.config.base_url) document.getElementById('restBase').value = r.data.config.base_url;
      if(r.data.config.jwt) document.getElementById('restJWT').value = r.data.config.jwt;
    }
  }catch(e){}
}
if(document.getElementById('panel-export-live')){ loadRestCfg(); }

document.getElementById('btnSaveRest').addEventListener('click', async ()=>{
  const base = document.getElementById('restBase').value || '';
  const jwt = document.getElementById('restJWT').value || '';
  await axios.post('/rest_config', { base_url: base, jwt });
  alert('Config REST guardada');
});

// Publish toggle wired into run
document.getElementById('btnExpRun').addEventListener('click', async ()=>{
  const q = new URLSearchParams(window.location.search);
  const docId = parseInt(document.getElementById('expDocId').value || q.get('document_id') || '0');
  const out = document.getElementById('expOut').value || '/tmp';
  const base = document.getElementById('expBaseImg').value || '';
  const zones = document.getElementById('expTEIZones').checked;
  const dcxml = document.getElementById('expDCXML').checked;
  const log = document.getElementById('expLog'); log.textContent = 'Ejecutando...\n';
  try{
    const iiif = await axios.post('/export/iiif', { document_id: docId, out, base_img_url: base });
    log.textContent += 'IIIF: '+iiif.data.file+'\n';
    const val = await axios.post('/export/iiif_validate', { path: iiif.data.file });
    log.textContent += 'IIIF Validación: '+(val.data.ok?'OK':'Problemas: '+JSON.stringify(val.data.problems))+'\n';
    const tei = await axios.post('/export/tei', { document_id: docId, out, include_zones: zones });
    log.textContent += 'TEI: '+tei.data.file+'\n';
    const dc = await axios.post('/export/dc', { document_id: docId, out });
    log.textContent += 'DC JSON-LD: '+dc.data.file+'\n';
    if(dcxml){
      const dcx = await axios.post('/export/dc', { document_id: docId, out, to_xml: true });
      log.textContent += 'DC XML: '+dcx.data.file+'\n';
    }
    const gj = await axios.post('/export/geojson', { document_id: docId, out });
    log.textContent += 'GeoJSON: '+gj.data.file+'\n';
    if(document.getElementById('expPublish').checked){
      const baseRest = document.getElementById('restBase').value || '';
      const jwt = document.getElementById('restJWT').value || '';
      const pub = await axios.post('/export/publish', { document_id: docId, out, base_img_url: base, endpoint: baseRest? (baseRest.replace(/\/$/,'') + '/api/documentos'): null, jwt });
      log.textContent += 'Publicación: '+(pub.data.ok?'OK':'Fallo')+' → '+pub.data.msg+'\nBundle: '+pub.data.bundle+'\n';
    }
    log.textContent += 'Hecho.';
  }catch(e){
    log.textContent += 'Error: '+(e.message||e);
  }
});
