// 测试用的假 Claude：内存数据库 + 按提示词内容回固定 JSON 的 sample + 假下载。只在 tests/ 里用，不进正式页面。
window.__seed = SEED_PLACEHOLDER;
(function(){
  var store = {};
  var listeners = [];
  function notify(){ setTimeout(function(){ listeners.forEach(function(l){ l(); }); }, 5); }
  function snapDoc(path){ var d = store[path]; return { id: path.split('/').pop(), exists: !!d, data: function(){ return d ? JSON.parse(JSON.stringify(d)) : undefined; }, metadata: {hasPendingWrites:false, fromCache:false} }; }
  function docRef(path){ return {
    id: path.split('/').pop(), path: path,
    get: async function(){ return snapDoc(path); },
    set: async function(data){ store[path] = JSON.parse(JSON.stringify(data)); notify(); },
    update: async function(data){ store[path] = Object.assign(store[path]||{}, data); notify(); },
    delete: async function(){ delete store[path]; notify(); },
    onSnapshot: function(next){ var f=function(){ next(snapDoc(path)); }; listeners.push(f); setTimeout(f, 5); return function(){ listeners = listeners.filter(function(x){return x!==f}); }; },
    collection: function(p){ return colRef(path + '/' + p); }
  }; }
  function colRef(path, ord, lim){
    function docsNow(){
      var depth = path.split('/').length + 1;
      var ds = Object.keys(store).filter(function(k){ return k.indexOf(path + '/') === 0 && k.split('/').length === depth; }).map(snapDoc);
      if (ord) ds.sort(function(a,b){ var x=a.data()[ord[0]], y=b.data()[ord[0]]; return ord[1]==='desc'? y-x : x-y; });
      if (lim) ds = ds.slice(0, lim);
      return ds;
    }
    return {
      path: path,
      doc: function(id){ return docRef(path + '/' + (id || ('d' + Math.random().toString(36).slice(2)))); },
      add: async function(data){ var r = this.doc(); await r.set(data); return r; },
      orderBy: function(f, dir){ return colRef(path, [f, dir||'asc'], lim); },
      limit: function(n){ return colRef(path, ord, n); },
      where: function(){ return this; },
      get: async function(){ var d=docsNow(); return {docs:d,size:d.length,empty:!d.length}; },
      onSnapshot: function(next){ var f=function(){ var d=docsNow(); next({docs:d,size:d.length,empty:!d.length,metadata:{}}); }; listeners.push(f); setTimeout(f, 5); return function(){ listeners = listeners.filter(function(x){return x!==f}); }; }
    };
  }
  var seed = window.__seed;
  store['projects/mengfusheng'] = seed.project;
  seed.checkpoints.forEach(function(c, i){ store['projects/mengfusheng/checkpoints/c' + i] = c; });
  var db = { doc: docRef, collection: function(p){ return colRef(p); } };
  function cand(){ return {candidates:[{id:'A',text:'测试候选一：她把信压在碑脚。',person:'她',object:'信',action:'压信',change:'信送到',step:'最后一步',effect:'选它会变：测试'},{id:'B',text:'测试候选二',person:'她',object:'碑',action:'抚',change:'哭',step:'x',effect:'y'},{id:'C',text:'测试候选三',person:'她',object:'风',action:'吹',change:'静',step:'x',effect:'y'}]}; }
  async function sampleJson(prompt, opts){
    window.__calls = (window.__calls||[]).concat([prompt.slice(-200)]);
    if (opts && opts.onText) opts.onText({text:'{...', delta:'{...'});
    if (prompt.indexOf('重新为这一段') >= 0) return cand();
    if (prompt.indexOf('为下面这些段') >= 0) return {segments: []};
    if (prompt.indexOf('把各段已选的段核心按顺序连读') >= 0) return {ok:false, summary:'基本连得上，01G 稍弱。', issues:[{code:'01G', problem:'收尾和集核心最后一步重复', fix:'把镜头升起放到这一段'}]};
    if (prompt.indexOf('四张表') >= 0) {
      var beats=[]; for (var t=0;t<120;t+=10) beats.push({a:t,b:t+10,scene:'窗边木桌',people:'婆婆',objects:'信',acting:'抚信',core: t===50?'':'信往前走一步',tension: Math.min(10, 2+t/12)});
      return {rules:['同一张桌子同一机位','她只哭一次'], props:[{name:'信',meaning:'核心',events:[{t:46,what:'开始写'},{t:86,what:'落地'}],end:'压在碑脚'},{name:'照片',meaning:'他的脸',events:[{t:2,what:'捧着'}],end:''}], people:[{seg:'01A',age:'八十多',want:'跟他待着',doing:'摸照片',notDoing:'不哭',him:'照片里'}], scenes:[{name:'窗边木桌',role:'写信的地方',segs:'01A、01D',contents:'照片、钢笔'}], beats:beats, proposals:[{id:'p1',text:'照片上他脸那块摸白了',where:'01A',why:'一眼看出摸了几十年'},{id:'p2',text:'碑前压信',where:'01G',why:'信送到了'}]};
    }
    if (prompt.indexOf('集核心候选') >= 0 || prompt.indexOf('3 个集核心候选') >= 0) return cand();
    return {};
  }
  var sample = function(){ return Promise.resolve({text:''}); };
  sample.json = sampleJson;
  var downloads = { save: async function(o){ window.__saved = o.filename; return {status:'saved'}; } };
  window.claude = { use: function(n){ return Promise.resolve(n==='db'?db:n==='sample'?sample:n==='downloads'?downloads:null); } };
  window.__store = store;
})();
