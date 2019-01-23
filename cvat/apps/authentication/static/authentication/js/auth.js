"use strict";


window.onload = function() {
    let mysterious_key = null;
    $.getJSON("https://api.ipify.org?format=jsonp&callback=?",
      function(json) {
        mysterious_key = json.ip;
        mysterious_key = md5(mysterious_key);
        $('#mysterious_key').prop('value', mysterious_key);
      }
    );
};