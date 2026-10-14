const fs=require('node:fs'),M=require('./model.js'),assert=require('node:assert/strict');
const s=M.parse(fs.readFileSync('C:/Users/LSY/Downloads/房间布局 (4).json','utf8'));
const shelves={id:'library',name:'暖木书架·卫生间外侧墙',x:1.5,y:1.91,w:2.4,d:.3,h:2,z:0,angle:180,color:'#b49370',visible:true,zone:'room',kind:'box',shape:'shelves'};
const collection={id:'collection',name:'独立收藏柜·浅柜',x:.25,y:2.85,w:1.2,d:.3,h:1.8,z:0,angle:90,color:'#a48768',visible:true,zone:'room',kind:'box',shape:'shelves'};
s.objects.push(shelves,collection);
for(const o of [shelves,collection])assert.deepEqual(M.warnings(o,s),[],o.name);
M.parse(JSON.stringify(s));fs.writeFileSync('温馨书房-书架收藏柜.json',JSON.stringify(s,null,2));
console.log('PASS: new 2.4m bookshelf and 1.2m shallow display cabinet fit existing layout, without overlap.');

