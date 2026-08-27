// مولد أصول الإصدار التالي — محلي فقط، لا رفع ولا نشر.
// صفحات WebP + مناطق الحواشي + الفهرس، لكل المقاسات؛ الوضعان: الأساس نظيف (دون توثيق)
// و«بتوثيق» يتحقق عبر مناطق النقر (الظل يرسم فوق الصورة من الإحداثيات)، وعينات مظللة للمعاينة.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT = process.env.OUT || 'release_r2';
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null;
const texts = JSON.parse(fs.readFileSync('master_texts.json', 'utf8'));
const entries = JSON.parse(fs.readFileSync('master_entries.json', 'utf8'));

const SIZES = [
  { name: 'mobile',  w: 720,  h: 1080, fs: 30, pad: 48 },
  { name: 'tablet',  w: 1080, h: 1620, fs: 38, pad: 72 },
  { name: 'desktop', w: 1440, h: 2160, fs: 46, pad: 96 },
];

const GROUP_OF = n => {
  const g = [[1,18],[19,26],[27,34],[35,42],[43,50],[51,58],[59,66],[67,74],[75,82],[83,90],[91,98],[99,106],[107,114],[115,122],[123,133]];
  for (let i=0;i<g.length;i++) if (n>=g[i][0]&&n<=g[i][1]) return i+1;
  return 0;
};

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// يحول متن الفصل (بعلامات #ن...#) إلى HTML
function chapterHTML(num, sz) {
  const t = texts[num];
  const paras = t.split(/\n\n+/);
  const titleLine = paras.shift().replace(/\*\*/g,'');
  const title = titleLine.replace(/^\d{3}\s*-\s*/,'');
  const body = paras.map(p=>{
    let h = esc(p);
    // مدايات التوثيق: #12نص# — الفتح رقم ثم النص حتى أول '#'
    h = h.replace(/#(\d+)(?!\d)([\s\S]*?)#/g, (m,n,seg)=>`<span class="doc" data-fn="${n}">${seg}</span>`);
    // التسويد
    h = h.replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>');
    return `<p>${h}</p>`;
  }).join('\n');
  return `<!doctype html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>
  @font-face{font-family:Amiri;src:url('file:///tmp/claude-0/-home-user-cgm-remote-monitor/3ec2e863-27e6-5b6f-b50a-e4725e49a6a0/scratchpad/fonts/Amiri-Regular.ttf');font-weight:400;}
  @font-face{font-family:Amiri;src:url('file:///tmp/claude-0/-home-user-cgm-remote-monitor/3ec2e863-27e6-5b6f-b50a-e4725e49a6a0/scratchpad/fonts/Amiri-Bold.ttf');font-weight:700;}
  html,body{margin:0;padding:0;background:#fdfcf8;}
  #book{width:${sz.w-2*sz.pad}px;margin:0 ${sz.pad}px;font-family:Amiri,serif;font-size:${sz.fs}px;
        line-height:1.9;color:#1d1a14;text-align:justify;}
  h1{font-size:${Math.round(sz.fs*1.5)}px;text-align:center;font-weight:700;margin:0;padding-top:${sz.pad}px;padding-bottom:${Math.round(sz.fs*0.8)}px;}
  p{margin:0;padding-top:${Math.round(sz.fs*0.55)}px;}
  strong{font-weight:700;}
  .shade .doc{background:rgba(176,138,64,0.16);border-radius:4px;}
  </style></head><body class="${process.env.SHADE?'shade':''}"><div id="book"><h1>${esc(title)}</h1>${body}</div></body></html>`;
}

async function main(){
  fs.mkdirSync(OUT,{recursive:true});
  const browser = await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
  const chapters = (ONLY||Object.keys(texts)).sort();
  const index = { release: null, sizes: {}, chapters: [] };
  for (const sz of SIZES) index.sizes[sz.name]={w:sz.w,h:sz.h,pages:0};
  const t0=Date.now();
  for (const num of chapters) {
    const chapMeta = { num, group: GROUP_OF(parseInt(num)),
      title: texts[num].split('\n')[0].replace(/\*\*/g,'').replace(/^\d{3}\s*-\s*/,''),
      footnotes: entries[num].length, pages:{}, hits:{} };
    for (const sz of SIZES) {
      const page = await browser.newPage({viewport:{width:sz.w,height:sz.h}});
      const htmlPath = path.resolve(`${OUT}/_tmp_${num}_${sz.name}.html`);
      fs.writeFileSync(htmlPath, chapterHTML(num, sz));
      await page.goto('file://'+htmlPath);
      await page.evaluate(()=>document.fonts.ready);
      // حدود الصفحات على رؤوس الفقرات + مواضع مناطق التوثيق
      const data = await page.evaluate((H)=>{
        const sy=window.scrollY;
        // أشرطة الأسطر: صناديق الأسطر لكل فقرة عبر Range، مدموجة عموديا
        const bands=[];
        for (const b of document.querySelectorAll('#book h1, #book p')){
          const range=document.createRange(); range.selectNodeContents(b);
          const rs=[...range.getClientRects()].filter(r=>r.width>0&&r.height>0);
          if (!rs.length){ const r=b.getBoundingClientRect(); rs.push(r); }
          for (const r of rs){
            const top=r.top+sy, bot=r.bottom+sy;
            const hit=bands.find(x=>!(bot<x.top-2||top>x.bot+2));
            if (hit){ hit.top=Math.min(hit.top,top); hit.bot=Math.max(hit.bot,bot); }
            else bands.push({top,bot});
          }
        }
        bands.sort((a,b)=>a.top-b.top);
        // دمج المتراكب بعد الفرز
        const merged=[]; for (const x of bands){
          if (merged.length && x.top<=merged[merged.length-1].bot+2)
            merged[merged.length-1].bot=Math.max(merged[merged.length-1].bot,x.bot);
          else merged.push({...x});
        }
        const paginate=(limit)=>{
          let pageTop=0; const brs=[0];
          for (const x of merged){
            if (x.bot - pageTop > limit && x.top > pageTop){ pageTop=x.top-6; brs.push(pageTop); }
          }
          return brs;
        };
        let breaks=paginate(H);
        const total=document.getElementById('book').getBoundingClientRect().height;
        // موازنة الصفحات: لا صفحة أخيرة يتيمة — أعد التقسيم على ارتفاع متساو تقريبًا
        if (breaks.length>1){
          const n=breaks.length;
          const eq=paginate(Math.max(total/n + 40, H*0.6));
          if (eq.length===n) breaks=eq;
        }
        const spans=[...document.querySelectorAll('span.doc')].map(s=>({
          fn: s.dataset.fn,
          rects: [...s.getClientRects()].map(r=>({x:r.left+window.scrollX,y:r.top+sy,w:r.width,h:r.height}))
        }));
        return {breaks, total, spans};
      }, sz.h - 2*sz.pad); // هامش سفلي وعلوي
      const breaks = data.breaks; breaks.push(data.total + 1);
      const npages = breaks.length-1;
      const dir = `${OUT}/${sz.name}/${num}`; fs.mkdirSync(dir,{recursive:true});
      const hits=[];
      for (let i=0;i<npages;i++){
        const y=breaks[i], hUsed=Math.min(sz.h, Math.ceil(breaks[i+1]-y));
        await page.screenshot({path:`${dir}/p${String(i+1).padStart(3,'0')}.png`,
          clip:{x:0,y,width:sz.w,height:Math.max(64,Math.min(hUsed,sz.h))}, fullPage:true});
      }
      for (const s of data.spans) for (const r of s.rects){
        // صفحة المستطيل
        let pi=0; for (let i=0;i<npages;i++) if (r.y>=breaks[i]&&r.y<breaks[i+1]) {pi=i;break;}
        hits.push({fn:+s.fn,page:pi+1,x:+(r.x/sz.w).toFixed(4),y:+((r.y-breaks[pi])/sz.h).toFixed(4),
                   w:+(r.w/sz.w).toFixed(4),h:+(r.h/sz.h).toFixed(4)});
      }
      fs.writeFileSync(`${dir}/hits.json`, JSON.stringify(hits));
      chapMeta.pages[sz.name]=npages; chapMeta.hits[sz.name]=hits.length;
      index.sizes[sz.name].pages+=npages;
      await page.close(); fs.unlinkSync(htmlPath);
    }
    // حواشي الفصل للنافذة الهادئة
    fs.writeFileSync(`${OUT}/notes_${num}.json`, JSON.stringify(entries[num].map(e=>({
      n:e.local, source:e.body.replace(/\s*الدرجة:.*$/,'').replace(/\*\*/g,''),
      grade:(e.body.match(/الدرجة:\s*\*\*([^*]+)\*\*/)||[,''])[1] })), null, 0));
    index.chapters.push(chapMeta);
    if (index.chapters.length%20===0) console.log(`..${index.chapters.length}/${chapters.length} فصلا (${Math.round((Date.now()-t0)/1000)}ث)`);
  }
  fs.writeFileSync(`${OUT}/index.json`, JSON.stringify(index,null,1));
  await browser.close();
  console.log('DONE chapters:', index.chapters.length, 'pages:', JSON.stringify(index.sizes));
}
main().catch(e=>{console.error(e);process.exit(1);});
