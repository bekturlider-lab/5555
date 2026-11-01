import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createLogoPressSequence} from '../src/utils/admin-shortcut.ts';

test('opens exactly on the seventh consecutive press, then starts a new series',()=>{
 const sequence=createLogoPressSequence();
 for(let n=0;n<6;n++)assert.equal(sequence.press(n*100),false);
 assert.equal(sequence.press(600),true);
 assert.equal(sequence.press(700),false);
});
test('a pause longer than one second starts the series over',()=>{
 const sequence=createLogoPressSequence();
 for(let n=0;n<6;n++)sequence.press(n*100);
 assert.equal(sequence.press(1501),false);
 for(let n=1;n<6;n++)assert.equal(sequence.press(1501+n*100),false);
 assert.equal(sequence.press(2101),true);
});
test('the one-second boundary is allowed',()=>{
 const sequence=createLogoPressSequence();
 for(let n=0;n<6;n++)assert.equal(sequence.press(n*1000),false);
 assert.equal(sequence.press(6000),true);
});
test('an outside click or loss of focus cancels an incomplete series',()=>{
 const sequence=createLogoPressSequence();
 for(let n=0;n<6;n++)sequence.press(n*100);
 sequence.reset();
 for(let n=0;n<6;n++)assert.equal(sequence.press(600+n*100),false);
 assert.equal(sequence.press(1200),true);
});
test('separate logos cannot share a series',()=>{
 const header=createLogoPressSequence(),footer=createLogoPressSequence();
 for(let n=0;n<4;n++)assert.equal(header.press(n*100),false);
 for(let n=0;n<3;n++)assert.equal(footer.press(400+n*100),false);
});
