/*
 * Put a self-updating countdown inside the element, 
 * and reload page without cache when it reaches zero.  
 */
page_reload_countdown = function(element, timeout) {
	t0 = (new Date()).getTime() + timeout;
	window.setInterval(function(element, t0) {
		var now = (new Date()).getTime();
		var timeout = Math.floor(Math.max(0, (t0 - now) / 1000));
		$(element).html(page_reload_countdown.msg(timeout));
	}, 250, element, t0);
	window.setTimeout(function(element) { location.reload(true); }, timeout);
}
page_reload_countdown.msg = function (timeout) { return "This page will automatically reload in <b>" + timeout + "</b> seconds." }

/*
 * Find the element 'find' that shares and ancestor 
 * 'closest' with obj and toggle its display attribute.
 *
 * Since bootstrap overrides the hidden class with !important, we have to first
 * remove that class before doing anything else.
 */
toggle_display = function(obj, closest, find) {
    hiddenObject = $(obj).closest(closest)
    if ( find ) {
        hiddenObject = hiddenObject.find(find)
    }
    if ( hiddenObject.hasClass("hidden") ) {
        hiddenObject.removeClass("hidden").hide()
    }
    hiddenObject.toggle("fast");
}
