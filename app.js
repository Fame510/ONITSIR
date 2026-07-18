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

async function loadRoster(){
  try{ const res=await fetch("roster.json"); const data=await res.json();
    ROSTER = Array.isArray(data)?data:(data.specialists||data.roster||[]);
  }catch(e){ ROSTER=[]; }
  $("rcount").textContent=ROSTER.length;
  $("pill-specialists").textContent=ROSTER.length;
  buildCats(); renderRoster();
}

function buildCats(){
  const cats=[...new Set(ROSTER.map(s=>s.category))].sort();
  const wrap=$("cats"); wrap.innerHTML="";
  const all=document.createElement("div"); all.className="cat active"; all.textContent="all"; all.dataset.cat="";
  wrap.appendChild(all);
  cats.forEach(c=>{const el=document.createElement("div");el.className="cat";el.textContent=c;el.dataset.cat=c;wrap.appendChild(el);});
  wrap.querySelectorAll(".cat").forEach(el=>el.onclick=()=>{
    wrap.querySelectorAll(".cat").forEach(x=>x.classList.remove("active"));el.classList.add("active");renderRoster();});
}
function renderRoster(){
  const q=($("search").value||"").toLowerCase().trim();
  const cat=(document.querySelector(".cat.active")||{}).dataset?.cat||"";
  const grid=$("rgrid"); grid.innerHTML="";
  let list=ROSTER.filter(s=>{
    if(cat && s.category!==cat) return false;
    if(!q) return true;
    return (s.name||'').toLowerCase().includes(q)||(s.description||'').toLowerCase().includes(q)
      ||(s.category||'').toLowerCase().includes(q)||(s.keywords||[]).join(' ').toLowerCase().includes(q);
  });
  $("rcount").textContent=list.length;
  list.slice(0,60).forEach(s=>{const c=document.createElement("div");c.className="card";
    c.innerHTML=`<div class="cat-tag">${s.category||''}</div><h4>${s.name||''}</h4><p>${(s.description||'').slice(0,120)}</p>`;
    grid.appendChild(c);});
  if(list.length>60){const more=document.createElement("div");more.className="card";
    more.innerHTML=`<h4>+${list.length-60} more</h4><p class="muted">Refine your search to narrow the roster.</p>`;grid.appendChild(more);}
}

function phaseRow(name){const d=document.createElement("div");d.className="phase";d.id="ph-"+name;
  d.innerHTML=`<span class="nm">${name}</span><span class="gv" id="gv-${name}">queued…</span>`;return d;}

async function runMission(){
  const goal=$("goal").value.trim();
  const crewSize=Math.max(1,Math.min(6,parseInt($("crew").value)||3));
  const budget=parseFloat($("budget").value)||0;
  const pcost=parseFloat($("pcost").value)||0;
  const hitl=$("hitl").value||null;
  const verifier=makeVerifier($("verifier").value);

  const crew=route(ROSTER,goal,crewSize);
  const cl=$("crewline"); cl.innerHTML="";
  if(!crew.length){cl.innerHTML='<span class="b-deny badge">NO MATCH</span> <span class="muted">No confident specialist matched — try a goal with clearer domain words.</span>';}
  else crew.forEach(a=>{const c=document.createElement("span");c.className="chip";
    c.innerHTML=`${a.name} <span class="cf">[${a.confidence}]</span>`;cl.appendChild(c);});

  const ph=$("phases"); ph.innerHTML=""; PHASES.forEach(p=>ph.appendChild(phaseRow(p)));
  const vd=$("verdict"); vd.className="verdict"; vd.textContent="";
  $("ledger").classList.remove("show");

  const gov=new Governor({budget_usd:budget,max_repeat_calls:3,hitl_mode:hitl});
  let shipped=true, stopReason=null, stopKind=null;

  for(const phase of PHASES){
    const row=$("ph-"+phase), gv=$("gv-"+phase);
    row.classList.add("on"); await sleep(230);
    // Governor gate
    const [v,r]=gov.evaluate("phase:"+phase,{cost:pcost});
    if(v==="DENY"){row.classList.remove("on");row.classList.add("block");
      gv.innerHTML=`<span class="badge b-deny">DENY</span> policy — ${r}`;
      shipped=false;stopReason=`${phase}: policy DENY — ${r}`;stopKind="block";break;}
    if(v==="HITL"){row.classList.remove("on");row.classList.add("hitl");
      gv.innerHTML=`<span class="badge b-hitl">HITL</span> ${r} — waiting on human`;
      shipped=false;stopReason=`${phase}: HITL required — ${r}`;stopKind="hitl";break;}
    gv.innerHTML=`<span class="badge b-allow">ALLOW</span> ${r} · <span class="muted">verifying…</span>`;
    await sleep(260);
    // Iron Law gate
    const ev=verifier(phase); const [ok,vr]=ironLaw(ev);
    if(!ok){row.classList.remove("on");row.classList.add("block");
      gv.innerHTML=`<span class="badge b-allow">ALLOW</span> · <span class="badge b-deny">IRON LAW FAIL</span> ${vr}`;
      shipped=false;stopReason=`${phase}: ${vr}`;stopKind="block";break;}
    row.classList.remove("on");row.classList.add("pass");
    gv.innerHTML=`<span class="badge b-allow">ALLOW</span> · <span class="badge b-ok">VERIFIED</span> ${ev.output}`;
  }

  // verdict
  if(shipped){vd.className="verdict show ship";
    vd.innerHTML=`✔ MISSION SHIPPED — cleared the Shackle gate and the Iron Law on all ${PHASES.length} phases. On it, done.`;}
  else if(stopKind==="hitl"){vd.className="verdict show hitl";
    vd.innerHTML=`⏸ MISSION PAUSED for human review — ${stopReason}`;}
  else {vd.className="verdict show block";
    vd.innerHTML=`✖ MISSION BLOCKED — ${stopReason}. No fake ship.`;}

  // ledger
  const tbl=$("ledgertbl"); tbl.innerHTML="";
  gov.ledger.entries.forEach(e=>{const tr=document.createElement("tr");
    const cls=e.verdict==="ALLOW"?"b-allow":e.verdict==="DENY"?"b-deny":"b-hitl";
    tr.innerHTML=`<td>#${e.index}</td><td><span class="badge ${cls}">${e.verdict}</span></td>
      <td>${e.tool_name}</td><td>${e.reason}</td><td class="h">${e.entry_hash.slice(0,12)}…</td>`;tbl.appendChild(tr);});
  $("ledgerhead").textContent="head "+gov.ledger.head.slice(0,12)+"…  ·  intact: "+gov.ledger.verify();
  $("ledger").classList.add("show");
}

document.addEventListener("DOMContentLoaded",()=>{
  loadRoster();
  $("run").onclick=runMission;
  $("search").addEventListener("input",renderRoster);
});
