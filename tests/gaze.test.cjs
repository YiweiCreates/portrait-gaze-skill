const {test}=require('node:test');
const assert=require('node:assert/strict');
const {offset}=require('../portrait-gaze/assets/gaze.js');
const eyes=[{center:[100,100],max_offset:[12,5]},{center:[200,100],max_offset:[10,6]}];
test('neutral at midpoint and without target',()=>{assert.deepEqual(offset(eyes,null),{x:0,y:0});assert.deepEqual(offset(eyes,{x:150,y:100}),{x:0,y:0});});
test('looks left and right with bounded displacement',()=>{assert.equal(offset(eyes,{x:-10000,y:100}).x,-10);assert.equal(offset(eyes,{x:10000,y:100}).x,10);});
test('all directions stay inside displacement ellipse',()=>{for(let i=0;i<360;i++){const t=i*Math.PI/180,o=offset(eyes,{x:150+1000*Math.cos(t),y:100+1000*Math.sin(t)});assert.ok((o.x/10)**2+(o.y/5)**2<=1+1e-12);}});
test('gaze frame rotates with a tilted portrait',()=>{const rotated=[{center:[100,100],max_offset:[12,5]},{center:[100,200],max_offset:[10,6]}];const o=offset(rotated,{x:100,y:10000});assert.ok(Math.abs(o.x)<1e-9);assert.equal(o.y,10);});
