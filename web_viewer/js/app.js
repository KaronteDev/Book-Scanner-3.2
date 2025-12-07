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
  try {
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
  } catch(e){
    console.error('loadAnnotations error', e);
    showError('cargando anotaciones', e);
  }
}
window.addEventListener('DOMContentLoaded', init);

document.getElementById('btnPull').addEventListener('click', async () => {
  try {
    const q = new URLSearchParams(window.location.search);
    const docId = q.get('document_id');
    await axios.get('/pull_annotations', { params: { document_id: docId } });
    await loadAnnotations(docId);
    alert('Anotaciones descargadas');
  } catch(e){
    console.error('btnPull error', e);
    showError('descargando anotaciones', e);
  }
});


document.getElementById('btnRunSearch').addEventListener('click', async () => {
  try {
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
  } catch(e){
    console.error('btnRunSearch error', e);
    showError('en búsqueda de anotaciones', e);
  }
});


async function loadProsopo(document_id){
  try {
    const r = await axios.get('/prosopo', { params: { document_id } });
    const p = r.data.persons || []; const g = r.data.places || [];
    const lp = document.getElementById('listPersons'); const lg = document.getElementById('listPlaces');
    lp.innerHTML = ''; lg.innerHTML = '';
    p.forEach(it => { const li=document.createElement('li'); li.textContent = `${it.id} · ${it.count}`; lp.appendChild(li); });
    g.forEach(it => { const li=document.createElement('li'); li.textContent = `${it.id} · ${it.count}`; lg.appendChild(li); });
  } catch(e){
    console.error('loadProsopo error', e);
    showError('cargando prosopografía', e);
  }
}

(async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  await loadProsopo(docId);
})();


async function renderSigma(document_id){
  try {
    if (!document_id) return;
    if (typeof graphology === 'undefined' || typeof Sigma === 'undefined') {
      console.warn('Graphology or Sigma library not loaded');
      return;
    }
    const r = await axios.get('/graph', { params: { document_id } });
    const G = new graphology.Graph();
    (r.data.nodes || []).forEach(n => { G.addNode(n.key, n); });
    (r.data.edges || []).forEach(e => { if(!G.hasEdge(e.key)) G.addEdge(e.source, e.target, e); });
    if (window.graphologyLayoutRandom) {
      graphologyLayoutRandom.assign(G);
    }
    const container = document.getElementById("sigma-container");
    if (container) {
      const renderer = new Sigma(G, container);
    }
  } catch(e){
    console.error('renderSigma error', e);
    showError('cargando grafo', e);
  }
}

(async () => {
  const q = new URLSearchParams(window.location.search);
  const docId = q.get('document_id');
  await renderSigma(docId);
})();


document.getElementById('btnLoadOCR').addEventListener('click', async () => {
  try {
    const q = new URLSearchParams(window.location.search);
    const docId = q.get('document_id');
    const seq = document.getElementById('ocrSeq').value;
    const res = await axios.get('/ocr_text', { params: { document_id: docId, seq: seq } });
    document.getElementById('ocrBox').value = res.data.ocr_text || '';
  } catch(e){
    console.error('btnLoadOCR error', e);
    showError('cargando OCR', e);
  }
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
  try {
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
      const revs = await axios.get('/ocr_revisions', { params:{ document_id: docId, seq: seq } });
      if((revs.data.revisions||[]).length>0){
        // For now use current corrected baseline (no dedicated revision fetch body endpoint)
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
  } catch(e){
    console.error('loadComparator error', e);
    showError('cargando comparador', e);
  }
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
  try {
    const revs = await axios.get('/ocr_revisions', { params:{ document_id: docId, seq: seq } });
    const sel = document.getElementById('revSelect');
    sel.innerHTML = '';
    (revs.data.revisions||[]).forEach(rv => {
      const opt = document.createElement('option');
      opt.value = rv.id; opt.textContent = `v${rv.version} · ${rv.user||''} · ${rv.created_at||''}`;
      sel.appendChild(opt);
    });
  } catch(e){
    console.error('populateRevisions error', e);
    showError('cargando revisiones', e);
  }
}

document.getElementById('btnLoadRevision').addEventListener('click', async () => {
  try {
    const rid = document.getElementById('revSelect').value;
    if(!rid) return;
    const r = await axios.get('/ocr_revision_body', { params:{ revision_id: rid } });
    const right = document.getElementById('rightPane');
    if(r.data && r.data.ocr_html){
      right.innerHTML = r.data.ocr_html;
    }else{
      right.innerText = r.data.ocr_text || '';
    }
  } catch(e){
    console.error('btnLoadRevision error', e);
    showError('cargando revisión', e);
  }
});

document.getElementById('btnRestoreRevision').addEventListener('click', async () => {
  try {
    const rid = document.getElementById('revSelect').value;
    if(!rid) return;
    if(!confirm('¿Restaurar esta revisión como la versión actual?')) return;
    const r = await axios.post('/restore_ocr_revision', { revision_id: parseInt(rid) });
    if(r.data && r.data.ok){ alert('Revisión restaurada.'); } else { alert('Error al restaurar.'); }
  } catch(e){
    console.error('btnRestoreRevision error', e);
    showError('restaurando revisión', e);
  }
});

document.getElementById('btnSignRevision').addEventListener('click', async () => {
  try {
    const rid = document.getElementById('revSelect').value;
    if(!rid) return;
    const who = prompt('Autor/Responsable de la firma:', 'web-editor');
    const note = prompt('Anotación de firma (opcional):', '');
    const r = await axios.post('/sign_ocr_revision', { revision_id: parseInt(rid), user: who||'web-editor', signature: note||'' });
    if(r.data && r.data.ok){ alert('Revisión firmada.'); } else { alert('Error al firmar.'); }
  } catch(e){
    console.error('btnSignRevision error', e);
    showError('firmando revisión', e);
  }
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
  try {
    const r = await axios.get('/ocr_text', { params:{ document_id: docId, seq: seq } });
    return r.data.ocr_text || '';
  } catch(e){
    console.error('currentBaseline error', e);
    return '';
  }
}

// Override save handler to include changes_html when Track changes
// Limpieza: eliminado oldSaveHandler no utilizado tras redefinir lógica de guardado
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
  try {
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
  } catch(e){
    console.error('btnApplyPartial error', e);
    showError('aplicando restauración parcial', e);
  }
});

// On load
(async () => { await loadUserRole(); })();


document.getElementById('btnApplyRange').addEventListener('click', async ()=>{
  try {
    const rid = document.getElementById('revSelect').value;
    if(!rid){ alert('Selecciona una revisión.'); return; }
    const a = parseInt(document.getElementById('charRangeStart').value||'0');
    const b = parseInt(document.getElementById('charRangeEnd').value||'0');
    if(!(b>a)){ alert('Rango inválido'); return; }
    const r = await axios.get('/ocr_revision_body', { params:{ revision_id: rid } });
    const src = (r.data && (r.data.ocr_text || r.data.ocr_html)) ? (r.data.ocr_text || r.data.ocr_html).toString() : '';
    const snippet = src.substring(a, b);
    const rp = document.getElementById('rightPane');
    rp.focus();
    const sel = window.getSelection();
    if(!sel.rangeCount){ alert('Selecciona el texto a reemplazar en el panel derecho.'); return; }
    const range = sel.getRangeAt(0);
    range.deleteContents();
    range.insertNode(document.createTextNode(snippet));
    sel.removeAllRanges();
  } catch(e){
    console.error('btnApplyRange error', e);
    showError('aplicando rango', e);
  }
});

document.getElementById('btnExportAudit').addEventListener('click', ()=>{
  window.open('/export_audit?format=csv','_blank');
});

// Utility: save merged as a new revision via /apply_partial_restore_chars
async function saveMergedFinal(){
  try {
    const q = new URLSearchParams(window.location.search);
    const docId = parseInt(q.get('document_id')); const seq = parseInt(document.getElementById('cmpSeq').value);
    const right = document.getElementById('rightPane');
    const text = right.innerText; const html = right.innerHTML;
    const roleResp = await axios.get('/user_role');
    await axios.post('/apply_partial_restore_chars', { document_id: docId, seq: seq, final_text: text, final_html: html, user: roleResp.data.user, role: roleResp.data.role });
    alert('Guardado como nueva revisión (caracteres).');
  } catch(e){
    console.error('saveMergedFinal error', e);
    showError('guardando revisión fusionada', e);
  }
}


async function setState(level){
  try {
    const q = new URLSearchParams(window.location.search);
    const docId = parseInt(q.get('document_id')); 
    const seq = parseInt(document.getElementById('cmpSeq') ? document.getElementById('cmpSeq').value : 0);
    const state = document.getElementById('stateSelect').value;
    const payload = { level, state, document_id: docId };
    if(level==='page') payload.seq = seq;
    const r = await axios.post('/change_state', payload);
    if(r.data && r.data.ok){ alert('Estado actualizado: '+r.data.state); } else { alert('No permitido o error.'); }
  } catch(e){
    console.error('setState error', e);
    showError('cambiando estado', e);
  }
}

document.getElementById('btnSetStatePage').addEventListener('click', ()=> setState('page'));
document.getElementById('btnSetStateDoc').addEventListener('click', ()=> setState('document'));

document.getElementById('btnLoadQuality').addEventListener('click', async ()=>{
  try {
    const q = new URLSearchParams(window.location.search);
    const docId = parseInt(q.get('document_id')); 
    const r = await axios.get('/ocr_quality_dashboard', { params: { document_id: docId } });
    const tb = document.querySelector('#tblQuality tbody'); tb.innerHTML='';
    (r.data.pages||[]).forEach(row => {
      const tr=document.createElement('tr');
      tr.innerHTML = `<td>${row.seq}</td><td>${row.state}</td><td>${(row.similarity*100).toFixed(1)}%</td>`;
      tb.appendChild(tr);
    });
  } catch(e){
    console.error('btnLoadQuality error', e);
    showError('cargando panel de calidad', e);
  }
});

document.getElementById('btnPublishDoc').addEventListener('click', async ()=>{
  try {
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
  } catch(e){
    console.error('btnPublishDoc error', e);
    showError('publicando documento', e);
  }
});


document.getElementById('btnBatchQuality').addEventListener('click', async ()=>{
  try {
    const q = new URLSearchParams(window.location.search);
    const docId = parseInt(q.get('document_id'));
    const r = await axios.post('/run_quality_batch', { document_id: docId });
    if(r.data && r.data.ok){ alert('Análisis por lotes lanzado. Páginas: '+r.data.result.processed); } else { alert('Error: '+(r.data.error||'')); }
  } catch(e){
    console.error('btnBatchQuality error', e);
    showError('lanzando análisis por lotes', e);
  }
});

document.getElementById('btnShowSched').addEventListener('click', async ()=>{
  try {
    const r = await axios.get('/scheduler_status');
    alert('Última ejecución: ' + (r.data.last_run || '—') + '\nResultado: ' + JSON.stringify(r.data.result || {}));
  } catch(e){
    console.error('btnShowSched error', e);
    showError('consultando scheduler', e);
  }
});


document.getElementById('btnLoadCalib').addEventListener('click', async ()=>{
  try {
    const r = await axios.get('/calibration');
    alert('Calibración:\n' + JSON.stringify(r.data, null, 2));
  } catch(e){
    console.error('btnLoadCalib error', e);
    showError('cargando calibración', e);
  }
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
  try {
    const q = new URLSearchParams(window.location.search);
    const docId = parseInt(q.get('document_id'));
    const r = await axios.post('/enhance_project', { document_id: docId });
    if(r.data && r.data.ok){ alert('Mejora por lotes lanzada. Páginas: '+r.data.result.processed); } else { alert('Error: '+(r.data.error||'')); }
  } catch(e){
    console.error('btnEnhanceProj error', e);
    alert('Error lanzando mejora: ' + (e.message||e));
  }
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
  try {
    const q = new URLSearchParams(window.location.search);
    const pageId = parseInt(q.get('page_id')) || parseInt(prompt("ID de página para TTS:"));
    if(!pageId) return;
    const r = await axios.post('/tts', { page_id: pageId, corrected: corrected, voice: 'es'});
    if(r.data && r.data.ok){
      alert('Archivo TTS listo: ' + r.data.file);
    }else{
      alert('Error TTS: ' + (r.data.error || ''));
    }
  } catch(e){
    console.error('runTTS error', e);
    showError('generando TTS', e);
  }
}
document.getElementById('btnTTSRaw').addEventListener('click', ()=> runTTS(false));
document.getElementById('btnTTSCorr').addEventListener('click', ()=> runTTS(true));

document.getElementById('btnSpellCheck').addEventListener('click', async ()=>{
  try {
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
  } catch(e){
    console.error('btnSpellCheck error', e);
    showError('ejecutando revisión ortográfica', e);
  }
});

document.getElementById('btnXMP').addEventListener('click', async ()=>{
  try {
    const q = new URLSearchParams(window.location.search);
    const pageId = parseInt(q.get('page_id')) || parseInt(prompt("ID de página XMP:"));
    if(!pageId) return;
    const r = await axios.post('/xmp_sidecar', { page_id: pageId });
    if(r.data && r.data.ok){ alert('XMP creado: ' + r.data.file); } else { alert('Error XMP: ' + (r.data.error || '')); }
  } catch(e){
    console.error('btnXMP error', e);
    showError('generando XMP', e);
  }
});


function getPageIdFromQuery(){
  const q = new URLSearchParams(window.location.search);
  return parseInt(q.get('page_id')) || null;
}

document.getElementById('btnWysOpen').addEventListener('click', async ()=>{
  try {
    const pid = getPageIdFromQuery() || parseInt(prompt("ID de página:"));
    if(!pid) return;
    const r = await axios.get('/page_text', { params: { page_id: pid, corrected: true }}).catch(()=>null);
    const html = (r && r.data && r.data.html) ? r.data.html : '';
    document.getElementById('wysArea').innerHTML = html || '';
    document.getElementById('panel-wysiwyg').style.display = 'block';
    document.getElementById('panel-wysiwyg').dataset.pageId = pid;
    // Lanzar resaltado y auto-expand tras apertura
    setTimeout(()=>{ try{ highlightAbbreviationsWithAuto(); }catch(e){ console.warn('highlightAbbreviationsWithAuto fallo', e); } }, 250);
  } catch(e){
    console.error('btnWysOpen error', e);
    showError('abriendo WYSIWYG', e);
  }
});
document.getElementById('btnWysClose').addEventListener('click', ()=>{
  document.getElementById('panel-wysiwyg').style.display = 'none';
});
document.getElementById('btnWysSpell').addEventListener('click', async ()=>{
  try {
    const pid = parseInt(document.getElementById('panel-wysiwyg').dataset.pageId);
    if(!pid) return;
    const r = await axios.post('/spellcheck', { page_id: pid });
    if(!(r.data && r.data.ok)) { alert('Error en revisión'); return; }
    const issues = r.data.issues || [];
    const area = document.getElementById('wysArea');
    let html = area.innerHTML;
    issues.forEach(it=>{
      if(it.word){
        const re = new RegExp('(?<!<[^>]*)\\b'+it.word+'\\b','gi');
        html = html.replace(re, `<span class="spell-err" title="Sugerencia: ${it.suggestion||''}" style="text-decoration:underline wavy red;">$&</span>`);
      }
    });
    area.innerHTML = html;
  } catch(e){
    console.error('btnWysSpell error', e);
    showError('revisión ortográfica WYSIWYG', e);
  }
});
document.getElementById('btnWysSave').addEventListener('click', async ()=>{
  try {
    const pid = parseInt(document.getElementById('panel-wysiwyg').dataset.pageId);
    const html = document.getElementById('wysArea').innerHTML;
    const r = await axios.post('/save_corrected', { page_id: pid, html: html });
    alert(r.data && r.data.ok ? 'Guardado' : ('Error: '+(r.data.error||'')));
  } catch(e){
    console.error('btnWysSave error', e);
    showError('guardando WYSIWYG', e);
  }
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


// ---- Drag & Resize Panels (glossary, style templates, diff) ----
function attachDragResize(panel){
  if(!panel) return;
  // Helper persistence functions
  function savePanelState(p){
    try{
      const st = { left: p.style.left, top: p.style.top, width: p.style.width, height: p.style.height };
      localStorage.setItem('panelState_'+p.id, JSON.stringify(st));
    }catch(e){}
  }
  function markConverted(p){ if(p.style.right){ p.style.right=''; } }
  // Header: first child div acts as drag handle
  const header = panel.querySelector('div');
  if(header){ header.classList.add('drag-header'); }
  // Add resize handle
  if(!panel.querySelector('.resize-handle')){
    const h = document.createElement('div'); h.className='resize-handle'; panel.appendChild(h);
    
    let resizing=false, startX=0,startY=0,startW=0,startH=0;
    h.addEventListener('mousedown', (e)=>{
      e.preventDefault(); 
      e.stopPropagation();
      resizing=true; 
      startX=e.clientX; 
      startY=e.clientY; 
      startW=panel.offsetWidth; 
      startH=panel.offsetHeight;
      document.addEventListener('mousemove', resizeMove); 
      document.addEventListener('mouseup', stopResize);
    });
    function resizeMove(e){
      if(!resizing) return;
      const dx = e.clientX - startX; const dy = e.clientY - startY;
      const newW = Math.max(340, startW + dx); const newH = Math.max(180, startH + dy);
      panel.style.width = newW + 'px'; panel.style.height = newH + 'px';
    }
    function stopResize(){ 
      resizing=false; 
      document.removeEventListener('mousemove', resizeMove); 
      document.removeEventListener('mouseup', stopResize); 
      savePanelState(panel); 
    }
  }
  let dragging=false, offX=0, offY=0;
  function toLeftTop(){
    // Convert right positioning to left for free dragging only once
    if(panel.style.right){
      const rect = panel.getBoundingClientRect();
      panel.style.left = rect.left + 'px';
      panel.style.top = rect.top + 'px';
      panel.style.right = '';
    }
  }
  header && header.addEventListener('mousedown', (e)=>{
    if(e.target.closest('.resize-handle')) return;
    dragging=true; toLeftTop(); offX = e.clientX - panel.getBoundingClientRect().left; offY = e.clientY - panel.getBoundingClientRect().top;
    document.addEventListener('mousemove', dragMove); document.addEventListener('mouseup', stopDrag);
  });
  function dragMove(e){
    if(!dragging) return;
    const vw = window.innerWidth; const vh = window.innerHeight;
    let x = e.clientX - offX; let y = e.clientY - offY;
    const maxX = vw - panel.offsetWidth - 4; const maxY = vh - panel.offsetHeight - 4;
    x = Math.max(0, Math.min(maxX, x)); y = Math.max(0, Math.min(maxY, y));
    panel.style.left = x + 'px'; panel.style.top = y + 'px';
  }
  function stopDrag(){ dragging=false; document.removeEventListener('mousemove', dragMove); document.removeEventListener('mouseup', stopDrag); savePanelState(panel); }
  // Restore previous state if exists
  try{
    const raw = localStorage.getItem('panelState_'+panel.id);
    if(raw){
      const s = JSON.parse(raw);
      if(s.left) panel.style.left = s.left;
      if(s.top) panel.style.top = s.top;
      if(s.width) panel.style.width = s.width;
      if(s.height) panel.style.height = s.height;
      markConverted(panel);
    }
  }catch(e){}
}

function initDragPanels(){
  ['panel-glossary','panel-style','panel-diff'].forEach(id=> {
    const panel = document.getElementById(id);
    if(panel && !panel.classList.contains('modal')) attachDragResize(panel);
  });
}

// Helper to ensure panel is initialized before showing
function showPanel(panelId, callback){
  const panel = document.getElementById(panelId);
  if(!panel) {
    console.warn('Panel not found:', panelId);
    return;
  }
  // If it's a Bootstrap modal, use the modal API
  if(panel.classList.contains('modal')){
    try{
      const modal = bootstrap.Modal.getOrCreateInstance(panel, {backdrop: true, keyboard: true, focus: true});
      if(callback){
        panel.addEventListener('shown.bs.modal', function onShown(){
          panel.removeEventListener('shown.bs.modal', onShown);
          callback();
        });
      }
      modal.show();
      return;
    }catch(e){ console.warn('Bootstrap modal not available, falling back.', e); }
  }
  // Fallback to legacy floating panel
  if(!panel.querySelector('.resize-handle')){
    attachDragResize(panel);
  }
  panel.style.display = 'block';
  if(callback) callback();
}

// Panel Glosarios
const btnGlossary = document.getElementById('btnGlossary');
const btnGlossClose = document.getElementById('btnGlossClose');
const btnLoadGloss = document.getElementById('btnLoadGloss');
const btnNewGloss = document.getElementById('btnNewGloss');

if(btnGlossary){
  btnGlossary.addEventListener('click', ()=> { 
    showPanel('panel-glossary', loadGlossariesIfNeeded);
  });
}
if(btnGlossClose){
  btnGlossClose.addEventListener('click', ()=> {
    const gPanel = document.getElementById('panel-glossary');
    if(!gPanel) return;
    if(gPanel.classList.contains('modal')){
      const inst = bootstrap.Modal.getInstance(gPanel) || bootstrap.Modal.getOrCreateInstance(gPanel);
      inst.hide();
    } else {
      gPanel.style.display='none';
    }
  });
}
if(btnLoadGloss){
  btnLoadGloss.addEventListener('click', loadGlossaries);
}
if(btnNewGloss){
  btnNewGloss.addEventListener('click', ()=>{
    const form = document.getElementById('glossCreate');
    if(form){ form.scrollIntoView({behavior:'smooth'}); form.classList.add('pulse'); setTimeout(()=>form.classList.remove('pulse'),1200); }
  });
}

// Import CSV glossary
document.getElementById('btnGlossImport').addEventListener('click', async ()=>{
  const name = prompt('Nombre para el glosario importado:','Maritime');
  if(!name) return;
  const inp = document.createElement('input'); inp.type='file'; inp.accept='.csv,text/csv';
  inp.onchange = async () => {
    const file = inp.files[0]; if(!file) return;
    const text = await file.text();
    const lines = text.split(/\r?\n/).filter(l=>l.trim()!=='');
    if(lines.length<2){ alert('CSV vacío'); return; }
    const header = lines[0].split(/[,;]/).map(h=>h.trim().toLowerCase());
    // Buscar columnas para abreviatura y expansión
    let colAb = header.findIndex(h=>/(abreviatura|abbr|termino|término)/.test(h));
    let colEx = header.findIndex(h=>/(expansión|expansion|definicion|definición|meaning)/.test(h));
    if(colAb===-1 || colEx===-1){ alert('No se encontraron columnas de abreviatura / expansión'); return; }
    const terms = {};
    for(let i=1;i<lines.length;i++){
      const row = lines[i].split(/[,;]/);
      if(row.length<=Math.max(colAb,colEx)) continue;
      const ab = (row[colAb]||'').trim();
      const ex = (row[colEx]||'').trim();
      if(ab) terms[ab]=ex;
    }
    try{
      const r = await axios.post('/glossaries/import_inline', { scope:'project', name, language:'es', terms });
      if(r.data && r.data.ok){
        alert('Importado '+r.data.created+' términos');
        loadGlossaries();
      }else{
        alert('Error al importar');
      }
    }catch(e){ alert('Fallo en la importación'); }
  };
  inp.click();
});

// Export helpers (CSV/JSON/TEI)
function exportGloss(id, fmt, name){
  if(!id){ alert('ID de glosario requerido'); return; }
  const safeName = (name || 'glosario').replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_\-\s]/g, '_').replace(/\s+/g, '_');
  const filename = `${safeName}.${fmt}`;
  
  // Obtener el glosario y descargarlo directamente
  axios.get(`/glossaries`).then(async res => {
    const glossaries = res.data.glossaries || [];
    const glossary = glossaries.find(g => g.id === id);
    if(!glossary) { alert('Glosario no encontrado'); return; }
    
    let terms = {};
    try { terms = JSON.parse(glossary.terms_json || '{}'); } catch(e) { terms = {}; }
    
    let content, mimeType;
    if(fmt === 'csv'){
      // Generar CSV
      let csv = 'Abreviatura,Expansión\n';
      Object.entries(terms).forEach(([ab, ex]) => {
        csv += '"' + ab.replace(/"/g, '""') + '","' + ex.replace(/"/g, '""') + '"\n';
      });
      content = csv;
      mimeType = 'text/csv;charset=utf-8;';
    } else if(fmt === 'json'){
      // Generar JSON
      content = JSON.stringify(terms, null, 2);
      mimeType = 'application/json;charset=utf-8;';
    } else if(fmt === 'tei'){
      // Generar TEI XML básico
      let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<list>\n';
      Object.entries(terms).forEach(([ab, ex]) => {
        const escAb = ab.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const escEx = ex.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        xml += `  <item>\n    <abbr>${escAb}</abbr>\n    <expan>${escEx}</expan>\n  </item>\n`;
      });
      xml += '</list>';
      content = xml;
      mimeType = 'application/xml;charset=utf-8;';
    }
    
    // Descargar archivo
    const blob = new Blob([content], {type: mimeType});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      document.body.removeChild(a);
    }, 100);
  }).catch(e => {
    const msg = e.response?.data?.error || e.message || 'Error al exportar';
    alert('Error al exportar: ' + msg);
  });
}

// Import TEI glossary
const btnImpTEI = document.getElementById('btnGlossImportTEI');
if(btnImpTEI){
  btnImpTEI.addEventListener('click', ()=>{
    const name = prompt('Nombre para el glosario TEI:', 'Glosario TEI');
    if(!name) return;
    const inp = document.createElement('input'); inp.type='file'; inp.accept='.xml,.tei,text/xml,application/xml';
    inp.onchange = async () => {
      const file = inp.files[0]; if(!file) return;
      const text = await file.text();
      let terms = {};
      try{
        const dom = new DOMParser().parseFromString(text, 'application/xml');
        const items = dom.querySelectorAll('list > item');
        items.forEach(item=>{
          const ab = (item.querySelector('abbr')||{}).textContent || '';
          const ex = (item.querySelector('expan')||{}).textContent || '';
          if(ab.trim()) terms[ab.trim()] = ex.trim();
        });
      }catch(e){ alert('Error parseando TEI'); return; }
      try{
        const r = await axios.post('/glossaries/import_inline', { scope:'project', name, language:'es', terms });
        alert(r.data && r.data.ok ? ('Importados '+r.data.created+' términos') : ('Error: '+(r.data.error||'')));
        if(r.data && r.data.ok) loadGlossaries();
      }catch(e){ alert('Fallo en la importación'); }
    };
    inp.click();
  });
}

async function loadGlossaries(){
  try {
    const r = await axios.get('/glossaries');
    const list = r.data.glossaries || [];
    const host = document.getElementById('glossList');
    host.innerHTML = '';
    list.forEach(g=>{
    let termsObj = {};
    try{ termsObj = JSON.parse(g.terms_json||'{}'); }catch(e){ termsObj = {}; }
    const total = Object.keys(termsObj).length;
    const div = document.createElement('div');
    div.className = 'gloss-entry';
    div.innerHTML = `
      <div class="gloss-header">
        <span class="gloss-name">${g.name}</span>
        <span class="chip" title="Ámbito">${g.scope}</span>
        <span class="chip" title="Idioma">${g.language}</span>
        <span class="gloss-meta"><span>${total} término(s)</span></span>
        <button class="gloss-toggle" data-state="expanded">Colapsar</button>
      </div>
      <div class="gloss-filter">
        <input type="text" placeholder="Filtrar términos..." class="inpFilter" aria-label="Filtrar términos">
        <button class="btnEdit gloss-toolbar-btn" data-id="${g.id}" title="Editar JSON">✎</button>
        <button class="btnDel gloss-toolbar-btn" data-id="${g.id}" title="Eliminar">🗑️</button>
        <button class="btnOrder gloss-toolbar-btn" data-order="asc" title="Ordenar">A→Z</button>
        <button class="btnCopyPage gloss-toolbar-btn" title="Copiar página visible">📋 Página</button>
        <button class="btnExportPage gloss-toolbar-btn" title="Exportar página visible CSV">⬇ Página</button>
        <button class="btnCopyAll gloss-toolbar-btn" title="Copiar todo JSON">📋 Todo</button>
        <button class="btnExportCSV gloss-toolbar-btn" data-id="${g.id}" data-name="${g.name}" title="Exportar CSV">CSV↧</button>
        <button class="btnExportJSON gloss-toolbar-btn" data-id="${g.id}" data-name="${g.name}" title="Exportar JSON">JSON↧</button>
        <button class="btnExportTEI gloss-toolbar-btn" data-id="${g.id}" data-name="${g.name}" title="Exportar TEI">TEI↧</button>
      </div>
      <div class="gloss-pager" style="margin:4px 0;display:flex;gap:6px;align-items:center">
        <button class="btnPrev gloss-toolbar-btn" title="Anterior" disabled>◀</button>
        <span class="pageInfo" style="font-size:12px"></span>
        <button class="btnNext gloss-toolbar-btn" title="Siguiente" disabled>▶</button>
      </div>
      <div class="gloss-terms"></div>
    `;
    const termsHost = div.querySelector('.gloss-terms');
    const filterInput = div.querySelector('.inpFilter');
    let ascending = true; // orden actual
    let currentSlice = [];
    const pageSize = 25; let page = 1; let totalPages = 1; 
    const pagerInfo = div.querySelector('.pageInfo');
    const btnPrev = div.querySelector('.btnPrev'); 
    const btnNext = div.querySelector('.btnNext');
    function computeEntries(){
      const q = (filterInput.value||'').trim().toLowerCase();
      let entries = Object.entries(termsObj).filter(([ab,ex])=> !q || ab.toLowerCase().includes(q) || ex.toLowerCase().includes(q));
      entries.sort((a,b)=> ascending ? a[0].localeCompare(b[0],'es',{sensitivity:'base'}) : b[0].localeCompare(a[0],'es',{sensitivity:'base'}));
      return entries;
    }
    function renderPage(){
      const entries = computeEntries();
      totalPages = Math.max(1, Math.ceil(entries.length / pageSize));
      if(page>totalPages) page = totalPages;
      const start = (page-1)*pageSize; const end = start + pageSize;
      currentSlice = entries.slice(start, end);
      termsHost.innerHTML='';
      if(entries.length===0){ 
        termsHost.innerHTML='<div class="gloss-empty">Sin coincidencias</div>'; 
        if(pagerInfo) pagerInfo.textContent='0 / 0';
        if(btnPrev) btnPrev.disabled=true; 
        if(btnNext) btnNext.disabled=true; 
        return; 
      }
      currentSlice.forEach(([ab,ex])=>{
        const tdiv=document.createElement('div'); tdiv.className='gloss-term';
        tdiv.innerHTML = `<span class="gt-abbr" title="Abreviatura">${ab}</span><span class="gt-exp" title="Expansión">${ex}</span>`;
        termsHost.appendChild(tdiv);
      });
      const infoText = `Página ${page} / ${totalPages} · ${entries.length} term.`;
      if(pagerInfo) pagerInfo.textContent = infoText;
      const disablePrev = page<=1; const disableNext = page>=totalPages;
      if(btnPrev) btnPrev.disabled = disablePrev; 
      if(btnNext) btnNext.disabled = disableNext;
    }
    renderPage();
    filterInput.addEventListener('input', ()=>{ page=1; renderPage(); });
    const goPrev = ()=>{ if(page>1){ page--; renderPage(); } };
    const goNext = ()=>{ if(page<totalPages){ page++; renderPage(); } };
    if(btnPrev) btnPrev.addEventListener('click', goPrev);
    if(btnNext) btnNext.addEventListener('click', goNext);
    const toggleBtn = div.querySelector('.gloss-toggle');
    toggleBtn.addEventListener('click', ()=>{
      const st = toggleBtn.getAttribute('data-state');
      if(st==='expanded'){
        termsHost.style.display='none'; toggleBtn.textContent='Expandir'; toggleBtn.setAttribute('data-state','collapsed');
      }else{
        termsHost.style.display=''; toggleBtn.textContent='Colapsar'; toggleBtn.setAttribute('data-state','expanded');
      }
    });
    // Orden
    const btnOrder = div.querySelector('.btnOrder');
    btnOrder.addEventListener('click', ()=>{
      ascending = !ascending;
      btnOrder.textContent = ascending ? 'A→Z' : 'Z→A';
      btnOrder.setAttribute('data-order', ascending ? 'asc':'desc');
      page=1; renderPage();
    });
    // Copiar página visible
    const btnCopyPage = div.querySelector('.btnCopyPage');
    btnCopyPage.addEventListener('click', ()=>{
      const obj = Object.fromEntries(currentSlice);
      const text = JSON.stringify(obj, null, 2);
      if(navigator.clipboard){ navigator.clipboard.writeText(text).catch(()=>{}); }
      else { const ta=document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); try{ document.execCommand('copy'); }catch(e){} document.body.removeChild(ta); }
    });
    // Copiar todo
    const btnCopyAll = div.querySelector('.btnCopyAll');
    btnCopyAll.addEventListener('click', ()=>{
      const text = JSON.stringify(termsObj, null, 2);
      if(navigator.clipboard){ navigator.clipboard.writeText(text).catch(()=>{}); }
      else { const ta=document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); try{ document.execCommand('copy'); }catch(e){} document.body.removeChild(ta); }
    });
    // Exportar página visible CSV
    const btnExportPage = div.querySelector('.btnExportPage');
    btnExportPage.addEventListener('click', ()=>{
      if(currentSlice.length===0){ alert('No hay términos visibles'); return; }
      let csv = 'Abreviatura,Expansión\n';
      currentSlice.forEach(([ab,ex])=>{ csv += '"'+ab.replace(/"/g,'""')+'","'+ex.replace(/"/g,'""')+'"\n'; });
      const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${g.name||'glosario'}_visible.csv`; a.style.display='none'; document.body.appendChild(a); a.click(); setTimeout(()=>{URL.revokeObjectURL(a.href); document.body.removeChild(a);},100);
    });
      host.appendChild(div);
    });
    host.querySelectorAll('.btnDel').forEach(b=> b.addEventListener('click', async ()=>{
      try { await axios.post('/glossaries/delete', { id: parseInt(b.dataset.id)}); } catch(e){ showError('eliminando glosario', e); }
      loadGlossariesIfNeeded(); // reload safely
    }));
    // Export buttons for each glossary
    host.querySelectorAll('.btnExportCSV').forEach(b=> b.addEventListener('click', ()=> exportGloss(parseInt(b.dataset.id), 'csv', b.dataset.name)));
    host.querySelectorAll('.btnExportJSON').forEach(b=> b.addEventListener('click', ()=> exportGloss(parseInt(b.dataset.id), 'json', b.dataset.name)));
    host.querySelectorAll('.btnExportTEI').forEach(b=> b.addEventListener('click', ()=> exportGloss(parseInt(b.dataset.id), 'tei', b.dataset.name)));
    host.querySelectorAll('.btnEdit').forEach(b=> b.addEventListener('click', async ()=>{
      try {
        const entry = b.closest('.gloss-entry');
        const id = parseInt(b.dataset.id);
        const r2 = await axios.get('/glossaries');
        const g2 = (r2.data.glossaries||[]).find(x=>x.id===id);
        let termsObj={}; try{ termsObj = JSON.parse(g2.terms_json||'{}'); }catch(e){ termsObj={}; }
        let editor = entry.querySelector('.inline-editor');
        if(!editor){
          editor = document.createElement('div'); editor.className='inline-editor'; editor.style.marginTop='8px';
          editor.innerHTML = `<textarea style="width:100%;height:160px" class="edtGlossJSON"></textarea><div style="margin-top:6px;display:flex;gap:8px"><button class="btnSaveGlossInline">Guardar</button><button class="btnCancelGlossInline">Cancelar</button></div>`;
          entry.appendChild(editor);
          const ta = editor.querySelector('.edtGlossJSON'); ta.value = JSON.stringify(termsObj, null, 2);
          editor.querySelector('.btnCancelGlossInline').addEventListener('click', ()=> editor.remove());
          editor.querySelector('.btnSaveGlossInline').addEventListener('click', async ()=>{
            const txt = ta.value; let newObj={}; try{ newObj = JSON.parse(txt); }catch(e){ alert('JSON inválido'); return; }
            try { await axios.post('/glossaries/update', { id, terms: newObj }); } catch(e){ showError('actualizando glosario', e); }
            editor.remove(); loadGlossoriesIfNeeded();
          });
        } else { editor.scrollIntoView({behavior:'smooth'}); }
      } catch(e){ console.error('edit glossary error', e); showError('cargando glosario', e); }
    }));
  } catch(e){
    console.error('loadGlossaries error', e);
    showError('cargando glosarios', e);
  }
}

// Cargar sólo si aún no hay elementos
function loadGlossoriesIfNeeded(){ /* deprecated alias */ loadGlossariesIfNeeded(); }
function loadGlossariesIfNeeded(){
  const host = document.getElementById('glossList');
  if(host && host.children.length===0){
    loadGlossaries();
  }
}

// Re-bind floating tool buttons removed - handlers defined below after DOM load

// Crear glosario inline (botón Crear)
function parseGlossInput(raw){
  raw = (raw||'').trim();
  if(!raw) return {};
  if(raw.startsWith('{')){ try{ return JSON.parse(raw); }catch(e){ return {}; } }
  const out={};
  raw.split(/\r?\n/).forEach(line=>{
    const ln = line.trim(); if(!ln) return;
    const m = ln.match(/^(.*?)\s*=>\s*(.+)$/);
    if(m){ const ab=m[1].trim(); const ex=m[2].trim(); if(ab) out[ab]=ex; return; }
    const parts = ln.split(/[,;]\s+/);
    if(parts.length===2){ const ab=parts[0].trim(); const ex=parts[1].trim(); if(ab) out[ab]=ex; }
  });
  return out;
}
const btnCreateGlossInline = document.getElementById('btnCreateGlossInline');
if(btnCreateGlossInline){
  btnCreateGlossInline.addEventListener('click', async ()=>{
    const name = (document.getElementById('newGlossName').value||'').trim()||'Glosario';
    const scope = document.getElementById('newGlossScope').value||'project';
    const language = (document.getElementById('newGlossLang').value||'es').trim()||'es';
    const raw = document.getElementById('newGlossTerms').value;
    const terms = parseGlossInput(raw);
    try{
      await axios.post('/glossaries', { scope, name, language, terms });
      document.getElementById('newGlossTerms').value='';
      loadGlossaries();
    }catch(e){ alert('Error creando glosario'); }
  });
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
  try {
    const path = prompt("Ruta del fichero a importar (CSV/JSON/XML):");
    if(!path) return;
    const fmt = (path.toLowerCase().endsWith('.csv')?'csv':(path.toLowerCase().endsWith('.json')?'json':'xml'));
    let field_map = {};
    if(fmt==='csv' || fmt==='xml'){
      const ab = prompt("Nombre de columna/etiqueta para ABREVIATURA (p.ej. 'Abreviatura' o 'abbr'):", "Abreviatura");
      const ex = prompt("Nombre de columna/etiqueta para EXPANSIÓN (p.ej. 'Expansión' o 'expansion'):", "Expansión");
      field_map = { abbr: ab, expansion: ex, item: 'item' };
    }else{
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
  } catch(e){
    console.error('btnImportGloss error', e);
    showError('importando glosario', e);
  }
});

// Export glossary (asks ID and format)
document.getElementById('btnExportGloss').addEventListener('click', async ()=>{
  try {
    const id = parseInt(prompt("ID de glosario a exportar:"));
    if(!id) return;
    const fmt = prompt("Formato (csv|json|tei):","csv") || "csv";
    const out = prompt("Ruta de salida (incluye extensión):","/tmp/glosario."+fmt);
    if(!out) return;
    const r = await axios.post('/glossary_export', { id, format: fmt, out });
    alert(r.data && r.data.ok ? ('Exportado: '+r.data.file) : ('Error: '+(r.data.error||'')));
  } catch(e){
    console.error('btnExportGloss error', e);
    showError('exportando glosario', e);
  }
});

// WYSIWYG: highlight abbreviations and click-to-expand (style-aware)
async function highlightAbbreviations(){
  try {
    const q = new URLSearchParams(window.location.search);
    const pageId = parseInt(q.get('page_id'));
    if(!pageId) return;
    const t = await axios.get('/page_text', { params: { page_id: pageId, corrected: true }}).catch(()=>null);
    const html = (t && t.data && t.data.html) ? t.data.html : '';
    const area = document.getElementById('wysArea'); if(!area) return;
    area.innerHTML = html;
    const r = await axios.post('/spellcheck', { page_id: pageId });
    const hints = (r.data && r.data.abbrev_hints) ? r.data.abbrev_hints : [];
    let text = area.innerHTML;
    hints.forEach(h=>{
      const ab = h.abbr.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&');
      const re = new RegExp('(>[^<]*)\\b'+ab+'\\b','g');
      text = text.replace(re, (m)=> m.replace(h.abbr, `<span class="abbr-hint" data-exp="${h.expansion||''}" style="border-bottom:1px dotted #555; cursor:help" title="${h.expansion||''}">${h.abbr}</span>`));
    });
    area.innerHTML = text;
    area.querySelectorAll('.abbr-hint').forEach(el=>{
      el.addEventListener('click', ()=>{
        const exp = el.getAttribute('data-exp') || '';
        if(!exp) return;
        const doExpand = confirm("Expandir abreviatura a: "+exp+" ?");
        if(doExpand){ el.outerHTML = exp; }
      });
    });
  } catch(e){
    console.error('highlightAbbreviations error', e);
    showError('resaltando abreviaturas', e);
  }
}

const btnWysOpen = document.getElementById('btnWysOpen');
if(btnWysOpen){
  btnWysOpen.addEventListener('click', ()=> setTimeout(highlightAbbreviations, 200));
}


async function autoExpandFirstOccurrence(){
  try {
    const area = document.getElementById('wysArea');
    if(!area) return;
    const st = await axios.get('/abbrev_style').catch(()=>({data:{style:'Chicago'}}));
    const style = (st.data && st.data.style)||'Chicago';
    const expandFirst = true;
    if(!expandFirst) return;
    const first = area.querySelector('.abbr-hint');
    if(first && !first.classList.contains('expanded')){
      const exp = first.getAttribute('data-exp')||'';
      if(exp){
        const orig = first.textContent;
        first.outerHTML = `<span class="abbr-expanded" data-orig="${orig}" style="background:rgba(255,235,150,.5)">${exp}</span>`;
      }
    }
  } catch(e){
    console.error('autoExpandFirstOccurrence error', e);
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
const btnStyleTpl = document.getElementById('btnStyleTpl');
const btnStyleClose = document.getElementById('btnStyleClose');
if(btnStyleTpl){
  btnStyleTpl.addEventListener('click', ()=> { 
    showPanel('panel-style', loadStyleTemplatesIfNeeded);
  });
}
if(btnStyleClose){
  btnStyleClose.addEventListener('click', ()=> {
    const pStyle = document.getElementById('panel-style');
    if(!pStyle) return;
    if(pStyle.classList.contains('modal')){
      const inst = bootstrap.Modal.getInstance(pStyle) || bootstrap.Modal.getOrCreateInstance(pStyle);
      inst.hide();
    } else {
      pStyle.style.display='none';
    }
  });
}
document.getElementById('btnStyleReload').addEventListener('click', loadStyleTemplates);
// Toggle ayuda plantilla
const btnStyleHelp = document.getElementById('btnStyleHelp');
const tplHelp = document.getElementById('tplHelp');
const btnStyleHelpClose = document.getElementById('btnStyleHelpClose');
if(btnStyleHelp && tplHelp){
  btnStyleHelp.addEventListener('click', ()=>{
    tplHelp.style.display = tplHelp.style.display==='none' ? 'block' : 'none';
    if(tplHelp.style.display==='block'){ tplHelp.scrollIntoView({behavior:'smooth'}); }
  });
}
if(btnStyleHelpClose){
  btnStyleHelpClose.addEventListener('click', ()=> tplHelp.style.display='none');
}
// Creación inline de plantilla (botón en formulario)
const btnCreateTplInline = document.getElementById('btnCreateTplInline');
if(btnCreateTplInline){
  btnCreateTplInline.addEventListener('click', async ()=>{
    const name = (document.getElementById('newTplName').value||'').trim() || 'Plantilla';
    const style_name = (document.getElementById('newTplStyleName').value||'').trim() || 'Chicago 17';
    const language = (document.getElementById('newTplLang').value||'es').trim() || 'es';
    const scope = document.getElementById('newTplScope').value || 'project';
    let rules = {}; let meta = {};
    try{ rules = JSON.parse(document.getElementById('newTplRules').value || '{}'); }catch(e){ alert('Rules JSON inválido'); return; }
    try{ const mtxt = document.getElementById('newTplMeta').value.trim(); meta = mtxt? JSON.parse(mtxt): {}; }catch(e){ alert('Meta JSON inválido'); return; }
    await axios.post('/style_templates', { name, style_name, language, scope, rules, meta });
    loadStyleTemplates();
  });
}
async function loadStyleTemplates(){
  try {
    const r = await axios.get('/style_templates');
    const list = r.data.templates || [];
    const host = document.getElementById('styleList'); host.innerHTML = '';
    list.forEach(t=>{
    const div = document.createElement('div');
    div.className='gloss-entry';
    const rulesShort = (t.rules_json||'{}').slice(0,160)+(t.rules_json && t.rules_json.length>160?'…':'');
    div.innerHTML = `
      <div class="gloss-header">
        <span class="gloss-name">${t.name}</span>
        <span class="chip" title="Estilo">${t.style_name||''}</span>
        <span class="chip" title="Ámbito">${t.scope}</span>
        <span class="gloss-meta"><span>ID ${t.id}</span></span>
        <button class="gloss-toggle" data-state="collapsed">Expandir</button>
      </div>
      <div style="display:flex;gap:6px;align-items:center;margin:4px 0 6px 0">
        <button class="btnApply" data-id="${t.id}">Aplicar</button>
        <button class="btnEdit" data-id="${t.id}">Editar</button>
        <button class="btnDel" data-id="${t.id}">Eliminar</button>
        <code style="flex:1;white-space:pre-wrap;background:#fafafa;padding:4px;border:1px solid #eee;border-radius:4px;font-size:11px">${rulesShort}</code>
      </div>
      <div class="tpl-full" style="display:none;white-space:pre-wrap;background:#fff;border:1px solid #eee;padding:6px;border-radius:4px;font-size:11px">${t.rules_json||''}</div>
    `;
    const toggleBtn = div.querySelector('.gloss-toggle');
    const full = div.querySelector('.tpl-full');
    toggleBtn.addEventListener('click', ()=>{
      const st = toggleBtn.getAttribute('data-state');
      if(st==='collapsed'){ full.style.display='block'; toggleBtn.textContent='Colapsar'; toggleBtn.setAttribute('data-state','expanded'); }
      else { full.style.display='none'; toggleBtn.textContent='Expandir'; toggleBtn.setAttribute('data-state','collapsed'); }
    });
      host.appendChild(div);
    });
    host.querySelectorAll('.btnDel').forEach(b=> b.addEventListener('click', async ()=>{
      try { await axios.post('/style_templates/delete', { id: parseInt(b.dataset.id) }); } catch(e){ alert('Error eliminando plantilla'); }
      loadStyleTemplates();
    }));
    host.querySelectorAll('.btnEdit').forEach(b=> b.addEventListener('click', async ()=>{
      try {
        const entry = b.closest('.gloss-entry');
        const id = parseInt(b.dataset.id);
        const r2 = await axios.get('/style_templates');
        const tpl = (r2.data.templates||[]).find(x=>x.id===id);
        let rulesObj={}; try{ rulesObj=JSON.parse(tpl.rules_json||'{}'); }catch(e){ rulesObj={}; }
        let editor = entry.querySelector('.inline-editor');
        if(!editor){
          editor = document.createElement('div'); editor.className='inline-editor'; editor.style.marginTop='6px';
          editor.innerHTML = `<textarea style="width:100%;height:140px" class="edtTplRules"></textarea><div style="margin-top:6px;display:flex;gap:8px"><button class="btnSaveTpl">Guardar</button><button class="btnCancelTpl">Cancelar</button></div>`;
          entry.appendChild(editor);
          const ta = editor.querySelector('.edtTplRules'); ta.value = JSON.stringify(rulesObj, null, 2);
          editor.querySelector('.btnCancelTpl').addEventListener('click', ()=> editor.remove());
          editor.querySelector('.btnSaveTpl').addEventListener('click', async ()=>{
            const txt = ta.value; let newRules={}; try{ newRules=JSON.parse(txt);}catch(e){ alert('JSON inválido'); return; }
            try { await axios.post('/style_templates/update', { id, name: tpl.name, rules: newRules, meta: {} }); } catch(e){ alert('Error guardando plantilla'); }
            editor.remove(); loadStyleTemplates();
          });
        } else { editor.scrollIntoView({behavior:'smooth'}); }
      } catch(e){ console.error('edit style template error', e); alert('Error cargando plantilla'); }
    }));
    host.querySelectorAll('.btnApply').forEach(b=> b.addEventListener('click', async ()=>{
      const q = new URLSearchParams(window.location.search);
      const docId = parseInt(q.get('document_id')) || parseInt(prompt('ID de documento:'));
      if(!docId) return;
      try {
        const r3 = await axios.post('/apply_style_doc', { document_id: docId, template_id: parseInt(b.dataset.id) });
        alert(r3.data && r3.data.ok ? ('Cambios: '+r3.data.result.count) : 'Error aplicando');
      } catch(e){ showError('aplicando plantilla', e); }
    }));
  } catch(e){
    console.error('loadStyleTemplates error', e);
    showError('cargando plantillas de estilo', e);
  }
}
function loadStyleTemplatesIfNeeded(){
  const host = document.getElementById('styleList');
  if(host && host.children.length===0){
    loadStyleTemplates();
  }
}
// Preset insertion for style templates
(function(){
  const area = document.getElementById('newTplRules');
  if(!area) return;
  document.querySelectorAll('.btnPreset').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const key = btn.getAttribute('data-target');
      const pre = document.querySelector(`pre[data-preset="${key}"]`);
      if(pre && area){ area.value = pre.textContent.trim(); area.scrollIntoView({behavior:'smooth'}); }
    });
  });
})();

// Custom preset management
(function(){
  const area = document.getElementById('newTplRules');
  const nameInput = document.getElementById('presetName');
  const saveBtn = document.getElementById('btnPresetSave');
  const clearBtn = document.getElementById('btnPresetClear');
  const listHost = document.getElementById('customPresetList');
  if(!area || !saveBtn || !listHost) return;
  function loadPresets(){
    let data={}; try{ data = JSON.parse(localStorage.getItem('styleCustomPresets')||'{}'); }catch(e){ data={}; }
    return data;
  }
  function savePresets(obj){
    try{ localStorage.setItem('styleCustomPresets', JSON.stringify(obj)); }catch(e){}
  }
  function renderList(){
    const data = loadPresets(); listHost.innerHTML='';
    const keys = Object.keys(data); if(keys.length===0){ listHost.innerHTML='<small style="grid-column:1/-1;color:#666">Sin presets guardados</small>'; return; }
    keys.forEach(k=>{
      const card = document.createElement('div');
      card.style.cssText='border:1px solid #dde3ea;border-radius:6px;padding:6px;background:#fff;display:flex;flex-direction:column;gap:4px;font-size:11px';
      const pre = document.createElement('pre'); pre.style.cssText='white-space:pre-wrap;margin:0;font-size:11px;max-height:120px;overflow:auto'; pre.textContent = data[k];
      const bar = document.createElement('div'); bar.style.cssText='display:flex;gap:4px';
      const btnUse = document.createElement('button'); btnUse.className='gloss-toolbar-btn'; btnUse.textContent='Usar'; btnUse.title='Cargar preset';
      const btnDel = document.createElement('button'); btnDel.className='gloss-toolbar-btn'; btnDel.textContent='✕'; btnDel.title='Eliminar preset';
      btnUse.addEventListener('click', ()=>{ area.value = data[k]; area.scrollIntoView({behavior:'smooth'}); });
      btnDel.addEventListener('click', ()=>{ const all=loadPresets(); delete all[k]; savePresets(all); renderList(); });
      bar.appendChild(btnUse); bar.appendChild(btnDel);
      const title = document.createElement('div'); title.style.cssText='font-weight:600;font-size:12px'; title.textContent = k;
      card.appendChild(title); card.appendChild(pre); card.appendChild(bar); listHost.appendChild(card);
    });
  }
  saveBtn.addEventListener('click', ()=>{
    const nm = (nameInput.value||'').trim(); if(!nm){ alert('Nombre requerido'); return; }
    // basic JSON validate
    try{ JSON.parse(area.value); }catch(e){ if(!confirm('El contenido no es JSON válido según parse. Guardar de todas formas?')) return; }
    const all = loadPresets(); all[nm] = area.value.trim(); savePresets(all); renderList(); nameInput.value='';
  });
  if(clearBtn){ clearBtn.addEventListener('click', ()=>{ if(confirm('¿Borrar todos los presets personalizados?')){ savePresets({}); renderList(); }}); }
  renderList();
})();
document.getElementById('btnApplyStyleDoc').addEventListener('click', async ()=>{
  try {
    const q = new URLSearchParams(window.location.search);
    const docId = parseInt(q.get('document_id')) || parseInt(prompt("ID de documento:"));
    if(!docId) return;
    const rules = prompt("JSON de reglas (vacío para estilo actual):","{}");
    let obj = null; if(rules && rules.trim()){ try{ obj = JSON.parse(rules);}catch(e){ alert("JSON inválido"); return; } }
    const r = await axios.post('/apply_style_doc', { document_id: docId, rules: obj });
    alert(r.data && r.data.ok ? ('Cambios: '+r.data.result.count) : 'Error');
  } catch(e){
    console.error('btnApplyStyleDoc error', e);
    showError('aplicando estilo al documento', e);
  }
});

// Panel Diff/Merge
const btnGlossDiff = document.getElementById('btnGlossDiff');
const btnDiffClose = document.getElementById('btnDiffClose');
if(btnGlossDiff){
  btnGlossDiff.addEventListener('click', ()=> {
    showPanel('panel-diff');
  });
}
if(btnDiffClose){
  btnDiffClose.addEventListener('click', ()=> {
    const pDiff = document.getElementById('panel-diff');
    if(!pDiff) return;
    if(pDiff.classList.contains('modal')){
      const inst = bootstrap.Modal.getInstance(pDiff) || bootstrap.Modal.getOrCreateInstance(pDiff);
      inst.hide();
    } else {
      pDiff.style.display='none';
    }
  });
}
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
  try {
    const r = await axios.get('/diff_page', { params: { page_id: pageId }});
    if(!(r.data && r.data.ok)){ alert('No se pudo cargar diff'); return; }
    renderTokens('diffColA', r.data.diffs.orig_vs_corr);
    renderTokens('diffColB', r.data.diffs.orig_vs_corr);
    renderTokens('diffColC', r.data.diffs.corr_vs_style);
    const side = document.getElementById('diffSide');
    side.innerHTML = '<h4>Cambios</h4><p>orig_vs_corr: '+r.data.diffs.orig_vs_corr.length+' tokens<br/>corr_vs_style: '+r.data.diffs.corr_vs_style.length+' tokens</p>';
  } catch(e){
    console.error('loadDiff error', e);
    showError('cargando diff', e);
  }
}

function openDiffLive(){
  try {
    const q = new URLSearchParams(window.location.search);
    const pageId = parseInt(q.get('page_id')) || parseInt(prompt("ID de página:"));
    if(!pageId) return;
    // Open as Bootstrap modal if available
    const modalEl = document.getElementById('panel-diff-live');
    if(modalEl && modalEl.classList.contains('modal')){
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl, {backdrop:true,keyboard:true,focus:true});
      modal.show();
    } else if(modalEl){
      modalEl.style.display='block';
    }
    loadDiff(pageId);
    document.getElementById('btnDiffAccept').onclick = async ()=>{
      try { await axios.post('/review_apply', { page_id: pageId, decision: 'accept' }); alert('Aplicado estilo como corregido'); } catch(e){ showError('aplicando aceptación', e); }
    };
    document.getElementById('btnDiffReject').onclick = async ()=>{
      try { await axios.post('/review_apply', { page_id: pageId, decision: 'reject' }); alert('Sin cambios'); } catch(e){ showError('rechazando cambios', e); }
    };
    document.getElementById('btnDiffRevert').onclick = async ()=>{
      try { await axios.post('/review_apply', { page_id: pageId, decision: 'revert' }); alert('Revertido a OCR original'); } catch(e){ showError('revirtiendo', e); }
    };
    const btnClose = document.getElementById('btnDiffLiveClose');
    if(btnClose){
      btnClose.onclick = ()=>{
        const el = document.getElementById('panel-diff-live');
        if(!el) return;
        if(el.classList.contains('modal')){
          const inst = bootstrap.Modal.getInstance(el) || bootstrap.Modal.getOrCreateInstance(el);
          inst.hide();
        } else {
          el.style.display='none';
        }
      };
    }
  } catch(e){
    console.error('openDiffLive error', e);
    showError('abriendo diff live', e);
  }
}

// Init panels on DOM ready
setTimeout(initDragPanels, 300);

const btnOpenDiff = document.getElementById('btnOpenDiff');
if(btnOpenDiff){
  btnOpenDiff.addEventListener('click', openDiffLive);
}


// Export modal live
function openExportLive(){
  const el = document.getElementById('panel-export-live');
  if(el && el.classList.contains('modal')){
    const modal = bootstrap.Modal.getOrCreateInstance(el, {backdrop:true,keyboard:true,focus:true});
    modal.show();
  } else if(el){
    el.style.display = 'block';
  }
}
const btnOpenExport = document.getElementById('btnOpenExport');
if(btnOpenExport){ btnOpenExport.addEventListener('click', openExportLive); }

document.getElementById('btnExpClose').addEventListener('click', ()=>{
  const el = document.getElementById('panel-export-live');
  if(!el) return;
  if(el.classList.contains('modal')){
    const inst = bootstrap.Modal.getInstance(el) || bootstrap.Modal.getOrCreateInstance(el);
    inst.hide();
  } else {
    el.style.display = 'none';
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

// Helper estandarizado para errores de exportación
function showError(ctx, err){
  const msg = 'Error '+ctx+': '+(err && err.message ? err.message : err);
  try{ alert(msg); }catch(_){ /* ignore */ }
  return msg;
}

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
    const em = showError('exportación', e);
    log.textContent += em + '\n';
  }
});
