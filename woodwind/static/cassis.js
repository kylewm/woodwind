<!-- cassis.js Copyright 2008-2015 Tantek Çelik http://tantek.com   -->
<!-- http://cassisproject.com conceived 2008-254, created 2009-299  -->
<!-- http://creativecommons.org/licenses/by-sa/3.0/                 -->
/* if you see this in the browser, you need to wrap your include of cassis.js with calls to ob_start and ob_end_clean, e.g. use the following in your PHP: ob_start(); include 'cassis.js'; ob_end_clean(); <?php 
// --------------------------------------------------------------------
// cassis0js.php - processed only by PHP. Use only // comments here.


// global configuration

if (php_min_version("5.1.0")) {
  date_default_timezone_set("UTC");
}

function php_min_version($s) {
  $s = explode(".",$s);
  $phpv = explode(".",phpversion());
  for ($i=0;$i<count($s);$i++) {
    if ($s[$i]>$phpv[$i]) {
      return false; 
    }
  }
  return true;
}


// date time functions

function date_get_full_year($d = "") {
 if ($d == "") {
   $d = new DateTime();
 }
 return $d->format('Y');
} 

function date_get_timestamp($d) { 
 return $d->format('U'); // $d->getTimestamp(); // in PHP 5.3+
}

function date_get_ordinal_days($d) {
 return 1+$d->format('z');
}

function date_get_rfc3339($d) {
 return $d->format('c');
}


// old wrappers. transition code away from them, do not use them in new code.
function getFullYear($d = "") {  
  // 2010-020 obsoleted. Use date_get_full_year instead
  return date_get_full_year($d);
}

// end cassis0js.php
// --------------------------------------------------------------------
/*/ // this comment inverter switches from PHP only to javascript only
// --------------------------------------------------------------------
// cassis0php.js - processed only by javascript. Use only // comments.


// arrays

function array() { // makes an array from as many items as you want to give it.
  return Array.prototype.slice.call(arguments);
}

function is_array(a) {
  return (typeof(a)=="object" && (a instanceof Array));
}

function count(a) {
 return a.length;
}

function array_slice(a, b, e) { // slice an array, begin, optional end
  if (a === undefined) { return array(); }
  if (b === undefined) { return a; }
  if (e === undefined) { return a.slice(b); }
  return a.slice(b, e);
}

// math and numerical functions

function floor(n) {
  return Math.floor(n);
}

function intval(n) {
  return parseInt(n);
}



Array.min = function(a){ // from http://ejohn.org/blog/fast-javascript-maxmin/
  return Math.min.apply(Math, a);
};

function min() {
 var m = arguments;
 if (m.length < 1) {
   return false;
 } 
 if (m.length == 1) {
   m = m[0];
   if (!is_array(m)) {
     return m;
   }
 }
 return Array.min(m);
}

function ctype_digit(s) {
 return /^[0-9]+$/.test(s);
}

function ctype_space(s) {
 return /\s/.test(s);
}

// date time functions

function date_create(s) {
 d = new Date();
 d.parse(s);
 return d;
}

function date_get_full_year(d) {
 if (arguments.length < 1) {
   d = new Date();
 }
 return d.getFullYear();
}

function date_get_timestamp($d) {
 return floor($d.getTime()/1000);
}

function date_get_rfc3339($d) {
  return strcat($d.getFullYear(),'-',
                str_pad_left(1+$d.getUTCMonth(),2,"0"),'-',
                str_pad_left($d.getDate(),2,"0"),'T',
                str_pad_left($d.getUTCHours(),2,"0"),':',
                str_pad_left($d.getUTCMinutes(),2,"0"),':',
                str_pad_left($d.getUTCSeconds(),2,"0"),'Z');
}

// newcal

function date_get_ordinal_days($d) {
  return ymdp_to_d($d.getFullYear(),1+$d.getMonth(),$d.getDate());
}


// character and string functions 

function ord(s) {
 return s.charCodeAt(0);
}

function strlen(s) {
 return s.length;
} 

function substr(s, o, n) {
  var m = strlen(s);
  if ((o < 0 ? -1-o : o) >= m) { return false; }
  if (o < 0) { o = m + o; }
  if (n < 0) { n = m - o + n; }
  if (n === undefined) { n = m - o; }
  return s.substring(o, o + n);
}

function substr_count(s, n) {
 return s.split(n).length - 1;
}

function strpos(h,n,o) {
 // clients must triple-equal test ===false for no match!
 // consider using offset(n,h) instead (0 - not found, else 1-based index)
 if (arguments.length == 2) {
  o = 0;
 }
 o = h.indexOf(n,o);
 if (o==-1) { return false; }
 else { return o; }
}

function strncmp(s1,s2,n) {
 s1 = substr(s1+'',0,n);
 s2 = substr(s2+'',0,n);
 return (s1==s2) ? 0 :
        ((s1 < s2) ? -1 : 1);
}

function explode(d,s,n) {
 if (arguments.length == 2) {
   return s.split(d);
 }
 return s.split(d,n);
}

function implode(d,a) {
 return a.join(d);
}

function rawurlencode(s) {
 return encodeURIComponent(s);
}

function htmlspecialchars(s) {
 var c= [["&","&amp;"],["<","&lt;"],[">","&gt;"],["'","&#039;"],['"',"&quot;"]];
 for (i=0;i<c.length;i++) {
  s = s.replace(new RegExp(c[i][0],"g"),c[i][1]); // s.replace(c[i][0],c[i][1]);
 }
 return s;
}

function str_ireplace(a,b,s) {
 return s.replace(new RegExp(a,"gi"),b);
}

function preg_match(p,s) {
  return (s.match(trim_slashes(p)) ? 1 : 0);
}

function preg_split(p,s) {
  return s.split(new RegExp(trim_slashes(p),"gi"));
}

function trim() {
 var m = arguments;
 var s = m[0];
 var c = count(m)>1 ? m[1] : " \t\n\r\f\x00\x0b\xa0";
 var i = 0;
 var j = strlen(s);
 while (contains(c,s[i]) && i<j) {
   i++;
 }
 --j;
 while (j>i && contains(c,s[j])) {
   --j;
 }
 j++;
 if (j>i) {
   return substr(s,i,j-i);
 }
 else {
   return '';
 }
}

function rtrim() {
 var m = arguments;
 var s = m[0];
 var c = count(m)>1 ? m[1] : " \t\n\r\f\x00\x0b\xa0";
 var j = strlen(s)-1;
 while (j>=0 && contains(c,s[j])) {
   --j;
 }
 if (j>=0) {
   return substr(s,0,j+1);
 }
 else {
   return '';
 }
}

function strtolower(s) {
  return s.toLowerCase();
}

function ucfirst(s) {
  return s.charAt(0).toUpperCase() + substr(s, 1);
}

// more javascript-only php-equivalent functions here 


// javascript-only framework functions
function targetelement(e) {
  var t;
  e = e ? e : window.event;
  t = e.target ? e.target : e.srcElement;
  t = (t.nodeType == 3) ? t.parentNode : t; // Safari workaround
  return t;
}

function doevent(el,evt) {
  if (evt=="click" && el.tagName=='A') {
  // note: dispatch/fireEvent not work FF3.5+/IE8+ on [a href] w "click" event
    window.location = el.href; // workaround
    return true;
  }
  if (document.createEvent) {
    var eo = document.createEvent("HTMLEvents");
    eo.initEvent(evt, true, true);
    return !el.dispatchEvent(eo);
  } 
  else if (document.createEventObject) {
    return el.fireEvent("on"+evt);
  }
}


// old wrappers. transition code away from them, do not use them in new code.
//function getFullYear(d) {       // use date_get_full_year instead
//  return date_get_full_year(d);
//}


// end cassis0php.js
// --------------------------------------------------------------------

/**/ // unconditional comment closer enters PHP+javascript processing
/* ------------------------------------------------------------------ */
/* cassis0.js - processed by both PHP and javascript */

function js() {
 return ("00"==false);
}

// character and string functions 

function strcat() { // takes as many strings as you want to give it.
 $strcatr = "";
 $isjs = js();
 $args = $isjs ? arguments : func_get_args();
 for ($strcati=count($args)-1; $strcati>=0; $strcati--) {
    $strcatr = $isjs ? $args[$strcati] + $strcatr : $args[$strcati] . $strcatr;
 }
 return $strcatr;
}

function number($s) {
 return $s - 0;
}

function string($n) {
 if (js()) { 
   if (typeof($n)=="number")
     return Number($n).toString(); 
   else if (typeof($n)=="undefined")
     return "";
   else return $n.toString();
 }
 else { return "" . $n; }
}

function str_pad_left($s1,$n,$s2) {
 $s1 = string($s1);
 $s2 = string($s2);
 if (js()) {
   $n -= strlen($s1);
   while ($n >= strlen($s2)) { 
     $s1 = strcat($s2,$s1); 
     $n -= strlen($s2);
   }
   if ($n > 0) {
     $s1 = strcat(substr($s2,0,$n),$s1);
   }
   return $s1;
 }
 else { return str_pad($s1,$n,$s2,STR_PAD_LEFT); }
}

function trim_slashes($s) {
  if ($s[0]=="/") { // strip unnecessary / delimiters that PHP regexp funcs want
    return substr($s,1,strlen($s)-2);
  }
  return $s;
}

function preg_matches($p,$s) {
  if (js()) {
    return $s.match(new RegExp(trim_slashes($p),"gi"));
  }
  else {
    $m = array();
    if (preg_match_all($p, $s, $m, PREG_PATTERN_ORDER) !== FALSE) {
      return $m[0];
    }
    else {
      return array();
    }
  }
}


/* end cassis0.js */


function ctype_email_local($s) {
 // close enough. no '.' because this is used for last char of.
 return (preg_match("/^[a-zA-Z0-9_%+-]+$/",$s));
}

function ctype_uri_scheme($s) {
 return (preg_match("/^[a-zA-Z][a-zA-Z0-9+.-]*$/",$s));
}
/* ------------------------------------------------------------------ */


/* newbase60 */

function num_to_sxg($n) {
 $s = "";
 $p = "";
 $m = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ_abcdefghijkmnopqrstuvwxyz";
 if ($n==="" || $n===0) { return "0"; }
 if ($n<0) {
   $n = 0-$n;
   $p = "-";
 }
 while ($n>0) {
   $d = $n % 60;
   $s = strcat($m[$d],$s);
   $n = ($n-$d)/60;
 }
 return strcat($p,$s);
}

function num_to_sxgf($n, $f) {
 if (!$f) { $f=1; }
 return str_pad_left(num_to_sxg($n), $f, "0");
}

function sxg_to_num($s) {
 $n = 0;
 $m = 1;
 $j = strlen($s);
 if ($s[0]=="-") {
   $m= -1;
   $j--;
   $s = substr($s,1,$j);
 }
 for ($i=0;$i<$j;$i++) { // iterate from first to last char of $s
   $c = ord($s[$i]); //  put current ASCII of char into $c  
   if ($c>=48 && $c<=57) { $c=$c-48; }
   else if ($c>=65 && $c<=72) { $c-=55; }
   else if ($c==73 || $c==108) { $c=1; } // typo capital I, lowercase l to 1
   else if ($c>=74 && $c<=78) { $c-=56; }
   else if ($c==79) { $c=0; } // error correct typo capital O to 0
   else if ($c>=80 && $c<=90) { $c-=57; }
   else if ($c==95 || $c==45) { $c=34; } // _ underscore and correct dash - to _
   else if ($c>=97 && $c<=107) { $c-=62; }
   else if ($c>=109 && $c<=122) { $c-=63; }
   else break; // treat all other noise as end of number
   $n = 60*$n + $c;
 }
 return $n*$m;
}

function sxg_to_numf($s, $f) {
 if ($f===undefined) { $f=1; }
 return str_pad_left(sxg_to_num($s), $f, "0");
}

/* == compat functions only == */
function numtosxg($n) {
  return num_to_sxg($n);
}

function numtosxgf($n, $f) {
  return num_to_sxgf($n, $f);
}

function sxgtonum($s) {
  return sxg_to_num($s);
}

function sxgtonumf($s, $f) {
  return sxg_to_numf($s, $f);
}
/* == end compat functions == */

/* end newbase60 */



/* ------------------------------------------------------------------ */


/* date and time */

function date_create_ymd($s) {
 if (!$s) {
   return (js() ? new Date() : new DateTime());
 }
 if (js()) { 
   if (substr($s,4,1)=='-') {
      $s=strcat(strcat(substr($s,0,4),substr($s,5,2)),substr($s,8,2));
   }
   $d = new Date(substr($s,0,4),substr($s,4,2)-1,substr($s,6,2));
   $d.setHours(0); // was setUTCHours, avoiding bc JS has no default timezone
   return $d;
 }
 else { return date_create(strcat($s," 00:00:00")); }
}

function date_create_timestamp($s) {
 if (js()) {
   return new Date(1000*$s);
 }
 else {
   return new DateTime(strcat("@",string($s)));
 }
}

// function date_get_timestamp($d) { } // defined in PHP/JS specific code above.

// function date_get_rfc3339($d) { } // defined in PHP/JS specific code above.

function dt_to_time($dt) {
  $dt = explode("T", $dt);
  if (count($dt)==1) {
    $dt = explode(" ", $dt);
  }
  return (count($dt)>1) ? $dt[1] : "0:00";
}

function dt_to_date($dt) {
  $dt = explode("T", $dt);
  if (count($dt)==1) {
    $dt = explode(" ", $dt);
  }
  return $dt[0];
}

function dt_to_ordinal_date($dt) {
  return ymd_to_yd(dt_to_date($dt));
}
/* end date and time */


/* ------------------------------------------------------------------ */


/* newcal */

function isleap($y) {
  return ($y % 4 == 0 && ($y % 100 != 0 || $y % 400 == 0));
}

function ymdp_to_d($y,$m,$d) {
  $md = array(
         array(0,31,59,90,120,151,181,212,243,273,304,334),
         array(0,31,60,91,121,152,182,213,244,274,305,335));
  return $md[number(isleap($y))][$m-1] + number($d);
}

function ymd_to_d($d) {
  if (substr($d,4,1)=='-') {
    return ymdp_to_d(substr($d,0,4),substr($d,5,2),substr($d,8,2));
  }
  else {
    return ymdp_to_d(substr($d,0,4),substr($d,4,2),substr($d,6,2));
  }
}

function ymdp_to_yd($y,$m,$d) {
  return strcat(str_pad_left($y,4,"0"),'-', str_pad_left(ymdp_to_d($y,$m,$d),3,"0"));
}

function ymd_to_yd($d) {
  if (substr($d,4,1)=='-') {
    return ymdp_to_yd(substr($d,0,4),substr($d,5,2),substr($d,8,2));
  }
  else {
    return ymdp_to_yd(substr($d,0,4),substr($d,4,2),substr($d,6,2));
  }
}

// function date_get_ordinal_days($d) {} // defined in PHP/JS specific code.

function date_get_bim() {
 $args = js() ? arguments : func_get_args();

 return bim_from_od(
         date_get_ordinal_days(
          date_create_ymd((count($args) > 0) ? $args[0] : 0)));
} 


function get_nm_str($m) {
  $a = array("New January", "New February", "New March", "New April", "New May", "New June", "New July", "New August", "New September", "New October", "New November", "New December");
  return $a[($m-1)];
}

function bim_from_od($d) {
  return 1+floor(($d-1)/61);
}

function nm_from_od($d) {
  return ((($d-1) % 61) > 29) ? 2+2*(bim_from_od($d)-1) : 1+2*(bim_from_od($d)-1);
}

function date_get_ordinal_date(/* $d = "" */) {
 $args = js() ? arguments : func_get_args();
 $d = date_create_ymd((count($args) > 0) ? $args[0] : 0);
 return strcat(date_get_full_year($d), '-',
               str_pad_left(date_get_ordinal_days($d), 3, "0"));
}

/* end newcal */


// -------------------------------------------------------------------
// begin epochdays

function y_to_days($y) {
  // convert y-01-01 to epoch days
  return floor(
   (date_get_timestamp(date_create_ymd(strcat($y, "-01-01"))) -
    date_get_timestamp(date_create_ymd("1970-01-01")))/86400);
}

// convert ymd to epoch days and sexagesimal epoch days (sd)

function ymd_to_days($d) {
  return yd_to_days(ymd_to_yd($d));
}

/* old:
function ymd_to_days($d) {
  // fails in JS, "2013-03-10" and "2013-03-11" both return 15774 
  return floor((date_get_timestamp(date_create_ymd($d))-date_get_timestamp(date_create_ymd("1970-01-01")))/86400);
}
*/

function ymd_to_sd($d) {
  return num_to_sxg(ymd_to_days($d));
}

function ymd_to_sdf($d,$f) {
  return num_to_sxgf(ymd_to_days($d),$f);
}

// convert ordinal date (YYYY-DDD) to 
// ymd - YYYY-MM-DD, epoch days, and sexagesimal epoch days (sd)

function ydp_to_ymd($y,$d) {
  $md = array(
         array(0,31,59,90,120,151,181,212,243,273,304,334,365),
         array(0,31,60,91,121,152,182,213,244,274,305,335,366));
  $d -= 1;
  $m = trunc($d / 29);
  if ($md[isleap($y)-0][$m] > $d) $m -= 1;
  $d = $d - $md[isleap($y)-0][$m] + 1;
  $m += 1;
  return strcat($y, '-', str_pad_left($m, 2, '0'),
                    '-', str_pad_left($d, 2, '0'));
}

function yd_to_ymd($d) {
  return ydp_to_ymd(substr($d, 0, 4), substr($d, 5, 3));
}

function yd_to_days($d) {
  return y_to_days(substr($d, 0, 4)) - 1 + 
         number(substr($d, 5, 3));
}

function yd_to_sd($d) {
  return num_to_sxg(yd_to_days($d));
}

function yd_to_sdf($d,$f) {
  return num_to_sxgf(yd_to_days($d),$f);
}

// convert epoch days or sexagesimal epoch days (sd) to ordinal date

function days_to_yd($d) {
  $d = date_create_timestamp(date_get_timestamp(date_create_ymd("1970-01-01")) + $d*86400);
  $y = date_get_full_year($d);
  $a = date_create_ymd(strcat($y,"-01-01"));
  return strcat($y, strcat("-", str_pad_left(1+floor((date_get_timestamp($d)-date_get_timestamp($a))/86400), 3, "0")));
}

function sd_to_yd($d) {
  return days_to_yd(sxg_to_num($d));
}

// -------------------------------------------------------------------
// compat as of 2011-143
function bimfromod($d) { return bim_from_od($d); }
function getnmstr($m) { return get_nm_str($m); }
function nmfromod($d) { return nm_from_od($d); }
function ymdptod($y,$m,$d) { return ymdp_to_d($y,$m,$d); }
function ymdptoyd($y,$m,$d) { return ymdp_to_yd($y,$m,$d); }
function ymdtoyd($d) { return ymd_to_yd($d); }
function ymdtodays($d) { return ymd_to_days($d); }
function ymdtosd($d) { return ymd_to_sd($d); }
function ymdtosdf($d,$f) { return ymd_to_sdf($d, $f); }
function ydtodays($d) { return yd_to_days($d); }
function ydtosd($d) { return yd_to_sd($d); }
function ydtosdf($d,$f) { return yd_to_sdf($d, $f); }
function daystoyd($d) { return days_to_yd($d); }
function sdtoyd($d) { return sd_to_yd($d); }

/* end epochdays */


/* ------------------------------------------------------------------ */


/* webaddress */

function web_address_to_uri($wa, $addhttp) {
  if ($wa=='' || (substr($wa, 0,7) == "http://") || (substr($wa, 0,8) == "https://") || (substr($wa, 0,6) == "irc://")) {
    return $wa;
  }
  if ((substr($wa, 0,7) == "Http://") || (substr($wa, 0,8) == "Https://")) { // handle iPad overcapitalization of input entries
    return strcat('h', substr($wa,1,strlen($wa)));
  }
  
  if (substr($wa,0,1) == "@") {
    return strcat("https://twitter.com/",substr($wa,1,strlen($wa)));
  }

  if ($addhttp) {
    $wa = strcat("http://",$wa);
  }
  return $wa;
}

function uri_clean($uri) {
  $uri = web_address_to_uri($uri, false);
  // prune the optional http:// for a neater param
  if (substr($uri, 0, 7) === 'http://') {
    $uri = explode('://', $uri);
    $uri = array_slice($uri, 1);
    $uri = implode('://', $uri);
  }
  // URL encode
  return str_ireplace("%3A",":",
                      str_ireplace("%2F","/",rawurlencode($uri)));
}

function protocol_of_uri($uri) {
  if (offset(':', $uri) === 0) { return ""; }
  $uri = explode(':', $uri, 2);
  if (!ctype_uri_scheme($uri[0])) { return ""; }
  return strcat($uri[0], ':');
}

function hostname_of_uri($uri) {
  $uri = explode('/', $uri, 4);
  if (count($uri) > 2) {
    $uri = $uri[2];
    if (offset(':', $uri) !== 0) {
      $uri = explode(':', $uri, 2);
      $uri = $uri[0];
    }
    return $uri;
  }   
  return "";
}

function sld_of_uri($uri) {
  $uri = hostname_of_uri($uri);
  $uri = explode('.', $uri);
  if (count($uri) > 1) {
    return $uri[count($uri) - 2];
  }
  return "";
}

function path_of_uri($uri) {
  $uri = explode('/', $uri);
  if (count($uri) > 3) {
    $uri = array_slice($uri, 3);
    $uri = strcat('/', implode('/', $uri));
    if (offset('?', $uri) !== 0) {
      $uri = explode('?', $uri, 2);
      $uri = $uri[0];
    }
    if (offset('#', $uri) !== 0) {
      $uri = explode('#', $uri, 2);
      $uri = $uri[0];
    }
    return $uri;    
  }
  return '/';
}

function prepath_of_uri($uri) {
  $uri = explode('/', $uri);
  $uri = array_slice($uri, 0, 3);
  return implode('/', $uri);
}

function is_http_uri($uri) {
  $uri = explode(':', $uri, 2);
  return !!strncmp($uri[0], 'http', 4);
}

function get_absolute_uri($uri,$base) {
  if (protocol_of_uri($uri) != "") { return $uri; }
  if (substr($uri, 0, 2) === '//') { 
    return strcat(protocol_of_uri($base), $uri);
  }
  if (substr($uri, 0, 1) === '/') {
    return strcat(prepath_of_uri($base), $uri);
  }
  // TBI # relative
  return strcat(prepath_of_uri($base), path_of_uri($base), $uri);
}

// -------------------------------------------------------------------
// compat as of 2011-149
function webaddresstouri($wa, $addhttp) { 
  return web_address_to_uri($wa, $addhttp);
}
function uriclean($uri) { return uri_clean($uri); }

function vcpdtreadable($d) { return vcp_dt_readable($d); }

/* end webaddress */


/* HTTP related */

function is_html_type($ct) {
  $ct = explode(';', $ct, 2);
  $ct = $ct[0];
  return ($ct === 'text/html' || $ct === 'application/xhtml+xml');
}

/* */


/* ------------------------------------------------------------------ */


/* hexatridecimal */

function numtohxt($n) {
 $s = "";
 $m = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
 if ($n===undefined || $n===0) { return "0"; }
 while ($n>0) {
   $d = $n % 36;
   $s = strcat($m[$d],$s);
   $n = ($n-$d)/36;
 }
 return $s;
}

function numtohxtf($n,$f) {
 if ($f===undefined) { $f=1; }
 return str_pad_left(numtohxt($n), $f, "0");
}

function hxttonum($h) {
 $n = 0;
 $j = strlen($h);
 for ($i=0;$i<$j;$i++) { // iterate from first to last char of $h
   $c = ord($h[$i]); //  put current ASCII of char into $c  
   if ($c>=48 && $c<=57) { $c=$c-48; } // 0-9
   else if ($c>=65 && $c<=90) { $c-=55; } // A-Z
   else if ($c>=97 && $c<=122) { $c-=87; } // a-z case-insensitive treat as A-Z
   else { $c = 0; } // treat all other noise as 0
   $n = 36*$n + $c;
 }
 return $n;
}

/* end hexatridecimal */


/* ------------------------------------------------------------------ */


/* ISBN-10 */

function numtoisbn10($n) {
 $n=string($n);
 $d=0;
 $f=2;
 for ($i=strlen($n)-1;$i>=0;$i--) {
  $d += $n[$i]*$f;
  $f++;  
 }
 $d = 11-($d % 11);
 if ($d==10) {$d="X";}
 else if ($d==11) {$d="0";}
 else {$d=string($d);}
 return strcat(str_pad_left($n,9,"0"),$d);
}
/* end ISBN-10 */


/* ------------------------------------------------------------------ */


/* ASIN */

function asintorsxg($a) { // ASIN to reversible sexagesimal; prefix ISBN-10 w ~
 $a = amazontoasin($a); // extract ASIN from Amazon URL if necessary
 if ($a[0]=='B') {
   $a=num_to_sxg(hxttonum(substr($a,1,9)));
 }
 else {
   $a = implode("",explode("-",$a)); // eliminate presentational hyphens
   if (strlen($a)>10 && substr($a,0,3)=="978") {
     $a = substr($a,3,9);
   }
   else {
     $a = substr($a,0,9);
   }
   $a = strcat("~",num_to_sxg($a));
 }
 return $a;
}

function amazontoasin($a) {
 // idempotent
 if (preg_match("/[\.\/]+/",$a)) {
   $a = explode("/",$a);
   for ($i=count($a)-1; $i>=0; $i--) {
     if (preg_match("/^[0-9A-Za-z]{10}$/",$a[$i])) {
       $a = $a[$i];
       break;
     }
   }
   if ($i==-1) { // no ASIN was found in URL
     $a=""; // reset $a to a string (instead of an array)
   }
 }
 return $a;
}

/* end ASIN */


/* ------------------------------------------------------------------ */


/* HyperTalk */

function trunc($n) { /* just an alias from BASIC days */
 return floor($n);
}

function offset($n, $h) {
 $n = strpos($h, $n);
 if ($n===false) { return 0; }
 else            { return $n+1; }
}

function contains($h, $n) {
 // actual HT syntax: haystack contains needle, e.g. if ("abc" contains "b")
 return !(strpos($h, $n)===false);
}

function last_character_of($s) {
  return strlen($s)>0 ? $s[strlen($s)-1] : '';
}
/* end HyperTalk */


/* ------------------------------------------------------------------ */


/* XPath */

function xphasclass($s) {
  return strcat("//*[contains(concat(' ',@class,' '),' ",$s," ')]");
}

function xprhasclass($s) {
  return strcat(".//*[contains(concat(' ',@class,' '),' ",$s," ')]");
}

function xphasid($s) {
  return strcat("//*[@id='",$s,"']");
}

function xpattrstartswith($a,$s) {
  return strcat("//*[starts-with(@",$a,",'",$s,"')]");
}

function xphasrel($s) {
  return strcat("//*[contains(concat(' ',@rel,' '),' ",$s," ')]");
}

function xprhasrel($s) {
  return strcat(".//*[contains(concat(' ',@rel,' '),' ",$s," ')]");
}

function xprattrstartswithhasrel($a,$s,$r) {
  return strcat(".//*[contains(concat(' ',@rel,' '),' ",$r," ') and starts-with(@",$a,",'",$s,"')]");
}

function xprattrstartswithhasclass($a,$s,$c) {
  return strcat(".//*[contains(concat(' ',@class,' '),' ",$c," ') and starts-with(@",$a,",'",$s,"')]");
}

/* end XPath */


/* ------------------------------------------------------------------ */


/* microformats */

/* value class pattern readable date time from ISO8601 datetime */
function vcp_dt_readable($d) {
  $d = explode("T", $d);                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
  $r = "";
  if (count($d)>1) { 
     $r = explode("-", $d[1]);
     if (count($d)==1) {
			 $r = explode("+", $d[1]);
     }
     if (count($d)>1) {
       $r = strcat('<time class="value" datetime="',$d[1],'">', 
                   $r[0],'</time> on ');
     }
     else {
			 $r = strcat('<time class="value">',$d[1],'</time> on ');
     }
  }
  return strcat($r,'<time class="value">',$d[0],'</time>');
}

/* end microformats */


/* ------------------------------------------------------------------ */


/* Whistle */

// algorithmic URL shortener core
// YYYY/DDD/tnnn to tdddss 
// ordinal date, type, decimal #, to sexagesimal epoch days, sexagesimal #
function whistle_short_path($p) {
  return strcat(substr($p,9,1),
                ((substr($p,9,1)!='t') ? "/" : ""),
                yd_to_sdf(substr($p,0,8),3),
                num_to_sxg(substr($p,10,3)));
}
/* end Whistle */


/* ------------------------------------------------------------------ */


/* Falcon */

function html_unesc_amp_only($s) {
  return str_ireplace('&amp;','&',$s);
}

function html_esc_amper_once($s) {
  return str_ireplace('&','&amp;',html_unesc_amp_only($s));
}

function html_esc_amp_ang($s) {
  return str_ireplace('<','&lt;',
          str_ireplace('>','&gt;',html_esc_amper_once($s)));
}

function ellipsize_to_word($s, $max, $e, $min) {
  if (strlen($s)<=$max) {
    return $s; // no need to ellipsize
  }

  $elen = strlen($e);
  $slen = $max-$elen;

  // if last characters before $max+1 are ': ', truncate w/o ellipsis.
  // no need to take length of ellipsis into account
  if ($e=='...') {
    for ($ii=1;$ii<=$elen+1;$ii++) {
      if (substr($s,$max-$ii,2)==': ') {
        return substr($s,0,$max-$ii+1);
      }
    }
  }

  if ($min) {
    // if a non-zero minimum is provided, then
    // find previous space or word punctuation to break at.
    // do not break at %`'"&.!?^ - reasons why to be documented.
    while ($slen>$min && !contains('@$ -~*()_+[]\{}|;,<>',$s[$slen-1])) {
      --$slen;
    }
  }
  // at this point we've got a min length string, 
  // only do minimum trimming necessary to avoid punctuation error.
  
  // trim slash after colon or slash
  if ($s[$slen-1]=='/' && $slen > 2) {
    if ($s[$slen-2]==':') {
      --$slen;    
    }
    if ($s[$slen-2]=='/') {
      $slen -= 2;
    }
  }

  //if trimmed at a ":" in a URL, trim the whole thing
    //or trimmed at "http", trim the whole URL
  if ($s[$slen-1]==':' && $slen > 5 && substr($s,$slen-5,5)=='http:') {
    $slen -= 5;
  }
  else if ($s[$slen-1]=='p' && $slen > 4 && substr($s,$slen-4,4)=='http') {
    $slen -= 4;
  }
  else if ($s[$slen-1]=='t' && $slen > 4 && (substr($s,$slen-3,4)=='http' || substr($s,$slen-3,4)==' htt')) {
    $slen -= 3;
  }
  else if ($s[$slen-1]=='h' && $slen > 4 && substr($s,$slen-1,4)=='http') {
    $slen -= 1;
  }
  
  // if char immed before ellipsis would be @$ then trim it as well
  if ($slen > 0 && contains('@$',$s[$slen-1])) {
    --$slen;
  }
 
  // while char immed before ellipsis would be sentence terminator, trim 2 more
  while ($slen > 1 && contains('.!?',$s[$slen-1])) {
    $slen-=2;
  }

  // trim extra whitespace before ellipsis down to one space
  if ($slen > 2 && contains("\n ",$s[$slen-1])) {
    while (contains("\n ",$s[$slen-2]) && $slen > 2) {
      --$slen;
    }
  }

  if ($slen < 1) { // somehow shortened too much
    return $e; // or ellipsis by itself filled/exceeded max, return ellipsis.
  }

  // if last two chars are ': ', omit ellipsis. 
  if ($e=='...' && substr($s,$slen-2,2)==': ') {
    return substr($s,0,$slen);
  }

  return strcat(substr($s,0,$slen),$e);
}

function auto_link_re() {
  return '/(?:\\@[_a-zA-Z0-9]{1,17})|(?:(?:(?:(?:http|https|irc)?:\\/\\/(?:(?:[!$&-.0-9;=?A-Z_a-z]|(?:\\%[a-fA-F0-9]{2}))+(?:\\:(?:[!$&-.0-9;=?A-Z_a-z]|(?:\\%[a-fA-F0-9]{2}))+)?\\@)?)?(?:(?:(?:[a-zA-Z0-9][-a-zA-Z0-9]*\\.)+(?:(?:aero|arpa|asia|a[cdefgilmnoqrstuwxz])|(?:biz|b[abdefghijmnorstvwyz])|(?:cat|com|coop|c[acdfghiklmnoruvxyz])|d[ejkmoz]|(?:edu|e[cegrstu])|f[ijkmor]|(?:gov|g[abdefghilmnpqrstuwy])|h[kmnrtu]|(?:info|int|i[delmnoqrst])|j[emop]|k[eghimnrwyz]|l[abcikrstuvy]|(?:mil|museum|m[acdeghklmnopqrstuvwxyz])|(?:name|net|n[acefgilopruz])|(?:org|om)|(?:pro|p[aefghklmnrstwy])|qa|r[eouw]|s[abcdeghijklmnortuvyz]|(?:tel|travel|t[cdfghjklmnoprtvwz])|u[agkmsyz]|v[aceginu]|w[fs]|y[etu]|z[amw]))|(?:(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[1-9])\\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[0-9])\\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[0-9])\\.(?:25[0-5]|2[0-4][0-9]|[0-1][0-9]{2}|[1-9][0-9]|[0-9])))(?:\\:\\d{1,5})?)(?:\\/(?:(?:[!#&-;=?-Z_a-z~])|(?:\\%[a-fA-F0-9]{2}))*)?)(?=\\b|\\s|$)/';
  // ccTLD compressed regular expression clauses (re)created.
  // .mobi .jobs deliberately excluded to discourage layer violations.
  // see http://flic.kr/p/2kmuSL for more on the problematic new gTLDs
  // part of $re derived from Android Open Source Project, Apache 2.0
  // with a bunch of subsequent fixes/improvements (e.g. ttk.me/t44H2)
  // thus auto_link_re is also Apache 2.0 licensed
  //  http://www.apache.org/licenses/LICENSE-2.0
  // - Tantek 2010-046 (moved to auto_link_re 2012-062)
}

// auto_link: param 1: text; 
//  optional: param 2: do embeds or not (false),
//            param 3: do auto_links or not (true)
// auto_link is idempotent, works on plain text or typical markup.
function auto_link(/*$t*/) {
  $isjs = js();
  $args = $isjs ? arguments : func_get_args();
  if (count($args) == 0) {
    return '';
  }
  $t = $args[0];
  $do_embed = (count($args) > 1) && ($args[1]!==false);
  $do_link = (count($args) < 3) || ($args[2]!==false);
  $re = auto_link_re();
  $ms = preg_matches($re,$t);
  if (!$ms) {
    return $t;
  }

  $mlen = count($ms);
  $sp = preg_split($re,$t);
  $t = "";
  $sp[0] = string($sp[0]); // force undefined to ""
  for ($i=0;$i<$mlen;$i++) {
    $mi = $ms[$i];
    $spliti = $sp[$i];
    $t = strcat($t, $spliti);
    $sp[$i+1] = string($sp[$i+1]); // force undefined to ""
    if (substr($sp[$i+1],0,1)=='/') { // regex omits end slash before </a
      $sp[$i+1] = substr($sp[$i+1],1,strlen($sp[$i+1])-1);
      $mi = strcat($mi, '/'); // explicitly include it in the match
    }
    $spe = substr($spliti,-2,2);
    // avoid 2x-linking, don't link CSS @-rules, attr values, asciibet
    if ((!$spe || !preg_match('/(?:\\=[\\"\\\']?|t;)/', $spe)) &&
        substr(trim($sp[$i+1]), 0, 3)!='</a' && 
        (!contains('@charset@font@font-face@import@media@namespace@page@ABCDEFGHIJKLMNOPQ@',
                   strcat($mi, '@'))))
    {
      $afterlink = '';
      $afterchar = substr($mi, -1, 1);
      while (contains('.!?,;"\')]}', $afterchar) && // trim punctuation from end
          ($afterchar!=')' || !contains($mi, '('))) { // allow one paren pair
          $afterlink = strcat($afterchar, $afterlink);
          $mi = substr($mi, 0, -1);
          $afterchar = substr($mi, -1, 1);
      }
      
      $fe = 0;
      if ($do_embed) {
         $fe = strtolower(
                (substr($mi, -4, 1) === '.') ? substr($mi, -4, 4) 
                                             : substr($mi, -5, 5));
      }
      $wmi = web_address_to_uri($mi, true);
      $prot = protocol_of_uri($wmi);
      $hn = hostname_of_uri($wmi);
      $pa = path_of_uri($wmi);
      $ih = is_http_uri($wmi);

      $ahref = '<span class="figure" style="text-align:left">';
      $enda = '</span>';
			if ($do_link) {
        $ahref = strcat('<a class="auto-link figure" href="',      
                        $wmi, '">');
        $enda = '</a>';
      }
      if ($fe && 
          ($fe === '.jpeg' || $fe === '.jpg' || $fe === '.png' || $fe === '.gif'))
      {
        $alt = strcat('a ',
                      (offset('photo', $mi)!=0) ? 'photo' 
                                                : substr($fe, 1));
        $t = strcat($t, $ahref, '<img class="auto-embed" alt="', 
                    $alt, '" src="', $wmi, '"/>', $enda, $afterlink);
      } else if ($fe && 
                 ($fe === '.mp4' || $fe === '.mov' || 
                  $fe === '.ogv' || $fe === '.webm'))
      {
        $t = strcat($t, $ahref, '<video class="auto-embed" ',
                    'controls="controls" src="', $wmi, '"></video>',
                    $enda, $afterlink);
      } else if ($hn === 'vimeo.com' 
                     && ctype_digit(substr($pa, 1)))
      {
				if ($do_link) {
				  $t = strcat($t, '<a class="auto-link" href="',
                      $wmi, '">', $mi, '</a> ');
				}

        $t = strcat($t, '<iframe class="vimeo-player auto-embed figure" width="480" height="385" style="border:0" src="', $prot, '//player.vimeo.com/video/', 
                    substr($pa, 1), '"></iframe>', 
                    $afterlink);
      } else if ($hn === 'youtu.be' ||
                (($hn === 'youtube.com' || $hn === 'www.youtube.com')
                 && ($yvid = offset('watch?v=', $mi)) !== 0))
      {
        if ($hn === 'youtu.be') {
          $yvid = substr($pa, 1);
        }
        else {
          $yvid = explode('&', substr($mi, $yvid+7));
          $yvid = $yvid[0];
        }
				if ($do_link) {
  				$t = strcat($t, '<a class="auto-link" href="',
                      $wmi, '">', $mi, '</a> ');
        }
        $t = strcat($t, '<iframe class="youtube-player auto-embed figure" width="480" height="385" style="border:0"  src="', $prot, '//www.youtube.com/embed/', 
                    $yvid, '"></iframe>', 
                    $afterlink);
      } else if ($mi[0] === '@' && $do_link) {
        if ($sp[$i+1][0] === '.' && 
            $spliti != '' &&
            ctype_email_local(substr($spliti, -1, 1))) {
          // if email address, simply append info, no linking
          $t = strcat($t, $mi, $afterlink);
        }
        else {
          // treat it as a Twitter @-username reference and link it
          $t = strcat($t, '<a class="auto-link h-x-username" href="',
                      $wmi, '">', $mi, '</a>', 
                      $afterlink);
        }           
      } else if ($do_link) {
        $t = strcat($t, '<a class="auto-link" href="',
                    $wmi, '">', $mi, '</a>', 
                    $afterlink);
      } else {
        $t = strcat($t, $mi, $afterlink);
      }
    } else {
      $t = strcat($t, $mi);
    }
  }
  return strcat($t, $sp[$mlen]);
}


function get_in_reply_to_urls($s) {
  // returns array of URLs after literal "in-reply-to:" in text
  $s = explode('in-reply-to: ', $s);
  $irtn = count($s);
  if ($irtn < 2) { return array(); }
  $r = array();
  $re = auto_link_re();
  for ($i=1; $i<$irtn; $i++) {
    // iterate through all strings after an 'in-reply-to: ' for URLs
    $ms = preg_matches($re, $s[$i]);
    $msn = count($ms);
    if ($ms) {
      $sp = preg_split($re, $s[$i]);
      $j = 0;
      $afterlink = '';
      while ($j<$msn && 
             $afterlink == '' &&
             ($sp[$j] == '' || ctype_space($sp[$j]))) {
        // iterate through space separated URLs and add them to $r
        $m = $ms[$j];
        if ($m[0] != '@') { // skip @-references
          $ac = substr($m, -1, 1);
          while (contains('.!?,;"\')]}', $ac) && // trim punc @ end
              ($ac != ')' || !contains($m, '('))) { 
              // allow one paren pair
              // *** not sure twitter is this smart
              $afterlink = strcat($ac, $afterlink);
              $m = substr($m, 0, -1);
              $ac = substr($m, -1, 1);
          }
          if (substr($m, 0, 6) === 'irc://') { 
            // skip it. no known use of in-reply-to an IRC URL
          } else {
            $r[count($r)] = web_address_to_uri($m, true);
          }
        }
        $j++;
      }
    }
  } 
  return $r;
}

/* Twitter POSSE support */

function tw_text_proxy($t) {
  // replace URLs with http://j.mp/0011235813 to mimic Twitter's t.co
  // $t must be plain text
  $re = auto_link_re();
  $ms = preg_matches($re, $t);
  if (!$ms) {
    return $t;
  }

  $mlen = count($ms);
  $sp = preg_split($re, $t);
  $t = "";
  $sp[0] = string($sp[0]); // force undefined to ""
  for ($i=0;$i<$mlen;$i++) {
    $mi = $ms[$i];
    $spliti = $sp[$i];
    $t = strcat($t, $spliti);
    $sp[$i+1] = string($sp[$i+1]); // force undefined to ""
    if (substr($sp[$i+1],0,1)=='/') { // regex omits '/' before </a
      $sp[$i+1] = substr($sp[$i+1],1,strlen($sp[$i+1])-1);
      $mi = strcat($mi, '/'); // explicitly include it in match
    }
    $spe = substr($spliti,-2,2);
    // don't proxy @-names, plain ccTLDs
    if ($mi[0] !== '@' &&
        (substr($mi, -3, 1) !== '.' || substr_count($mi, '.') > 1)) {
      $afterlink = '';
      $afterchar = substr($mi, -1, 1);
      while (contains('.!?,;"\')]}',$afterchar) && // trim punc @ end
          ($afterchar!=')' || !contains($mi, '('))) { 
          // allow one paren pair
          // *** not sure twitter is this smart
          $afterlink = strcat($afterchar,$afterlink);
          $mi = substr($mi,0,-1);
          $afterchar = substr($mi,-1,1);
      }
      
      $prot = protocol_of_uri($mi);
      $proxy_url = '';
      if ($prot === 'https:') { 
        $proxy_url = 'https://j.mp/0011235813';
      } 
      else if ($prot==='irc:') {
        $proxy_url = $mi; // Twitter doesn't tco irc: URLs
      }
      else { /* 'http:/' or presumed for schemeless URLs */ 
        $proxy_url = 'http://j.mp/0011235813';
      }
      $t = strcat($t, $proxy_url, $afterlink);
    }
    else {
      $t = strcat($t, $mi);
    }
  }
  return strcat($t, $sp[$mlen]);
}


function note_length_check($note, $maxlen, $username) {
// checks to see if $note fits in $maxlen characters.
// if $username is non-empty, checks to see if a RT'd $note fits in $maxlen
// 0 - bad params or other precondition failure error
// 200 - exactly fits max characters with RT if username provided
// 206 - less than max chars with RT if username provided
// 207 - more than RT safe length, but less than tweet max
// 208 - tweet max length but with RT would be over
// 413 - (entity too large) over max tweet length
// strlen('RT @: ') == 6.
  if ($maxlen < 1) return 0;
  
  $note_size_check_u = $username ? 6 + strlen(string($username)) : 0;
  $note_size_check_n = strlen(string($note)) + $note_size_check_u;
  
  if ($note_size_check_n == $maxlen)                      return 200;
  if ($note_size_check_n < $maxlen)                       return 206;
  if ($note_size_check_n - $note_size_check_u < $maxlen)  return 207;
  if ($note_size_check_n - $note_size_check_u == $maxlen) return 208;
  return 413;
}

function tw_length_check($t, $maxlen, $username) {
  return note_length_check(tw_text_proxy($t), 
                           $maxlen, $username);
}

function tw_url_to_status_id($u) {
// $u - tweet permalink url
// returns tweet status id string; 0 if not a tweet permalink.
  if (!$u) return 0;
  $u = explode("/", string($u)); // https:,,twitter.com,t,status,nnn
  if ($u[2] != "twitter.com" || 
      $u[4] != "status"      ||
      !ctype_digit($u[5])) {
    return 0;
  }
  return $u[5];
}

function tw_url_to_username($u) {
// $u - tweet permalink url
// returns twitter username; 0 if not a tweet permalink.
  if (!$u) return 0;
  $u = explode("/", string($u)); // https:,,twitter.com,t,status,nnn
  if ($u[2] != "twitter.com" || 
      $u[4] != "status"      ||
      !ctype_digit($u[5])) {
    return 0;
  }
  return $u[3];
}

function fb_url_to_event_id($u) {
// $u - fb event permalink url
// returns fb event id string; 0 if not a fb event permalink.
  if (!$u) return 0;
  $u = explode("/", string($u)); // https:,,fb.com,events,nnn
  if (($u[2] != "fb.com" && $u[2] != "facebook.com" && 
       $u[2] != "www.facebook.com") || 
      $u[3] != "events"      ||
      !ctype_digit($u[4])) {
    return 0;
  }
  return $u[4];
}

/* end Falcon */


/* ------------------------------------------------------------------ */

/* end cassis.js */
// ?> -->