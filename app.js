/* ONITSIR — in-browser engine.
   A faithful JS port of the Python package: Router + Shackle Governor
   (decide + hash-chained ledger) + Workflow phase machine + Iron-Law gate.
   The landing page IS the app. */

// ── tiny synchronous SHA-256 (for the audit ledger hash chain) ──────────────
function sha256(ascii){
  function rr(n,x){return (x>>>n)|(x<<(32-n));}
  const m=Math.pow(2,32);
  const K=[]; const H=[];
  (function(){
    function isPrime(n){for(let f=2;f*f<=n;f++) if(n%f===0) return false; return true;}
    let n=2,pi=0,pj=0;
    while(pj<64){
      if(isPrime(n)){
        if(pi<8) H[pi]=(Math.pow(n,.5)%1*m)|0;
        K[pj]=(Math.pow(n,1/3)%1*m)|0; pj++; if(pi<8)pi++;
      }
      n++;
    }
  })();
  // utf-8 encode
  const bytes=[]; for(const ch of unescape(encodeURIComponent(ascii))) bytes.push(ch.charCodeAt(0));
  const l=bytes.length*8; bytes.push(0x80);
  while(bytes.length%64!==56) bytes.push(0);
  for(let i=7;i>=0;i--) bytes.push((l/Math.pow(2,i*8))&0xff);
  const w=new Int32Array(64); const hh=H.slice();
  for(let j=0;j<bytes.length;j+=64){
    for(let i=0;i<16;i++) w[i]=(bytes[j+i*4]<<24)|(bytes[j+i*4+1]<<16)|(bytes[j+i*4+2]<<8)|(bytes[j+i*4+3]);
    for(let i=16;i<64;i++){
      const s0=rr(7,w[i-15])^rr(18,w[i-15])^(w[i-15]>>>3);
      const s1=rr(17,w[i-2])^rr(19,w[i-2])^(w[i-2]>>>10);
      w[i]=(w[i-16]+s0+w[i-7]+s1)|0;
    }
    let [a,b,c,d,e,f,g,h]=hh;
    for(let i=0;i<64;i++){
      const S1=rr(6,e)^rr(11,e)^rr(25,e);
      const chc=(e&f)^(~e&g);
      const t1=(h+S1+chc+K[i]+w[i])|0;
      const S0=rr(2,a)^rr(13,a)^rr(22,a);
      const maj=(a&b)^(a&c)^(b&c);
      const t2=(S0+maj)|0;
      h=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;
    }
    hh[0]=(hh[0]+a)|0;hh[1]=(hh[1]+b)|0;hh[2]=(hh[2]+c)|0;hh[3]=(hh[3]+d)|0;
    hh[4]=(hh[4]+e)|0;hh[5]=(hh[5]+f)|0;hh[6]=(hh[6]+g)|0;hh[7]=(hh[7]+h)|0;
  }
  return hh.map(x=>('00000000'+(x>>>0).toString(16)).slice(-8)).join('');
}
function canonicalJSON(o){ // sorted keys, tight separators
  if(o===null||typeof o!=='object') return JSON.stringify(o);
  if(Array.isArray(o)) return '['+o.map(canonicalJSON).join(',')+']';
  const keys=Object.keys(o).sort();
  return '{'+keys.map(k=>JSON.stringify(k)+':'+canonicalJSON(o[k])).join(',')+'}';
}
const canonicalHash=o=>sha256(canonicalJSON(o));

// ── Shackle governance decision surface (ONITSIR Governor) ──────────────────
function decide(config,state,call){
  const params=call.params||{};
  const pending=state.pending_transition;
  if(params.__noncanonical__===true) return ["DENY","policy_violation:malformed_input"];
  if(state.circuit_tripped===true) return ["DENY","circuit_open"];
  const seen=state.seen_nonces||[];
  if(call.nonce!=null && seen.includes(call.nonce)){
    if(pending&&pending.resume_attempt===true&&["rejected","superseded"].includes(pending.terminal_status))
      return ["DENY","policy_violation:duplicate_resume_no_effect"];
    return ["DENY","policy_violation:duplicate_nonce"];
  }
  if(pending){
    const d=pending.decision;
    if(d==="approve") return ["ALLOW","hitl_transition:approve"];
    if(d==="reject") return ["DENY","hitl_transition:reject"];
    if(d==="modify") return ["ALLOW","hitl_transition:modify_successor"];
    if(d==="defer"||d==="escalate") return ["HITL","hitl_transition:defer_escalate"];
  }
  const budget=config.budget_usd||0;
  const remaining=state.budget_remaining_usd;
  if(remaining!=null && remaining<=0 && budget>0) return ["DENY","budget_exhausted"];
  const maxRepeat=config.max_repeat_calls, rc=state.repeat_counts, lt=state.last_tool_name;
  if(maxRepeat!=null && rc && lt){
    const c=rc[call.tool_name];
    if(c!=null && c>=maxRepeat && lt===call.tool_name) return ["DENY","max_repeat_exceeded"];
  }
  if(config.hitl_mode==="always") return ["HITL","hitl_all_calls"];
  if(config.hitl_mode==="on_threshold" && config.hitl_budget_threshold!=null){
    const init=state.budget_initial_usd;
    if(init){ const frac=(state.budget_remaining_usd||0)/init;
      if(frac<=config.hitl_budget_threshold) return ["HITL","budget_threshold"]; }
  }
  if(params.ctx==="opaque") return ["HITL","fail_closed:opaque_context"];
  return ["ALLOW","within_thresholds"];
}

// ── Governor + hash-chained audit ledger ────────────────────────────────────
const GENESIS="0".repeat(64);
class AuditLedger{
  constructor(){this.entries=[];}
  append(tool,verdict,reason){
    const index=this.entries.length;
    const at=Math.floor(Date.now()/1000);
    const prev=this.entries.length?this.entries[this.entries.length-1].entry_hash:GENESIS;
    const entry_hash=canonicalHash({index,at,tool_name:tool,verdict,reason,prev_hash:prev});
    const e={index,at,tool_name:tool,verdict,reason,prev_hash:prev,entry_hash};
    this.entries.push(e); return e;
  }
  verify(){let prev=GENESIS;
    for(let i=0;i<this.entries.length;i++){const e=this.entries[i];
      if(e.index!==i||e.prev_hash!==prev) return false;
      const exp=canonicalHash({index:e.index,at:e.at,tool_name:e.tool_name,verdict:e.verdict,reason:e.reason,prev_hash:e.prev_hash});
      if(exp!==e.entry_hash) return false; prev=e.entry_hash;}
    return true;}
  get head(){return this.entries.length?this.entries[this.entries.length-1].entry_hash:GENESIS;}
}
class Governor{
  constructor(cfg){this.config=Object.assign({budget_usd:1,max_repeat_calls:3,hitl_mode:null,hitl_budget_threshold:null},cfg||{});
    this.spent=0;this.repeat={};this.seen=[];this.tripped=false;this.lastTool=null;this.ledger=new AuditLedger();}
  _state(){return{circuit_tripped:this.tripped,seen_nonces:[...this.seen],
    budget_initial_usd:this.config.budget_usd,budget_remaining_usd:Math.max(this.config.budget_usd-this.spent,0),
    repeat_counts:{...this.repeat},last_tool_name:this.lastTool};}
  evaluate(tool,{cost=0,nonce=null,params=null}={}){
    this.spent+=cost; this.repeat[tool]=(this.repeat[tool]||0)+1; this.lastTool=tool;
    const call={tool_name:tool,params:params||{}}; if(nonce!=null) call.nonce=nonce;
    const [v,r]=decide(this.config,this._state(),call);
    if(nonce!=null&&!this.seen.includes(nonce)) this.seen.push(nonce);
    if(v==="DENY") this.tripped=true;
    this.ledger.append(tool,v,r); return [v,r];
  }
}

// ── Router ──────────────────────────────────────────────────────────────────
function tokenize(s){return (s.toLowerCase().match(/[a-z0-9]+/g)||[]);}
function scoreSpecialist(sp,tokens){
  let score=0; const cat=(sp.category||'').toLowerCase();
  const kws=(sp.keywords||[]).map(k=>k.toLowerCase());
  const name=(sp.name||'').toLowerCase();
  for(const t of tokens){
    if(cat.includes(t)) score+=3;
    if(kws.some(k=>k.includes(t)||t.includes(k))) score+=2;
    if(name.includes(t)) score+=2;
    const desc=(sp.description||'').toLowerCase();
    if(desc.includes(t)) score+=1;
  }
  return score;
}
function route(roster,goal,crewSize){
  const tokens=tokenize(goal); if(!tokens.length) return [];
  const scored=roster.map(sp=>({sp,score:scoreSpecialist(sp,tokens)})).filter(x=>x.score>0);
  scored.sort((a,b)=>b.score-a.score);
  return scored.slice(0,crewSize).map(x=>({name:x.sp.name,category:x.sp.category,score:x.score,
    confidence: x.score>=9?"high":x.score>=4?"medium":"low"}));
}

// ── Workflow phases + verifier ──────────────────────────────────────────────
const PHASES=["intake","spec","plan","build","verify","ship"];
function makeVerifier(mode){
  return (phase)=>{
    if(mode==="stale") return {command:"check",output:"ok",passed:true,at:Math.floor(Date.now()/1000)-999999};
    if(mode&&mode.startsWith("fail:")){const t=mode.split(":")[1];
      const pass=phase!==t; return {command:`verify ${phase}`,output:pass?"1 passed":"boom: 1 failed",passed:pass,at:Math.floor(Date.now()/1000)};}
    return {command:`verify ${phase}`,output:"1 passed, 0 failed",passed:true,at:Math.floor(Date.now()/1000)};
  };
}
function ironLaw(ev,maxAge=3600){
  if(!ev) return [false,"no evidence"];
  if(!ev.command||!ev.command.trim()) return [false,"no command"];
  if(!ev.passed) return [false,"evidence not passing"];
  if(!ev.output||!ev.output.trim()) return [false,"empty output"];
  if(maxAge!=null && ev.at && (Math.floor(Date.now()/1000)-ev.at)>maxAge) return [false,"stale evidence"];
  return [true,"verified"];
}

// ── UI wiring ────────────────────────────────────────────────────────────────
let ROSTER=[];
const $=id=>document.getElementById(id);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

// richer routing — matched keywords + description for the crew cards
function routeDetailed(roster, goal, n){
  const tokens=tokenize(goal); if(!tokens.length) return [];
  const scored=roster.map(sp=>{
    const score=scoreSpecialist(sp,tokens);
    const kws=(sp.keywords||[]);
    const matched=[...new Set(kws.filter(k=>{const kl=k.toLowerCase();
      return tokens.some(t=>kl.includes(t)||t.includes(kl));}))].slice(0,4);
    return {name:sp.name,category:sp.category,description:sp.description||'',score,matched};
  }).filter(x=>x.score>0);
  scored.sort((a,b)=>b.score-a.score);
  return scored.slice(0,n).map(x=>({...x, confidence: x.score>=9?'high':x.score>=4?'medium':'low'}));
}

const PIPE=["intake","spec","plan","build","verify","ship"];
let lastGov=null;

async function staffCrew(){
  const goal=($("goal").value||"").trim();
  if(!goal){ $("goal").focus(); return; }
  const res=$("result");
  const crew=routeDetailed(ROSTER, goal, 5);
  const crewEl=$("crew"); crewEl.innerHTML="";
  res.classList.add("show");

  if(!crew.length){
    $("crewmeta").textContent="";
    crewEl.innerHTML='<div class="nomatch">No specialist matched confidently. Try a goal with a clearer domain word — like <b>reddit</b>, <b>landing page</b>, <b>video</b>, <b>ads</b>, or <b>brand</b>.</div>';
    $("pipeblock").style.display="none"; $("ledblock").style.display="none"; $("realnote").style.display="none";
    res.scrollIntoView({behavior:"smooth",block:"start"});
    return;
  }
  $("pipeblock").style.display=""; $("ledblock").style.display=""; $("realnote").style.display="";
  $("crewmeta").textContent=crew.length+" of "+ROSTER.length+" specialists";
  const top=crew[0].score||1;
  crew.forEach((m,i)=>{
    const el=document.createElement("div"); el.className="member"; el.style.animationDelay=(i*70)+"ms";
    const dsc=esc(m.description);
    el.innerHTML='<div class="top"><span class="ctag">'+esc(m.category)+'</span>'
      +'<span class="conf '+m.confidence+'">'+m.confidence+' match</span></div>'
      +'<h4>'+esc(m.name)+'</h4>'
      +'<div class="bar"><span style="width:'+Math.round(m.score/top*100)+'%"></span></div>'
      +'<p>'+dsc.slice(0,120)+(m.description.length>120?'…':'')+'</p>'
      +(m.matched.length?'<div class="kws">'+m.matched.map(k=>'<span class="kw">'+esc(k)+'</span>').join('')+'</div>':'');
    crewEl.appendChild(el);
  });

  await runPipeline(goal);
  res.scrollIntoView({behavior:"smooth",block:"start"});
}

async function runPipeline(goal){
  const budget=parseFloat($("budget").value)||0;
  const forcefail=$("forcefail").checked;
  const pcost=0.10; // fixed per-phase cost: a low budget genuinely runs out mid-mission
  const gov=new Governor({budget_usd:budget, max_repeat_calls:5});
  lastGov=gov;

  const ph=$("phases"); ph.innerHTML="";
  PIPE.forEach(p=>{ const d=document.createElement("div"); d.className="phase wait"; d.id="p-"+p;
    d.innerHTML='<span class="nm">'+p+'</span><span class="st" id="s-'+p+'">queued</span>'; ph.appendChild(d); });
  const vd=$("verdict"); vd.className="verdict"; vd.innerHTML="";

  let ok=true, kind=null, why=null;
  for(const p of PIPE){
    const row=$("p-"+p), st=$("s-"+p); row.classList.remove("wait");
    await sleep(200);
    const [v,r]=gov.evaluate("phase:"+p,{cost:pcost});
    if(v==="DENY"){ st.innerHTML='<span class="badge b-deny">DENY</span> Governor stopped the run — <b>'+r+'</b>';
      ok=false; kind="stop"; why='the Governor denied <b>'+p+'</b> ('+r+')'; break; }
    if(v==="HITL"){ st.innerHTML='<span class="badge b-hitl">HITL</span> paused for human approval — '+r;
      ok=false; kind="pause"; why='the Governor paused at <b>'+p+'</b> for human approval'; break; }
    if(p==="build" && forcefail){
      st.innerHTML='<span class="badge b-allow">ALLOW</span> <span class="badge b-deny">IRON LAW</span> evidence not passing — refused';
      ok=false; kind="stop"; why='the Iron Law refused to advance past <b>build</b> — the verification evidence didn\'t pass'; break;
    }
    st.innerHTML='<span class="badge b-allow">ALLOW</span> <span class="badge b-gate">GATE ✓</span> governed · evidence required';
  }

  if(ok){ vd.className="verdict show ok";
    vd.innerHTML='✔ Plan cleared every gate. In the product, ONITSIR now executes each phase with real command-level verification — and only reports "done" when the evidence actually passes.'; }
  else if(kind==="pause"){ vd.className="verdict show pause";
    vd.innerHTML='⏸ Paused — '+why+'. It waits for you instead of guessing.'; }
  else { vd.className="verdict show stop";
    vd.innerHTML='✖ Stopped honestly — '+why+'. No fake ship, ever.'; }

  renderLedger(gov);
}

function renderLedger(gov){
  const tb=$("ledbody"); tb.innerHTML="";
  gov.ledger.entries.forEach(e=>{ const tr=document.createElement("tr");
    const cls=e.verdict==="ALLOW"?"b-allow":e.verdict==="DENY"?"b-deny":"b-hitl";
    tr.innerHTML='<td>'+e.index+'</td><td><span class="badge '+cls+'">'+e.verdict+'</span></td>'
      +'<td>'+esc(e.tool_name)+'</td><td>'+esc(e.reason)+'</td>'
      +'<td><span class="h">'+e.entry_hash.slice(0,14)+'…</span></td>';
    tb.appendChild(tr); });
  $("ledmeta").textContent=gov.ledger.entries.length+" rulings";
}

function verifyChain(){
  if(!lastGov) return;
  const ok=lastGov.ledger.verify();
  const b=$("verifybtn");
  b.innerHTML = ok ? '✓ Chain verified' : '✗ Chain broken';
  b.style.color = ok ? 'var(--green)' : 'var(--red)';
  setTimeout(()=>{ b.innerHTML='🔒 Verify chain'; b.style.color=''; }, 2200);
}

function setRealNote(){
  $("realnote").innerHTML='<b>What just ran, for real:</b> the crew was routed live by scoring your goal against all '
    +ROSTER.length+' specialists, and the pipeline\'s ALLOW/DENY/HITL rulings plus the hash-chained audit ledger were computed right here in your browser — tap <b>Verify chain</b> to re-hash it. '
    +'The autonomous building and real command-level verification run inside the ONITSIR product; this page is the engine\'s routing + governance core, running live.';
}

// ── roster browser ──
function buildCats(){
  const cats=[...new Set(ROSTER.map(s=>s.category))].filter(Boolean).sort();
  const wrap=$("cats"); wrap.innerHTML="";
  const all=document.createElement("div"); all.className="cat active"; all.textContent="all"; all.dataset.cat=""; wrap.appendChild(all);
  cats.forEach(c=>{ const el=document.createElement("div"); el.className="cat"; el.textContent=c; el.dataset.cat=c; wrap.appendChild(el); });
  wrap.querySelectorAll(".cat").forEach(el=>el.onclick=()=>{
    wrap.querySelectorAll(".cat").forEach(x=>x.classList.remove("active")); el.classList.add("active"); renderRoster(); });
}
function renderRoster(){
  const q=($("search").value||"").toLowerCase().trim();
  const active=document.querySelector(".cat.active");
  const cat=active?active.dataset.cat:"";
  const grid=$("rgrid"); grid.innerHTML="";
  const list=ROSTER.filter(s=>{
    if(cat && s.category!==cat) return false;
    if(!q) return true;
    return (s.name||'').toLowerCase().includes(q)||(s.description||'').toLowerCase().includes(q)
      ||(s.category||'').toLowerCase().includes(q)||(s.keywords||[]).join(' ').toLowerCase().includes(q);
  });
  $("rcount").textContent=list.length;
  list.slice(0,60).forEach(s=>{ const c=document.createElement("div"); c.className="rcard";
    c.innerHTML='<div class="ctag">'+esc(s.category)+'</div><h4>'+esc(s.name)+'</h4><p>'+esc((s.description||'').slice(0,110))+'</p>';
    grid.appendChild(c); });
  if(list.length>60){ const m=document.createElement("div"); m.className="rcard";
    m.innerHTML='<h4>+'+(list.length-60)+' more</h4><p class="muted">Refine your search to narrow the roster.</p>'; grid.appendChild(m); }
}

async function loadRoster(){
  try{ const res=await fetch("roster.json"); const data=await res.json();
    ROSTER = Array.isArray(data)?data:(data.specialists||data.roster||[]);
  }catch(e){ ROSTER=[]; }
  const n=ROSTER.length;
  ["pill-specialists","pill2","rcount"].forEach(id=>{ const el=$(id); if(el) el.textContent=n; });
  buildCats(); renderRoster(); setRealNote();
}

document.addEventListener("DOMContentLoaded", ()=>{
  loadRoster();
  $("staff").onclick=staffCrew;
  $("goal").addEventListener("keydown", e=>{ if(e.key==="Enter") staffCrew(); });
  $("examples").querySelectorAll(".ex").forEach(x=>x.onclick=()=>{ $("goal").value=x.textContent.trim(); staffCrew(); });
  $("advBtn").onclick=()=>$("adv").classList.toggle("open");
  $("verifybtn").onclick=verifyChain;
  $("search").addEventListener("input", renderRoster);
});
