// JavaScript Document
//滚动图片展览

var box,scrollIndex=0,sbArr=new Array(),sbImg=new Array();
function $(id){return document.getElementById(id)}
window.onload=function(){
	box=$("scroll");
	var bb=box.firstChild;
	var tmp=bb.getElementsByTagName("li");
	var allWidth=0;
	for (var n=0;n<tmp.length;n++){
		if(tmp[n].className=="smallbox" || true){
			var innerImg=tmp[n].getElementsByTagName('img');
			sbArr.push(tmp[n]);
			sbImg.push(innerImg[0]);
			sbArr[sbArr.length-1].scrollFlag=allWidth;
			allWidth=allWidth+sbArr[sbArr.length-1].offsetWidth;
		}
	}
	resize(bb);
	changeBtn();
}
function resize(o){
	var width=0,height=0;
	for (var n=0;n<sbArr.length;n++){
		width=width+sbArr[n].offsetWidth;
		if (sbArr[n].offsetHeight>height) height=sbArr[n].offsetHeight;
	}
	o.style.width=width+"px";
	o.style.height=height+"px";
}
function goPrevious1(){
	if (--scrollIndex<0) scrollIndex=0;
	moveBox(sbArr[scrollIndex].scrollFlag);
	changeBtn();
}
function goNext1(){
	if (sbArr[scrollIndex+1].scrollFlag>=box.scrollWidth-box.clientWidth){
		moveBox(box.scrollWidth-box.clientWidth);
		if (box.scrollLeft!=box.scrollWidth-box.clientWidth) ++scrollIndex;
	}else{
		if (++scrollIndex>sbArr.length-1) scrollIndex=sbArr.length-1;
		moveBox(sbArr[scrollIndex].scrollFlag);
	}
	changeBtn();
}
function goPrevious(){
	goPrevious1();
	goPrevious1();
	goPrevious1();
	goPrevious1();
	goPrevious1();
	showImgs();
}
function goNext(){
	goNext1();
	goNext1();
	goNext1();
	goNext1();
	goNext1();
	showImgs();
}
function showImgs(){
	for (var n=scrollIndex;n<scrollIndex+5;n++){
		sbImg[n].setAttribute("src", sbImg[n].getAttribute("data-src"));
	}
}
function changeBtn(){
	if(scrollIndex==0)$("go_left").className="go_left";
	else $("go_left").className="leftOn";
	if(box.scrollWidth-870==box.scrollLeft)$("go_right").className="go_right";
	else $("go_right").className="rightOn";
}
function moveBox(scrollFlag){
	clearTimeout(box.getAttribute("ta"));
	if (Math.abs(scrollFlag-box.scrollLeft)<1){
		box.scrollLeft=scrollFlag;
		changeBtn();
	}else{
		var ta=parseInt((scrollFlag-box.scrollLeft)/5+1);
		if (Math.abs(ta)<0.5) ta=ta>0?0.5:-0.5;
		box.scrollLeft=box.scrollLeft+ta;
		box.setAttribute("ta",setTimeout(function(){moveBox(scrollFlag)},5));
	}
}