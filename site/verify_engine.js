// Verify the browser engine's core logic in Node (no DOM), and check the
// SHA-256 + canonical hash match Python's hashlib exactly.
const fs = require("fs");
let src = fs.readFileSync("/tmp/ONITSIR/site/app.js", "utf8");
src = src.split("// ── UI wiring")[0];  // drop DOM code
const M = eval(src + "\n;({canonicalHash,Governor,AuditLedger});");
const {canonicalHash,Governor,AuditLedger}=M;
// sha256, decide, route, ironLaw are function declarations that leak from eval

let fails = 0;
function ok(name, cond){ console.log((cond?"PASS":"FAIL")+" — "+name); if(!cond) fails++; }

// 1. sha256 known-answer
ok("sha256('abc')", sha256("abc") === "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
ok("sha256('')", sha256("") === "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");

// 2. canonical hash order-independence
ok("canonicalHash order-independent",
   canonicalHash({query:"x",error:"y"}) === canonicalHash({error:"y",query:"x"}));

// 3. decide precedence
ok("decide default ALLOW", JSON.stringify(decide({},{}, {tool_name:"t"}))===JSON.stringify(["ALLOW","within_thresholds"]));
ok("decide circuit_open", decide({},{circuit_tripped:true},{tool_name:"t"})[1]==="circuit_open");
ok("decide budget_exhausted", decide({budget_usd:1},{budget_remaining_usd:0},{tool_name:"t"})[1]==="budget_exhausted");
ok("decide hitl_always", decide({hitl_mode:"always"},{},{tool_name:"t"})[0]==="HITL");
ok("decide max_repeat", decide({max_repeat_calls:3},{repeat_counts:{t:3},last_tool_name:"t"},{tool_name:"t"})[1]==="max_repeat_exceeded");

// 4. Governor budget breaker + ledger integrity
const g=new Governor({budget_usd:0.05});
g.evaluate("phase:a",{cost:0.05});
const [v,r]=g.evaluate("phase:b");
ok("governor denies over budget", v==="DENY");
ok("ledger chain intact", g.ledger.verify()===true);

// 5. Router staffs a crew from the real roster
const roster=JSON.parse(fs.readFileSync("/tmp/ONITSIR/data/roster.json","utf8"));
const crew=route(roster,"reddit community growth marketing",3);
ok("router staffs <=3", crew.length>0 && crew.length<=3);
ok("router top match relevant", /reddit|community|market|growth/i.test(crew[0].name+crew[0].category));
console.log("TOP CREW:", crew.map(c=>c.name+" ["+c.confidence+"]").join(", "));

// 6. Iron law rejects stale/failing
ok("ironLaw rejects not-passing", ironLaw({command:"c",output:"x",passed:false})[0]===false);
ok("ironLaw accepts good", ironLaw({command:"c",output:"ok",passed:true,at:Math.floor(Date.now()/1000)})[0]===true);

console.log(fails===0 ? "\nALL JS ENGINE CHECKS PASS" : `\n${fails} CHECK(S) FAILED`);
process.exit(fails===0?0:1);
