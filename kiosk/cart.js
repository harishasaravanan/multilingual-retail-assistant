let lastPid=null;
const _show=show;
show=function(p){lastPid=p.product_id;_show(p)};
const kj=(m,u,b)=>fetch(u,{method:m,headers:{...hdr(K),"Content-Type":"application/json"},body:b?JSON.stringify(b):undefined}).then(r=>r.json());
function renderCart(c){
  $("cart").innerHTML=c.items.map(i=>'<div>'+i.product+(i.available?'':' (out of stock)')+' <button onclick="cartRemove(\''+i.product_id+'\')">x</button></div>').join("")||"Cart empty";
}
async function cartAdd(){ if(lastPid) renderCart(await kj("POST","/cart/add",{product_id:lastPid})); }
async function cartRemove(id){ renderCart(await kj("POST","/cart/remove",{product_id:id})); }
async function cartClear(){ renderCart(await kj("POST","/cart/clear")); }
function drawCartMap(order){
  let g='<svg viewBox="0 0 400 300" width="420" style="background:#fff;border:1px solid #ccc;border-radius:8px">';
  for(const k in POS){ if(k==="KIOSK")continue;
    const [x,y]=POS[k], i=order.indexOf(k), on=i>=0;
    g+='<rect x="'+(x-35)+'" y="'+(y-30)+'" width="70" height="60" rx="6" fill="'+(on?'#2e7d32':'#e0e0e0')+'" stroke="#999"/>'
     +'<text x="'+x+'" y="'+(y+5)+'" fill="'+(on?'#fff':'#222')+'" font-size="15" text-anchor="middle">'+k+(on?' ('+(i+1)+')':'')+'</text>';
  }
  g+='<rect x="145" y="235" width="80" height="40" rx="6" fill="#1565c0"/><text x="185" y="260" fill="#fff" font-size="14" text-anchor="middle">KIOSK</text>';
  let pts=[[185,235],[185,210]], cy=210;
  for(const n of order){
    const [x,y]=POS[n], top=y<100, ny=top?110:210;
    pts.push([185,cy],[185,ny],[x,ny],[x,top?90:180],[x,ny]); cy=ny;
  }
  g+='<polyline points="'+pts.map(q=>q.join(",")).join(" ")+'" fill="none" stroke="#e65100" stroke-width="4" stroke-dasharray="8 4"/>';
  $("map").innerHTML=g+'</svg>';
}
async function cartRoute(){
  const r=await kj("GET","/cart/route");
  state("result"); $("main").textContent="Cart route";
  drawCartMap(r.order);
  $("route").textContent=r.stops.map((s,i)=>(i+1)+". Aisle "+s.node+": "+s.items.map(t=>t.product+" (shelf "+t.shelf+")").join(", ")).join("\n")+(r.skipped.length?"\nOut of stock: "+r.skipped.join(", "):"");
}
kj("GET","/cart").then(renderCart);
async function listStart(){
  await kj("POST","/list/start"); renderCart({items:[]});
  state("listening"); $("main").textContent="List mode: say items, then say 'done'";
  $("map").innerHTML=""; $("route").textContent="";
}
function onList(d){
  renderCart({items:d.items});
  if(d.done){ cartRoute(); return; }
  state("listening");
  $("main").textContent="Heard: "+(d.heard||"")+"\n→ "+(d.product||d.status);
}
(function(){const b=document.createElement("button");b.textContent="Start list";b.onclick=listStart;$("cartbar").prepend(b," ");})();
const MSG={LOW_CONFIDENCE:"Not sure. Please say the full product name.",NOT_FOUND:"Not found in this store.",ERROR:"Something went wrong. Please try again.",OUT_OF_STOCK:"Added (currently out of stock)",OK:"Added"};
onList=function(d){
  renderCart({items:d.items});
  if(d.done){ cartRoute(); return; }
  state("listening");
  $("main").textContent="Heard: "+(d.heard||"")+"\n"+(d.product?d.product+" — ":"")+(MSG[d.status]||d.status);
};
let idleT=null;
function resetIdle(){ clearTimeout(idleT); idleT=setTimeout(async()=>{ await cartClear(); $("main").textContent=""; $("map").innerHTML=""; $("route").textContent=""; state("idle"); },180000); }
["click","keydown"].forEach(e=>document.addEventListener(e,resetIdle));
resetIdle();
(function(){const b=document.createElement("button");b.textContent="New customer";b.onclick=()=>{cartClear();$("main").textContent="";$("map").innerHTML="";$("route").textContent="";state("idle")};$("cartbar").append(" ",b);})();
